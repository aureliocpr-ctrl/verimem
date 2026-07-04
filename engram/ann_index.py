"""ANN (HNSW) index for global recall at scale.

Brute-force cosine recall is exact but O(N): 0.6 / 5.9 / 28.4 ms @ 10k/100k/500k
(SCALE.md). Past ~100k facts it is the wall. This wraps a faiss HNSW index over
the corpus-cache matrix and returns a candidate POOL (k*oversample indices in
matrix space); the live recall path then applies the identical
cosine/decay/status/valid-time filters + fusion + rerank + write-gate INSIDE the
pool — ANN swaps only the top-k *selection*, never the trust logic.

Ported from the validated arch-lab prototype (recall-in-pool -> ~1.0 with
oversample >= 4, real e5 corpus). Two production additions over the prototype:
- **incremental `add`** (SCALE.md's "hard part"): faiss IndexHNSWFlat.add appends
  new vectors without a full rebuild (rebuild was 348 s @ 500k);
- **gating** `should_use_ann`: below `_ANN_MIN_N` brute-force wins (no build/sync
  overhead) so this stays opt-in + dormant on small corpora.
"""
from __future__ import annotations

import numpy as np

try:
    import faiss
except ImportError:  # pragma: no cover - faiss is a core dep, guarded for safety
    faiss = None

#: Below this fact count the exact brute-force path wins (build/sync overhead
#: outweighs the sublinear query). ANN is opt-in AND gated on top of that.
_ANN_MIN_N = 100_000


class ANNIndex:
    """HNSW over the corpus-cache matrix. ``query`` returns the top-(k*oversample)
    INDICES in matrix space, to be filtered/reranked downstream EXACTLY as the
    current brute-force path does. Oversampling lets the exact post-cosine
    filters (freshness/status/valid-time) survive on the ANN candidate pool."""

    def __init__(self, matrix, *, M: int = 16, ef_construction: int = 200,
                 ef_search: int = 128):
        if faiss is None:
            raise RuntimeError("faiss not available (pip install faiss-cpu)")
        matrix = np.ascontiguousarray(matrix, dtype=np.float32)
        if matrix.ndim != 2:
            raise ValueError("matrix must be 2-D (n_vectors, dim)")
        self.d = int(matrix.shape[1])
        self.idx = faiss.IndexHNSWFlat(self.d, M)
        self.idx.hnsw.efConstruction = ef_construction
        self.idx.hnsw.efSearch = ef_search
        if matrix.shape[0]:
            self.idx.add(matrix)

    @property
    def size(self) -> int:
        """Number of vectors currently indexed (grows with ``add``)."""
        return int(self.idx.ntotal)

    def add(self, vectors) -> None:
        """Append new vectors incrementally — no full rebuild. Their matrix
        indices continue from the current size, matching the corpus-cache
        append order the recall path assumes."""
        v = np.ascontiguousarray(vectors, dtype=np.float32)
        if v.ndim == 1:
            v = v.reshape(1, -1)
        if v.shape[1] != self.d:
            raise ValueError(f"dim mismatch: index d={self.d}, got {v.shape[1]}")
        if v.shape[0]:
            self.idx.add(v)

    def query(self, q, k: int, *, oversample: int = 4):
        """Top-(k*oversample) candidate indices for query vector ``q``. faiss
        pads with -1 when the pool exceeds the index size; those are stripped so
        the caller never dereferences a negative index."""
        pool = max(1, k) * max(1, oversample)
        qv = np.ascontiguousarray(np.asarray(q, dtype=np.float32).reshape(1, -1))
        _, ids = self.idx.search(qv, pool)
        out = ids[0]
        return out[out >= 0]


def should_use_ann(n: int, *, enabled: bool) -> bool:
    """ANN is used only when explicitly enabled AND the corpus is large enough
    that its sublinear query beats brute-force + build/sync overhead."""
    return bool(enabled) and n >= _ANN_MIN_N
