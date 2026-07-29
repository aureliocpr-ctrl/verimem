"""The MCP API this server is built on, asserted once and by name.

2026-07-29: `mcp` 2.0.0 removed ``Server.list_tools``, which mcp_server.py uses
in 11 places. The CI installs the newest release that satisfies the declared
range, so a run that had been green on 2026-07-26 came back with hundreds of
identical `AttributeError: 'Server' object has no attribute 'list_tools'` and
nothing pointing at the cause.

The CI going red is not the damage. Published verimem 0.7.0 declares
``mcp>=1.0.0`` with no ceiling, so every `pip install verimem` since 2.0.0 was
released resolves to it and gets an MCP server that cannot start. The ceiling in
pyproject fixes that; this test is what makes the next attempt to lift it fail
LOUDLY and in one line instead of by exhaustion.

Same shape as the critic-orchestrator lesson from the night before: "ruff clean"
was true of the pinned local version while CI installed a wider one. An
unbounded dependency is a claim about software that does not exist yet.
"""
from __future__ import annotations

import pytest

#: Decorators the server class must expose. `request_handlers` is deliberately
#: NOT here: it lives on the INSTANCE, and asserting it on the class passes for
#: the wrong reason or fails for one — it gets its own check below.
_REQUIRED_SERVER_ATTRS = ("list_tools", "call_tool")


@pytest.mark.parametrize("attr", _REQUIRED_SERVER_ATTRS)
def test_the_mcp_server_api_this_project_uses_still_exists(attr: str) -> None:
    from mcp.server import Server
    assert hasattr(Server, attr), (
        f"mcp.server.Server has no {attr!r}. mcp 2.0.0 removed list_tools and "
        f"this project calls it in 11 places, so the MCP surface will not "
        f"start. pyproject pins mcp<2 for exactly this reason — if you are "
        f"lifting that bound, migrate the call sites in the same change."
    )


def test_the_live_server_still_dispatches_tool_calls() -> None:
    """The instance-level entry point every MCP test drives, and the one an
    editor's MCP client hits first."""
    from mcp.types import CallToolRequest, ListToolsRequest

    from verimem import mcp_server
    handlers = getattr(mcp_server.server, "request_handlers", None)
    assert handlers, "the built server exposes no request_handlers"
    for req in (CallToolRequest, ListToolsRequest):
        assert req in handlers, (
            f"{req.__name__} has no handler — the MCP surface is registered "
            f"differently in this version of mcp"
        )


def test_the_installed_mcp_is_within_the_declared_bound() -> None:
    """Catches the environment drifting away from what pyproject asks for —
    a venv built before the ceiling was added, or an install with --upgrade."""
    from importlib.metadata import version
    major = int(version("mcp").split(".")[0])
    assert major < 2, (
        f"mcp {version('mcp')} is installed but this project requires <2. "
        f"Reinstall the pinned dependencies before trusting a green run."
    )
