"""Dentate Gyrus pattern separation — sparse coding via k-WTA.

The biological dentate gyrus does the opposite of what cosine top-k
does: instead of treating near-identical inputs as the same thing,
it actively *increases* their distance in the encoded representation.
The mechanism is sparse coding via k-Winners-Take-All (k-WTA) on a
high-dimensional random projection.

Math (Yassa & Stark 2011, Leutgeb et al. 2007):

    expanded = W_random @ emb           # d_in → d_expand
    sparse[i] = expanded[i] if i ∈ topk(expanded, k_sparse) else 0
    output = sparse / ||sparse||         # unit-norm

The separation comes from the random expansion: small differences in
the input get amplified along different directions of W, and the k-WTA
gates pick *different subsets* of the expanded dimensions for inputs
that diverge by even a tiny amount. The cosine between two near-identical
inputs collapses dramatically after k-WTA.

Why this matters for HippoAgent:

  Two episodes with cosine 0.99 (e.g. same task family, slight
  variation) currently compete for the SAME slot in cosine top-k. The
  user sees "5 nearly-identical results" instead of "1 representative
  + 4 distinct events". DG-encoding makes near-duplicates LOOK
  different to retrieval — so cosine top-k surfaces a richer mix.

This module is the *primitive*. Cabling it into the EpisodicMemory
pipeline (encode-on-store + encode-on-recall with the same W matrix)
is a separate pezzo (#11.5+). For now, the primitive can be used
standalone for any retrieval-side experiment.

Cost: O(d_in * d_expand) per encode — for d_in=384, d_expand=4096
this is ~1.5M float ops, sub-millisecond.
"""
from __future__ import annotations

import numpy as np


def _normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 0 else v


def build_dg_projection(
    *, d_in: int, d_expand: int, seed: int,
) -> np.ndarray:
    """Build the random projection matrix `W ∈ R^{d_expand × d_in}`.

    Gaussian initialisation, scaled by `1/sqrt(d_in)` (standard random
    projection / Johnson-Lindenstrauss conventions). The `seed` is the
    persistence story: a process restart produces the SAME matrix, so
    episodes encoded yesterday remain comparable to ones encoded
    today — without storing the matrix on disk.

    `d_expand` should be a few × `d_in` for meaningful separation.
    The classical DG ratio is roughly 10× (1M granule cells / 100k
    EC inputs); here we default to 8-10× via the bench. Less is
    cheaper but loses separation power.
    """
    rng = np.random.default_rng(seed=seed)
    scale = 1.0 / float(np.sqrt(max(1, d_in)))
    return (rng.standard_normal(size=(d_expand, d_in)) * scale).astype(np.float32)


def dg_encode(
    embedding: np.ndarray,
    W: np.ndarray,
    *,
    k_sparse: int,
) -> np.ndarray:
    """Pattern-separating encode of a dense embedding.

    Steps:
      1. Random expansion `expanded = W @ embedding` to `d_expand`.
      2. k-WTA: zero everything outside the top-`k_sparse` magnitudes.
         (Magnitude = `abs(expanded)` so both positive and negative
         strong activations are kept — that doubles the representational
         capacity vs taking only positives.)
      3. L2-normalise so cosine remains the comparison op.

    Returns: a unit-norm `d_expand` vector with exactly `k_sparse`
    non-zero entries (or fewer if the input is degenerate).

    Defensive: `k_sparse=0` or larger than `d_expand` are clamped to
    the valid range. Zero input produces zero output.
    """
    expanded = W @ embedding.astype(np.float32)
    # k-WTA on magnitude — keep positions with the largest |x|.
    k = max(1, min(int(k_sparse), expanded.size))
    mag = np.abs(expanded)
    if k >= expanded.size:
        sparse = expanded
    else:
        # Indices of the top-k by magnitude.
        top_idx = np.argpartition(-mag, k - 1)[:k]
        sparse = np.zeros_like(expanded)
        sparse[top_idx] = expanded[top_idx]
    return _normalize(sparse)


__all__ = ["build_dg_projection", "dg_encode"]
