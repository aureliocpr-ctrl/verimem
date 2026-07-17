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

## ANN index — the scale path (the README's "1.3 ms at 1M" number)

Brute cosine is O(N) in BOTH RAM and latency. A faiss HNSW index is the answer at
scale, and is exactly what the README's "1.3 ms at 1M facts vs 81 ms brute-force"
refers to. Measured (`ann_recall_scale_bench.py`, dim=768, k=8, oversample=8,
seeded — pure numpy+faiss, no LLM):

| N | brute p50 | ANN p50 | speedup | source |
|---|----------:|--------:|--------:|--------|
| 100 000   | 7.2–8.8 ms | 0.8–1.1 ms | ~7.8× | `ann_scale_bench_repro.json` + 2026-07-16 recheck |
| 500 000   | 37.4 ms | 1.25 ms | ~30× | `ann_scale_bench_repro.json` |
| 1 000 000 | 81.4 ms | **1.31 ms** | ~62× | `ann_scale_bench_repro.json` |

**Honest caveats (measured, not hidden):**
- The 500k/1M rows need ~a 32 GB box to BUILD the index. The 2026-07-16 recheck
  OOM'd at 500k on a smaller machine and reproduced only 100k (7.8×, ANN 1.12 ms).
  The 1M number is real but reproduces only where RAM allows.
- HNSW is APPROXIMATE. Recall-in-pool @ oversample 8 measured **0.844 on random
  unit vectors** (worst case) — up to ~16% of the exact top-k can be missed. Real
  e5 neighbourhoods are less adversarial, but the "recall latency stays ~flat"
  headline is about LATENCY; the ANN trades a little RECALL for it — stated, not
  hidden.
- Default is EXACT brute-force; the ANN is opt-in (`ENGRAM_ANN_RECALL`) for
  >200k corpora, so nobody pays the approximation unless they choose to.

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

## Gateway under concurrent load (measured — `benchmark/gateway_load_probe.py`)

Real uvicorn, one enterprise tenant, 16 concurrent workers, 200 req/phase; the invariant
is **overload may slow or politely refuse, never 5xx or corrupt**. Measured 2026-07-17
(`benchmark/results/gateway_load_probe_2026-07-17.json`), single node, this machine:

| phase | rps | p50 | p95 | codes |
|-------|----:|----:|----:|-------|
| writes | 12.8 | 1.26 s | 1.39 s | 200 ×200 |
| searches | 10.5 | 1.16 s | 3.92 s | 200 ×200 |
| mixed (½ write ½ search) | 22.1 | 0.49 s | 1.59 s | 200 ×200 |
| big_payload (256 KB) | 0.7 | 5.19 s | 5.76 s | 200 ×10 |
| bad_key | 205 | 66 ms | 104 ms | **401 ×50** |

**0 violations**: no 5xx anywhere, every bad key is a fast 401, oversized payloads are
served (linearly) not hung. Latency under 16-way concurrency is **embedding-bound** — one
in-process e5 model + the GIL serialize the encode, so per-request p50 sits ~0.5–1.3 s at
saturation; it degrades gracefully rather than failing. The horizontal path (per-tenant
processes, the encode daemon, the ANN index above) is the lever when a single node's
~10–22 rps ceiling is reached; nobody hits it at today's corpus sizes.

**DoS fixed here** (`d623cc6`): the probe first exposed a 64 KB write hanging **23.8 s** —
an O(n²) `re` backtrack in the L1 gate's `_DEV_CONTEXT` pattern that ran on every write.
Bounded regex + an 8 KB lexical-scan cap dropped it to 468 ms (linear to 256 KB); a large
paste can no longer stall the write path.

## Read-path robustness on adversarial queries (measured)

Symmetric to the write path: a hostile search/answer query must not hang or crash
the server. Swept `Memory.search`/`Memory.explain` with 64 KB no-space, unicode-mixed,
all-digit and near-match-repeat queries (2026-07-17). Every op returns correctly —
`encode` 0.5 s, `search` 1–4 s, `explain` 0.6–3.8 s — slower on a pathological query
(the reranker cross-encoder scores a giant string) but never hangs. No 5xx and no crash
in the single-process serving model — the gateway load probe's 16 concurrent in-process
workers ran clean. (A one-off native segfault appeared only when TWO separate torch/faiss
*processes* ran at once — an OpenMP/thread contention artifact of the test harness, not
reachable in the one-process gateway; not reproducible single-process.)
