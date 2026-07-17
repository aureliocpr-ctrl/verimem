"""Cycle #148.5 (2026-05-18 sera) — swarm lifecycle wrappers.

Thin shims around the native ``claude {stop,respawn,rm}`` commands that
add HippoAgent audit logging on a swarm chat topic. Every lifecycle
action becomes a chat fact, so the audit trail of who killed/restarted
what survives even after ``claude rm`` deletes the underlying state.

Plus ``list_swarm_sessions`` to discover all sessions belonging to a
given run by scanning ``~/.claude/jobs/`` and filtering on the display
name (which the spawner sets to ``<run_id>-<agent_name>``).
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from .._proc_quiet import quiet_popen_kwargs
from ..semantic import Fact, SemanticMemory


def _hhmmss() -> str:
    return time.strftime("%H:%M:%S", time.localtime())


def _default_jobs_dir() -> Path:
    return Path.home() / ".claude" / "jobs"


def _audit(
    *,
    action: str,
    short_id: str,
    ok: bool,
    topic: str,
    sm: SemanticMemory,
    agent_name: str,
    detail: str = "",
) -> str:
    status = "OK" if ok else "FAIL"
    proposition = (
        f"[swarm-{agent_name} @{_hhmmss()}] lifecycle {action} "
        f"session {short_id}: {status}{(' — ' + detail) if detail else ''}"
    )
    fact = Fact(
        proposition=proposition,
        topic=topic,
        confidence=1.0,
        verified_by=[f"claude:session:{short_id}", f"action:{action}"],
        status="model_claim",
    )
    sm.store(fact)
    return fact.id


def _run_claude(args: list[str]) -> tuple[bool, str, str]:
    """Run a 1-shot claude subcommand. Returns (ok, stdout, stderr)."""
    try:
        proc = subprocess.run(
            args, capture_output=True, text=True, timeout=30.0, check=False,
            **quiet_popen_kwargs(),
        )
    except subprocess.TimeoutExpired:
        return (False, "", "timeout")
    return (proc.returncode == 0, proc.stdout, proc.stderr)


def stop_session(
    short_id: str, *,
    topic: str, sm: SemanticMemory, agent_name: str,
) -> bool:
    ok, _, err = _run_claude(["claude", "stop", short_id])
    _audit(
        action="stop", short_id=short_id, ok=ok,
        topic=topic, sm=sm, agent_name=agent_name,
        detail=err.strip()[:120] if not ok else "",
    )
    return ok


def respawn_session(
    short_id: str, *,
    topic: str, sm: SemanticMemory, agent_name: str,
) -> bool:
    ok, _, err = _run_claude(["claude", "respawn", short_id])
    _audit(
        action="respawn", short_id=short_id, ok=ok,
        topic=topic, sm=sm, agent_name=agent_name,
        detail=err.strip()[:120] if not ok else "",
    )
    return ok


def remove_session(
    short_id: str, *,
    topic: str, sm: SemanticMemory, agent_name: str,
) -> bool:
    ok, _, err = _run_claude(["claude", "rm", short_id])
    _audit(
        action="rm", short_id=short_id, ok=ok,
        topic=topic, sm=sm, agent_name=agent_name,
        detail=err.strip()[:120] if not ok else "",
    )
    return ok


def list_swarm_sessions(
    run_id: str, *,
    jobs_dir: Path | None = None,
) -> list[str]:
    """Return short_ids of sessions whose state.json ``name`` starts with
    ``<run_id>-``. The empty run_id returns nothing (safety: never list
    "every" session by accident — that's a 'claude agents' concern).
    """
    if not run_id:
        return []
    base = jobs_dir or _default_jobs_dir()
    if not base.is_dir():
        return []
    prefix = f"{run_id}-"
    out: list[str] = []
    for p in sorted(base.iterdir()):
        if not p.is_dir():
            continue
        sj = p / "state.json"
        if not sj.is_file():
            continue
        try:
            raw = json.loads(sj.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        name = (raw.get("name") or "") if isinstance(raw, dict) else ""
        if name.startswith(prefix):
            out.append(p.name)
    return out
