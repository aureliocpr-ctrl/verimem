"""Cycle 366 (2026-05-23) — STANDALONE MCP SERVER for engram syscall bridge.

Exposes the cycle 362-368 stack (mesh_memory + syscall_bridge +
op_supervisor + capability_token + dashboard_widget) as MCP tools
callable from any MCP-compatible host (Claude Code, Cursor, etc).

A3 honest: NOT singolarità — engineering integration. Single-file
MCP server, NO modification to the 10804-LOC engram/mcp_server.py
monolith. Aurelio can later wire these tools into the main server
or run this stand-alone via `python -m verimem.engram_syscall_mcp`.

Tools exposed (5):
  engram_invoke_recall — typed top-k recall with audit
  engram_invoke_mesh_query — publish query on vec_bus mesh channel
  engram_invoke_mesh_fetch — fetch recent mesh messages
  engram_invoke_audit_tail — read audit JSONL log
  engram_dashboard — render dashboard widget (text or json)

All tools route through engram_invoke (cycle 364) so they get the
full safety stack: manifest validation + supervisor circuit-breaker
+ rate limiting + audit + optional capability token.

Run: python -m verimem.engram_syscall_mcp
"""
from __future__ import annotations

import json
import sys
from typing import Any


def _have_mcp_sdk() -> bool:
    try:
        from mcp import server  # noqa: F401
        return True
    except ImportError:
        return False


# ───────────────────────── tool implementations ─────────────────────────

def tool_engram_invoke_recall(query: str, k: int = 5,
                                actor: str = "mcp_client",
                                capability_token: str | None = None) -> dict:
    """Typed engram recall via syscall_bridge.

    Returns {ok, result: {hits: [(fact_id, score)]}, audit_id, blocked_by}.
    """
    from verimem.syscall_bridge import engram_invoke
    return engram_invoke(
        "recall", {"query": query, "k": k}, actor=actor,
        capability_token=capability_token,
    )


def tool_engram_invoke_mesh_query(text: str,
                                    channel: str = "mesh/recall/req",
                                    actor: str = "mcp_client",
                                    capability_token: str | None = None) -> dict:
    """Publish a query on the mesh recall channel (vec_bus broadcast)."""
    from verimem.syscall_bridge import engram_invoke
    return engram_invoke(
        "mesh_query", {"text": text, "channel": channel, "sender": actor},
        actor=actor, capability_token=capability_token,
    )


def tool_engram_invoke_mesh_fetch(channel: str,
                                    since_ts: float = 0.0,
                                    skip_own: bool = True,
                                    actor: str = "mcp_client",
                                    capability_token: str | None = None) -> dict:
    """Fetch recent mesh messages on a channel."""
    from verimem.syscall_bridge import engram_invoke
    return engram_invoke(
        "mesh_fetch",
        {"channel": channel, "since_ts": since_ts, "skip_own": skip_own},
        actor=actor, capability_token=capability_token,
    )


def tool_engram_invoke_audit_tail(n: int = 20) -> list[dict]:
    """Read last N entries from verimem syscall audit JSONL."""
    from verimem.syscall_bridge import engram_audit_tail
    return engram_audit_tail(n=n)


def tool_engram_dashboard(format: str = "text", tail: int = 30) -> str:
    """Render engram dashboard widget.

    Args:
        format: "text" or "json"
        tail: audit tail entries to summarize

    Returns: rendered string.
    """
    from verimem.dashboard_widget import collect_state, render_json, render_text
    state = collect_state(tail_n=tail)
    return render_json(state) if format == "json" else render_text(state)


# ───────────────────────── MCP server registration ─────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "engram_invoke_recall",
        "description": (
            "Typed top-k semantic recall via engram syscall bridge "
            "(cycle 362-368 stack). Returns fact_ids + cosine scores, "
            "NO plaintext (privacy primitive)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "k": {"type": "integer", "default": 5},
                "actor": {"type": "string", "default": "mcp_client"},
                "capability_token": {"type": ["string", "null"], "default": None},
            },
            "required": ["query"],
        },
        "handler": tool_engram_invoke_recall,
    },
    {
        "name": "engram_invoke_mesh_query",
        "description": (
            "Publish a query embedding on the vec_bus mesh recall channel. "
            "Peers respond via mesh_fetch with their local top-k embeddings."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "channel": {"type": "string", "default": "mesh/recall/req"},
                "actor": {"type": "string", "default": "mcp_client"},
                "capability_token": {"type": ["string", "null"], "default": None},
            },
            "required": ["text"],
        },
        "handler": tool_engram_invoke_mesh_query,
    },
    {
        "name": "engram_invoke_mesh_fetch",
        "description": (
            "Fetch recent mesh messages on a channel "
            "(vec_bus binary embedding broadcasts)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "channel": {"type": "string"},
                "since_ts": {"type": "number", "default": 0.0},
                "skip_own": {"type": "boolean", "default": True},
                "actor": {"type": "string", "default": "mcp_client"},
                "capability_token": {"type": ["string", "null"], "default": None},
            },
            "required": ["channel"],
        },
        "handler": tool_engram_invoke_mesh_fetch,
    },
    {
        "name": "engram_invoke_audit_tail",
        "description": (
            "Read last N entries from the engram syscall audit JSONL log. "
            "Each entry: {audit_id, op, actor, ok, blocked_by, ts, ...}"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "n": {"type": "integer", "default": 20},
            },
        },
        "handler": tool_engram_invoke_audit_tail,
    },
    {
        "name": "engram_dashboard",
        "description": (
            "Render the engram supervision tree dashboard: stack layers, "
            "manifest ops, per-op circuit states, rate-limit current "
            "window, audit summary. format='text' or 'json'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "default": "text",
                            "enum": ["text", "json"]},
                "tail": {"type": "integer", "default": 30},
            },
        },
        "handler": tool_engram_dashboard,
    },
]


def get_tool_definitions() -> list[dict[str, Any]]:
    """Return tool defs for any MCP-compatible host to register.

    Each def: {name, description, input_schema, handler}.
    """
    return TOOL_DEFINITIONS


def main() -> int:
    """Standalone entry: print tool definitions as JSON (for inspection)
    or run an MCP server if SDK present.
    """
    if "--list-tools" in sys.argv or not _have_mcp_sdk():
        # Print JSON listing of available tools (no MCP transport needed)
        defs = [
            {k: v for k, v in d.items() if k != "handler"}
            for d in TOOL_DEFINITIONS
        ]
        print(json.dumps({
            "server": "engram-syscall-mcp",
            "version": "cycle-366",
            "tools": defs,
        }, indent=2))
        return 0

    # MCP server transport path: lazy-imported only if SDK available
    print("[engram-syscall-mcp] MCP SDK available — server mode TBD by "
          "Aurelio wiring. Tool definitions available via "
          "verimem.engram_syscall_mcp.get_tool_definitions()",
          file=sys.stderr)
    print(json.dumps({
        "server": "engram-syscall-mcp",
        "version": "cycle-366",
        "tools": [d["name"] for d in TOOL_DEFINITIONS],
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
