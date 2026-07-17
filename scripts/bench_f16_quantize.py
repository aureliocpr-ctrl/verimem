"""Cycle 208 (2026-05-23) — real-corpus f32 vs f16 round-trip bench.

Closes part of gap §5 cycle 206. Probes cycle-207 quantize/dequantize
on the operator's live ~/.engram/semantic.db corpus and reports:
  - Round-trip max relative error per fact.
  - Top-K cosine match between f32-only and f16-roundtrip rankings.
  - Total bytes saved if all embeddings switched to f16.

Run:
    python scripts/bench_f16_quantize.py
"""
from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

import numpy as np


def _load_embeddings(db_path: Path, limit: int = 2000) -> tuple[list[str], np.ndarray]:
    """Return (ids, np.array(N, 384) float32) for alive facts."""
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT id, embedding FROM facts "
            "WHERE superseded_by IS NULL "
            "  AND length(embedding) = 1536 "
            "LIMIT ?",
            (int(limit),),
        ).fetchall()
    finally:
        conn.close()
    ids = [str(r[0]) for r in rows]
    if not ids:
        return ids, np.zeros((0, 384), dtype=np.float32)
    flat = b"".join(r[1] for r in rows)
    arr = np.frombuffer(flat, dtype=np.float32).reshape(-1, 384)
    return ids, arr


def main() -> int:
    db = Path.home() / ".engram" / "semantic" / "semantic.db"
    if not db.exists():
        sys.stderr.write(f"semantic.db not found at {db}\n")
        return 1
    from verimem.embedding_quantize import dequantize_float16, quantize_float16

    t0 = time.perf_counter_ns()
    ids, embs_f32 = _load_embeddings(db, limit=5000)
    load_ms = (time.perf_counter_ns() - t0) / 1e6
    n = len(ids)
    if n == 0:
        sys.stderr.write("no embeddings found\n")
        return 1

    print(f"=== Cycle 208 bench: f32 ↔ f16 round-trip on {n} real facts ===")
    print(f"load: {load_ms:.1f}ms")

    # Round-trip each embedding through quantize.
    t0 = time.perf_counter_ns()
    embs_recovered = np.empty_like(embs_f32)
    for i in range(n):
        f32_blob = embs_f32[i].tobytes()
        f16_blob = quantize_float16(f32_blob)
        rec_blob = dequantize_float16(f16_blob)
        embs_recovered[i] = np.frombuffer(rec_blob, dtype=np.float32)
    rt_ms = (time.perf_counter_ns() - t0) / 1e6
    print(f"round-trip {n} facts: {rt_ms:.1f}ms ({rt_ms / n:.3f}ms/fact)")

    # Element-wise abs error stats.
    err = np.abs(embs_f32 - embs_recovered)
    print(f"abs error: max={err.max():.6f} mean={err.mean():.6f}")

    # Cosine top-K match on random queries.
    rng = np.random.default_rng(42)
    q_idx = rng.choice(n, min(20, n), replace=False)
    matches = 0
    total = 0
    K = 5
    for qi in q_idx:
        q = embs_f32[qi]
        scores_f32 = embs_f32 @ q
        scores_f16 = embs_recovered @ q
        top_f32 = set(np.argsort(-scores_f32)[:K].tolist())
        top_f16 = set(np.argsort(-scores_f16)[:K].tolist())
        matches += len(top_f32 & top_f16)
        total += K
    print(
        f"top-{K} match rate over {len(q_idx)} queries: "
        f"{matches}/{total} = {100 * matches / total:.1f}%"
    )

    # Storage delta.
    f32_total = n * 1536
    f16_total = n * 768
    saved = f32_total - f16_total
    print(
        f"storage: f32={f32_total / 1024:.1f} KB, "
        f"f16={f16_total / 1024:.1f} KB, "
        f"saved={saved / 1024:.1f} KB ({100 * saved / f32_total:.0f}%)"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
