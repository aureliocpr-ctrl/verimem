"""Single-instance guard: reap ORPHANED `engram mcp` servers on startup.

Root cause of the recurring multi-minute save-hang (2026-06-06, empirical via
Win32_Process enumeration): Claude Code restarts spawn a fresh `engram mcp`
server each time but the OLD ones are never reaped — observed 6 simultaneously,
each contending CPU/disk + driving its own embedding work, starving the live
server's encode until a save hung for minutes.

The matcher is the risky part (a wrong match would terminate the wrong process),
so it is pinned hard here: it must match the engram MCP server in all its launch
forms and must NOT match the sibling bridge/clp/daemon processes.
"""
from __future__ import annotations

import engram._singleton_guard as g

# --- cmdline matcher: must be exact about WHAT is an engram mcp server ---

POSITIVE = [
    r'C:\Users\dev\miniconda3\Scripts\engram.exe mcp',
    r'"C:\Users\dev\miniconda3\Scripts\engram.exe" mcp',
    "python -m engram.mcp_server",
    "C:/Users/dev/miniconda3/python.exe -m engram.mcp_server",
    "hippo mcp",
    "engram mcp",
]

NEGATIVE = [
    "python C:/Users/dev/Code/engram-orchestrator/clp/engram_bridge_mcp.py",
    "python C:/Users/dev/Code/engram-orchestrator/clp/clp_mcp_server.py",
    "python C:/Users/dev/Code/engram-orchestrator/clp/duo_bridge_mcp.py",
    "pythonw.exe -m engram.encode_service",
    r"pythonw.exe C:\Users\dev\.engram\bin\engram_embedding_daemon.py",
    "python -m critic_orchestrator.mcp_server",
    "engram run 'capital of France?'",
    "engram dashboard --port 8765",
    "",
]


def test_matcher_accepts_every_engram_mcp_launch_form():
    for cmd in POSITIVE:
        assert g._is_engram_mcp_cmdline(cmd), f"should match engram mcp server: {cmd!r}"


def test_matcher_rejects_siblings_and_daemons():
    for cmd in NEGATIVE:
        assert not g._is_engram_mcp_cmdline(cmd), f"must NOT match: {cmd!r}"


# --- orphan selection: only engram-mcp, only orphaned (parent dead), never self ---

def test_select_orphans_only_parent_dead_engram_mcp_excluding_self():
    procs = [
        (100, "python -m engram.mcp_server", False),   # orphan engram mcp -> REAP
        (101, "python -m engram.mcp_server", True),    # live parent -> KEEP (multi-window safe)
        (102, "engram.exe mcp", False),                # orphan engram mcp -> REAP
        (200, "python clp_mcp_server.py", False),      # not engram mcp -> KEEP
        (300, "pythonw -m engram.encode_service", False),  # daemon -> KEEP
        (999, "python -m engram.mcp_server", False),   # SELF -> KEEP even if orphan
    ]
    out = sorted(g._select_orphan_pids(procs, self_pid=999))
    assert out == [100, 102], f"expected [100,102], got {out}"


def test_reaper_dry_run_returns_pids_without_killing(monkeypatch):
    # dry_run must never terminate; just report what WOULD be reaped.
    sentinel = {"terminated": []}

    class _FakeProc:
        def __init__(self, pid, cmdline, parent):
            self.info = {"pid": pid, "cmdline": cmdline}
            self._parent = parent
        def parent(self):
            return self._parent
        def terminate(self):
            sentinel["terminated"].append(self.info["pid"])

    fake_procs = [
        _FakeProc(100, ["python", "-m", "engram.mcp_server"], None),    # orphan
        _FakeProc(101, ["python", "-m", "engram.mcp_server"], object()),  # live parent
    ]

    class _FakePsutil:
        NoSuchProcess = AccessDenied = Exception
        @staticmethod
        def process_iter(_attrs):
            return fake_procs
        @staticmethod
        def Process(pid):
            raise AssertionError("dry_run must not construct Process for kill")

    monkeypatch.setattr(g, "_import_psutil", lambda: _FakePsutil)
    monkeypatch.setattr(g.os, "getpid", lambda: 555)

    reaped = g.reap_orphan_mcp_servers(dry_run=True)
    assert reaped == [100], f"dry_run should report orphan 100, got {reaped}"
    assert sentinel["terminated"] == [], "dry_run must NOT terminate anything"
