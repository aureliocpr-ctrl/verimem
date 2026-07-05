"""ANNCache — keep one HNSW index alive across recall calls.

The ANN only beats brute-force if the index is built ONCE and reused (HNSW
build is ~52s @100k). This caches a single ``ANNIndex`` keyed by a
caller-supplied corpus **version**:

- same version   -> reuse the index (the common hot case);
- ``grew_from=N`` -> the corpus only APPENDED rows past index N -> incremental
  ``add`` of the new tail (no rebuild — the piece SCALE.md flagged as hard);
- bumped version otherwise -> full rebuild (rows changed/removed).

Gated by ``_ANN_MIN_N``: below it, ``query_pool`` returns ``None`` so the
recall path keeps the exact brute-force cosine+argsort. The returned pool is
top-(k*oversample) matrix-space indices; the caller applies the identical
filters/fusion/rerank/write-gate INSIDE the pool.

BACKGROUND mode (auto-enable, iter 26): ``query_pool(..., background=True)``
never builds inline — it kicks ONE builder thread and returns ``None`` (the
caller stays exact brute) until the index for the CURRENT version is ready.
An index is only ever served for the version it was built for (no stale-row
hazard: row identity can shift across versions); version churn re-triggers at
most one rebuild per debounce window. A failed build just keeps brute forever.
"""
from __future__ import annotations

import os
import threading
import time
from typing import Any

from engram.ann_index import _ANN_MIN_N, ANNIndex


def _default_min_n() -> int:
    """Deploy override for the ANN gate; falls back to the module default."""
    v = os.environ.get("ENGRAM_ANN_MIN_N", "").strip()
    return int(v) if v.isdigit() else _ANN_MIN_N


class ANNCache:
    def __init__(self, *, min_n: int | None = None,
                 rebuild_debounce_s: float = 60.0):
        self.min_n = int(min_n) if min_n is not None else _default_min_n()
        self._idx: ANNIndex | None = None
        self._version: Any = None
        self._n: int = 0
        self.builds = 0   # observability: how many full rebuilds happened
        self.adds = 0     # observability: how many incremental appends
        self.building = False
        self._build_lock = threading.Lock()
        self._last_build_start = float("-inf")
        self.rebuild_debounce_s = float(rebuild_debounce_s)

    def _spawn_build(self, matrix, version: Any) -> None:
        """Start at most ONE background builder for (matrix snapshot, version),
        debounced so version churn cannot thrash CPU with rebuild loops."""
        with self._build_lock:
            if self.building:
                return
            now = time.monotonic()
            if now - self._last_build_start < self.rebuild_debounce_s:
                return
            self.building = True
            self._last_build_start = now
        snapshot = matrix.copy()   # rows may mutate under the builder otherwise

        def _run() -> None:
            try:
                idx = ANNIndex(snapshot)
            except Exception:  # noqa: BLE001 — a failed build just keeps brute
                idx = None
            with self._build_lock:
                if idx is not None:
                    self._idx = idx
                    self._version = version
                    self._n = int(snapshot.shape[0])
                    self.builds += 1
                self.building = False

        threading.Thread(target=_run, name="engram-ann-build",
                         daemon=True).start()

    def query_pool(self, matrix, q, k: int, *, oversample: int = 8,
                   version: Any = None, grew_from: int | None = None,
                   background: bool = False):
        """Return top-(k*oversample) candidate indices via the cached ANN, or
        ``None`` when the corpus is below the gate OR (background mode) the
        index for this version is not ready yet — the caller stays brute-force.

        ``version`` identifies the corpus state; pass ``grew_from=<old_n>`` when
        the change was a pure append past ``old_n`` so the tail is added
        incrementally instead of triggering a rebuild (synchronous mode)."""
        n = int(matrix.shape[0])
        if n < self.min_n:        # gate: below threshold brute-force wins
            return None

        if background:
            with self._build_lock:
                ready = (self._idx is not None and self._version == version
                         and not self.building)
                idx = self._idx if ready else None
            if idx is None:
                self._spawn_build(matrix, version)
                return None       # exact brute until the index is ready
            return idx.query(q, k, oversample=oversample)

        if self._idx is None or self._version != version:
            if (self._idx is not None and grew_from is not None
                    and grew_from == self._n and n > self._n):
                # pure append: add only the new tail, keep the index object
                self._idx.add(matrix[self._n:])
                self.adds += 1
            else:
                self._idx = ANNIndex(matrix)
                self.builds += 1
            self._version = version
            self._n = n
        return self._idx.query(q, k, oversample=oversample)
