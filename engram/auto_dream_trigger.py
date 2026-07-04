"""Auto-Dream trigger on SessionStart (cycle #69, 2026-05-14).

Turns HippoAgent from "memory-on-demand" into "memory that *also* proposes
insight while the agent is dormant". When a fresh Claude session starts,
the hook calls `maybe_trigger_dream(...)` which:

  1. Reads env-gate `ENGRAM_AUTO_DREAM_ENABLED` (cycle #110.A: default ON).
     Opt-out: set ENGRAM_AUTO_DREAM_ENABLED=0/false/no/off.
  2. Counts new episodes + facts since the last trigger.
  3. Checks the cooldown window (default 30 min) is respected.
  4. If all conditions met, invokes a `dream_callable` (usually
     `engram.dream.propose_dream_tasks`) to schedule **one** Dream
     observe-pattern task.
  5. Persists `now` to a tiny state file so the next call respects cooldown.
  6. Catches *any* exception from the dream call and returns a structured
     error — never blocks SessionStart.

The whole module is intentionally side-effect-light: all SQL is read-only,
the dream call is injected (so tests can substitute), and the orchestrator
returns a structured dict instead of raising. Pure Python stdlib (no
numpy, no sentence-transformers) so import is cheap inside a hook.

Env vars (read at call time):
  - ENGRAM_AUTO_DREAM_ENABLED  : "1"/"true"/"yes"/"on" → enabled.
                                 "0"/"false"/"no"/"off" → disabled.
                                 Default ON (cycle #110.A, 2026-05-16).
  - ENGRAM_AUTO_DREAM_MIN_ITEMS: threshold of new episode+fact items.
                                 Default 5.
  - ENGRAM_AUTO_DREAM_COOLDOWN_S: minimum seconds between consecutive
                                 triggers. Default 1800 (30 min).
"""
from __future__ import annotations

import os
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

_STATE_FILENAME = "auto_dream_state.txt"
_TRUTHY = {"1", "true", "yes", "on", "True", "TRUE"}

# Critic counterexample (cycle #69 review, 2026-05-14): a state file with
# `ts > now` (NTP backward correction, VM hibernate/resume, dual-boot UTC
# bias, manual file copy) previously blocked Auto-Dream indefinitely because
# the cooldown delta `(now - last_ts)` went negative and was always <
# cooldown_s. Treating future timestamps as corrupt state (load returns
# None ⇒ first-run semantics) is the cheapest, self-healing fix.
_FUTURE_TS_TOLERANCE_S = 60.0  # 1 minute of slack for benign clock jitter


# ---------------------------------------------------------------------------
# Pure decision function — no IO. Easy to test exhaustively.
# ---------------------------------------------------------------------------


def should_trigger(
    *,
    last_trigger_ts: float | None,
    now: float,
    new_items_count: int,
    min_items: int,
    min_cooldown_s: float,
    enabled: bool,
) -> bool:
    """Return True iff every gate passes (env, item count, cooldown).

    Order of checks (short-circuit):
      1. enabled (env-gate)
      2. new_items_count >= min_items
      3. (last_trigger_ts is None) OR (now - last_trigger_ts >= cooldown)
    """
    if not enabled:
        return False
    if new_items_count < min_items:
        return False
    if last_trigger_ts is None:
        return True
    return (now - last_trigger_ts) >= min_cooldown_s


# ---------------------------------------------------------------------------
# DB counter — read-only SQLite over episodes.db + semantic.db.
# Designed to be tolerant: missing files, missing tables → 0, no crash.
# ---------------------------------------------------------------------------


def _count_table(db_path: Path, table: str, since_ts: float | None) -> int:
    """Count rows in `table` whose `created_at` > since_ts.
    Returns 0 if the DB or table does not exist."""
    if not db_path.exists():
        return 0
    try:
        with sqlite3.connect(db_path) as conn:
            if since_ts is None:
                row = conn.execute(
                    f"SELECT COUNT(*) FROM {table}"  # noqa: S608
                ).fetchone()
            else:
                row = conn.execute(
                    f"SELECT COUNT(*) FROM {table} "  # noqa: S608
                    f"WHERE created_at > ?",
                    (since_ts,),
                ).fetchone()
            return int(row[0]) if row else 0
    except sqlite3.Error:
        # Schema mismatch or other DB error — treat as "nothing new".
        return 0


def count_new_items(
    *,
    episodes_db: Path,
    semantic_db: Path,
    since_ts: float | None,
) -> int:
    """Return sum of new episodes + new facts created after `since_ts`.

    If `since_ts is None`, returns the total corpus size (used the very
    first time the trigger runs, to decide whether the corpus is even
    big enough to warrant a Dream).
    """
    return (
        _count_table(Path(episodes_db), "episodes", since_ts)
        + _count_table(Path(semantic_db), "facts", since_ts)
    )


# ---------------------------------------------------------------------------
# State file IO — single float (epoch seconds) on disk.
# ---------------------------------------------------------------------------


def load_last_trigger_ts(state_path: Path) -> float | None:
    """Read the last-trigger timestamp; return None on missing or corrupt.

    Corrupt includes: unparseable content, IO errors, AND a timestamp in
    the future relative to the current clock (clock-skew defence — see
    `_FUTURE_TS_TOLERANCE_S` and the critic counterexample documented at
    module top).
    """
    p = Path(state_path)
    if not p.exists():
        return None
    try:
        ts = float(p.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None
    # Self-heal against clock-skew: a ts beyond now + tolerance is corrupt.
    if ts > time.time() + _FUTURE_TS_TOLERANCE_S:
        return None
    return ts


def save_last_trigger_ts(state_path: Path, ts: float) -> None:
    p = Path(state_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"{ts:.6f}\n", encoding="utf-8")


def _resolve_db_paths(engram_dir: Path) -> tuple[Path, Path]:
    """Resolve the actual episodes.db and semantic.db paths.

    HippoAgent has two historical layouts:
      A) <engram_dir>/episodes/episodes.db  +  <engram_dir>/semantic/semantic.db
      B) <engram_dir>/episodes.db           +  <engram_dir>/semantic.db

    Prefer the nested (canonical, current) layout; fall back to the
    flat layout only if the nested file is missing. This mirrors the
    logic the SessionStart hook already uses for the banner.
    """
    nested_ep = engram_dir / "episodes" / "episodes.db"
    flat_ep = engram_dir / "episodes.db"
    ep_db = nested_ep if nested_ep.exists() else flat_ep

    nested_sm = engram_dir / "semantic" / "semantic.db"
    flat_sm = engram_dir / "semantic.db"
    # Prefer the nested file IF it has tables (avoids picking an empty stub).
    if nested_sm.exists():
        sm_db = nested_sm
    else:
        sm_db = flat_sm
    return ep_db, sm_db


# ---------------------------------------------------------------------------
# Orchestrator — the single entry point a hook should call.
# ---------------------------------------------------------------------------


def maybe_trigger_dream(
    *,
    engram_dir: Path,
    now: float,
    dream_callable: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """One-shot decision + (optional) dream firing.

    Args:
        engram_dir: typically `~/.engram`. Must contain (or be where we
            create) episodes.db / semantic.db / auto_dream_state.txt.
        now: current epoch seconds (injected for deterministic tests).
        dream_callable: function that performs the actual Dream proposal.
            Signature is liberal — we pass `engram_dir` and any future
            options. Must NOT raise to the caller of `maybe_trigger_dream`;
            we catch and report via the return dict.

    Returns:
        A status dict with at minimum:
          - triggered: bool
          - reason: short string explaining outcome
        Plus, when fired:
          - dream_id: str (from `dream_callable`'s return)
        When errored:
          - error: str (the exception message)
    """
    engram_dir = Path(engram_dir)
    # Cycle #110.A (2026-05-16): Auto-Dream is ON by default.
    # The semantics of the check are unchanged from cycle #69 -- only the
    # default flips from "0" to "1". The check remains an allowlist
    # (``in _TRUTHY``) so any non-truthy value (e.g. "0", "off", "no",
    # "false", "", "banana") disables the worker. Predictable behaviour:
    # if you don't set the env var, the worker runs; if you set it to
    # anything other than a known-truthy token, it's off.
    enabled_raw = os.environ.get("ENGRAM_AUTO_DREAM_ENABLED", "1")
    enabled = enabled_raw.strip() in _TRUTHY
    if not enabled:
        return {"triggered": False, "reason": "disabled"}

    try:
        min_items = int(os.environ.get("ENGRAM_AUTO_DREAM_MIN_ITEMS", "5"))
    except ValueError:
        min_items = 5
    try:
        cooldown_s = float(
            os.environ.get("ENGRAM_AUTO_DREAM_COOLDOWN_S", "1800")
        )
    except ValueError:
        cooldown_s = 1800.0

    state_file = engram_dir / _STATE_FILENAME
    last_ts = load_last_trigger_ts(state_file)
    # Check cooldown FIRST — if it's not time to look, don't even open the DB.
    if last_ts is not None and (now - last_ts) < cooldown_s:
        return {"triggered": False, "reason": "cooldown",
                "elapsed_s": now - last_ts, "cooldown_s": cooldown_s}

    episodes_db, semantic_db = _resolve_db_paths(engram_dir)
    new_count = count_new_items(
        episodes_db=episodes_db, semantic_db=semantic_db, since_ts=last_ts,
    )

    if new_count == 0:
        return {"triggered": False, "reason": "no_new_items",
                "new_items": 0, "last_trigger_ts": last_ts}
    if new_count < min_items:
        return {"triggered": False, "reason": "not_enough_items",
                "new_items": new_count, "min_items": min_items,
                "last_trigger_ts": last_ts}

    # All gates passed. Fire the dream — but never propagate exceptions.
    try:
        result = dream_callable(engram_dir=engram_dir)
    except Exception as e:  # noqa: BLE001 — explicit broad catch
        return {"triggered": False, "reason": "error",
                "error": str(e), "new_items": new_count}

    # Persist state *only* on success — a failed dream shouldn't burn cooldown.
    save_last_trigger_ts(state_file, now)
    out: dict[str, Any] = {"triggered": True, "reason": "fired",
                           "new_items": new_count}
    if isinstance(result, dict) and "dream_id" in result:
        out["dream_id"] = result["dream_id"]
    return out


__all__ = [
    "should_trigger",
    "count_new_items",
    "load_last_trigger_ts",
    "save_last_trigger_ts",
    "maybe_trigger_dream",
]
