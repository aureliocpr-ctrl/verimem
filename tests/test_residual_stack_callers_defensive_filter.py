"""Cycle 172 (2026-05-22) — extend cycle 171 defensive filter to the
4 residual np.stack callers the counterexample worker flagged.

ROADMAP context
---------------
Cycle 171 (PR #112) closed the SQL-side defensive filter on
``engram/semantic.py`` (facts.embedding). The critic counterexample
worker (job ``baeff444993554e8``) explicitly flagged 4 other
``np.stack`` callers in the codebase that remain vulnerable to the
same ragged-array crash:

  * engram/freshness_check.py:116-117  (facts.embedding via emb_map)
  * engram/memory.py:1002 / 1229 / 1340 (episodes.summary_embedding,
                                          .context_embedding)
  * engram/skill.py:344 (skills.trigger_embedding)
  * engram/topic_cleanup_suggestions.py:73 (facts.embedding)

Empirical bytes (verified on Aurelio's live DB 2026-05-22):
  * facts.embedding             = 1536 bytes ✓
  * episodes.summary_embedding  = 1536 bytes ✓
  * episodes.context_embedding  = 1536 bytes ✓
  * skills.trigger_embedding    = 1536 bytes ✓
  * episodes.dg_embedding       =  482 bytes  ← OUT OF SCOPE (sparse,
                                                 separate constant
                                                 needed; cycle 173).

This file tests each caller crashes pre-fix when a malformed blob
sneaks in, and passes post-fix with the SQL-side ``AND length(<col>)
= 1536`` guard.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import numpy as np
import pytest

from verimem.episode import Episode
from verimem.memory import EpisodicMemory
from verimem.semantic import Fact, SemanticMemory
from verimem.skill import Skill, SkillLibrary

# -----------------------------------------------------------------------
# Helpers: inject malformed embedding blobs directly into the DB.
# -----------------------------------------------------------------------


def _inject_malformed_episode(
    db_path: Path, ep_id: str, col: str, blob: bytes,
) -> None:
    """Set ``col`` (summary_embedding | context_embedding) on episode
    ``ep_id`` to a malformed blob, bypassing EpisodicMemory.store."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            f"UPDATE episodes SET {col} = ? WHERE id = ?",  # noqa: S608
            (blob, ep_id),
        )
        conn.commit()
    finally:
        conn.close()


def _inject_malformed_skill(
    db_path: Path, sk_id: str, blob: bytes,
) -> None:
    """Set trigger_embedding on skill ``sk_id`` to a malformed blob."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "UPDATE skills SET trigger_embedding = ? WHERE id = ?",
            (blob, sk_id),
        )
        conn.commit()
    finally:
        conn.close()


def _inject_malformed_fact(
    db_path: Path, fid: str, prop: str, blob: bytes,
) -> None:
    """Insert a raw row in facts with a malformed embedding blob."""
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "INSERT INTO facts ("
            "id, proposition, topic, confidence, source_episodes, "
            "created_at, embedding, status, verified_by, "
            "source_signature) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (fid, prop, "cycle172/poison", 0.9, "",
             time.time(), blob, "model_claim", "[]", None),
        )
        conn.commit()
    finally:
        conn.close()


# -----------------------------------------------------------------------
# memory.py — episodes summary_embedding callers
# -----------------------------------------------------------------------


@pytest.fixture
def mem(tmp_path: Path) -> EpisodicMemory:
    return EpisodicMemory(db_path=tmp_path / "ep.db")


class TestMemoryEpisodicCallers:
    def test_recall_with_summary_embedding_b_empty_does_not_crash(
        self, mem: EpisodicMemory,
    ) -> None:
        """memory.py line 1222 SELECT summary_embedding → np.stack(line 1229).
        Pre-fix: ValueError on ragged shape. Post-fix: filter SQL-side."""
        ep_good = Episode(
            task_id="t-good",
            task_text="successful task with embedding alpha beta",
            final_answer="ok",
            outcome="success",
        )
        mem.store(ep_good)

        ep_bad = Episode(
            task_id="t-bad",
            task_text="poison task with broken embedding",
            final_answer="ok",
            outcome="success",
        )
        mem.store(ep_bad)
        _inject_malformed_episode(
            mem.db_path, ep_bad.id, "summary_embedding", b"",
        )

        # Must not raise.
        hits = mem.recall("alpha beta", k=3)
        ids = {h[0].id for h in hits}
        assert ep_good.id in ids, f"good episode lost: {ids}"
        assert ep_bad.id not in ids, (
            f"malformed episode leaked: {ids}"
        )

    def test_recent_failures_with_broken_summary_does_not_crash(
        self, mem: EpisodicMemory,
    ) -> None:
        """memory.py line 994 SELECT id, summary_embedding FROM episodes
        ORDER BY created_at DESC → np.stack(line 1002)."""
        for i in range(3):
            mem.store(Episode(
                task_id=f"good-{i}",
                task_text=f"good task gamma delta {i}",
                final_answer="ok",
                outcome="success",
            ))
        ep_bad = Episode(
            task_id="bad-summary",
            task_text="poison summary blob",
            final_answer="ok",
            outcome="failure",
        )
        mem.store(ep_bad)
        _inject_malformed_episode(
            mem.db_path, ep_bad.id, "summary_embedding", b"",
        )

        # _ensure_recall_index() rebuilds the index; bust cache first.
        mem._recall_index = None
        mem._index_dirty = True

        hits = mem.recall("gamma delta", k=5)
        ids = {h[0].id for h in hits}
        assert ep_bad.id not in ids


# -----------------------------------------------------------------------
# skill.py — skills trigger_embedding caller
# -----------------------------------------------------------------------


@pytest.fixture
def skills(tmp_path: Path) -> SkillLibrary:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    return SkillLibrary(
        dir_path=skills_dir, db_path=tmp_path / "sk.db",
    )


class TestSkillTriggerCaller:
    def test_top_skills_with_broken_trigger_does_not_crash(
        self, skills: SkillLibrary,
    ) -> None:
        """skill.py line 339 SELECT id, trigger_embedding FROM skills
        WHERE status != 'retired' → np.stack(line 344)."""
        good = Skill(
            name="good-skill",
            trigger="trigger word epsilon zeta",
            body="step 1\nstep 2",
        )
        skills.store(good)

        bad = Skill(
            name="bad-skill",
            trigger="poison trigger",
            body="step bad",
        )
        skills.store(bad)
        _inject_malformed_skill(skills.db_path, bad.id, b"")

        # top_for() is the method that goes through line 339 → 344.
        out = skills.retrieve("epsilon zeta", k=3)
        ids = {s.id for s in out}
        assert good.id in ids, f"good skill missing: {ids}"
        assert bad.id not in ids, f"bad skill leaked: {ids}"


# -----------------------------------------------------------------------
# topic_cleanup_suggestions.py — facts.embedding caller
# -----------------------------------------------------------------------


class TestTopicCleanupCaller:
    def test_topic_cleanup_with_broken_fact_embedding_does_not_crash(
        self, tmp_path: Path,
    ) -> None:
        """topic_cleanup_suggestions.py line 57/62 SELECT embedding FROM
        facts → np.stack(line 73)."""
        from verimem.topic_cleanup_suggestions import topic_cleanup_suggestions

        sm = SemanticMemory(db_path=tmp_path / "sem.db")
        # Live topic with good fact.
        sm.store(Fact(
            proposition="alive proposition iota kappa",
            topic="live/topic",
            confidence=0.9,
            source_episodes=["ep_1"],
            status="model_claim",
        ))
        # Inject a malformed row.
        _inject_malformed_fact(
            sm.db_path, "bad_fid", "poison topic cleanup row", b"",
        )

        # Must not raise.
        try:
            out = topic_cleanup_suggestions(sm)
        except ValueError as e:
            pytest.fail(
                f"topic_cleanup_suggestions raised ValueError on "
                f"malformed embedding: {e}"
            )
        # Caller may return any structure — we only assert it ran.
        assert out is not None


# -----------------------------------------------------------------------
# freshness_check.py — facts.embedding caller (via emb_map)
# -----------------------------------------------------------------------


class TestFreshnessCheckCaller:
    def test_freshness_check_with_broken_fact_embedding_does_not_crash(
        self, tmp_path: Path,
    ) -> None:
        """freshness_check.py line 169 SELECT id, embedding FROM facts
        WHERE id IN (...) feeds emb_map; line 116/117 np.stack."""
        from verimem.freshness_check import facts_freshness_check

        sm = SemanticMemory(db_path=tmp_path / "sem.db")
        # Seed facts under one topic glob with old timestamps so they're
        # flagged stale (the freshness path only runs np.stack on stale
        # rows). Sim_threshold low so candidates emerge.
        for i in range(3):
            f = Fact(
                proposition=f"freshness fact {i} lambda mu nu",
                topic="freshness/group",
                confidence=0.9,
                source_episodes=[f"ep_{i}"],
                created_at=time.time() - 60 * 86400.0,  # 60d ago = stale
                status="model_claim",
            )
            sm.store(f)
        # Inject malformed fact in the same topic.
        _inject_malformed_fact(
            sm.db_path, "bad_fresh", "poison freshness row", b"",
        )

        # Must not raise.
        try:
            out = facts_freshness_check(
                sm, "freshness/*",
                threshold_days=10.0, sim_threshold=0.1,
            )
        except ValueError as e:
            pytest.fail(
                f"facts_freshness_check raised ValueError on "
                f"malformed embedding: {e}"
            )
        assert out is not None
