"""Write-time / read-time telemetry denylist must share ONE source (no drift).

2026-06-13: a LIVE hippo_facts_recall surfaced cache/ market/ citations/ JSON
blobs because semantic's recall denylist had been extended to hide them but the
admission_gate's hand-maintained regex still ADMITTED them — a silent drift
between the read side and the write side. Both now derive from
``verimem._telemetry_prefixes.TELEMETRY_TOPIC_PREFIXES``; this test pins that they
stay one source AND that the gate routes every machine-state namespace.
"""
from __future__ import annotations

import pytest

from verimem._telemetry_prefixes import TELEMETRY_TOPIC_PREFIXES
from verimem.admission_gate import ROUTE_TELEMETRY, classify_admission

_NEW = ["cache/", "market/", "citations/", "obs/", "signal/",
        "dispatch/", "supervisor/", "namespace/", "diary/"]
_ORIG = ["bus/", "metric/", "alloc/", "lock/", "tx/", "nego/", "replay/"]


@pytest.mark.parametrize("pfx", _NEW + _ORIG)
def test_machine_state_topic_routed_to_telemetry(pfx):
    v = classify_admission(topic=pfx + "x/1779", proposition="machine state value")
    assert v.decision == ROUTE_TELEMETRY, f"{pfx} must route to telemetry, got {v.decision}"
    assert v.admit_to_curated is False


@pytest.mark.parametrize("topic", ["lessons/x", "project/engram", "test/round5",
                                   "handoff/loop", "bench/h1"])
def test_knowledge_topic_not_routed_as_telemetry(topic):
    v = classify_admission(topic=topic, proposition="una lezione vera importante",
                           source_episodes=["ep1"], status="verified")
    assert v.decision != ROUTE_TELEMETRY, f"{topic} is knowledge, must NOT be telemetry"


def test_write_gate_and_read_denylist_share_one_source():
    # Anti-drift: the write-time gate and the read-time recall denylist must be
    # the SAME tuple object — a future edit to one can't desync the other.
    import verimem.admission_gate as ag
    import verimem.semantic as sem
    assert ag._TELEMETRY_TOPIC_PREFIXES is TELEMETRY_TOPIC_PREFIXES
    assert sem._TELEMETRY_TOPIC_PREFIXES is TELEMETRY_TOPIC_PREFIXES
