# Verimem (engram engine) — Retrieval Benchmarks

Judge-free, 100% local, zero external APIs. Every number below is
reproducible from this repo; every harness declares its fairness notes in
the module docstring. Limits are stated next to the numbers they qualify.

## 1. Comparative: Engram vs vanilla RAG (identical embedder)

**Question answered**: how much does the Engram layer add over a bare
cosine top-k with the *same* embedding model? ("Better than plain RAG" is
a claim — this is the measurement.)

- Dataset: LongMemEval-s (arXiv 2410.10813), session-level retrieval of
  gold `answer_session_ids`, k=5, n=100 (first 100 questions).
- Embedder for **all** arms: `intfloat/multilingual-e5-base` (768d), same
  `passage:`/`query:` prefix scheme — the baseline is not handicapped.
- Harness: `benchmark/comparative_retrieval.py` (commit `fdc69b8`),
  identical (sid, text) ingest per arm, fresh hermetic store per question.

| arm | recall@5 | hit@5 | MRR | query latency |
|---|---|---|---|---|
| engram (prod, rerank+length-guard) | 0.800 | 0.830 | 0.719 | 53 ms |
| engram-base (no rerank) | 0.800 | 0.830 | 0.719 | 22 ms |
| vanilla cosine (same e5) | 0.790 | 0.820 | 0.717 | ~0 ms* |
| mem0 OSS 2.0.4 (e5parity, infer=False)** | 0.790 | 0.820 | 0.717 | 59 ms |

\* vanilla's ingest/encode cost is paid outside the timer, like the
engram arms pay theirs in `store()`.

\** **Mem0 arm required working around a real mem0 bug.** As shipped,
mem0 2.0.4 + chroma scored **0.000 across all 100 questions**: chroma
returns an L2 *distance* which `Memory.search` feeds into its
`score_and_rank()` fusion as if it were a *similarity* — the semantic
ranking comes back inverted **before** the top-k cut, so the cut keeps
the worst candidates (A/B proof: same query vector, gold session is
rank 1 via mem0's own `vector_store.search`, rank 50/50 via
`Memory.search`; the gold's "score" 0.4026 equals 2−2·cos(0.7987)
exactly). Our arm (`benchmark/mem0_arm_runner.py`, isolated venv,
`infer=False`, LLM never invoked) queries mem0's `vector_store.search`
directly — its embedder, its store, its add pipeline, the pre-bug
point. With that workaround mem0 lands exactly on the vanilla numbers,
which is what a raw vector store with the same embedder should do.
Upstream issue material. The `asis` variant (no e5 prefixes) is a
planned follow-up.

**Honest readings** (the numbers cut both ways):

1. On *pure ranking* over a clean haystack, the Engram layer adds ~+0.01
   over bare cosine — within noise. Engram's value on this axis is NOT a
   better ranking function; it is provenance/anti-confabulation gating,
   per-model isolation, multi-tenancy, crash-durable writes and lineage —
   properties a bare matrix does not have and this metric does not see.
2. The 2-stage cross-encoder rerank (default-ON for production) is
   **regime-dependent**: on short atomic facts it is twice-validated with
   large wins (below); on session-length documents it *hurt* (0.723 vs
   0.800) until the length guard — the CE truncates at 512 tokens and
   cannot judge what it cannot read. The guard skips the CE (not even
   loaded) when the candidate pool's median document exceeds
   `ENGRAM_RERANK_MAX_DOC_CHARS` (default 2000 chars; `0` disables).
   Guarded rerun: 0.800/0.830/0.719 — identical to base, no CE tax.

## 2. Cross-encoder rerank on the real corpus (short facts)

Where the reranker earns its default-ON (both paired McNemar, COPY of the
live corpus, CPU):

| regime | n | R@1 | R@10 | MRR | p |
|---|---|---|---|---|---|
| HARD probes (shuffled content words) | 300 | 0.520 → 0.810 | — | 0.611 → 0.832 | <1e-5 |
| FAIR (fluent paraphrases) | 120 | 0.533 → 0.683 | 0.750 → 0.817 | 0.602 → 0.736 | 0.00052 |

The FAIR regime is the one that **refuted** keyword-overlap hybrid recall
(R@1 0.54 → 0.24, commit `2f92d9e`) — the reranker survives where that
died. Cost: ~1.6 s/query on CPU (pool 20, `ENGRAM_RERANK_TOPN`).

## 3. Scale (gate: no OOM at 10k)

`scripts/bench_scale_recall.py`, synthetic 384-d corpus: **no OOM up to
100k facts** (10× the gate), flat RSS (Δ≈0.2–0.4 MB per step), cold
matrix build 0.25 s at 100k. Caveats: synthetic dim 384 (live corpus is
768d → ~2× matrix RAM, still trivial: ~307 MB at 100k); p50 0.7 ms rows
are encode-cached queries — realistic per-query latency with encode is
~14 ms.

## 4. LongMemEval-s full-500 (single-arm, historical headline)

Engram, e5-base, judge-free retrieval protocol (commit `18c7b8a`,
2026-06-05): **recall@5 0.853, hit@5 0.926, MRR 0.846**, mean 59 ms.
Per-type: multi-session 0.900, single-session-assistant 0.982,
knowledge-update 0.891, temporal-reasoning 0.786, single-session-user
0.743. Note: retrieval recall@k, NOT end-to-end QA accuracy — not 1:1
comparable with LLM-judged leaderboard numbers.

## 5. Fusion 3-signal A/B — the retrieval moat

The competitive differentiator: recall fuses dense-cosine + entity-PPR +
BM25-lexical via RRF, then the CE-rerank — a combination neither
HippoRAG-2 (no CE, no lexical) nor Zep (no CE) nor Mem0 (cosine only)
ships. **Default-ON since 2026-06-15** (+40ms steady-state for +7.5pp, made safe
by 3 guards: a PPR budget-thread, all recall paths applying it, and a corpus-floor
that skips it under 50 facts); opt-out via `ENGRAM_PPR_FUSION=0` for the
byte-identical pre-flip recall.

A/B on LongMemEval-s, k=5, e5-base, rerank OFF (to isolate the fusion
signal from the CE), **same code, only `ENGRAM_PPR_FUSION` toggled**
(`benchmark/longmemeval_runner.py`), **n=300**:

| arm | recall@5 | hit@5 | MRR |
|---|---|---|---|
| fusion OFF (dense cosine) | 0.834 | 0.903 | 0.800 |
| **fusion ON (3-signal)** | **0.909** | **0.967** | **0.868** |
| Δ | **+7.5 pp** | +6.3 pp | +6.8 pp |

The lift concentrates where the bi-encoder is weakest:
**single-session-user** 0.757 → 0.943 (**+18.6 pp**) and
**temporal-reasoning** 0.766 → 0.860 (**+9.4 pp**) — the BM25 channel
recovers exact-token queries the dense vector smears; multi-session, already
strong, barely moves (0.901 → 0.917). A smaller n=100 run read +13.9 pp
(0.800 → 0.939); the **n=300 figure (+7.5 pp) is the steadier, honest
headline** — the n=100 baseline was simply lower.

Versus the competition: mem0 (e5-parity, §1) lands at 0.790 — exactly where
Engram's fusion-OFF bare-cosine arm sits, because both are the same cosine
top-k. The fusion is the delta no competitor ships, so **+7.5 pp over a
mem0-class baseline** is the moat (n=300; the direct mem0 head-to-head is
n=100, where the gap was +15 pp — mem0 not yet re-run at n=300).

Cost (declared, NOT hidden): fusion ON pays the BM25 channel, and in this
hermetic-per-question harness the FTS index is rebuilt per store, so latency
inflates with corpus size (57 ms OFF → 311 ms at n=100 → 935 ms at n=300).
In production the FTS is persistent with incremental trigger-sync (commit
`4b49d79`), so the real per-query cost is far lower. **Measured**
(`scripts/bench_fusion_latency.py`, n=300, FTS persistent + warm graph,
`ENGRAM_PPR_FUSION_BUDGET_S=0`): OFF mean **178 ms** → ON **218 ms** = **+40 ms**
(p95 +36 ms). The 935 ms above is the harness's per-query FTS rebuild, not the
steady-state cost. **+40 ms for +7.5 pp recall@5 is the trade-off that justifies
default-ON**, gated behind 3 prereqs (PPR budget-thread, cold-path consistency,
corpus-floor) so the cap, coverage and small-corpus cases are all handled.

Limit: retrieval recall@k, not end-to-end QA; CE-rerank OFF in this A/B to
isolate the fusion signal; mem0 head-to-head still at n=100.

## 6. hallucination-rate@k — the anti-confab moat, measured

§5 answers "did we find it"; this answers "can the caller trust what we
found" — the axis no cosine-only store has a signal for. `hallucination-rate@k`
= the fraction of the top-k whose live trust verdict is RISKY
(obsolete/contested/unverified). Module `engram/hallucination_rate.py`, exposed
as the MCP tool `hippo_hallucination_rate`; reproduce with
`scripts/bench_hallucination_rate.py`.

Synthetic corpus (declared) built so the 3 STRONGEST matches to the query are
unreliable — the dangerous case where the most relevant fact is itself a
retracted or never-verified claim. Same store, same embedder, k=5:

| retrieval | hallucination-rate@5 | what the caller sees |
|---|---|---|
| **Engram (gate ON)** | **0.40** | retracted fact filtered out of the window; the 2 surviving low-conf hits are LABELED `unverified` |
| cosine-only (mem0-class) | 0.60 | the retracted fact re-enters the top-k as a live answer; all 3 risky hits returned UNLABELED |

Two distinct wins, both measured: Engram (1) drops the retracted fact from the
window (0.60→0.40 here) AND (2) attaches a per-hit verdict so the remaining risk
is VISIBLE and avoidable. A mem0-class store returns the same vectors with no
status / supersession / contradiction, so neither win is available to it — the
risk is handed back silently. This is a mechanism demonstration on a constructed
corpus (the absolute rate depends on the unreliable-fact mix), not a leaderboard
number; the point is that the signal exists at all — competitors report none.

## 7. LoCoMo retrieval (turn-level) — honest, mid-pack (2026-06-17)

LoCoMo (arXiv 2402.17753 — the dataset mem0 reports on): 10 multi-session
conversations, 1982 answerable QA, gold evidence at TURN granularity ("D1:3").
`benchmark/locomo_runner.py`, e5-base 768d, k=5, turn→Fact mapping, judge-free:

| metric | overall | single-hop | temporal | multi-hop | open-domain | adversarial |
|---|---|---|---|---|---|---|
| recall@5 | **0.576** | 0.297 | 0.677 | 0.268 | 0.680 | 0.546 |
| hit@5 | 0.634 | 0.582 | 0.710 | 0.370 | 0.693 | 0.554 |

**Honest reading (no spin): mid-pack, not strong.** On LongMemEval (§1/§4) Engram
retrieves at 0.85–0.88 (live re-run 2026-06-17, n=100: recall@5 0.880); on LoCoMo's
finer TURN-level retrieval it drops to 0.576, with single-hop (0.30) and multi-hop
(0.27) the weak spots — finding the exact turn in a long dialogue is hard for a
naive 1-turn→1-Fact mapping. mem0 does NOT index turns 1:1; it distills memories
from turns. Closing that gap (fact-extraction per turn) is the lever — a TODO, not
an alibi.

**NOT comparable to the leaderboard number.** mem0 reports a QA-accuracy J-score of
**55.51** on LoCoMo (LLM-judged answer correctness; full-context baseline 68.47 —
source: mem0.ai/blog/ai-memory-benchmarks-in-2026). Our 0.576 is *retrieval*
recall@5, a different axis — affixing them side by side would be dishonest. The
comparable QA-accuracy number requires the end-to-end recall→answer→judge pipeline
(not yet built; O5 caveat: our judge would be Claude, theirs GPT-4).

## 8. LoCoMo QA-accuracy (the leaderboard axis) — Engram 0.81, abstains on adversarial (2026-06-17)

§7's retrieval recall is judge-free but is NOT what competitors quote. The
leaderboard number is QA-accuracy: retrieve → answer → LLM-judge. We built it
(`benchmark/qa_eval.py` + `qa_runner.py`, 24 tests). Answerer + judge = `claude -p`
(subscription, ZERO external API key — O5), run lean (the global CLAUDE.md + hooks
are stripped via `--system-prompt --setting-sources project
--exclude-dynamic-system-prompt-sections`: 30128 → ~4228 input tokens/call, so the
model reasons about the question, not the operator's rules file). Retrieval:
e5-base, k=30, ±1-turn windows, with each turn carrying its session timestamp
(temporal QA needs it to resolve "yesterday"). n=150 QA sampled at random across
all 10 conversations (seed 0 → the true category mix), graded with the fair
semantic rubric the public LoCoMo / LongMemEval judges use.

| category (full-set share) | QA-accuracy |
|---|---|
| open-domain (42%) | 0.873 |
| adversarial (22%) | 0.882 |
| temporal (16%) | 0.692 |
| single-hop (14%) | 0.533 |
| multi-hop (5%) | 1.000 (n=4) |
| **overall (n=150)** | **0.813** |
| **distribution-weighted (true mix)** | **0.804** |

**Update (2026-06-19): strict anti-hallucination abstention is now the default**
(`docs/SEMANTIC_GROUNDING_STUDY.md`). Re-run, same n=150: **overall 0.813 → 0.827**
(cat5 adversarial 0.88 → 0.94, cat1 0.53 → 0.67, cat4 open-domain unchanged 0.87, cat2
temporal 0.69 → 0.62 = the only cost). A validated net-win — the answer path now
abstains rather than fabricating, deployed not just measured.

**The adversarial result is the point.** LoCoMo's adversarial category (22% of the
set) asks UNANSWERABLE / false-premise questions; the gold answer is `None` and the
correct behaviour is to ABSTAIN. Engram says "not mentioned" / rejects the false
premise on **0.88** of them instead of fabricating — the anti-confabulation property,
measured on a public benchmark. (Naive scoring that string-matches the model's
abstention against the literal `"None"` scores 0.06; abstention IS the correct
answer here — `judge_abstention` scores it as such.)

**Honest caveats — read before quoting the number:**
- Judge = Claude (`claude -p`), NOT GPT-4. mem0 reports a LoCoMo J-score of 55.51
  with a GPT-4 judge. Different judge → this is NOT a clean head-to-head; 0.81 is
  Engram's QA-accuracy under a fair Claude judge — comparable in METHOD, not judge-identical.
- n=150 (random, seeded), a representative sample, not the full 1982 QA.
- The weak categories (single-hop 0.53, temporal 0.69) are the genuine retrieval
  gap (§7): evidence recall@100 is only 0.76 for single-hop — the e5 bi-encoder
  mis-ranks abstract questions against casual answer turns. The full-context ceiling
  (all turns, no retrieval, fair judge) on single-hop is 0.75 → ~15pp of that gap is
  retrieval, the rest is answer/judge. Two cheap retriever levers were tried and
  BOTH measured as no-lift, then dropped (honesty over hope): HyDE query-expansion
  (cat1 0.58→0.49) and mem0-style LLM memory-extraction at ingest (cat1 0.567 vs
  0.583 raw-turns). Closing this gap needs a genuinely stronger retriever (a better
  embedding / entity-centric retrieval), not prompt tricks — a real build, not a
  quick win. So 0.81 is near the honest ceiling of the current retrieval stack.

## 9. LongMemEval QA-accuracy — Engram 0.625 (2026-06-17)

Same pipeline, LongMemEval-s, n=40 spread across all 6 question types, fair Claude
judge, retrieval k=5 (recall@5 is already 0.88 per §4 — the gold sessions ARE found):

| question type | QA-accuracy |
|---|---|
| single-session-assistant | 1.00 |
| single-session-user | 0.83 |
| knowledge-update | 0.67 |
| multi-session | 0.64 |
| temporal-reasoning | 0.30 |
| **overall (n=40)** | **0.625** |

Retrieval is NOT the bottleneck here (recall@5 0.88); the drag is temporal-reasoning
(0.30) — answering needs reasoning over timestamps across sessions, an answer-side
limit, not a retrieval one. mem0 reports ~0.66 on LongMemEval (GPT-4 judge); 0.625
under a fair Claude judge is competitive. Same caveats as §8 (judge = Claude, n=40).

## Method notes & declared limits

- All runs on one Windows 11 laptop, CPU-only, no network calls.
- LongMemEval sessions are long; Engram is tuned for short atomic facts —
  the session→Fact mapping truncates at the encoder's token limit. This
  is a property of the mapping, stated, not hidden.
- mem0 arm: isolated venv (`.venv-mem0bench`), mem0 2.0.4 + chroma + the
  same HF e5 model, `add(..., infer=False)` (raw storage, LLM never
  invoked — config uses an ollama placeholder that is never called).
  Two variants planned: `e5parity` (prefix scheme injected) and `asis`
  (mem0 as shipped). Sanity probe note: results are re-sorted by the
  returned score defensively.
- The anti-confabulation write gate stays ACTIVE during Engram ingest —
  it is part of the product under test; its warnings on dataset texts
  (e.g. "MERGED", "is open") are logged by design.
