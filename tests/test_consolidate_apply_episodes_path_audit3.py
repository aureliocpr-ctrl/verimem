"""audit#3-r3 R4: ``engram consolidate apply`` must persist the master Episode
to the CANONICAL episodes DB (``CONFIG.episodes_db`` layout =
``<data>/episodes/episodes.db``), NOT a flat ``<data>/episodes.db`` that
nothing else reads.

Pre-fix ``_consolidate_em()`` hardcoded the flat path while ``_facts_sm()`` (and
``CONFIG.episodes_db``, used by the MCP server and every normal
``EpisodicMemory()``) use the subdir layout. So on a standard install the
master Fact's ``source_episodes`` pointed at an Episode written to an orphan
file — lineage master-fact -> episode silently resolved to nothing.
"""
from __future__ import annotations

from engram.memory import EpisodicMemory
from engram.semantic import Fact


def _seed_cluster(sm, prefix: str = "proj/alpha", n: int = 4) -> None:
    for i in range(n):
        sm.store(
            Fact(
                proposition=f"{prefix} detail number {i} is settled and true",
                topic=f"{prefix}/item{i}",
                confidence=0.9,
                status="verified",
                source_episodes=[f"seed{i}"],
            )
        )


def test_consolidate_apply_writes_master_episode_to_canonical_subdir(
    tmp_path, monkeypatch
):
    # Isolate the corpus to tmp. _facts_data_dir checks ENGRAM_DATA_DIR FIRST,
    # then HIPPO_DATA_DIR — pin both so a maintainer's ~/.engram never leaks in.
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    from engram import cli

    sm = cli._facts_sm()  # creates tmp/semantic/semantic.db (canonical subdir)
    _seed_cluster(sm, n=4)

    cli.consolidate_apply(min_size=2, prefix_depth=2)

    canonical = tmp_path / "episodes" / "episodes.db"
    flat = tmp_path / "episodes.db"

    master = next(
        f for f in sm.all() if f.proposition.startswith("AUTO-CLUSTER-MASTER")
    )
    assert master.source_episodes, "master fact has no source Episode id"
    ep_id = master.source_episodes[0]

    assert canonical.exists(), (
        "canonical episodes DB <data>/episodes/episodes.db was never created — "
        "consolidate apply wrote the master Episode to the wrong path"
    )
    canon_em = EpisodicMemory(db_path=canonical)
    assert canon_em.get(ep_id) is not None, (
        "master Episode not found in canonical <data>/episodes/episodes.db; "
        "the master Fact's source_episodes points at an unreadable Episode"
    )

    if flat.exists():
        flat_em = EpisodicMemory(db_path=flat)
        assert flat_em.get(ep_id) is None, (
            "master Episode leaked into orphan flat <data>/episodes.db"
        )
