"""Semantic skill duplicate detection — TDD coverage."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np
import pytest

os.environ.setdefault("HIPPO_OFFLINE", "1")
os.environ.setdefault("HIPPO_HOSTED", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


@dataclass
class _FakeSkill:
    """Minimal stand-in for engram.skill.Skill."""
    id: str
    name: str
    trigger: str = ""
    body: str = ""
    status: str = "candidate"
    trials: int = 0
    successes: int = 0


def _pair(s: _FakeSkill, vec: np.ndarray) -> tuple:
    return (s, vec)


def _vec(*x: float) -> np.ndarray:
    v = np.array(x, dtype=np.float32)
    n = np.linalg.norm(v)
    return v / n if n else v


def test_finds_near_identical_pair():
    from engram.skill_semantic_dedup import find_semantic_duplicate_skills
    s1 = _FakeSkill(id="aaa", name="Provide Final Answer", trials=87, successes=38)
    s2 = _FakeSkill(id="bbb", name="Provide Final Answer", trials=86, successes=36)
    s3 = _FakeSkill(id="ccc", name="Totally unrelated", trials=10, successes=5)
    inp = [
        _pair(s1, _vec(1, 0, 0, 0, 0, 0, 0, 0)),
        _pair(s2, _vec(0.999, 0.045, 0, 0, 0, 0, 0, 0)),
        _pair(s3, _vec(0, 1, 0, 0, 0, 0, 0, 0)),
    ]
    out = find_semantic_duplicate_skills(inp, threshold=0.95)
    assert out["n_scanned"] == 3
    pairs = out["pairs"]
    assert len(pairs) == 1, f"expected exactly 1 dup pair, got {pairs}"
    p = pairs[0]
    assert {p["skill_a"], p["skill_b"]} == {"aaa", "bbb"}
    assert p["cosine"] >= 0.99
    assert p["merge_recommendation"] == "aaa"


def test_threshold_excludes_loosely_similar():
    from engram.skill_semantic_dedup import find_semantic_duplicate_skills
    inp = [
        _pair(_FakeSkill(id="a", name="X"), _vec(1, 0, 0, 0)),
        _pair(_FakeSkill(id="b", name="Y"), _vec(0.7, 0.714, 0, 0)),
    ]
    assert find_semantic_duplicate_skills(inp, threshold=0.95)["pairs"] == []


def test_retired_excluded_by_default():
    from engram.skill_semantic_dedup import find_semantic_duplicate_skills
    inp = [
        _pair(_FakeSkill(id="a", name="X"), _vec(1, 0, 0, 0)),
        _pair(_FakeSkill(id="b", name="X clone", status="retired"),
              _vec(0.99, 0.14, 0, 0)),
    ]
    assert find_semantic_duplicate_skills(inp)["pairs"] == []
    out = find_semantic_duplicate_skills(inp, exclude_retired=False)
    assert len(out["pairs"]) == 1


def test_empty_pool_safe():
    from engram.skill_semantic_dedup import find_semantic_duplicate_skills
    assert find_semantic_duplicate_skills([])["pairs"] == []


def test_skips_skills_without_embedding():
    from engram.skill_semantic_dedup import find_semantic_duplicate_skills
    inp = [
        _pair(_FakeSkill(id="a", name="X"), np.array([], dtype=np.float32)),
        _pair(_FakeSkill(id="b", name="Y"), _vec(1, 0, 0, 0)),
        _pair(_FakeSkill(id="c", name="Z"), _vec(0.999, 0.045, 0, 0)),
    ]
    out = find_semantic_duplicate_skills(inp, threshold=0.95)
    assert out["n_scanned"] == 2
    assert len(out["pairs"]) == 1
    assert {out["pairs"][0]["skill_a"], out["pairs"][0]["skill_b"]} == {"b", "c"}


# --- E2E with the LIVE corpus: must surface the real-world dup the
#     audit found (the two "Provide Final Answer" skills 6e9dfdd5d5c7
#     and bbc513ccf05f). Skipped if those skills no longer exist (e.g.
#     after merge).

def test_classification_tags_noise_vs_hot():
    """When ref_counts is supplied, each pair carries a classification."""
    from collections import Counter

    from engram.skill_semantic_dedup import find_semantic_duplicate_skills
    s1 = _FakeSkill(id="hot1", name="X", trials=10, successes=8)
    s2 = _FakeSkill(id="hot2", name="X", trials=10, successes=7)
    s3 = _FakeSkill(id="noise1", name="Y", trials=1, successes=1)
    s4 = _FakeSkill(id="noise2", name="Y", trials=0, successes=0)
    s5 = _FakeSkill(id="dust1", name="Z", trials=0, successes=0)
    s6 = _FakeSkill(id="dust2", name="Z", trials=0, successes=0)
    near = _vec(1, 0, 0, 0)
    near2 = _vec(0.999, 0.045, 0, 0)
    far_a = _vec(0, 1, 0, 0)
    far_b = _vec(0, 0.999, 0.045, 0)
    far2_a = _vec(0, 0, 1, 0)
    far2_b = _vec(0, 0, 0.999, 0.045)
    refs = Counter({"hot1": 20, "hot2": 15, "noise1": 5, "noise2": 0})
    out = find_semantic_duplicate_skills(
        [(s1, near), (s2, near2),
         (s3, far_a), (s4, far_b),
         (s5, far2_a), (s6, far2_b)],
        ref_counts=refs, threshold=0.95,
    )
    by_cls = {p["classification"]: p for p in out["pairs"]}
    assert "hot_clone" in by_cls
    assert "noise_clone" in by_cls
    assert "degenerate" in by_cls
    assert by_cls["hot_clone"]["safe_to_retire"] is None
    assert by_cls["noise_clone"]["safe_to_retire"] == "noise2"
    assert by_cls["degenerate"]["safe_to_retire"] in {"dust1", "dust2"}
    summary = out["summary"]
    assert summary["by_classification"] == {
        "hot_clone": 1, "noise_clone": 1, "degenerate": 1,
    }
    assert summary["n_safe_to_retire"] == 2


def test_real_corpus_finds_known_dup():
    from pathlib import Path

    from engram.config import CONFIG
    db = Path(CONFIG.data_dir) / "skills" / "skills_index.db"
    if not db.exists():
        pytest.skip("no live skill DB available")

    import sqlite3
    with sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True) as c:
        rows = c.execute(
            "SELECT id FROM skills WHERE name = 'Provide Final Answer'"
        ).fetchall()
    ids = {r[0] for r in rows}
    if len(ids) < 2:
        pytest.skip(f"only {len(ids)} 'Provide Final Answer' skill(s) in live DB")

    from engram.skill_semantic_dedup import (
        find_semantic_duplicate_skills,
        load_skills_with_embeddings,
    )

    out = find_semantic_duplicate_skills(
        load_skills_with_embeddings(), threshold=0.90,
    )
    flagged_pairs = [
        p for p in out["pairs"]
        if {p["skill_a"], p["skill_b"]} <= ids
    ]
    assert flagged_pairs, (
        f"semantic dedup missed the 2 known-duplicate 'Provide Final Answer' "
        f"skills {ids} — pairs found: {out['pairs'][:5]}"
    )
