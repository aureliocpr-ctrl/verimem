"""FORGIA pezzo #259 — Wave 58: audit log summary aggregator.

Existing `hippo_audit_tail` returns last N raw entries. This
aggregates: outcome counts, tool-usage frequency, recent rejections,
rate-limit hits.
"""
from __future__ import annotations


def test_empty_returns_zeros():
    from engram.audit_summary import summarize_audit

    out = summarize_audit([])
    assert out["n_total"] == 0
    assert out["by_outcome"] == {}


def test_counts_by_outcome():
    from engram.audit_summary import summarize_audit

    entries = [
        {"tool": "x", "outcome": "ok"},
        {"tool": "x", "outcome": "ok"},
        {"tool": "y", "outcome": "rejected_schema"},
        {"tool": "z", "outcome": "rate_limited"},
    ]
    out = summarize_audit(entries)
    assert out["by_outcome"]["ok"] == 2
    assert out["by_outcome"]["rejected_schema"] == 1
    assert out["by_outcome"]["rate_limited"] == 1


def test_counts_by_tool():
    from engram.audit_summary import summarize_audit

    entries = [
        {"tool": "hippo_recall", "outcome": "ok"},
        {"tool": "hippo_recall", "outcome": "ok"},
        {"tool": "hippo_search", "outcome": "ok"},
    ]
    out = summarize_audit(entries)
    by_tool = {t["tool"]: t["count"] for t in out["top_tools"]}
    assert by_tool["hippo_recall"] == 2
    assert by_tool["hippo_search"] == 1


def test_recent_rejections_listed():
    from engram.audit_summary import summarize_audit

    entries = [
        {"tool": "x", "outcome": "ok"},
        {"tool": "y", "outcome": "rejected_schema",
            "error": "bad arg"},
        {"tool": "z", "outcome": "rejected_empty"},
    ]
    out = summarize_audit(entries)
    assert len(out["recent_rejections"]) == 2


def test_top_k_tools_respected():
    from engram.audit_summary import summarize_audit

    entries = [{"tool": f"t{i}", "outcome": "ok"} for i in range(20)]
    out = summarize_audit(entries, top_k_tools=5)
    assert len(out["top_tools"]) == 5


def test_payload_shape_complete():
    from engram.audit_summary import summarize_audit

    out = summarize_audit([])
    for k in ("n_total", "by_outcome", "top_tools",
                "recent_rejections", "summary"):
        assert k in out


def test_n_rate_limited_separate_count():
    from engram.audit_summary import summarize_audit

    entries = [
        {"tool": "x", "outcome": "rate_limited"},
        {"tool": "y", "outcome": "rate_limited"},
        {"tool": "z", "outcome": "ok"},
    ]
    out = summarize_audit(entries)
    assert out["n_rate_limited"] == 2
