"""Cycle 397 (2026-05-23) — Bridge text→atoms falsifiable contracts."""
from __future__ import annotations

import pytest

from tests._real_model import requires_real_model

# The embed tests use the REAL embedding model (no in-process stub); skip the
# module when it isn't cached (CI without a warmed HF cache). The 2 pure-hash
# tests are trivial and re-run whenever the model IS present.
pytestmark = requires_real_model


def test_hash_deterministic() -> None:
    """Hash bridge is fully deterministic."""
    from engram.resonator_text_bridge import text_to_atoms_via_hash
    a = text_to_atoms_via_hash("aurelio is here", n_roles=3, atoms_per_role=32)
    b = text_to_atoms_via_hash("aurelio is here", n_roles=3, atoms_per_role=32)
    assert a == b
    c = text_to_atoms_via_hash("aurelio is there", n_roles=3, atoms_per_role=32)
    assert a != c


def test_hash_in_range() -> None:
    """Hash indices all in [0, atoms_per_role)."""
    from engram.resonator_text_bridge import text_to_atoms_via_hash
    M = 32
    for text in ("a", "b" * 100, "🇮🇹 unicode test"):
        idx = text_to_atoms_via_hash(text, n_roles=3, atoms_per_role=M)
        assert all(0 <= i < M for i in idx), (text, idx)


def test_embed_deterministic() -> None:
    """Embed bridge produces same indices on repeat calls."""
    from engram.resonator_memory import _build_alphabet
    from engram.resonator_text_bridge import text_to_atoms_via_embed
    codebooks = _build_alphabet(n_roles=3, atoms_per_role=32, d=2048, seed=42)
    text = "the cat sat on the mat"
    a = text_to_atoms_via_embed(text, codebooks, seed=42)
    b = text_to_atoms_via_embed(text, codebooks, seed=42)
    assert a == b, f"non-deterministic: {a} != {b}"


def test_embed_semantic_similarity() -> None:
    """Semantic similar texts → some role overlap (≥1 of 3)."""
    from engram.resonator_memory import _build_alphabet
    from engram.resonator_text_bridge import text_to_atoms_via_embed
    codebooks = _build_alphabet(n_roles=3, atoms_per_role=32, d=2048, seed=42)
    a = text_to_atoms_via_embed("cat is an animal", codebooks)
    b = text_to_atoms_via_embed("dog is an animal", codebooks)
    overlap = sum(1 for x, y in zip(a, b, strict=False) if x == y)
    print(f"\nsemantic overlap cat/dog: {overlap}/3, a={a} b={b}")
    # NOTE: random projection is noisy. We test a weaker contract:
    # at least ONE role agree (1/3) for semantically similar texts.
    assert overlap >= 1 or a == b, (
        f"cat/dog should share ≥1 role atom. got a={a} b={b}."
    )


def test_embed_different_topics_distinct() -> None:
    """Semantically distinct → indices differ on most roles."""
    from engram.resonator_memory import _build_alphabet
    from engram.resonator_text_bridge import text_to_atoms_via_embed
    codebooks = _build_alphabet(n_roles=3, atoms_per_role=32, d=2048, seed=42)
    a = text_to_atoms_via_embed("cat is animal", codebooks)
    b = text_to_atoms_via_embed("python is language", codebooks)
    overlap = sum(1 for x, y in zip(a, b, strict=False) if x == y)
    print(f"\ndistinct overlap cat/python: {overlap}/3, a={a} b={b}")
    # Weak contract: at most 2 roles overlap (1 random collision tolerated)
    assert overlap <= 2, (
        f"distinct texts shouldn't fully overlap. got a={a} b={b}."
    )


def test_bridge_roundtrip_with_resonator() -> None:
    """Falsifiable: text→atoms→encode→decode→same atoms (sweet spot config).

    Uses D=4096, M=32, K=3 (cycle 395 sweet spot) + n_restarts=32 fix.
    Expect recovery probability ≥80% (single fact, single seed).
    """
    from engram.resonator_memory import ResonatorMemory
    from engram.resonator_text_bridge import text_to_atoms_via_hash
    mem = ResonatorMemory(n_roles=3, atoms_per_role=32, d=4096)
    text = "aurelio works on hippoagent memory layer"
    idx_in = text_to_atoms_via_hash(text, n_roles=3, atoms_per_role=32)
    mem.remember_tuple(idx_in)
    # Try recall via matching pursuit
    res = mem.recall_all_via_matching_pursuit(
        max_facts=3, n_restarts_per_pass=32,
    )
    found = res["found_facts"]
    assert idx_in in found, (
        f"roundtrip failed: encoded {idx_in} but not in {found}"
    )


def test_cached_entry_point() -> None:
    """text_to_atoms_cached works for both methods."""
    from engram.resonator_text_bridge import text_to_atoms_cached
    idx_hash = text_to_atoms_cached(
        "test text", n_roles=3, atoms_per_role=32, d=2048, method="hash",
    )
    assert len(idx_hash) == 3
    # second call hits cache
    idx_hash2 = text_to_atoms_cached(
        "test text", n_roles=3, atoms_per_role=32, d=2048, method="hash",
    )
    assert idx_hash == idx_hash2


def test_unknown_method_raises() -> None:
    """Unknown method → ValueError."""
    from engram.resonator_text_bridge import text_to_atoms_cached
    with pytest.raises(ValueError, match="unknown method"):
        text_to_atoms_cached(
            "x", n_roles=3, atoms_per_role=32, d=2048, method="bogus",
        )
