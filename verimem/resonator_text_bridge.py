"""Cycle 397 (2026-05-23) — Bridge text → ResonatorMemory tuple indices.

Production prerequisite: ResonatorMemory cycle 388-396 funziona su
tuple (s_idx, v_idx, o_idx). Per usarlo in HippoAgent (free text facts)
serve mapping deterministico text → indices.

Tre strategie implementate:
  A) HASH-based (cycle 389 esistente): SHA256 → bytes → indices
     Pro: deterministic, no model load. Con: no semantic similarity.
  B) EMBED-based: sentence-transformer encode → project to codebook
     Pro: semantically similar texts → close atoms. Con: model load 5s.
  C) HYBRID: hash for role atoms + embed for text→atom projection
     Pro: best of both. Con: complex.

Implementazione cycle 397: strategia B (EMBED), perché:
  - HippoAgent già usa sentence-transformers all-MiniLM-L6-v2 (384-dim)
  - Semantic similarity è feature richiesta (recall by topic similarity)
  - Hash version già esiste come fallback (text_to_indices in
    resonator_memory.py)

Pipeline EMBED:
  1. text → embedding (384-dim) via sentence-transformer
  2. project embedding to D-dim codebook via linear map (random projection)
  3. per role r: find argmax cosine(projected, codebook[r]) → idx

Falsifiable contracts (vedi tests/test_resonator_text_bridge.py):
  (a) deterministic: same text → same indices, always
  (b) semantic similarity: "cat is animal" vs "dog is animal" → close atoms
      (≥1 role overlap on K=3)
  (c) different topics: "cat is animal" vs "code is python" → distinct
      (≤1 role overlap on K=3)
  (d) bridge roundtrip: text → indices → encode in Resonator → decode
      → same indices recovered (>90% with n_restarts=32)

A3 honest: embedding-to-atom projection is LOSSY. Multiple texts can
map to same atom tuple (collisions). Trade-off: semantic richness vs
exact reproducibility. Test (a) ensures stability per-call.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Any

import numpy as np

_EMBED_MODEL: Any = None
_RANDOM_PROJ_CACHE: dict[tuple[int, int], np.ndarray] = {}


def _get_embed_model() -> Any:
    """Lazy load sentence-transformer (cycle 387 reuse pattern)."""
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _EMBED_MODEL


def _random_projection(src_dim: int, dst_dim: int, seed: int = 42) -> np.ndarray:
    """Cached random projection matrix (src_dim, dst_dim)."""
    key = (src_dim, dst_dim)
    if key in _RANDOM_PROJ_CACHE:
        return _RANDOM_PROJ_CACHE[key]
    rng = np.random.default_rng(seed)
    M = rng.standard_normal((src_dim, dst_dim)).astype(np.float32)
    # Normalize columns for stability
    M /= np.maximum(np.linalg.norm(M, axis=0, keepdims=True), 1e-9)
    _RANDOM_PROJ_CACHE[key] = M
    return M


def text_to_atoms_via_embed(
    text: str,
    codebooks: list[np.ndarray],
    seed: int = 42,
) -> tuple[int, ...]:
    """Map text → tuple of atom indices via sentence-transformer + projection.

    Pipeline:
      1. embed = sentence-transformer.encode(text) → 384-dim
      2. project: x = embed @ R, where R ∈ R^{384 × D} random projection
      3. per role r: idx_r = argmax cosine(x, codebooks[r])

    Args:
        text: free-text fact (topic + proposition concatenated).
        codebooks: list of K codebook matrices (M_atoms, D).

    Returns:
        Tuple (idx_0, idx_1, ..., idx_{K-1}).
    """
    model = _get_embed_model()
    embed = model.encode([text], convert_to_numpy=True)[0].astype(np.float32)
    embed_norm = float(np.linalg.norm(embed))
    if embed_norm > 1e-9:
        embed = embed / embed_norm

    D = codebooks[0].shape[1]
    R = _random_projection(embed.shape[0], D, seed=seed)
    x = embed @ R  # (D,)
    x_norm = float(np.linalg.norm(x))
    if x_norm > 1e-9:
        x = x / x_norm

    indices = []
    # Different role gets a different sub-projection to decorrelate
    for r, codebook in enumerate(codebooks):
        # Per-role shift: roll x by r positions for decorrelation
        x_role = np.roll(x, r * 17)
        scores = codebook @ x_role  # (M_atoms,)
        idx = int(np.argmax(scores))
        indices.append(idx)
    return tuple(indices)


def text_to_atoms_via_hash(
    text: str, n_roles: int, atoms_per_role: int,
) -> tuple[int, ...]:
    """Hash-only fallback (cycle 389 mirror). Deterministic, no model load."""
    h = hashlib.sha256(text.encode("utf-8")).digest()
    indices = []
    bytes_per_role = max(len(h) // n_roles, 4)
    for r in range(n_roles):
        chunk = h[r * bytes_per_role:(r + 1) * bytes_per_role]
        if len(chunk) < 4:
            chunk = chunk.ljust(4, b"\x00")
        v = int.from_bytes(chunk[:4], "big")
        indices.append(v % atoms_per_role)
    return tuple(indices)


@lru_cache(maxsize=1024)
def text_to_atoms_cached(
    text: str,
    n_roles: int,
    atoms_per_role: int,
    d: int,
    method: str = "hash",
    seed: int = 42,
) -> tuple[int, ...]:
    """Cached entry point. method="embed" or "hash"."""
    if method == "hash":
        return text_to_atoms_via_hash(text, n_roles, atoms_per_role)
    elif method == "embed":
        from verimem.resonator_memory import _build_alphabet
        codebooks = _build_alphabet(n_roles, atoms_per_role, d, seed=seed)
        return text_to_atoms_via_embed(text, codebooks, seed=seed)
    else:
        raise ValueError(f"unknown method: {method}")
