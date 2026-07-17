"""Cycle 388 (2026-05-23) — B4 NUCLEAR HOLOGRAPHIC MEMORY (database-less).

Aurelio mandate post-compact 2026-05-23: "sperimenta anche cose che non
siano database, sii creativo, rispetta meta regole, non confabulare".

B5 divergenza 12 ipotesi → B4 nuclear pick concatenazione 4 elementi
mai combinati per AI agent persistent memory:
  1. Plate 1995 HRR — circular convolution (binding) / correlation (unbind)
  2. Ramsauer 2020 Modern Hopfield — beta-softmax pattern completion
  3. Bloom filter — probabilistic existence O(k) memory
  4. HippoAgent lineage_to — circular shift for chain depth encoding

WebSearch 2026 (A1 anti-confab honest findings):
  - "Holographic" 2026 prodotto: HRR but SQLite + FTS5 sotto (compromesso)
  - mem0 / Supermemory / Cloudflare AgentMemory: tutti DB-based
  - Modern Hopfield super-linear capacity confermato (Ramsauer 2020+24)
  - "Hey Pentti" 2025 paper: HRR Lisp encoding prova compositional power
  ⇒ Novità specifica questa implementazione: ZERO DB sotto. Pure vector.

Architettura:
  - M : R^D (D=8192 default) = single aggregated vector
  - bloom : ~10KB bitfield (k=5 hash, ~1% FP at 10k facts)
  - cleanup_pool : bounded list[(topic, prop)] for Hopfield decoder
    (NOT a database: hard cap, ring buffer, lossy compression)

Falsifiable contracts (vedi tests/test_holographic_memory.py):
  (a) storage_size(N=500) < 100KB → SUPPORTED se ≤; FALSIFIED se >
  (b) recall@1(N=100) ≥ 0.7 → SUPPORTED; FALSIFIED se <
  (c) recall@1(N=1000) << recall@1(N=100) → cliff edge (M9 verifiable)
  (d) write_latency_p99 < 10ms → SUPPORTED; FALSIFIED se ≥
  (e) read_latency_p99 < 20ms → SUPPORTED; FALSIFIED se ≥

A3 honest scope:
  Vector-symbolic memory NON è rivoluzione assoluta (HRR 1995 prior art).
  Novità specifica: ZERO DB sotto + Bloom existence + lineage shift +
  Hopfield cleanup integrati in single aggregate. Lossy by design.
  Trade-off accettato. Negative result accettabile per Popperian discipline.

API:
  HolographicMemory(d=8192).remember(topic, proposition, lineage_depth=0)
  HolographicMemory(d=8192).recall(topic, top_k=1, lineage_depth=0)
  HolographicMemory.contains(topic, proposition)
  HolographicMemory.forget(topic, proposition)
  HolographicMemory.save(path) / .load(path)
  HolographicMemory.stats() → storage_bytes, n_facts, aggregate_norm, ...
"""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

D_DEFAULT = 8192
BLOOM_SIZE_BITS = 80_000  # ~10KB at 1 byte/bit, ~1% FP for 10k facts k=5
BLOOM_HASH_FUNCS = 5
BETA_HOPFIELD = 8.0  # softmax sharpness (higher = more decisive)
DEFAULT_CLEANUP_POOL_CAP = 2048


def _seed_from_text(text: str) -> int:
    """Deterministic int seed from text via SHA-256 prefix."""
    h = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big")


def _filler(text: str, d: int = D_DEFAULT) -> np.ndarray:
    """Deterministic unit-norm random filler vector for `text`.

    Plate 1995: filler vectors are random gaussian unit-norm, ortho-
    expected in high D. SHA-256 seed gives deterministic mapping.
    """
    rng = np.random.default_rng(_seed_from_text(text))
    v = rng.standard_normal(d).astype(np.float32)
    v /= max(float(np.linalg.norm(v)), 1e-9)
    return v


def _circular_conv(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Circular convolution via FFT (Plate 1995 binding operator).

    Properties: associative-like, distributive, unit element exists.
    Complexity: O(D log D).
    """
    A = np.fft.fft(a)
    B = np.fft.fft(b)
    return np.real(np.fft.ifft(A * B)).astype(np.float32)


def _circular_corr(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Circular correlation via FFT (Plate 1995 unbinding operator).

    Approx inverse of binding: corr(a, conv(a, b)) ≈ b (noisy).
    Cleanup required via Hopfield to get exact b.
    """
    A = np.fft.fft(a)
    B = np.fft.fft(b)
    return np.real(np.fft.ifft(np.conj(A) * B)).astype(np.float32)


def _circular_shift(v: np.ndarray, k: int) -> np.ndarray:
    """Shift filler by k positions (lineage chain depth encoding).

    Cycle-388 novelty: lineage_depth k → topic_filler shifted k positions
    so chain[depth] facts share topic-base but differ via shift.
    """
    return np.roll(v, k)


class _BloomFilter:
    """Minimal Bloom filter: k hashes from SHA-256 prefix splits."""

    def __init__(self, n_bits: int = BLOOM_SIZE_BITS,
                 k: int = BLOOM_HASH_FUNCS) -> None:
        self.n_bits = n_bits
        self.k = k
        self.bits = np.zeros(n_bits, dtype=np.uint8)

    def _idx(self, item: str) -> list[int]:
        # SHA-256 = 32 bytes. k=5 → 5×4-byte chunks = 20 bytes used.
        h = hashlib.sha256(item.encode("utf-8")).digest()
        return [
            int.from_bytes(h[i * 4:(i + 1) * 4], "big") % self.n_bits
            for i in range(self.k)
        ]

    def add(self, item: str) -> None:
        for i in self._idx(item):
            self.bits[i] = 1

    def __contains__(self, item: str) -> bool:
        return all(self.bits[i] == 1 for i in self._idx(item))

    def to_bytes(self) -> bytes:
        return self.bits.tobytes()

    @classmethod
    def from_bytes(cls, blob: bytes, n_bits: int = BLOOM_SIZE_BITS,
                   k: int = BLOOM_HASH_FUNCS) -> _BloomFilter:
        b = cls(n_bits=n_bits, k=k)
        b.bits = np.frombuffer(blob, dtype=np.uint8).copy()
        return b


@dataclass
class HolographicMemory:
    """Database-less AI agent memory: 1 aggregate vector + 1 Bloom.

    Persist as single binary file:
      header(20B) + aggregate(D*4B) + bloom(n_bits B) + cleanup_pool(variable)

    cleanup_pool is bounded ring buffer of (topic, proposition) tuples
    used by Hopfield decoder to map noisy unbind output back to known
    proposition fillers. NOT a database: hard cap, ring-eviction.
    """
    d: int = D_DEFAULT
    aggregate: np.ndarray = field(default=None)  # type: ignore[assignment]
    bloom: _BloomFilter = field(default=None)  # type: ignore[assignment]
    n_facts: int = 0
    cleanup_pool: list[tuple[str, str, int]] = field(default_factory=list)
    cleanup_pool_cap: int = DEFAULT_CLEANUP_POOL_CAP

    def __post_init__(self) -> None:
        if self.aggregate is None:
            self.aggregate = np.zeros(self.d, dtype=np.float32)
        if self.bloom is None:
            self.bloom = _BloomFilter()

    # ---------------- WRITE PATH ----------------
    def remember(self, topic: str, proposition: str,
                 lineage_depth: int = 0) -> dict[str, Any]:
        """Store (topic, proposition) bound vector + bloom + cleanup.

        Pipeline:
          1. topic_f = filler(topic) [shift if lineage_depth>0]
          2. prop_f = filler(proposition)
          3. bound = circular_conv(topic_f, prop_f)
          4. aggregate += bound
          5. bloom.add(topic||proposition)
          6. cleanup_pool.append((topic, proposition, lineage_depth))
        """
        topic_f = _filler(topic, self.d)
        if lineage_depth > 0:
            topic_f = _circular_shift(topic_f, lineage_depth)
        prop_f = _filler(proposition, self.d)
        bound = _circular_conv(topic_f, prop_f)
        self.aggregate = self.aggregate + bound
        self.bloom.add(f"{topic}\x00{proposition}\x00{lineage_depth}")
        self.cleanup_pool.append((topic, proposition, lineage_depth))
        if len(self.cleanup_pool) > self.cleanup_pool_cap:
            self.cleanup_pool.pop(0)
        self.n_facts += 1
        return {
            "ok": True,
            "n_facts": self.n_facts,
            "aggregate_norm": float(np.linalg.norm(self.aggregate)),
            "lineage_depth": lineage_depth,
        }

    # ---------------- READ PATH ----------------
    def recall(self, topic: str, top_k: int = 1,
               lineage_depth: int = 0,
               cleanup_subset_only: bool = True) -> list[dict[str, Any]]:
        """Decode aggregate to find proposition(s) for topic.

        Pipeline:
          1. topic_f = filler(topic) [shifted if lineage_depth>0]
          2. noisy = circular_corr(topic_f, aggregate)
          3. Hopfield cleanup: stack M from cleanup_pool fillers,
             score = M @ noisy, probs = softmax(beta * score)
          4. Sort desc, return top_k.

        If cleanup_subset_only=True (default), Hopfield only considers
        cleanup_pool entries whose topic matches; widens to entire pool
        if no exact-topic hit (graceful degradation).
        """
        topic_f = _filler(topic, self.d)
        if lineage_depth > 0:
            topic_f = _circular_shift(topic_f, lineage_depth)
        noisy = _circular_corr(topic_f, self.aggregate)
        if not self.cleanup_pool:
            return []
        if cleanup_subset_only:
            relevant = [
                (t, p, d) for (t, p, d) in self.cleanup_pool
                if t == topic and d == lineage_depth
            ]
            if not relevant:
                relevant = list(self.cleanup_pool)
        else:
            relevant = list(self.cleanup_pool)
        M = np.stack([_filler(p, self.d) for (_, p, _) in relevant])
        scores = M @ noisy
        s = scores - scores.max()
        probs = np.exp(BETA_HOPFIELD * s)
        probs /= probs.sum()
        order = np.argsort(-probs)[:top_k]
        return [
            {
                "topic": relevant[idx][0],
                "proposition": relevant[idx][1],
                "lineage_depth": relevant[idx][2],
                "score": float(probs[idx]),
                "rank": rank,
            }
            for rank, idx in enumerate(order)
        ]

    def contains(self, topic: str, proposition: str,
                 lineage_depth: int = 0) -> bool:
        """Bloom existence check. False = certainly absent. True = probably present."""
        return f"{topic}\x00{proposition}\x00{lineage_depth}" in self.bloom

    def forget(self, topic: str, proposition: str,
               lineage_depth: int = 0) -> dict[str, Any]:
        """Soft forget: subtract bound vector + remove cleanup entry.

        Note: HRR forget is approximate. Bloom cannot be unset without
        rebuild (we leave it; false positives on forgotten facts are
        acceptable since cleanup_pool gates real retrieval).
        """
        topic_f = _filler(topic, self.d)
        if lineage_depth > 0:
            topic_f = _circular_shift(topic_f, lineage_depth)
        prop_f = _filler(proposition, self.d)
        bound = _circular_conv(topic_f, prop_f)
        # SCAN-68 FIX 2026-06-02 (NONNA): muta l'aggregate SOLO dopo aver
        # confermato che il fatto esisteva. Prima la sottrazione era PRIMA del
        # check di esistenza -> un forget di un fatto mai memorizzato sottraeva
        # un bound mai aggiunto -> drift permanente dello stato HRR.
        try:
            self.cleanup_pool.remove((topic, proposition, lineage_depth))
        except ValueError:
            return {"ok": False, "reason": "not_in_cleanup_pool"}
        self.aggregate = self.aggregate - bound
        self.n_facts -= 1
        return {"ok": True, "n_facts": self.n_facts}

    # ---------------- INTROSPECTION ----------------
    def stats(self) -> dict[str, Any]:
        """Storage + state introspection."""
        return {
            "d": self.d,
            "n_facts": self.n_facts,
            "aggregate_size_bytes": int(self.aggregate.nbytes),
            "bloom_size_bytes": int(self.bloom.bits.nbytes),
            "cleanup_pool_size": len(self.cleanup_pool),
            "cleanup_pool_cap": self.cleanup_pool_cap,
            "aggregate_norm": float(np.linalg.norm(self.aggregate)),
        }

    # ---------------- PERSIST ----------------
    def save(self, path: Path | str) -> dict[str, Any]:
        """Persist to single binary file. Returns {bytes_written}."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        agg_bytes = self.aggregate.tobytes()
        bloom_bytes = self.bloom.to_bytes()
        cl_parts: list[bytes] = []
        for t, prop, depth in self.cleanup_pool:
            t_b = t.encode("utf-8")
            p_b = prop.encode("utf-8")
            cl_parts.append(
                struct.pack(">III", len(t_b), len(p_b), depth)
                + t_b + p_b,
            )
        cleanup_blob = b"".join(cl_parts)
        header = (
            b"HOLO"
            + struct.pack(">I", self.d)
            + struct.pack(">I", self.n_facts)
            + struct.pack(">I", self.bloom.n_bits)
            + struct.pack(">I", len(cleanup_blob))
        )
        full = header + agg_bytes + bloom_bytes + cleanup_blob
        p.write_bytes(full)
        return {"ok": True, "bytes_written": len(full), "path": str(p)}

    @classmethod
    def load(cls, path: Path | str) -> HolographicMemory:
        """Reverse of save()."""
        p = Path(path)
        blob = p.read_bytes()
        if blob[:4] != b"HOLO":
            raise ValueError(f"bad magic: {blob[:4]!r}")
        d = struct.unpack(">I", blob[4:8])[0]
        n_facts = struct.unpack(">I", blob[8:12])[0]
        bloom_bits = struct.unpack(">I", blob[12:16])[0]
        cleanup_len = struct.unpack(">I", blob[16:20])[0]
        offset = 20
        agg_size = d * 4  # float32
        aggregate = np.frombuffer(
            blob[offset:offset + agg_size], dtype=np.float32,
        ).copy()
        offset += agg_size
        bloom_size = bloom_bits  # 1 byte per bit in our impl
        bloom = _BloomFilter.from_bytes(
            blob[offset:offset + bloom_size], n_bits=bloom_bits,
        )
        offset += bloom_size
        cleanup_blob = blob[offset:offset + cleanup_len]
        cleanup_pool: list[tuple[str, str, int]] = []
        i = 0
        while i < len(cleanup_blob):
            t_len, p_len, depth = struct.unpack(">III", cleanup_blob[i:i + 12])
            i += 12
            t = cleanup_blob[i:i + t_len].decode("utf-8")
            i += t_len
            prop = cleanup_blob[i:i + p_len].decode("utf-8")
            i += p_len
            cleanup_pool.append((t, prop, depth))
        return cls(
            d=d, aggregate=aggregate, bloom=bloom,
            n_facts=n_facts, cleanup_pool=cleanup_pool,
        )
