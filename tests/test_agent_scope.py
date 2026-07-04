"""R4: Multi-agent memory namespacing via topic prefix convention.

Zero schema change. Convention:
  - Single-agent memory: topic="nexus/cve/CVE-X" (no agent prefix)
  - Per-agent memory:    topic="agent:pentester/nexus/cve/CVE-X"
  - Shared topic:        topic="shared/lessons/wafs" (no prefix, but explicit)

Helpers to scope/tag/filter without touching SQLite schema.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _FakeFact:
    id: str
    proposition: str
    topic: str
    confidence: float = 0.9


def test_tag_topic_for_agent():
    from engram.agent_scope import tag_for_agent

    out = tag_for_agent("nexus/cve/CVE-2024-X", agent_id="pentester")
    assert out == "agent:pentester/nexus/cve/CVE-2024-X"


def test_tag_idempotent():
    """Tagging an already-tagged topic shouldn't double-prefix."""
    from engram.agent_scope import tag_for_agent

    once = tag_for_agent("foo", agent_id="A")
    twice = tag_for_agent(once, agent_id="A")
    assert once == twice


def test_extract_agent_id():
    from engram.agent_scope import agent_id_from_topic

    assert agent_id_from_topic("agent:pentester/nexus") == "pentester"
    assert agent_id_from_topic("nexus/cve") is None
    assert agent_id_from_topic("agent:reviewer/code/X") == "reviewer"


def test_filter_facts_by_agent_id():
    from engram.agent_scope import filter_facts_by_agent

    facts = [
        _FakeFact("f1", "x", "agent:pentester/cve"),
        _FakeFact("f2", "y", "agent:reviewer/code"),
        _FakeFact("f3", "z", "shared/lessons"),
        _FakeFact("f4", "w", "agent:pentester/lesson"),
    ]
    out = filter_facts_by_agent(facts, agent_id="pentester")
    ids = sorted([f.id for f in out])
    assert ids == ["f1", "f4"]


def test_filter_includes_shared_when_requested():
    from engram.agent_scope import filter_facts_by_agent

    facts = [
        _FakeFact("f1", "x", "agent:pentester/cve"),
        _FakeFact("f2", "y", "shared/lessons"),
        _FakeFact("f3", "z", "agent:reviewer/code"),
    ]
    out = filter_facts_by_agent(facts, agent_id="pentester", include_shared=True)
    ids = sorted([f.id for f in out])
    assert ids == ["f1", "f2"]  # pentester + shared, no reviewer


def test_filter_by_agent_id_none_returns_all_without_prefix():
    """agent_id=None returns only un-namespaced facts (legacy)."""
    from engram.agent_scope import filter_facts_by_agent

    facts = [
        _FakeFact("f1", "x", "math/collatz"),  # no prefix
        _FakeFact("f2", "y", "agent:A/cve"),
        _FakeFact("f3", "z", "shared/lessons"),
    ]
    out = filter_facts_by_agent(facts, agent_id=None)
    ids = sorted([f.id for f in out])
    assert "f1" in ids
    assert "f2" not in ids


def test_count_by_agent():
    from engram.agent_scope import count_by_agent

    facts = [
        _FakeFact("f1", "x", "agent:A/x"),
        _FakeFact("f2", "x", "agent:A/y"),
        _FakeFact("f3", "x", "agent:B/x"),
        _FakeFact("f4", "x", "shared/x"),
    ]
    out = count_by_agent(facts)
    assert out["A"] == 2
    assert out["B"] == 1
    assert out["(shared)"] == 1


def test_payload_keys_count_by_agent():
    from engram.agent_scope import count_by_agent
    out = count_by_agent([])
    assert isinstance(out, dict)


def test_tag_with_special_chars_safe():
    # agent_id with slash should be sanitized or rejected
    import pytest

    from engram.agent_scope import tag_for_agent
    with pytest.raises(ValueError):
        tag_for_agent("foo", agent_id="bad/id")
