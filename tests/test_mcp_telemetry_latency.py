"""Cycle #115.A — MCP tool-call telemetry: latency_ms in the audit log.

Aurelio direttiva 2026-05-17 (CEO mode): "fai scalare realmente questo
prodotto" → misura ROI cognitivo reale. Step #1: ogni chiamata MCP deve
loggare la propria latency_ms. L'`_audit()` esistente già scrive un
record JSONL per call (`<engram>/mcp_audit.log`). Cycle 115.A estende
quel record con `latency_ms`.

Design (zero modifiche ai ~100 call-site `_audit()`):
* `_REQUEST_START_NS: ContextVar[int | None]` modulo-level.
* `call_tool()` setta il context var con `time.monotonic_ns()` all'inizio.
* `_audit()` legge il context var e calcola `latency_ms` da solo;
  se il var è None (call_tool non chiamato, es. test diretto), il
  campo è omesso dal record.

I test verificano sia la lettura corretta del campo dal context var,
sia l'omissione quando il var non è settato.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest


@pytest.fixture
def audit_log_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolated audit log path per test."""
    log = tmp_path / "mcp_audit.log"
    monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(log))
    return log


def _read_records(log_path: Path) -> list[dict]:
    if not log_path.exists():
        return []
    return [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class TestAuditWithoutTimerHasNoLatency:
    """Direct `_audit()` call without context-var set: no latency_ms field."""

    def test_audit_without_timer_omits_latency(
        self, audit_log_path: Path,
    ) -> None:
        from engram.mcp_server import _audit
        _audit("hippo_test_tool", {"arg": "v"}, outcome="ok")

        recs = _read_records(audit_log_path)
        assert len(recs) == 1
        assert "latency_ms" not in recs[0]


class TestAuditWithTimerEmitsLatency:
    """`_REQUEST_START_NS` is set: the record carries `latency_ms`."""

    def test_audit_with_timer_emits_latency_field(
        self, audit_log_path: Path,
    ) -> None:
        from engram.mcp_server import _REQUEST_START_NS, _audit
        token = _REQUEST_START_NS.set(time.monotonic_ns())
        try:
            # Cycle #133 fix: Windows timer resolution can leave a 5ms sleep
            # measured as 0ms latency (QueryPerformanceCounter delta below
            # scheduler quantum). 50ms is comfortably above any platform's
            # tick granularity, so latency must be strictly positive.
            time.sleep(0.050)  # 50 ms
            _audit("hippo_test_tool", {"a": 1}, outcome="ok")
        finally:
            _REQUEST_START_NS.reset(token)

        recs = _read_records(audit_log_path)
        assert len(recs) == 1
        assert "latency_ms" in recs[0]
        assert isinstance(recs[0]["latency_ms"], float)
        # 50 ms sleep — relax floor to 1 ms to absorb Windows tick slack
        # while still proving the timer wired up correctly (>0).
        assert recs[0]["latency_ms"] >= 1.0
        # Sanity upper bound: a single _audit() call should be << 1 second.
        assert recs[0]["latency_ms"] < 1000.0


class TestCallToolSetsTimer:
    """The async `call_tool()` entry point sets `_REQUEST_START_NS`
    before running, so every `_audit()` inside the handler picks it up."""

    @pytest.mark.asyncio
    async def test_call_tool_emits_latency_on_audit(
        self, audit_log_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from engram import mcp_server
        # Use a tool that hits the empty-task rejection path; that path
        # already calls `_audit(..., outcome="rejected_empty")`.
        result = await mcp_server.call_tool(
            "hippo_run_task", {"task": ""},
        )
        assert result  # any non-empty list[TextContent]

        recs = _read_records(audit_log_path)
        assert len(recs) >= 1
        # The last record corresponds to our call.
        last = recs[-1]
        assert last["tool"] == "hippo_run_task"
        assert "latency_ms" in last
        assert last["latency_ms"] >= 0.0


class TestRecordSchemaStable:
    """The pre-existing fields stay present, latency is additive."""

    def test_existing_fields_unchanged(
        self, audit_log_path: Path,
    ) -> None:
        from engram.mcp_server import _REQUEST_START_NS, _audit
        token = _REQUEST_START_NS.set(time.monotonic_ns())
        try:
            _audit("hippo_x", {"a": 1}, outcome="ok", error="")
        finally:
            _REQUEST_START_NS.reset(token)

        recs = _read_records(audit_log_path)
        r = recs[0]
        for k in ("ts", "tool", "caller_pid", "args_hash", "outcome", "error"):
            assert k in r, f"pre-existing field missing: {k}"
        assert r["tool"] == "hippo_x"
        assert r["outcome"] == "ok"
