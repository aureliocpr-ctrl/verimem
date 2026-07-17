"""Single-instance guard — reap ORPHANED `engram mcp` server processes on startup.

Root cause of the recurring multi-minute "Engram froze on a save" incident
(2026-06-06, empirical via Win32_Process enumeration): Claude Code restarts spawn
a fresh `engram mcp` server each time, but the OLD ones are never reaped. They
pile up (6 observed simultaneously); each contends for CPU/disk and drives its own
embedding work, starving the live server's encode until a save blocks for minutes.

This module, called once at server startup, terminates sibling `engram mcp`
servers that are ORPHANED — their spawning client (Claude Code) is gone.

Multi-window SAFE: a sibling whose parent client is still alive is NEVER touched
(``psutil.Process.parent()`` validates ppid AND create_time, so a recycled PID is
not mistaken for a live parent). Detached embedding daemons are intentionally
excluded from the matcher (they have no live parent by design — single-instancing
them is the daemon's own job, via the encode_service reachability lock).

Best-effort: every failure path is swallowed — the guard must NEVER break server
startup, and psutil is optional.
"""
from __future__ import annotations

import os
import re

# Matches the engram MCP server in ALL its launch forms:
#   "<path>\verimem.exe" mcp   |   hippo mcp   |   engram mcp
# plus the explicit-module substring "verimem.mcp_server" (handled separately).
# Deliberately does NOT match the sibling processes that merely contain "mcp":
#   engram_bridge_mcp.py / clp_mcp_server.py / duo_bridge_mcp.py /
#   critic_orchestrator.mcp_server / verimem.encode_service / engram_embedding_daemon.py
#   (none has the `(engram|hippo)[.exe] <whitespace> mcp` token boundary).
_MCP_CMDLINE_RE = re.compile(
    r'(?:^|[\s"/\\])(?:engram|hippo)(?:\.exe)?["\']?\s+mcp(?:\s|$|["\'])',
    re.IGNORECASE,
)


def _is_engram_mcp_cmdline(cmdline: str) -> bool:
    """True iff ``cmdline`` is an engram/hippo MCP *server* invocation."""
    if not cmdline:
        return False
    if "verimem.mcp_server" in cmdline:
        return True
    return bool(_MCP_CMDLINE_RE.search(cmdline))


def _select_orphan_pids(procs, *, self_pid: int) -> list[int]:
    """Pure selection: given ``procs`` = iterable of
    ``(pid: int, cmdline: str, parent_alive: bool)``, return the pids that are
    engram-mcp servers, orphaned (parent NOT alive), and not ``self_pid``."""
    out: list[int] = []
    for pid, cmdline, parent_alive in procs:
        if pid == self_pid:
            continue
        if not _is_engram_mcp_cmdline(cmdline):
            continue
        if not parent_alive:
            out.append(pid)
    return out


def _import_psutil():
    """Return the psutil module, or None if unavailable (indirection for tests)."""
    try:
        import psutil  # noqa: PLC0415
        return psutil
    except Exception:  # noqa: BLE001
        return None


def reap_orphan_mcp_servers(*, dry_run: bool = False) -> list[int]:
    """Terminate orphaned sibling `engram mcp` servers. Returns the reaped pids
    (or, under ``dry_run``, the pids that WOULD be reaped). Never raises."""
    psutil = _import_psutil()
    if psutil is None:
        return []
    self_pid = os.getpid()
    candidates = []  # (pid, cmdline, parent_alive, proc)
    try:
        for p in psutil.process_iter(["pid", "cmdline"]):
            try:
                pid = p.info["pid"]
                cmdline = " ".join(p.info.get("cmdline") or [])
                if not _is_engram_mcp_cmdline(cmdline):
                    continue
                parent_alive = p.parent() is not None
                candidates.append((pid, cmdline, parent_alive, p))
            except Exception:  # noqa: BLE001 — one bad proc never aborts the sweep
                continue
    except Exception:  # noqa: BLE001
        return []
    orphan_pids = set(_select_orphan_pids(
        [(pid, cmd, alive) for pid, cmd, alive, _ in candidates],
        self_pid=self_pid,
    ))
    reaped: list[int] = []
    for pid, _cmd, _alive, proc in candidates:
        if pid not in orphan_pids:
            continue
        if dry_run:
            reaped.append(pid)
            continue
        try:
            proc.terminate()
            reaped.append(pid)
        except Exception:  # noqa: BLE001
            continue
    return reaped
