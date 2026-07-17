"""FORGIA pezzo #181 — `WakeAgent.prime_skills_via_topics`.

Reweights base skill scores using the schema topic distribution
returned by `SemanticMemory.topics_for_query`. Skills whose
trigger or name matches a primed topic get a multiplicative boost;
unrelated skills are left untouched.

This is the consumer for #180 and the first concrete instance of
schema-driven priming (Preston & Eichenbaum 2013) in HippoAgent.
"""
from __future__ import annotations

from pathlib import Path

from verimem.memory import EpisodicMemory
from verimem.semantic import Fact, SemanticMemory
from verimem.skill import Skill, SkillLibrary
from verimem.wake import WakeAgent


def _build(tmp_path: Path) -> WakeAgent:
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    sem = SemanticMemory(db_path=tmp_path / "sem.db")
    wake = WakeAgent(memory=mem, skills=skills, semantic=sem)
    return wake


def test_prime_with_no_facts_is_identity(tmp_path: Path):
    """No semantic facts → no priming → scores unchanged."""
    wake = _build(tmp_path)
    base = {"sk1": 0.5, "sk2": 0.7}
    primed = wake.prime_skills_via_topics(
        task="something",
        base_scores=base,
        skills=[
            Skill(id="sk1", name="parse", trigger="parse",
                  body="b"),
            Skill(id="sk2", name="lint", trigger="lint",
                  body="b"),
        ],
    )
    assert primed == base


def test_prime_boosts_topic_matching_skill(tmp_path: Path):
    """A skill whose trigger matches the primed topic gets a boost."""
    wake = _build(tmp_path)
    # Token-overlap with the task ("network connection request") ensures
    # the stub embedder pulls the networking fact (vs. the algorithms one).
    wake.semantic.store(Fact(
        proposition="network connection request handshake",
        topic="networking", confidence=0.9,
    ))
    wake.semantic.store(Fact(
        proposition="bubble sort comparison swap",
        topic="algorithms", confidence=0.9,
    ))
    skills = [
        Skill(id="net", name="net-handler", trigger="networking",
              body="b"),
        Skill(id="sort", name="sort", trigger="algorithms",
              body="b"),
    ]
    base = {"net": 0.5, "sort": 0.5}
    primed = wake.prime_skills_via_topics(
        task="network connection request",
        base_scores=base,
        skills=skills,
    )
    # The networking skill must be boosted strictly above sort.
    assert primed["net"] > primed["sort"]
    assert primed["net"] > base["net"]


def test_prime_does_not_create_new_keys(tmp_path: Path):
    wake = _build(tmp_path)
    wake.semantic.store(Fact(proposition="apple banana", topic="fruit",
                              confidence=0.9))
    base = {"sk1": 0.5}
    primed = wake.prime_skills_via_topics(
        task="apple banana cherry",
        base_scores=base,
        skills=[
            Skill(id="sk1", name="a", trigger="b", body="b"),
        ],
    )
    assert set(primed.keys()) == set(base.keys())


def test_prime_skill_with_no_topic_match_is_unchanged(tmp_path: Path):
    """A skill whose trigger/name doesn't match any primed topic is
    left at its base score."""
    wake = _build(tmp_path)
    wake.semantic.store(Fact(
        proposition="network connection request",
        topic="networking", confidence=0.9,
    ))
    base = {"unrelated": 0.4}
    skills = [Skill(id="unrelated", name="zzz", trigger="zzz", body="b")]
    primed = wake.prime_skills_via_topics(
        task="network connection request", base_scores=base, skills=skills,
    )
    assert primed["unrelated"] == 0.4
