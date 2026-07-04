"""HippoAgent SessionStart hook — inject memory context at every session start.

Runs at the moment Claude Code creates a session (CLI or desktop).
Stdout becomes "additional context" the model sees at turn 0, so the
host LLM knows the persistent memory is reachable AND has a snapshot
of the most recent facts + pinned episodes BEFORE the user types.

This is what makes HippoAgent feel like "always-on memory" rather than
"a tool I might call". The MCP server still has the full toolset for
on-demand recall — this hook just primes the context.

Designed to be FAST (< 50ms): pure SQLite reads, no ML/embedding load.
Errors are silent (we'd rather start the session without memory than
crash startup). All paths defensive.

Cycle #110.E (2026-05-16): after the banner, conditionally spawn the
background daemons (contradiction_scan, decay_run). Each is gated by
its own env var (default OFF, opt-in) and cooldown — see
``engram.daemon_runner.DEFAULT_DAEMONS``.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import time
from pathlib import Path


def _find_data_dir() -> Path | None:
    """Locate the HippoAgent data dir. Tries env var, then common
    locations (user home, the worktree path)."""
    # Cycle #41: data dir resolution honors ~/.engram (new) → ~/.hippoagent
    # (legacy) → worktree fallbacks. Env override priority: ENGRAM_DATA_DIR
    # → HIPPO_DATA_DIR (deprecated alias).
    candidates = [
        os.environ.get("ENGRAM_DATA_DIR"),
        os.environ.get("HIPPO_DATA_DIR"),
        str(Path.home() / ".engram" / "data"),
        str(Path.home() / ".hippoagent" / "data"),
    ]
    for c in candidates:
        if not c:
            continue
        p = Path(c)
        if (p / "episodes" / "episodes.db").exists():
            return p
        if (p / "semantic.db").exists():
            return p
    return None


def _safe_count(db: Path, table: str) -> int:
    try:
        with sqlite3.connect(str(db)) as conn:
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            return int(row[0]) if row else 0
    except Exception:
        return -1


def _safe_recent_facts(db: Path, limit: int = 8) -> list[tuple]:
    # Anti-laundering (2026-06-03): le promozioni conversational a basso-trust
    # (writer_role='conversational_promotion' non ancora 'verified') NON devono
    # affiorare nel banner come fossero conoscenza curata. Schema-tolerant: i DB
    # legacy senza writer_role/status ricadono sulla query non-filtrata (non hanno
    # comunque promozioni conversational, quel ruolo non esisteva).
    try:
        with sqlite3.connect(str(db)) as conn:
            try:
                return conn.execute(
                    "SELECT proposition, topic FROM facts "
                    "WHERE NOT (COALESCE(writer_role,'agent_inference') = "
                    "'conversational_promotion' "
                    "AND COALESCE(status,'model_claim') != 'verified') "
                    "ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
            except sqlite3.OperationalError:
                return conn.execute(
                    "SELECT proposition, topic FROM facts "
                    "ORDER BY created_at DESC LIMIT ?", (limit,)
                ).fetchall()
    except Exception:
        return []


def _safe_pinned_episodes(db: Path, limit: int = 5) -> list[tuple]:
    try:
        with sqlite3.connect(str(db)) as conn:
            # Tolerate older schemas without `pinned` column.
            try:
                return conn.execute(
                    "SELECT id, task_text FROM episodes WHERE pinned = 1 "
                    "LIMIT ?", (limit,)
                ).fetchall()
            except sqlite3.OperationalError:
                return []
    except Exception:
        return []


def _safe_recent_episodes(db: Path, limit: int = 5) -> list[tuple]:
    try:
        with sqlite3.connect(str(db)) as conn:
            return conn.execute(
                "SELECT id, task_text, outcome FROM episodes "
                "ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
    except Exception:
        return []


def _maybe_spawn_background_daemons(
    data_dir: Path,
) -> list[str]:
    """Cycle #110.E: opt-in background daemon launcher.

    Returns short human-readable lines for the banner. All failures
    are converted into a status line — we never raise out of the
    SessionStart hook. The repo root is needed because the daemon
    scripts live under ``scripts/`` and the hook may be invoked from
    an arbitrary cwd.
    """
    try:
        # Add the repo root to sys.path so we can import engram.* even
        # when the hook is invoked outside an installed venv.
        repo_root = Path(__file__).resolve().parent.parent
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from engram.daemon_runner import (
            DEFAULT_DAEMONS,
            maybe_spawn_all_default_daemons,
        )
        from engram.daemon_spawn import production_spawn
    except Exception as e:  # noqa: BLE001
        return [f"  (daemon runner import failed: {e})"]

    try:
        results = maybe_spawn_all_default_daemons(
            state_dir=data_dir,
            now=time.time(),
            spawn_callable=production_spawn,
        )
    except Exception as e:  # noqa: BLE001
        return [f"  (daemon orchestration crashed: {e})"]

    lines: list[str] = []
    for spec in DEFAULT_DAEMONS:
        status = results.get(spec.name, {})
        reason = status.get("reason", "unknown")
        if status.get("spawned"):
            pid = status.get("spawn_result", {}).get("pid", "?")
            lines.append(f"  {spec.name}: spawned (pid={pid})")
        else:
            lines.append(f"  {spec.name}: {reason}")
    return lines


def main() -> int:
    data_dir = _find_data_dir()
    if data_dir is None:
        # Memory not configured. Silent — don't pollute the session.
        return 0

    ep_db = data_dir / "episodes" / "episodes.db"
    # Try both legacy (data/semantic.db) and current (data/semantic/semantic.db)
    sem_db = data_dir / "semantic" / "semantic.db"
    if not sem_db.exists():
        sem_db = data_dir / "semantic.db"
    skills_dir = data_dir / "skills"

    ep_count = _safe_count(ep_db, "episodes")
    fact_count = _safe_count(sem_db, "facts")
    skill_count = (
        sum(1 for _ in skills_dir.glob("*.json")) if skills_dir.exists() else 0
    )

    facts = _safe_recent_facts(sem_db, limit=8)
    pinned = _safe_pinned_episodes(ep_db, limit=5)
    recent = _safe_recent_episodes(ep_db, limit=3)

    out = []
    out.append("=" * 70)
    out.append("HippoAgent persistent memory ACTIVE")
    out.append(f"  Data: {data_dir}")
    out.append(
        f"  Episodes: {ep_count}  |  Facts: {fact_count}  "
        f"|  Skills: {skill_count}"
    )

    if facts:
        out.append("")
        out.append("Recent facts you have stored (semantic memory):")
        for prop, topic in facts:
            topic_str = f"[{topic}] " if topic else ""
            out.append(f"  - {topic_str}{(prop or '')[:140]}")

    if pinned:
        out.append("")
        out.append("Pinned episodes (never decay — high priority):")
        for eid, task in pinned:
            out.append(f"  - {eid[:8]}: {(task or '')[:100]}")

    if recent:
        out.append("")
        out.append("Last 3 episodes:")
        for eid, task, outcome in recent:
            out.append(
                f"  - [{outcome}] {eid[:8]}: {(task or '')[:90]}"
            )

    # Cycle #110.E (2026-05-16): conditionally spawn background daemons
    # (contradiction_scan, decay_run). Default OFF; user enables via env
    # ENGRAM_CONTRADICTION_ENABLED / ENGRAM_DECAY_ENABLED.
    daemon_lines = _maybe_spawn_background_daemons(data_dir)
    if daemon_lines:
        out.append("")
        out.append("Background daemons (cycle 110.E, opt-in):")
        out.extend(daemon_lines)

    out.append("")
    out.append(
        "USE THIS MEMORY: when the user asks about 'memoria/ricordi/"
        "saved/stored', call mcp__hippoagent__hippo_facts_search or "
        "mcp__hippoagent__hippo_recall — DO NOT read CLAUDE.md / "
        "MEMORY.md unless explicitly asked. The 45 hippo_* tools are "
        "free in HOSTED MODE (no API extra cost)."
    )
    out.append("=" * 70)

    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
