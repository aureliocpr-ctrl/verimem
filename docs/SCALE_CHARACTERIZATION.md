# Recall scale — measured, not assumed

The facts-recall hot path (`SemanticMemory.recall`, `topic=None` cache branch)
holds the whole live corpus as one in-process float32 matrix and scores a query
with `corpus @ q` + `argsort` — brute-force, exact, O(N) per query. This note
records what that actually costs, measured, so the limit is grounded and not
re-derived wrong by the next instance.

Reproduce: `python -m benchmark.facts_recall_scale_probe` and
`python -m benchmark.recall_quant_fidelity` (pure numpy, hermetic, no DB/model).

## Brute-force cost (dim=1024, k=8, this machine)

| N facts | matrix RAM | recall p50 | recall p95 |
|--------:|-----------:|-----------:|-----------:|
| 1 000   | 4 MB       | 0.2 ms     | 0.3 ms     |
| 10 000  | 41 MB      | 1.0 ms     | 1.8 ms     |
| 50 000  | 205 MB     | 4.3 ms     | 5.6 ms     |
| 100 000 | 410 MB     | 8.7 ms     | 9.9 ms     |
| 300 000 | 1.2 GB     | 27 ms      | 31 ms      |

Latency is linear (~9 ms / 100k) and stays comfortable to ~300k. **The first
wall is RAM, not latency**: the resident float32 matrix is ~4 KB/fact, so 1M
facts ≈ 4 GB held in process. For reference, a live corpus today is ~4.5k facts
(<20 MB) — the scale limit is real but nobody hits it yet.

## Why naive quantization does NOT fix it (refuted by measurement)

Hypothesis: store the cached matrix as fp16/int8 to cut RAM. Measured at N=100k,
200 queries (`recall_quant_fidelity.py`):

| storage | resident RAM | top-8 overlap vs f32 | recall p50 |
|---------|-------------:|---------------------:|-----------:|
| float32 | 410 MB       | 1.0000               | 9.4 ms     |
| float16 | 205 MB       | 0.9994               | **267 ms** |
| int8    | 103 MB       | 0.9838               | **276 ms** |

Ranking fidelity is excellent (fp16 ~perfect, int8 within ~1.6%), but latency
regresses **~30×**: pure numpy has no SIMD fp16/int8 matmul kernel, so each query
upcasts the whole matrix back to float32 — which also re-allocates the full f32
size transiently, so it doesn't even reduce *peak* RAM (no help for the OOM case
at 1M). Naive in-numpy quantization is a loss, not a win.

## The real lever (deliberate, not yet taken)

Beyond ~300k–1M the honest path is an out-of-numpy index with SIMD/quantized
kernels and mmap/on-disk storage — **faiss-cpu** (IVF-PQ / HNSW) or **hnswlib**.
That cuts both RAM (PQ codes) and latency (sub-linear search) at the cost of a
real build dependency and approximate (not exact) recall. It is gated on an
actual ≥300k-fact need; until then brute-force is the correct, exact, dependency-
free choice. Decision belongs to the project owner — this note exists so the
trade-off is made on measured numbers, not vibes.

## Durability posture (verified — already adequate, not a gap)

The production-scaling review flagged "synchronous=NORMAL never checkpointed = data-loss
window". Verified against the code, that is imprecise — the posture is already sound:

* All DB connections open WAL + `busy_timeout=60000` + `synchronous=NORMAL`
  (`engram/_sqlite_pragma.synchronous_mode`, tunable to `FULL`).
* `wal_autocheckpoint` is left at SQLite's default (1000 pages ≈ 4 MB), so the WAL is
  auto-checkpointed continuously — the uncheckpointed window is bounded to the last few
  MB, and only a power-loss/OS-crash (not a process crash — the WAL survives that) can
  touch it.
* The journal-replay path additionally forces a synchronous `PRAGMA wal_checkpoint(FULL)`
  + `fsync` before unlinking the crash journal (`semantic._durable_checkpoint`), closing
  the replay→unlink gap.
* Deployments needing per-commit fsync durability set `ENGRAM_SQLITE_SYNCHRONOUS=FULL`.

So there is no unbounded data-loss window. Adding a second periodic-checkpoint mechanism
would duplicate `wal_autocheckpoint` for no measurable gain — deliberately NOT done.
