"""R16: Live introspection — narrative rationale for "what am I doing right now".

Given the most recent audit/log entries + active skills + last recall
result, produce a human-readable narrative: "I'm doing X because I
recall Y; skill Z is active."

Useful as a dashboard widget showing agent's current reasoning state.
"""
from __future__ import annotations


def test_empty_returns_idle():
    from verimem.live_introspection import introspect_state
    out = introspect_state(recent_audit=[], active_skills=[],
                           last_recall=[])
    assert "idle" in out["narrative"].lower() or out["narrative"] == ""


def test_narrates_recent_action():
    from verimem.live_introspection import introspect_state
    audit = [
        {"name": "hippo_recall", "ts": 1000.0, "outcome": "ok"},
        {"name": "hippo_remember", "ts": 1001.0, "outcome": "ok"},
    ]
    out = introspect_state(recent_audit=audit, active_skills=[],
                           last_recall=[])
    assert "hippo_recall" in out["narrative"] or "hippo_remember" in out["narrative"]


def test_includes_active_skills():
    from verimem.live_introspection import introspect_state
    out = introspect_state(
        recent_audit=[],
        active_skills=[{"id": "cf7-rce", "name": "CF7 RCE"}],
        last_recall=[],
    )
    assert "cf7-rce" in out["narrative"] or "CF7 RCE" in out["narrative"]


def test_includes_last_recall_context():
    from verimem.live_introspection import introspect_state
    out = introspect_state(
        recent_audit=[],
        active_skills=[],
        last_recall=[{"task": "WordPress exploit acme.io",
                      "outcome": "success", "similarity": 0.85}],
    )
    assert "WordPress" in out["narrative"]


def test_payload_keys():
    from verimem.live_introspection import introspect_state
    out = introspect_state(recent_audit=[], active_skills=[],
                           last_recall=[])
    for k in ("narrative", "stage", "components"):
        assert k in out


def test_stage_classification():
    """Stage should be one of: idle/recalling/acting/learning."""
    from verimem.live_introspection import introspect_state

    audit_action = [{"name": "hippo_record_episode", "outcome": "ok"}]
    out = introspect_state(
        recent_audit=audit_action, active_skills=[], last_recall=[],
    )
    assert out["stage"] in {"idle", "recalling", "acting", "learning"}


def test_narrative_is_markdown_friendly():
    from verimem.live_introspection import introspect_state
    out = introspect_state(
        recent_audit=[{"name": "hippo_recall", "outcome": "ok"}],
        active_skills=[{"id": "s1", "name": "skill A"}],
        last_recall=[{"task": "X", "outcome": "success",
                      "similarity": 0.9}],
    )
    # Should be a non-empty string fit for direct rendering
    assert isinstance(out["narrative"], str)
    assert len(out["narrative"]) > 10
