"""TDD — P85 actor/self-provenance (Vivarium 2026-07-11, prerequisite for any
engine that WRITES into its own memory, e.g. the composition daemon):

  * engine-written facts carry an ``actor:<component>`` ref — SIGNED footprints;
  * actor sources are NEVER independent witnesses: they cannot confirm a value,
    cannot earn consistency reputation, cannot manufacture consensus (self-echo);
  * the self-write ratio is monitored: past 0.5 the world's drift becomes
    invisible behind the engine's own echo (P85's exact phase transition) — alarm.
"""
from __future__ import annotations

import pytest

from verimem.self_provenance import (
    SELF_PREFIX,
    actor_of,
    is_self_ref,
    self_write_check,
)
from verimem.source_trust import (
    SourceTrustBook,
    auto_confirm_agreement,
    canonical_source,
)


def test_is_self_ref_and_actor_of():
    assert is_self_ref("actor:composer") is True
    assert is_self_ref("actor:composer:run42") is True
    assert is_self_ref("source-doc:alice:t1") is False
    assert is_self_ref("") is False
    assert actor_of("actor:composer:run42") == "composer"
    assert actor_of("source-doc:alice:t1") is None


def test_canonical_source_recognizes_actor_never_user_fallback():
    """An engine write must NOT masquerade as the 'user' source (the fallback):
    it canonicalises to a namespaced actor id, distinguishable everywhere."""
    assert canonical_source(["actor:composer:run42"]) == f"{SELF_PREFIX}:composer"
    # ordinary refs unchanged (regression guard on the existing regex)
    assert canonical_source(["source-doc:alice:t1"]) == "alice"
    assert canonical_source([]) == "user"


def test_actor_sources_cannot_confirm_themselves_or_others():
    book = SourceTrustBook()
    # 3 distinct actor ids asserting together: ZERO confirmations (self-echo dead)
    book.observe_confirmation([f"{SELF_PREFIX}:composer", f"{SELF_PREFIX}:dreamer",
                               f"{SELF_PREFIX}:reconciler"])
    assert book.to_dict() == {}
    # 2 real + 1 actor: the real pair confirms, the actor earns NOTHING
    book.observe_confirmation(["alice", "bob", f"{SELF_PREFIX}:composer"])
    d = book.to_dict()
    assert d["alice"]["confirms"] == 1.0 and d["bob"]["confirms"] == 1.0
    assert f"{SELF_PREFIX}:composer" not in d
    # 1 real + 1 actor is NOT >=2 real witnesses -> nobody rises
    book2 = SourceTrustBook()
    book2.observe_confirmation(["alice", f"{SELF_PREFIX}:composer"])
    assert book2.to_dict() == {}


def test_accept_value_ignores_actor_witnesses():
    book = SourceTrustBook()
    got = book.accept_value({
        "42": ["alice", "bob"],                                   # 2 real witnesses
        "666": [f"{SELF_PREFIX}:a", f"{SELF_PREFIX}:b",
                f"{SELF_PREFIX}:c"],                              # 3 engine echoes
    })
    assert got is not None
    assert got[0] == "42"                       # the echo chamber never wins
    only_self = book.accept_value({
        "666": [f"{SELF_PREFIX}:a", f"{SELF_PREFIX}:b"]})
    assert only_self is None                    # engine alone accepts nothing


def test_auto_confirm_agreement_strips_actors():
    book = SourceTrustBook()
    res = auto_confirm_agreement(book, "k1", {
        "alice": "42", "bob": "42", f"{SELF_PREFIX}:composer": "42"})
    assert res["accepted"] == "42"
    assert f"{SELF_PREFIX}:composer" not in res["confirmed"]
    assert f"{SELF_PREFIX}:composer" not in book.to_dict()


def test_self_write_check_ratio_and_alarm(tmp_path):
    """The P85 phase transition made operational: ratio of engine-written facts
    in the recent window; alarm past the 0.5 threshold."""
    from verimem.semantic import Fact, SemanticMemory
    sm = SemanticMemory(tmp_path / "sp.db")
    for i in range(4):
        sm.store(Fact(proposition=f"world fact {i}", topic="w",
                      verified_by=[f"source-doc:alice:t{i}"]))
    for i in range(2):
        sm.store(Fact(proposition=f"derived fact {i}", topic="w",
                      verified_by=["actor:composer:run1"]))
    ok = self_write_check(sm.db_path, window=100)
    assert ok["n"] == 6 and abs(ok["self_ratio"] - 2 / 6) < 1e-9
    assert ok["alarm"] is False
    for i in range(4):                      # engine floods its own memory
        sm.store(Fact(proposition=f"derived flood {i}", topic="w",
                      verified_by=["actor:composer:run2"]))
    bad = self_write_check(sm.db_path, window=100)
    assert bad["n"] == 10 and bad["self_ratio"] == 0.6
    assert bad["alarm"] is True             # past 0.5: drift now invisible (P85)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
