"""Cycle #148.2 (2026-05-18 sera) — spawn one Claude Code background agent.

Wraps ``claude --bg`` with arguments composed from an :class:`AgentSpec`.
Captures stdout, parses the short session ID, returns a :class:`SpawnResult`.
The orchestrator stores the SpawnResult so it can later attach/logs/stop
the session and so the HippoAgent bridge can mirror messages to memory.

Empirical evidence (Fase 0, smoke test session d3ffcf29):
    Starting background service…
    backgrounded · d3ffcf29
      claude agents             list sessions
      claude attach d3ffcf29    open in this terminal
      ...

Short ID regex: ``backgrounded\\s*[·.]\\s*([a-f0-9]{8})``.

Environment variable ``CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`` is
forced ON for every spawned session so inter-agent ``SendMessage`` tool
is available. The env is composed from os.environ + the override so
existing user vars (e.g. ``HIPPO_DATA_DIR``) are preserved.
"""
from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from .._proc_quiet import quiet_popen_kwargs
from .schemas import AgentSpec

_SHORT_ID_RE = re.compile(
    r"backgrounded\s*[·.]\s*([a-f0-9]{8})",
    re.IGNORECASE,
)


class SpawnError(RuntimeError):
    """Raised when ``claude --bg`` exits non-zero or output is unparseable."""


@dataclass
class SpawnResult:
    """Outcome of a successful spawn."""

    short_id: str
    command: list[str]
    stdout: str
    spawned_at: float = field(default_factory=time.time)


def _compose_command(spec: AgentSpec, *, run_id: str) -> list[str]:
    """Build the exact argv to invoke ``claude --bg ...``.

    Order: flags first, prompt as last positional. The empirical Fase 0
    test confirmed the binary accepts this order without complaint.
    """
    cmd: list[str] = ["claude", "--bg"]

    # Display name = "<run_id>-<agent_name>" for grep-ability in
    # ``claude agents`` and ``claude logs``.
    cmd += ["--name", f"{run_id}-{spec.name}"]

    cmd += ["--model", spec.model]
    cmd += ["--max-budget-usd", str(spec.max_budget_usd)]
    cmd += ["--permission-mode", spec.permission_mode]

    if spec.worktree:
        # Empirical: ``-w`` short form accepted, named worktree slot.
        cmd += ["--worktree", f"{run_id}-{spec.name}"]

    if spec.bare:
        cmd += ["--bare"]

    if spec.allowed_tools:
        # ``--allowedTools`` accepts a single comma- or space-separated
        # arg; we join with commas for deterministic shell parsing.
        cmd += ["--allowedTools", ",".join(spec.allowed_tools)]

    if spec.max_turns is not None:
        cmd += ["--max-turns", str(spec.max_turns)]

    if spec.cwd:
        # Note: ``claude --bg`` runs in the current cwd of the spawning
        # shell. We pass ``--add-dir`` so the agent has read+write access
        # to its own target directory even if it sits outside cwd.
        cmd += ["--add-dir", spec.cwd]

    # Positional prompt — LAST so flags are unambiguous.
    cmd += [spec.prompt]
    return cmd


def _compose_env(env_overrides: dict | None = None) -> dict:
    """Inherit os.environ then force the agent-teams flag on.

    Caller-supplied ``env_overrides`` apply on top so tests can stub.
    """
    env = dict(os.environ)
    env["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"] = "1"
    if env_overrides:
        env.update(env_overrides)
    return env


def spawn_agent(
    spec: AgentSpec,
    *,
    run_id: str,
    swarm_cwd: Path | None = None,
    env_overrides: dict | None = None,
    timeout_sec: float = 60.0,
) -> SpawnResult:
    """Spawn one background agent. Blocks until ``claude --bg`` returns
    (typically <2s — it only schedules the daemon job and prints the ID).

    Raises :class:`SpawnError` if the subprocess returns non-zero or its
    stdout cannot be parsed for the short session id.
    """
    cmd = _compose_command(spec, run_id=run_id)
    env = _compose_env(env_overrides)
    cwd = str(swarm_cwd) if swarm_cwd else None

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
        timeout=timeout_sec,
        check=False,
        **quiet_popen_kwargs(),
    )

    if proc.returncode != 0:
        raise SpawnError(
            f"claude --bg exit {proc.returncode}: "
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}",
        )

    m = _SHORT_ID_RE.search(proc.stdout)
    if not m:
        raise SpawnError(
            f"claude --bg produced no parseable session id. "
            f"stdout={proc.stdout!r}",
        )
    return SpawnResult(
        short_id=m.group(1),
        command=cmd,
        stdout=proc.stdout,
    )
