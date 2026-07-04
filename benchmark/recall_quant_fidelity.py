"""Quantization fidelity probe for the cached recall matrix. The verified scale
bottleneck is RAM (the in-process float32 corpus matrix: ~4GB @ 1M facts), not
latency. This measures whether fp16 / int8 storage preserves the top-k ranking
(overlap vs the float32 ground truth) while cutting resident memory — i.e. whether
quantization is a safe, real lever before we wire it. Pure numpy, hermetic.

Run: python -m benchmark.recall_quant_fidelity [--n 100000] [--dim 1024] [--k 8] [--queries 200]
"""
from __future__ import annotations

import argparse
import time

import numpy as np


def _normalized(n: int, dim: int, rng: np.random.Generator) -> np.ndarray:
    m = rng.standard_normal((n, dim)).astype(np.float32)
    m /= np.linalg.norm(m, axis=1, keepdims=True) + 1e-8
    return m


def _topk_f32(corpus: np.ndarray, q: np.ndarray, k: int) -> np.ndarray:
    return np.argsort(-(corpus @ q))[:k]


def _topk_f16(corpus16: np.ndarray, q: np.ndarray, k: int) -> np.ndarray:
    # store fp16, compute by upcasting the matmul (numpy promotes) — resident
    # cache is halved; compute stays accurate.
    return np.argsort(-(corpus16.astype(np.float32) @ q))[:k]


def _quantize_int8(corpus: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-row symmetric int8: q = round(v / scale), scale = max|v| / 127."""
    scale = (np.max(np.abs(corpus), axis=1, keepdims=True) / 127.0).astype(np.float32)
    q = np.round(corpus / scale).clip(-127, 127).astype(np.int8)
    return q, scale


def _topk_int8(q8: np.ndarray, scale: np.ndarray, q: np.ndarray, k: int) -> np.ndarray:
    # dot(int8_row * scale, query) = scale * dot(int8_row, query); ranking only
    # needs the per-row scaled dot. int16 accum to avoid overflow.
    raw = q8.astype(np.int32) @ q  # query is float32 -> result float32
    return np.argsort(-(raw * scale[:, 0]))[:k]


def _overlap(a: np.ndarray, b: np.ndarray) -> float:
    return len(set(a.tolist()) & set(b.tolist())) / len(a)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100000)
    ap.add_argument("--dim", type=int, default=1024)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--queries", type=int, default=200)
    args = ap.parse_args()
    rng = np.random.default_rng(7)
    corpus = _normalized(args.n, args.dim, rng)
    queries = _normalized(args.queries, args.dim, rng)

    corpus16 = corpus.astype(np.float16)
    q8, scale = _quantize_int8(corpus)

    mb = lambda a: a.nbytes / 1e6  # noqa: E731
    print(f"recall quant fidelity  n={args.n} dim={args.dim} k={args.k} queries={args.queries}")
    print(f"  resident MB: f32={mb(corpus):.0f}  f16={mb(corpus16):.0f}  "
          f"int8={mb(q8) + mb(scale):.0f}")

    ov16, ov8, lat32, lat16, lat8 = [], [], [], [], []
    for q in queries:
        t = time.perf_counter(); truth = _topk_f32(corpus, q, args.k); lat32.append((time.perf_counter() - t) * 1e3)
        t = time.perf_counter(); r16 = _topk_f16(corpus16, q, args.k); lat16.append((time.perf_counter() - t) * 1e3)
        t = time.perf_counter(); r8 = _topk_int8(q8, scale, q, args.k); lat8.append((time.perf_counter() - t) * 1e3)
        ov16.append(_overlap(truth, r16))
        ov8.append(_overlap(truth, r8))

    def stat(x):
        x = sorted(x); return f"p50={x[len(x)//2]:.2f}ms"
    print(f"  top-{args.k} overlap vs f32:  f16={np.mean(ov16):.4f}  int8={np.mean(ov8):.4f}")
    print(f"  latency:  f32 {stat(lat32)}  f16 {stat(lat16)}  int8 {stat(lat8)}")


if __name__ == "__main__":
    main()
