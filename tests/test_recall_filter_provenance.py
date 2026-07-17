"""Cycle #109 S4-A: recall() / search_facts() must filter by provenance status.

Background (Aurelio sfida 2026-05-16): la memoria amplifica hallucination
se i fact ``legacy_unverified`` (eredità pre-cycle-109, no verification)
appaiono allo stesso livello dei fact ``verified``. Le 815 righe
``legacy_unverified`` nel corpus live diventerebbero "verità" se Claude le
ripescasse senza distinguere.

Design:

* Add kw-only ``exclude_legacy: bool = False`` and ``min_status: str | None
  = None`` to :meth:`SemanticMemory.recall` and
  :meth:`SemanticMemory.search_facts`.
* Default behaviour stays retro-compatible (no filter): MCP wrapper
  flips to the safe default in S4-A part 2.
* Status hierarchy (highest trust first): ``verified > model_claim >
  provisional > legacy_unverified``. ``min_status="model_claim"`` keeps
  verified + model_claim, drops provisional + legacy_unverified.

These tests RED before impl, GREEN after.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

import pytest

from verimem.semantic import Fact, SemanticMemory


def _make_repo(tmp_path: Path) -> tuple[Path, str, Path]:
    """Cycle #111 v2 helper: build a tmp git repo with one file + one
    commit so that the v2 hard-gate has real I/O targets to verify
    against. Returns (repo_root, head_sha, file_path)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=repo, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Cycle 111 Test"],
        cwd=repo, check=True,
    )
    src = repo / "src.py"
    src.write_text("\n".join(f"line_{i}" for i in range(1, 11)) + "\n",
                   encoding="utf-8")
    subprocess.run(["git", "add", "src.py"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "cycle111-v2 fixture commit"],
        cwd=repo, check=True,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return repo, head, src


def _seed(
    mem: SemanticMemory, *, verified_ref: str,
) -> dict[str, Fact]:
    """Seed the memory with one fact per status. The 'verified' fact
    uses ``verified_ref`` which must pass the cycle 111 v2 hard-gate
    against the SemanticMemory's repo_root."""
    facts = {
        "verified": Fact(
            id="f-verified", proposition="alpha verified knowledge",
            topic="lessons/test", confidence=0.95,
            status="verified",
            verified_by=[verified_ref],
        ),
        "model_claim": Fact(
            id="f-model", proposition="alpha model claim knowledge",
            topic="lessons/test", confidence=0.7,
            status="model_claim",
        ),
        "provisional": Fact(
            id="f-prov", proposition="alpha provisional research finding",
            topic="research/test", confidence=0.6,
            status="provisional",
            verified_by=["url:arxiv.org/abs/2310.11511"],
        ),
        "legacy_unverified": Fact(
            id="f-legacy", proposition="alpha legacy unverified inheritance",
            topic="lessons/test", confidence=0.5,
            status="legacy_unverified",
        ),
    }
    for f in facts.values():
        mem.store(f)
    return facts


@pytest.fixture
def mem(tmp_path: Path) -> SemanticMemory:
    """Cycle #111 v2: build a tmp git repo so the verified seed fact
    survives the I/O hard-gate."""
    repo, head_sha, _src = _make_repo(tmp_path)
    db = tmp_path / "sem.db"
    m = SemanticMemory(db_path=db, repo_root=repo)
    _seed(m, verified_ref=f"commit {head_sha[:12]}")
    return m


class TestRecallDefaultBackwardsCompatible:
    """Pre-cycle-109 callers must keep working: default recall returns all."""

    def test_recall_default_returns_all_statuses(self, mem: SemanticMemory) -> None:
        hits = mem.recall("alpha", k=10)
        statuses = {f.status for f, _ in hits}
        assert statuses == {
            "verified", "model_claim", "provisional", "legacy_unverified"
        }


class TestRecallExcludeLegacy:
    """``exclude_legacy=True`` drops only legacy_unverified rows."""

    def test_exclude_legacy_filters_legacy_unverified(
        self, mem: SemanticMemory,
    ) -> None:
        hits = mem.recall("alpha", k=10, exclude_legacy=True)
        statuses = {f.status for f, _ in hits}
        assert "legacy_unverified" not in statuses
        # other statuses still present
        assert {"verified", "model_claim", "provisional"} <= statuses

    def test_exclude_legacy_preserves_topic_filter(
        self, mem: SemanticMemory,
    ) -> None:
        hits = mem.recall(
            "alpha", k=10, topic="lessons/test", exclude_legacy=True,
        )
        ids = {f.id for f, _ in hits}
        # only verified + model_claim are in lessons/test (legacy excluded)
        assert ids == {"f-verified", "f-model"}


class TestRecallMinStatus:
    """``min_status`` enforces a hierarchical trust floor."""

    def test_min_status_verified_returns_only_verified(
        self, mem: SemanticMemory,
    ) -> None:
        hits = mem.recall("alpha", k=10, min_status="verified")
        assert [f.id for f, _ in hits] == ["f-verified"]

    def test_min_status_model_claim_excludes_legacy_and_provisional(
        self, mem: SemanticMemory,
    ) -> None:
        hits = mem.recall("alpha", k=10, min_status="model_claim")
        ids = {f.id for f, _ in hits}
        assert ids == {"f-verified", "f-model"}

    def test_min_status_provisional_excludes_only_legacy(
        self, mem: SemanticMemory,
    ) -> None:
        hits = mem.recall("alpha", k=10, min_status="provisional")
        ids = {f.id for f, _ in hits}
        assert ids == {"f-verified", "f-model", "f-prov"}

    def test_min_status_invalid_raises(self, mem: SemanticMemory) -> None:
        with pytest.raises(ValueError, match="min_status"):
            mem.recall("alpha", k=10, min_status="bogus")


class TestSearchFactsExcludeLegacy:
    """``search_facts`` (substring SQL) gets the same filter API."""

    def test_default_returns_all(self, mem: SemanticMemory) -> None:
        results = mem.search_facts("alpha", limit=10)
        statuses = {f.status for f in results}
        assert "legacy_unverified" in statuses

    def test_exclude_legacy_filters(self, mem: SemanticMemory) -> None:
        results = mem.search_facts("alpha", limit=10, exclude_legacy=True)
        statuses = {f.status for f in results}
        assert "legacy_unverified" not in statuses

    def test_min_status_verified(self, mem: SemanticMemory) -> None:
        results = mem.search_facts("alpha", limit=10, min_status="verified")
        assert [f.id for f in results] == ["f-verified"]


class TestRecallStatusVisibility:
    """Returned ``Fact`` objects must expose ``status`` field — already
    enforced by cycle #109 S1, here we re-assert at the recall-path level."""

    def test_recall_results_carry_status(self, mem: SemanticMemory) -> None:
        hits = mem.recall("alpha", k=10)
        for f, _sim in hits:
            assert f.status in {
                "verified", "model_claim", "provisional", "legacy_unverified",
            }
            assert hasattr(f, "verified_by")

    def test_search_facts_results_carry_status(
        self, mem: SemanticMemory,
    ) -> None:
        results = mem.search_facts("alpha", limit=10)
        for f in results:
            assert f.status in {
                "verified", "model_claim", "provisional", "legacy_unverified",
            }
