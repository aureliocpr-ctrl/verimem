"""Cycle #141 (2026-05-18 sera) — 4D importance composite (SCM gap).

Aurelio direttiva 2026-05-18: HippoAgent deve essere infallibile su
qualsiasi task. La cross-memory deve essere sfruttata sempre. SCM paper
arxiv 2604.20943 ha 4D importance composite che noi non abbiamo (cycle
141 subagent F WAVE 2 hallucinated, file fantasma). Adesso implemento
IO diretto, no subagent.

SCM formula (paper section Importance Tagging):
    I(c) = 0.30·novelty + 0.20·|valence| + 0.35·task + 0.15·repetition

Dove:
- novelty   ∈ [0,1]: 1 - max(cosine_to_existing_episodes) → 1.0 se nessun
                    episode simile, 0.0 se duplicato perfetto
- |valence| ∈ [0,1]: abs(sentiment) — high su parole emotive (bug/fix/
                    error/success/etc), low su task neutri
- task      ∈ [0,1]: cosine(episode, self_model_focus) → match goal corrente
- repetition ∈ [0,1]: log(1+count_same_topic) / log(1+max_count) → high su
                     topic ricorrente

Backward compat: `compute_salience` 1D resta com'è. NEW: `compute_salience_4d`
ritorna dict {novelty, valence, task, repetition, composite}.

Test BACK-COMPAT obbligatorio: il vecchio metodo NON cambia output.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from engram.episode import Episode
from engram.memory import EpisodicMemory


def _mk_episode(
    task_text: str,
    final_answer: str = "ok",
    outcome: str = "success",
    task_id: str = "test/cycle141",
) -> Episode:
    return Episode(
        task_id=task_id,  # used as proxy for "topic" on episodes
        task_text=task_text,
        final_answer=final_answer,
        outcome=outcome,
        created_at=time.time(),
    )


@pytest.fixture
def empty_mem(tmp_path: Path) -> EpisodicMemory:
    return EpisodicMemory(db_path=tmp_path / "ep.db")


@pytest.fixture
def seeded_mem(tmp_path: Path) -> EpisodicMemory:
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    # Seed 5 episodes on topic "trading/eth-trend"
    for i in range(5):
        mem.store(_mk_episode(
            task_text=f"analyze ETH trend day {i}",
            final_answer=f"bullish continuation #{i}",
            outcome="success",
            task_id="trading/eth-trend",
        ))
    # Seed 1 unrelated topic
    mem.store(_mk_episode(
        task_text="refactor auth module",
        final_answer="extracted to auth.py",
        outcome="success",
        task_id="code/refactor",
    ))
    return mem


class TestComputeSalience4DContract:
    """The new compute_salience_4d returns a dict with exactly 5 keys."""

    def test_returns_dict_with_5_keys(self, empty_mem: EpisodicMemory) -> None:
        ep = _mk_episode("first ever task")
        out = empty_mem.compute_salience_4d(ep)
        assert isinstance(out, dict)
        expected_keys = {"novelty", "valence", "task", "repetition", "composite"}
        assert set(out.keys()) == expected_keys, (
            f"cycle 141: keys must be exactly {expected_keys}, got {set(out.keys())}"
        )

    def test_all_components_in_unit_interval(
        self, seeded_mem: EpisodicMemory,
    ) -> None:
        ep = _mk_episode("brand new task no overlap")
        out = seeded_mem.compute_salience_4d(ep)
        for k in ("novelty", "valence", "task", "repetition", "composite"):
            v = out[k]
            assert 0.0 <= v <= 1.0, (
                f"cycle 141: '{k}'={v!r} must be in [0,1]"
            )


class TestCompositeFormula:
    """The composite must equal the SCM weighted sum within float epsilon."""

    def test_composite_matches_scm_formula(
        self, seeded_mem: EpisodicMemory,
    ) -> None:
        ep = _mk_episode("analyze ETH trend bullish moment")
        out = seeded_mem.compute_salience_4d(ep)
        expected = (
            0.30 * out["novelty"]
            + 0.20 * out["valence"]
            + 0.35 * out["task"]
            + 0.15 * out["repetition"]
        )
        assert abs(out["composite"] - expected) < 1e-6, (
            f"cycle 141: composite must equal SCM weighted sum 0.30·n + "
            f"0.20·|v| + 0.35·t + 0.15·r. Got composite={out['composite']!r} "
            f"vs expected={expected!r}"
        )


class TestNoveltyAxis:
    """Novelty: 1.0 on empty corpus, low on near-duplicate."""

    def test_novelty_max_on_empty_corpus(
        self, empty_mem: EpisodicMemory,
    ) -> None:
        ep = _mk_episode("first ever task on empty store")
        out = empty_mem.compute_salience_4d(ep)
        assert out["novelty"] >= 0.95, (
            f"cycle 141: empty-corpus novelty must approach 1.0, got "
            f"{out['novelty']!r}"
        )

    def test_novelty_low_on_near_duplicate(
        self, seeded_mem: EpisodicMemory,
    ) -> None:
        # An episode whose task text is almost identical to seeded ones.
        ep = _mk_episode("analyze ETH trend day 7")  # near-dup of seeded 0..4
        out = seeded_mem.compute_salience_4d(ep)
        assert out["novelty"] < 0.6, (
            f"cycle 141: near-duplicate novelty must drop below 0.6, got "
            f"{out['novelty']!r}"
        )


class TestRepetitionAxis:
    """Repetition: high when many same-topic episodes exist."""

    def test_repetition_high_on_repeated_topic(
        self, seeded_mem: EpisodicMemory,
    ) -> None:
        # 5 episodes on trading/eth-trend already seeded.
        ep = _mk_episode(
            "new ETH analysis but same topic",
            task_id="trading/eth-trend",
        )
        out = seeded_mem.compute_salience_4d(ep)
        assert out["repetition"] > 0.5, (
            f"cycle 141: 5-episode-topic repetition must exceed 0.5, got "
            f"{out['repetition']!r}"
        )

    def test_repetition_zero_on_brand_new_topic(
        self, seeded_mem: EpisodicMemory,
    ) -> None:
        ep = _mk_episode(
            "totally fresh subject",
            task_id="research/quantum-foam-cosmology",
        )
        out = seeded_mem.compute_salience_4d(ep)
        assert out["repetition"] < 0.1, (
            f"cycle 141: brand-new-topic repetition must be near 0, got "
            f"{out['repetition']!r}"
        )


class TestValenceAxis:
    """Valence: high on emotion-loaded text."""

    def test_valence_high_on_emotion_keywords(
        self, empty_mem: EpisodicMemory,
    ) -> None:
        ep = _mk_episode(
            "CRITICAL bug found — ERROR cascade caused production FAILURE",
            final_answer="emergency rollback, system restored",
            outcome="failure",
        )
        out = empty_mem.compute_salience_4d(ep)
        assert out["valence"] > 0.3, (
            f"cycle 141: emotion-loaded text valence must exceed 0.3, got "
            f"{out['valence']!r}"
        )

    def test_valence_low_on_neutral_text(
        self, empty_mem: EpisodicMemory,
    ) -> None:
        ep = _mk_episode(
            "list files in working directory",
            final_answer="file1.txt file2.txt",
        )
        out = empty_mem.compute_salience_4d(ep)
        assert out["valence"] < 0.3, (
            f"cycle 141: neutral text valence must stay below 0.3, got "
            f"{out['valence']!r}"
        )


class TestBackwardCompatCompute1D:
    """The 1D compute_salience must still return a float — NOT a dict.

    Cycle 141 must be ADDITIVE: existing callers of compute_salience
    that expect float must keep working unchanged.
    """

    def test_1d_compute_salience_still_returns_float(
        self, seeded_mem: EpisodicMemory,
    ) -> None:
        ep = _mk_episode("any task")
        out = seeded_mem.compute_salience(ep)
        assert isinstance(out, float), (
            f"cycle 141 back-compat: compute_salience must still return "
            f"float, got {type(out).__name__}"
        )
        assert 0.0 <= out <= 1.0
