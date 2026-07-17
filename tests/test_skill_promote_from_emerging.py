"""Cycle 235 (2026-05-23) — promote emerging_skill fact into a real Skill row.

Closes the discovery → adoption loop:

  detect (213) → normalize (215) → draft (217) → register fact (229)
    → REGISTER skill row (235) ← here

The promotion is a TRANSCODE step:
  - emerging_skill fact.proposition (cycle 229) → Skill.body (cycle 144 schema)
  - evidence.purity * evidence.cohesion → Skill.fitness (Beta prior)
  - trigger_keywords → Skill.trigger (text)
  - dominant_topic → Skill.name (slug)

A4 honest: the promoted skill is created with status='candidate'
(NOT 'promoted'). The cycle-184 anti-confab L1.8 gate still applies
to the underlying emerging_skill fact via topic match. Only the
``promote_or_retire`` cycle-144 path (run on real trials) moves the
candidate to 'promoted'.
"""
from __future__ import annotations

from pathlib import Path

import pytest

# RED MARKER
from verimem.skill_promote_from_emerging import (
    promote_emerging_to_skill,
)


@pytest.fixture
def tmp_library(tmp_path: Path, monkeypatch):
    """Build an isolated SkillLibrary so the test does NOT touch live data."""
    # Stub embedding.encode to avoid sentence-transformers cold start.
    import numpy as np

    from verimem import embedding as emb_mod
    monkeypatch.setattr(
        emb_mod, "encode",
        lambda s: np.zeros(384, dtype=np.float32),
    )
    from verimem.skill import SkillLibrary
    return SkillLibrary(
        dir_path=tmp_path / "skills",
        db_path=tmp_path / "skills_index.db",
    )


def _make_emerging_fact() -> dict:
    """Shape mirrors what cycle 229 register writes."""
    return {
        "id": "29bc77efdd96f6ea",
        "proposition": (
            "Auto-discovered skill: emerging_skill_master-fact\n"
            "Evidence: size=15, purity=0.53, cohesion=0.72, "
            "score=5.77, topic=clp/master-fact\n"
            "Trigger keywords: clp, loop, commands, master, commit, "
            "test, config, recovery\n"
            "Draft preview:\n# emerging_skill_master-fact (DRAFT) ..."
        ),
        "topic": "emerging_skill/auto-discovered/emerging_skill_master-fact",
        "confidence": 0.384,
        "status": "model_claim",
    }


class TestPromoteEmergingToSkill:
    def test_creates_skill_with_candidate_status(
        self, tmp_library,
    ) -> None:
        fact = _make_emerging_fact()
        out = promote_emerging_to_skill(fact, tmp_library)
        assert "skill_id" in out
        skill = tmp_library.get(out["skill_id"])
        assert skill is not None
        assert skill.status == "candidate"

    def test_skill_name_derived_from_topic_slug(
        self, tmp_library,
    ) -> None:
        fact = _make_emerging_fact()
        out = promote_emerging_to_skill(fact, tmp_library)
        skill = tmp_library.get(out["skill_id"])
        # The leaf of the topic path should appear somewhere in name.
        assert "master-fact" in skill.name.lower()

    def test_skill_body_carries_proposition(
        self, tmp_library,
    ) -> None:
        fact = _make_emerging_fact()
        out = promote_emerging_to_skill(fact, tmp_library)
        skill = tmp_library.get(out["skill_id"])
        # Body must include the auto-discovered marker so a reviewer can
        # tell this came from cycle 213-229.
        assert "auto-discovered" in skill.body.lower() or \
               "emerging" in skill.body.lower()

    def test_trigger_keywords_become_trigger(
        self, tmp_library,
    ) -> None:
        fact = _make_emerging_fact()
        out = promote_emerging_to_skill(fact, tmp_library)
        skill = tmp_library.get(out["skill_id"])
        # 'clp' is in the source trigger_keywords; must appear.
        assert "clp" in skill.trigger.lower()

    def test_idempotent_on_repeated_promotion(
        self, tmp_library,
    ) -> None:
        fact = _make_emerging_fact()
        first = promote_emerging_to_skill(fact, tmp_library)
        second = promote_emerging_to_skill(fact, tmp_library)
        # Same skill_id => idempotent.
        assert first["skill_id"] == second["skill_id"]
        # Library must hold only one such skill (filtered by name).
        all_skills = tmp_library.all()
        same_name = [s for s in all_skills if s.name == first["name"]]
        assert len(same_name) == 1

    def test_rejects_non_emerging_topic(self, tmp_library) -> None:
        """A fact NOT under emerging_skill/* must be rejected explicitly."""
        fact = {
            "id": "abc",
            "proposition": "Random fact",
            "topic": "project/clp/some-other-thing",
            "confidence": 0.5,
            "status": "model_claim",
        }
        with pytest.raises(ValueError, match="emerging_skill"):
            promote_emerging_to_skill(fact, tmp_library)

    def test_provenance_records_source_fact_id(
        self, tmp_library,
    ) -> None:
        """Skill.provenance_episodes should include the source fact id
        so the lineage chain stays navigable."""
        fact = _make_emerging_fact()
        out = promote_emerging_to_skill(fact, tmp_library)
        skill = tmp_library.get(out["skill_id"])
        assert fact["id"] in skill.provenance_episodes
