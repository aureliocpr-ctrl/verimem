"""Cycle #110.E (2026-05-16) — generalized background-daemon spawner.

Cycle 110.B/C/D ha aggiunto 3 daemon idempotenti (contradiction_scan,
decay_run, legacy_audit) come CLI standalone. Cycle 110.E li rende
attivabili dal SessionStart hook con lo stesso pattern Auto-Dream
(cycle #69 / cycle #110.A): env-gate + cooldown + injected
spawn_callable, structured-dict return, **never raises**.

Default: OFF (opt-in). A future cycle può flippare default a ON.

Design notes
------------
* `DaemonSpec` is a frozen dataclass — registry rows in `DEFAULT_DAEMONS`
  are picked up by `maybe_spawn_all_default_daemons`.
* State is one tiny file per daemon under ``state_dir``: avoids any
  multi-daemon coordination problem (lock-free, idempotent, easy to
  garbage-collect by deleting the file).
* Spawn is "fire and forget" — we DON'T track the PID after launch.
  This is intentional: if a daemon crashes, the next call (after
  cooldown) tries again; we don't want a stale-PID file blocking
  recovery. Tests inject ``spawn_callable`` so no real subprocess
  fires under pytest.
* All paths use stdlib only (Path + sqlite-free). Importing this
  module is therefore as cheap as importing ``auto_dream_trigger``
  — safe to call from a SessionStart hook.
"""
from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_TRUTHY = {"1", "true", "yes", "on", "True", "TRUE"}
_FUTURE_TS_TOLERANCE_S = 60.0


# ---------------------------------------------------------------------------
# Spec dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DaemonSpec:
    name: str
    script_path: str
    env_gate: str
    cooldown_seconds: float
    extra_args: list[str] = field(default_factory=list)
    default_enabled: bool = False

    def state_filename(self) -> str:
        return f"daemon_{self.name}_last.txt"


# ---------------------------------------------------------------------------
# Env-gate helper (mirrors auto_dream_trigger semantic — allowlist of
# truthy tokens; anything else is OFF).
# ---------------------------------------------------------------------------


def _is_enabled(env_gate: str, default_enabled: bool) -> bool:
    raw = os.environ.get(env_gate)
    if raw is None:
        return default_enabled
    return raw.strip() in _TRUTHY


# ---------------------------------------------------------------------------
# State file IO — single epoch-second float per daemon.
# Mirror auto_dream_trigger.load_last_trigger_ts / save_last_trigger_ts
# but parameterized over the daemon name (different file per daemon).
# ---------------------------------------------------------------------------


def _load_last_ts(path: Path, *, now: float | None = None) -> float | None:
    """Read the last-spawn timestamp; ``None`` on missing / corrupt / future.

    ``now`` (epoch seconds) is the reference clock for the future-ts
    self-heal. Tests inject a deterministic ``now``; production callers
    pass ``time.time()``. Falling back to ``time.time()`` when ``now``
    is ``None`` keeps backward compatibility with ad-hoc callers.
    """
    if not path.exists():
        return None
    try:
        ts = float(path.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None
    ref = time.time() if now is None else now
    if ts > ref + _FUTURE_TS_TOLERANCE_S:
        return None
    return ts


def _save_last_ts(path: Path, ts: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{ts:.6f}\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Single-daemon orchestrator
# ---------------------------------------------------------------------------


def maybe_spawn_daemon(
    spec: DaemonSpec,
    *,
    state_dir: Path,
    now: float,
    spawn_callable: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Decide + (optionally) spawn one daemon. Never raises.

    Args:
        spec: which CLI to launch + its gating policy.
        state_dir: directory for per-daemon timestamp files (typically
            ``~/.engram``).
        now: current epoch seconds (injected for deterministic tests).
        spawn_callable: callable doing the actual spawn. Signature::

                spawn_callable(*, script_path: str,
                               extra_args: list[str]) -> dict

            Production wires this to a ``subprocess.Popen``-based helper.

    Returns:
        ``{"spawned": bool, "reason": str, ...}``. The cooldown is
        only burned if the spawn succeeds — a raising callable leaves
        the state file untouched.
    """
    if not _is_enabled(spec.env_gate, spec.default_enabled):
        return {"spawned": False, "reason": "disabled", "name": spec.name}

    state_path = Path(state_dir) / spec.state_filename()
    last_ts = _load_last_ts(state_path, now=now)
    if last_ts is not None and (now - last_ts) < spec.cooldown_seconds:
        return {
            "spawned": False, "reason": "cooldown", "name": spec.name,
            "elapsed_s": now - last_ts,
            "cooldown_s": spec.cooldown_seconds,
        }

    try:
        result = spawn_callable(
            script_path=spec.script_path,
            extra_args=list(spec.extra_args),
        )
    except Exception as e:  # noqa: BLE001 — explicit broad catch
        return {
            "spawned": False, "reason": "error", "name": spec.name,
            "error": str(e),
        }

    _save_last_ts(state_path, now)
    out: dict[str, Any] = {
        "spawned": True, "reason": "fired", "name": spec.name,
    }
    if isinstance(result, dict):
        out["spawn_result"] = result
    return out


# ---------------------------------------------------------------------------
# Built-in registry — cycle 110.B + 110.C daemons (cycle 110.D is
# report-only and excluded by design: a SessionStart hook should never
# emit a noisy audit report; the 815-bucket scan stays manual).
# ---------------------------------------------------------------------------


DEFAULT_DAEMONS: list[DaemonSpec] = [
    DaemonSpec(
        name="contradiction_scan",
        script_path="scripts/contradiction_scan.py",
        env_gate="ENGRAM_CONTRADICTION_ENABLED",
        # 6h cooldown: contradictions are slow-moving; once a day is
        # plenty. Quarter-day catches drift faster without thrashing.
        cooldown_seconds=21600.0,
        extra_args=["--json"],
        default_enabled=False,
    ),
    DaemonSpec(
        name="decay_run",
        script_path="scripts/decay_run.py",
        env_gate="ENGRAM_DECAY_ENABLED",
        # 24h cooldown: confidence decay is multiplicative — running
        # it more than once per day double-decays and erodes the
        # signal too fast.
        cooldown_seconds=86400.0,
        extra_args=["--json"],
        default_enabled=False,
    ),
]


def maybe_spawn_all_default_daemons(
    *,
    state_dir: Path,
    now: float,
    spawn_callable: Callable[..., dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Fan-out wrapper: try each ``DEFAULT_DAEMONS`` entry.

    Returns a dict keyed by daemon name; each value is the
    structured-dict from ``maybe_spawn_daemon``. Errors in one
    daemon never affect the others.
    """
    out: dict[str, dict[str, Any]] = {}
    for spec in DEFAULT_DAEMONS:
        out[spec.name] = maybe_spawn_daemon(
            spec, state_dir=state_dir, now=now,
            spawn_callable=spawn_callable,
        )
    return out


__all__ = [
    "DEFAULT_DAEMONS",
    "DaemonSpec",
    "maybe_spawn_all_default_daemons",
    "maybe_spawn_daemon",
]
