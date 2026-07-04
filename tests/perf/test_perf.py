"""Performance benchmarks for HippoAgent hot paths.

Run with:
    pytest tests/perf/test_perf.py --benchmark-only
    pytest tests/perf/test_perf.py --benchmark-only --benchmark-json=out.json

Markers:
    pytest tests/perf/test_perf.py -m perf

Budgets (CI gate, see RND_PERFORMANCE.md):
    skill.find_duplicates (1k)        P95 < 200 ms
    skill.cluster_by_embedding (1k)   P95 < 200 ms
    memory.recall (5k, k=5)           P95 <  50 ms
    memory.cluster_similar (5k)       P95 < 5000 ms
    semantic.recall (500, k=5)        P95 <  30 ms
    repomap.build_repomap (1k cold)   P95 < 1000 ms
    repomap.build_repomap (1k warm)   P95 < 200 ms
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tests.perf.seed_data import seed_all

pytestmark = [pytest.mark.perf, pytest.mark.slow]


@pytest.fixture(scope="module")
def seeded(tmp_path_factory):
    """Seed once per test module — 1k skills, 5k episodes, 500 facts, 1k repo files."""
    base = Path(tmp_path_factory.mktemp("perf_seed"))
    paths = seed_all(base)
    return paths


@pytest.fixture
def patch_config(seeded):
    """Override the (frozen) Config dataclass to point at seeded paths.

    monkeypatch.setattr can't traverse `frozen=True`; we use `object.__setattr__`
    directly and restore the originals after the test.
    """
    from engram.config import CONFIG
    keys = ["skills_dir", "skills_db", "episodes_db", "semantic_db"]
    originals = {k: getattr(CONFIG, k) for k in keys}
    object.__setattr__(CONFIG, "skills_dir", seeded["skills_dir"])
    object.__setattr__(CONFIG, "skills_db", seeded["skills_db"])
    object.__setattr__(CONFIG, "episodes_db", seeded["episodes_db"])
    object.__setattr__(CONFIG, "semantic_db", seeded["semantic_db"])
    yield seeded
    for k, v in originals.items():
        object.__setattr__(CONFIG, k, v)


@pytest.fixture
def skills(patch_config):
    from engram.skill import SkillLibrary
    sl = SkillLibrary(
        dir_path=patch_config["skills_dir"],
        db_path=patch_config["skills_db"],
    )
    # Warm up the cache so the first benchmark iteration is representative
    # of repeated calls during a sleep cycle.
    sl.all()
    return sl


@pytest.fixture
def memory(patch_config):
    from engram.memory import EpisodicMemory
    mem = EpisodicMemory(db_path=patch_config["episodes_db"])
    mem._ensure_recall_index()  # warm up
    return mem


@pytest.fixture
def semantic(patch_config):
    from engram.semantic import SemanticMemory
    return SemanticMemory(db_path=patch_config["semantic_db"])


def test_skill_find_duplicates(benchmark, skills):
    """Vectorised pairwise similarity over 1k skills.

    Budget: P95 < 200 ms.
    """
    benchmark(skills.find_duplicates)


def test_skill_cluster_by_embedding(benchmark, skills):
    """Connected-component clustering over 1k skills.

    Budget: P95 < 200 ms.
    """
    benchmark(skills.cluster_by_embedding)


def test_skill_retrieve_topk(benchmark, skills):
    """Single-query top-k retrieval over 1k skills.

    Budget: P95 < 50 ms.
    """
    benchmark(lambda: skills.retrieve("optimize python performance", k=5))


def test_memory_recall_unfiltered(benchmark, memory):
    """Top-k recall over 5k episodes — unfiltered hot path.

    Budget: P95 < 50 ms.
    """
    benchmark(lambda: memory.recall("debug python error", k=5))


def test_memory_recall_filtered(benchmark, memory):
    """Top-k recall with outcome filter — falls back to SQL scan.

    Budget: P95 < 250 ms.
    """
    benchmark(lambda: memory.recall("debug python error", k=5, outcome_filter="success"))


def test_semantic_recall(benchmark, semantic):
    """Top-k recall over 500 facts.

    Budget: P95 < 30 ms.
    """
    benchmark(lambda: semantic.recall("python optimization", k=5))


def test_repomap_cold(benchmark, patch_config, tmp_path):
    """Build repomap with NO existing cache — cold I/O path.

    Budget: P95 < 1000 ms.
    """
    from engram.repomap import build_repomap

    cache = tmp_path / "rmap_cache.json"
    benchmark(lambda: build_repomap(
        patch_config["repo_root"], cache_path=cache, use_cache=False,
    ))


def test_repomap_warm(benchmark, patch_config, tmp_path):
    """Build repomap with a populated cache — warm hot-reload path.

    Budget: P95 < 200 ms.
    """
    from engram.repomap import build_repomap

    cache = tmp_path / "rmap_cache.json"
    # Prime cache once
    build_repomap(patch_config["repo_root"], cache_path=cache, use_cache=True)

    benchmark(lambda: build_repomap(
        patch_config["repo_root"], cache_path=cache, use_cache=True,
    ))


def test_embedding_encode_cache_hit(benchmark):
    """LRU cache hit on a single re-encoded text.

    Budget: P95 < 0.1 ms.
    """
    from engram import embedding
    text = "task example warm cache"
    embedding.encode(text)  # populate cache once
    benchmark(lambda: embedding.encode(text))


# Smoke test: ensure the seeded data has the expected shape. Not a
# benchmark — annotated so `pytest --benchmark-only` skips it cleanly.
@pytest.mark.benchmark(disable_gc=False)
def test_seed_shape(benchmark, patch_config):
    skills_dir = patch_config["skills_dir"]
    n_skill_files = sum(1 for _ in skills_dir.glob("*.json"))
    assert n_skill_files == 1000
    benchmark(lambda: None)
