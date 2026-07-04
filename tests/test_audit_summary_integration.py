"""Integration test for `hippo_audit_summary` MCP handler.

CRITIC-TROVATO 2026-05-14 (job 210a18ac2bf44d3d): the handler in
`engram/mcp_server.py:6254-6283` calls a function `_audit_tail_entries`
that is NEVER defined in the codebase (grep confirms no match). The
intended fallback at line 6267 reads `<data_dir>/mcp_audit.jsonl` —
but the writer at `_audit_log_path()` writes `<data_dir>/mcp_audit.log`.
Result: `hippo_audit_summary` ALWAYS returns `n_total: 0`, even when
the real audit log contains thousands of entries (verified live: 11451
lines / 1.5 MB in `~/.engram/mcp_audit.log`, tool returned 0).

This is the 4th silent-failure of the same family (cycle #10 list_facts,
#11 token_usage_stats, #13 a.sleep.cycle_light) — handler references
a symbol that doesn't exist, `NameError` is silently swallowed by a
broken fallback, the tool ships with the appearance of working.

These tests instantiate the real MCP dispatcher, point the audit-log
env var at a tmp file with known entries, and assert the dispatcher
actually counts them. Pre-fix all three FAIL with `n_total == 0`.
Post-fix all three PASS.
"""
from __future__ import annotations

import json

import pytest
from mcp.types import CallToolRequest, CallToolRequestParams

from engram import mcp_server

# ---------------------------------------------------------------------------
# Minimal agent stub — the audit_summary handler does NOT touch agent state,
# it only reads the audit log file. But the dispatcher needs `_ag()` to not
# error out before reaching the handler branch.
# ---------------------------------------------------------------------------


class _StubAgent:
    """Bare-minimum agent placeholder. `hippo_audit_summary` ignores it."""

    skills = None
    memory = None
    semantic = None


@pytest.fixture
def stub_agent(monkeypatch: pytest.MonkeyPatch) -> _StubAgent:
    a = _StubAgent()
    monkeypatch.setattr(mcp_server, "_ag", lambda: a)
    monkeypatch.setattr(mcp_server, "_agent", a, raising=False)
    return a


# ---------------------------------------------------------------------------
# Helper: invoke a tool through the registered MCP CallToolRequest handler.
# ---------------------------------------------------------------------------


async def _invoke_audit_summary(arguments: dict | None = None) -> dict:
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(
            name="hippo_audit_summary",
            arguments=arguments or {},
        ),
    )
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    text_blocks = [c.text for c in payload.content if hasattr(c, "text")]
    assert text_blocks, "no text content returned"
    return json.loads(text_blocks[0])


# ---------------------------------------------------------------------------
# RED tests — these must fail pre-fix and pass post-fix.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_summary_counts_entries_from_real_log(
    stub_agent: _StubAgent,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Counterexample: writer writes `mcp_audit.log`, handler MUST read it.

    Pre-fix: NameError on `_audit_tail_entries` → fallback path
    `mcp_audit.jsonl` (wrong filename) → file not found → entries=[]
    → n_total=0. Test FAILS.
    """
    log_path = tmp_path / "mcp_audit.log"
    entries_in = [
        {"ts": 1.0, "tool": "hippo_recall", "outcome": "ok", "error": ""},
        {"ts": 2.0, "tool": "hippo_remember", "outcome": "ok", "error": ""},
        {"ts": 3.0, "tool": "hippo_stats", "outcome": "ok", "error": ""},
    ]
    log_path.write_text(
        "\n".join(json.dumps(e) for e in entries_in) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(log_path))

    out = await _invoke_audit_summary()

    # The dispatcher writes one more audit entry AFTER the read
    # (the "ok" entry for the audit_summary call itself), but
    # the read happened BEFORE that — so we expect at least
    # the 3 entries we seeded.
    assert out["n_total"] >= 3, (
        f"Expected >=3 entries (3 seeded + maybe self-log), "
        f"got {out['n_total']}. Payload: {out}"
    )
    tool_names = {t["tool"] for t in out["top_tools"]}
    assert "hippo_recall" in tool_names, (
        f"hippo_recall missing from top_tools: {tool_names}"
    )


@pytest.mark.asyncio
async def test_audit_summary_aggregates_outcomes(
    stub_agent: _StubAgent,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The handler must correctly aggregate outcome counts."""
    log_path = tmp_path / "mcp_audit.log"
    entries_in = [
        {"ts": 1.0, "tool": "x", "outcome": "ok"},
        {"ts": 2.0, "tool": "y", "outcome": "ok"},
        {"ts": 3.0, "tool": "z", "outcome": "rejected_schema",
         "error": "bad arg"},
    ]
    log_path.write_text(
        "\n".join(json.dumps(e) for e in entries_in) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(log_path))

    out = await _invoke_audit_summary()

    # by_outcome ok>=2 from seed (+1 from self-log), rejected_schema==1
    by_o = out["by_outcome"]
    assert by_o.get("ok", 0) >= 2, f"expected >=2 ok, got: {by_o}"
    assert by_o.get("rejected_schema", 0) == 1, (
        f"expected 1 rejected_schema, got: {by_o}"
    )


@pytest.mark.asyncio
async def test_audit_summary_empty_file_returns_zero(
    stub_agent: _StubAgent,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """File exists but empty — must return 0 cleanly (no crash)."""
    log_path = tmp_path / "mcp_audit.log"
    log_path.write_text("", encoding="utf-8")
    monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(log_path))

    out = await _invoke_audit_summary()

    # 0 seeded + 1 self-log → exactly 1
    assert out["n_total"] <= 1, (
        f"Expected <=1 (only self-log), got {out['n_total']}: {out}"
    )


@pytest.mark.asyncio
async def test_audit_summary_missing_file_returns_zero(
    stub_agent: _StubAgent,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """File doesn't exist at all — must return 0 cleanly (no crash)."""
    log_path = tmp_path / "nonexistent_audit.log"
    # Do NOT create the file.
    monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(log_path))

    out = await _invoke_audit_summary()

    # 0 seeded; the self-log write will create the file mid-call,
    # but the read happened first → n_total should be 0 or 1.
    assert out["n_total"] <= 1, (
        f"Expected 0-1, got {out['n_total']}: {out}"
    )
