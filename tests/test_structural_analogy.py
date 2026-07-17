"""Tests for FORGIA pezzo #210 — Pezzo C: structural analogy.

Gentner (1983) "Structure-mapping: A theoretical framework for
analogy", Cognitive Science 7:155–170. The cognitive insight:
analogy is matching by RELATIONAL STRUCTURE, not by surface
similarity. "Atom is like solar system" works because both are
"smaller things orbit a central larger thing", not because atoms
look like planets.

For HippoAgent: when the user faces a task with NO semantically-
similar skill in the library, we should still surface skills with
similar PROCEDURAL STRUCTURE that might transfer. Operationally:

  structural_signature(skill) = bag-of-tokens from
      name + trigger + preconditions + postconditions

  structural_jaccard(A, B) = |A ∩ B| / |A ∪ B|

  is_analogue(target, candidate) iff
      structural_jaccard(target, candidate) ≥ θ_struct
      AND semantic_cosine(target, candidate) ≤ θ_sem

The interesting case is HIGH structural / LOW semantic — that's a
true analogy, not "same kind of thing said differently".

Six invariants:

  1. SIGNATURE EMPTY for empty skill → empty signature.
  2. SIGNATURE includes name + trigger + pre + post tokens.
  3. JACCARD(x, x) == 1.0 (reflexive).
  4. JACCARD(x, y) == JACCARD(y, x) (symmetric).
  5. find_analogues filters BOTH thresholds (structural high,
     semantic low).
  6. Self is excluded from candidates (a skill is not its own
     analogy).
"""
from __future__ import annotations

import numpy as np

from verimem.skill import Skill


def test_structural_signature_empty_skill():
    from verimem.analogy import structural_signature

    s = Skill()
    sig = structural_signature(s)
    # Empty default skill: empty signature.
    assert sig == set()


def test_structural_signature_extracts_all_fields():
    """Signature should include tokens from name + trigger + pre/post."""
    from verimem.analogy import structural_signature

    s = Skill(
        name="deploy_web",
        trigger="deploy a web app to production",
        preconditions=["have_credentials"],
        postconditions=["app_live"],
    )
    sig = structural_signature(s)
    assert "deploy" in sig
    assert "web" in sig
    assert "production" in sig
    assert "credentials" in sig
    assert "app" in sig


def test_structural_signature_lowercases_and_dedupes():
    from verimem.analogy import structural_signature

    s = Skill(name="Deploy", trigger="deploy DEPLOY")
    sig = structural_signature(s)
    # Lowercased, deduped.
    assert "deploy" in sig
    assert "Deploy" not in sig


def test_jaccard_reflexive():
    from verimem.analogy import structural_jaccard

    a = {"deploy", "web", "to", "production"}
    assert structural_jaccard(a, a) == 1.0


def test_jaccard_symmetric():
    from verimem.analogy import structural_jaccard

    a = {"deploy", "web", "to", "aws"}
    b = {"deploy", "mobile", "to", "gcp"}
    assert structural_jaccard(a, b) == structural_jaccard(b, a)


def test_jaccard_disjoint_is_zero():
    from verimem.analogy import structural_jaccard

    a = {"alpha", "beta"}
    b = {"gamma", "delta"}
    assert structural_jaccard(a, b) == 0.0


def test_jaccard_partial_overlap():
    from verimem.analogy import structural_jaccard

    a = {"x", "y", "z"}
    b = {"y", "z", "w"}
    # |∩|=2, |∪|=4 → 0.5
    assert abs(structural_jaccard(a, b) - 0.5) < 1e-9


def test_jaccard_both_empty_is_zero():
    """Convention: empty/empty is 0 (no signal), not 1 (trivial match)."""
    from verimem.analogy import structural_jaccard

    assert structural_jaccard(set(), set()) == 0.0


# ---------- find_structural_analogues ------------------------------------


def _semantic_distance_from_pairs(distances: dict[tuple[str, str], float]):
    """Build a pluggable semantic-distance fn from a (a_id, b_id) → cosine
    dict. Returns 0.0 for unknown pairs (treated as identical, hence
    NOT analogues — this is the safe default)."""
    def _dist(a: Skill, b: Skill) -> float:
        return distances.get((a.id, b.id), distances.get((b.id, a.id), 0.0))
    return _dist


def test_find_analogues_filters_high_semantic():
    """A candidate that is ALSO semantically similar (cosine high)
    is a near-duplicate, not an analogy. Must be excluded."""
    from verimem.analogy import find_structural_analogues

    target = Skill(id="t", name="deploy_web", trigger="deploy web to aws")
    # Candidate with high structural overlap AND high semantic sim.
    # cosine 0.9 means very similar in embedding space.
    duplicate = Skill(id="d", name="deploy_web_v2",
                      trigger="deploy web to aws")
    cosine_table = {("t", "d"): 0.9}
    out = find_structural_analogues(
        target, [duplicate],
        semantic_cosine_fn=lambda a, b: cosine_table.get((a.id, b.id), 0.0),
        min_structural=0.4,
        max_semantic=0.5,
    )
    assert out == [], (
        "high-semantic candidate is a duplicate, must be filtered"
    )


def test_find_analogues_filters_low_structural():
    """Structurally distant candidates are filtered too."""
    from verimem.analogy import find_structural_analogues

    target = Skill(id="t", name="deploy_web", trigger="deploy web to aws")
    distant = Skill(id="d", name="parse_json",
                    trigger="parse JSON file")
    out = find_structural_analogues(
        target, [distant],
        semantic_cosine_fn=lambda a, b: 0.0,
        min_structural=0.4,
        max_semantic=0.5,
    )
    assert out == []


def test_find_analogues_returns_high_struct_low_sem():
    """The interesting case: high structural overlap, low semantic
    cosine → a true analogy."""
    from verimem.analogy import find_structural_analogues

    target = Skill(id="t",
                   name="deploy_to_production",
                   trigger="deploy and verify",
                   preconditions=["build_ready"],
                   postconditions=["live_in_production"])
    # Different semantic domain (different embeddings), same
    # procedural shape: deploy + verify + production state.
    analogue = Skill(id="a",
                     name="release_to_production",
                     trigger="deploy and verify",
                     preconditions=["build_ready"],
                     postconditions=["live_in_production"])
    out = find_structural_analogues(
        target, [analogue],
        semantic_cosine_fn=lambda a, b: 0.2,  # low semantic cosine
        min_structural=0.4,
        max_semantic=0.5,
    )
    assert len(out) == 1
    cand, info = out[0]
    assert cand.id == "a"
    assert "structural" in info and "semantic" in info
    assert info["structural"] >= 0.4
    assert info["semantic"] <= 0.5


def test_find_analogues_excludes_self():
    """Target skill never returned as its own analogy."""
    from verimem.analogy import find_structural_analogues

    target = Skill(id="t", name="x", trigger="y")
    out = find_structural_analogues(
        target, [target],
        semantic_cosine_fn=lambda a, b: 0.0,
        min_structural=0.0,
        max_semantic=1.0,
    )
    assert out == []


def test_find_analogues_sorted_descending_by_structural():
    """Multiple analogues returned sorted by structural score."""
    from verimem.analogy import find_structural_analogues

    target = Skill(id="t", name="alpha beta gamma delta",
                   trigger="alpha beta gamma delta")
    weak = Skill(id="w", name="alpha beta epsilon zeta",
                 trigger="alpha beta epsilon zeta")
    strong = Skill(id="s", name="alpha beta gamma delta",
                   trigger="alpha beta gamma epsilon")
    out = find_structural_analogues(
        target, [weak, strong],
        semantic_cosine_fn=lambda a, b: 0.0,
        min_structural=0.0,
        max_semantic=1.0,
    )
    # Sorted by structural descending. The strong one (more overlap)
    # should be first.
    assert len(out) == 2
    assert out[0][0].id == "s", (
        f"expected strong analogue first, got {[c.id for c, _ in out]}"
    )


def test_find_analogues_empty_corpus():
    from verimem.analogy import find_structural_analogues

    out = find_structural_analogues(
        Skill(id="t"),
        [],
        semantic_cosine_fn=lambda a, b: 0.0,
    )
    assert out == []


def test_find_analogues_top_k_limit():
    from verimem.analogy import find_structural_analogues

    target = Skill(id="t", name="x y z", trigger="x y z")
    # Many candidates, all structurally similar.
    candidates = [
        Skill(id=f"c{i}", name="x y z", trigger=f"x y z extra{i}")
        for i in range(10)
    ]
    out = find_structural_analogues(
        target, candidates,
        semantic_cosine_fn=lambda a, b: 0.0,
        min_structural=0.0, max_semantic=1.0,
        top_k=3,
    )
    assert len(out) == 3
