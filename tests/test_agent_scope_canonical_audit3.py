"""audit#3-r3 R14: agent_scope.agent_id_from_topic (the single primitive behind
hippo_count_by_agent, hippo_agent_workload, hippo_agent_specialization and
hippo_cross_agent_consensus) used a ``^agent:`` regex that only matched the
LEGACY ``agent:<id>/...`` form. The canonical B-1 form
``user:<u>/agent:<id>/...`` starts with ``user:`` so it never matched — every
canonically-scoped fact was misattributed to ``(shared)`` and the per-agent
tools were blind to multi-tenant memory.

Fix: delegate to scope.parse_scope, which recognizes the ``agent:`` segment in
BOTH forms (same primitive recall/search/list and the Fix-E hippo_facts_by_agent
already use).
"""
from __future__ import annotations

import pytest

from engram.agent_scope import agent_id_from_topic, count_by_agent


@pytest.mark.parametrize(
    "topic,expected",
    [
        ("agent:pentester/cve/x", "pentester"),            # legacy
        ("user:alice/agent:pentester/cve/x", "pentester"),  # canonical (was None)
        ("user:alice/run:r1/agent:rev/x", "rev"),           # mixed dims
        ("nexus/cve/2026", None),                           # unscoped
        ("user:bob/project/x", None),                        # user-only, no agent
        ("", None),
    ],
)
def test_agent_id_from_topic_sees_canonical_and_legacy(topic, expected):
    assert agent_id_from_topic(topic) == expected, topic


class _F:
    def __init__(self, topic: str) -> None:
        self.topic = topic


def test_count_by_agent_attributes_canonical_scope():
    facts = [
        _F("agent:pentester/a"),                 # legacy
        _F("user:alice/agent:pentester/b"),       # canonical — pre-fix -> (shared)
        _F("user:alice/agent:reviewer/c"),        # canonical — pre-fix -> (shared)
        _F("nexus/legacy/d"),                     # genuinely shared/unscoped
    ]
    counts = count_by_agent(facts)
    assert counts.get("pentester") == 2, counts   # pre-fix: 1
    assert counts.get("reviewer") == 1, counts     # pre-fix: absent
    assert counts.get("(shared)") == 1, counts      # pre-fix: 3
