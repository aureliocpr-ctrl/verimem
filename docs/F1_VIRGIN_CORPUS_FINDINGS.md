# F1 — Virgin-corpus validation findings (task #22)

Status: IN PROGRESS (started 2026-07-10). Mandate (Aurelio): run the COMPLETE
engine on an ESTRANEO corpus never touched in development — "se e' sviluppato
sul mio cadra' su uno nuovo". Every fall is a phase-C fix. This file is the
running catalogue of falls; the fixes are TDD, AFTER measurement, not now.

**Phase-C update (same evening, task #25)** — Aurelio mandate: "i gate devono
essere separati... se uno non passa fa backpropagation chiedendo: ma questo
tocca a me o a qualcuno di voi?". Shipped, TDD:

- **Gate router** (`engram/gate_router.py`): every write-path gate now routes
  on the ownership answer — agent_claim / external_content / user_input /
  trusted_hook (`classify_provenance`). When a gate fires, its event carries
  the attribution (the "whose claim is this?" question) instead of deciding
  silently. Security invariant: provenance never weakens the injection
  defense — it only routes the warning-only self-claim heuristics.
- **C4 FIXED — sanitize-then-scan** (`sanitize_dangerous_unicode` +
  `ENGRAM_UNICODE_SANITIZE`, default ON): invisible code points are stripped
  BEFORE any detector (screen AND admission gate share the choke point).
  Full-dev MuSiQue rescan: paragraphs quarantined 382→**39** (0.8%→0.08%),
  questions with a GOLD quarantined 97→**1** (4.0%→**0.04%**), 343 paragraphs
  sanitized+admitted. Residual declared: 38 obfuscation (mixed-script
  homoglyph defense, kept on purpose) + 1 role_hijack prose FP.
  **Red-team UNCHANGED pre/post: catch 0.9677 (30/31), FP 0.0, unicode-evasion
  2/2 still caught** (post-strip the L1.20 matcher sees the exposed claim) —
  defused, not weakened. Discovery en route: quarantine is enforced at TWO
  points (injection screen + admission gate, `ENGRAM_ADMISSION_GATE=1` on this
  machine) — the shared sanitize hoist fixes both; a per-gate patch would not.
- **C1 FIXED — cold-load overruns no longer trip the breaker**: only a
  STEADY overrun (`_reranker_ready()` True) counts toward the N=5 trip; a
  separate generous bound (`ENGRAM_RERANK_COLD_BREAKER_N`, default 40) still
  covers the never-warms pathology. Rerank (+0.29 R@1) stays available.
- **C2 FIXED — L1.x routed by provenance**: skip for external_content /
  user_input (a document saying "merged" is not the agent claiming a merge);
  full discipline kept for agent claims and hooks.

Suites green: 67 (sanitize+router+breaker+injection) + 19 (multilang+redteam
fixes) + 123 (anti-confab) + 18 (source-trust guard). Run C (n=210, fixed
engine, writer_role=external_content) pending below.

## Discipline

- **Virgin corpora only.** Burnt (tuned/measured on): LongMemEval, LoCoMo,
  HaluEval, TruthfulQA, ClashEval, HaluMem. HotpotQA is a cousin (HaluEval's
  `knowledge` is built on it) — excluded. Chosen fresh: **MuSiQue** (multi-hop
  QA), **MSC** (multi-session chat), **QuALITY** (long documents).
- **Real engine, judge-free, no API** (CLAUDE.md O5). Objective metrics only:
  retrieval of gold `is_supporting` ids. No LLM judge, no external key.
- **Production write path.** Facts stored through the real `SemanticMemory.store`
  — redaction + injection screen ON by default, exactly as a user would hit it.

## The thesis emerging from F1

> The engine's gates are calibrated for **agent work-memory** (short,
> ASCII, self-asserted facts). Fed **externally-ingested document content**
> they misfire — from harmless noise (C2) to **silent data loss** (C4). The
> corpus fell exactly where the mandate predicted, and the cause is a single
> axis: **provenance**. A `writer_role='agent_inference'` self-claim and a
> paragraph ingested from a trusted document must not pass the same gate.

---

## Corpus 1 — MuSiQue-Answerable dev (multi-hop, 2417 q, virgin)

Harness: `benchmark/external_f1_musique.py` (+ pure-fn tests
`tests/test_external_f1_musique.py`, 9 green). Each item's 20 paragraphs →
one `Fact` each (proposition = "title. text"); recall the question; score
recall@k / hit@k / **all-hops@k** / MRR against the supporting ids. all-hops@k
= ALL supporting paragraphs in top-k (the multi-hop-honest metric).

### Numbers — n=210 stratified by hop, bi-encoder, injection ON (as-is production)

| k | recall@k | hit@k | all-hops@k |
|---|---|---|---|
| 2 | 0.453 | 0.924 | 0.081 |
| 5 | 0.627 | 0.986 | 0.257 |
| 10 | 0.772 | 0.990 | 0.457 |
| 20 | 0.982 | 1.000 | 0.938 |

MRR=0.896, top1_score≈0.834, latency 82ms. By hop (all-hops@5): 2-hop 0.529,
3-hop 0.186, 4-hop **0.057** — collapses with chain depth.

**Reading.** hit@k and MRR are excellent — the engine finds A hop almost
always and ranks the first gold at the top. all-hops@k is the multi-hop wall:
at small k it rarely holds the WHOLE chain, worst at 3/4 hops. This is C3, the
honest hard case the graph (#1) must beat, not a regression.

**Run C — same n=210, FIXED engine (writer_role=external_content, sanitize
ON), `f1_musique_fixedC_n210.json`.** C4 closed end-to-end on the real engine:

| k | recall (A→C) | all-hops (A→C) |
|---|---|---|
| 20 | 0.982 → **1.000** | 0.938 → **1.000** |
| 10 | 0.772 → 0.789 | 0.457 → 0.519 |

Every gold paragraph now returns at full k — the ~6% that was missing was the
quarantined gold, gone. (MRR 0.896→0.857: the recovered paragraphs put ~1 more
real distractor back in the pool, a fair trade for +6pt all-hops. The C3
multi-hop wall at small k is unchanged — that is the graph's job, not the
gate's.)

**all_hops@20 = 0.938, not 1.0** — with k=20 over 20 paragraphs it should be
1.0. The ~6% gap is C4: a quarantined gold never returns, even at full k. A
clean cross-check that the gate, not the retriever, costs recall. Isolated by
the injection-OFF run (`f1_musique_noscreen_n210.json`): expect all_hops@20 →
~1.0. Global detector scan of the full 2417-q dev set: **382/48315 paragraphs
(0.8%) quarantined; 97 questions (4.0%) have a GOLD paragraph quarantined =
unanswerable by the gate.** Signals: unicode_smuggling 343, obfuscation 38,
role_hijack 1.

---

## Falls catalogued

### C4 — Injection screen quarantines legitimate document text (CRITICAL, verified)

**Symptom.** ~8% of Wikipedia paragraphs (5/60 in a 3-item probe) are
QUARANTINED by the always-on prompt-injection screen — rank -1, hidden from
default recall. **1 of the 5 was a GOLD supporting paragraph** ("Richmond,
Virginia", the answer-bearing hop), so its question becomes unanswerable
because of the gate, not the retriever.

**Evidence (codepoints, verified directly against `detect_injection`).**
Signal `unicode_smuggling` fires on:
- `U+FEFF` zero-width no-break space — Wikipedia coordinates (`37°32′N 77°28′W`);
- `U+200B` zero-width space — IPA pronunciation blocks;
- IPA symbols `ˈ æ ɜ ː ɡ ʁ` (Strasbourg, Ottawa lede);
- `° ′ ″` geographic symbols.

All normal document content. `obfuscation` fires similarly on mixed-script text.

**Root cause.** The screen is correct FOR agent work-memory (a short fact with
a BOM or zero-width run IS a poisoning vector). The bug is the POLICY when the
content is ingested from a trusted document: a hard, recall-lossy quarantine.

**Product impact.** On a document-ingesting SaaS, ~8% of multilingual / place /
phonetic content silently disappears from recall. This is the exact
"malfunction a user could complain about" the mandate sets to ~zero.

**Fix candidate (phase C).** Do NOT weaken the detector (keeps agent-memory
defense). Branch on provenance: for document-ingest (writer_role document/user
or a source-doc episode), **sanitize** (strip zero-width, NFKC-normalize) and
admit, instead of quarantine. Keep quarantine for self-asserted agent facts.
Sanitization must be logged (non-silent) and reversible.

### C1 — Rerank breaker trips during cold-load, disabling the CE for the process (HIGH, verified)

**Symptom.** The cross-encoder rerank (worth +0.29 R@1 on LongMemEval) is OFF
for the whole run: 5 consecutive cold-budget overruns trip the breaker.

**Root cause.** `_rerank_stage2` calls `_rerank_breaker_overrun()` on a
cold-load overrun (`_reranker_ready()` False, ~33s CE load, 0.25s cold budget)
identically to a steady-state overrun. The first few recalls of any fresh
process trip the breaker WHILE the CE is still warming — then it stays off
until restart.

**Interaction with fix #14 (RAM).** Reranker preload is default-OFF (my RAM
fix), so the CE is always cold at start; a burst of early queries trips the
breaker → rerank effectively off in production, not just in this bench.

**Fix candidate (phase C).** Count an overrun toward the trip ONLY when
`_reranker_ready()` is True (steady CE too slow = a real problem). A cold-load
overrun is transient by definition and must not trip. Optionally: warm the CE
once before a batch bench so the measured number reflects rerank-ON.

### C2 — L1.x anti-confab warns on ordinary document words (MEDIUM, verified)

**Symptom.** Warnings on paragraphs containing `MERGED / SHIPPED / DEPLOYED /
DIAGNOSED / "is open" / "is closed"` — all common English, here in Wikipedia
prose ("the companies merged in 1998").

**Root cause.** L1/L1.5/L1.7 detectors key on agent work-status keywords
(SHIPPED-without-commit = confabulation). Applied to ingested document content
they false-positive. Warning-only (the fact IS saved), so no recall loss —
but the warning is emitted (BUS event) and would surface in a customer dossier.

**Fix candidate (phase C).** Same provenance branch as C4: skip L1.x for
document/user-provenance facts; keep them for `agent_inference` self-claims.
(The schema already has `writer_role` + `meta_narrative` for exactly this kind
of gating — extend it to the ingest path.)

### C3 — Multi-hop bridge gap (bi-encoder finds the easy hop) (EXPECTED, quantifying)

**Symptom.** hit@k high, all_hops@k low at small k, worst at 3/4 hops. The
bi-encoder retrieves the lexically-close hop and misses the bridge entity that
only the multi-hop chain connects. Quantified by the n=210 run (pending).

**Note.** This is the honest hard case, not a regression — MuSiQue is
adversarially built for it. The lever is the multi-hop graph (task #1,
traced_paths / reasoning_dossier): retrieve hop-1, expand via the entity graph,
retrieve hop-2. F1 gives the baseline this must beat.

---

## Corpus 2 — MSC-Self-Instruct (conversational memory, virgin)

Harness `benchmark/external_f1_msc.py` (4 fn-tests green). The PRODUCT case:
prior chat sessions ingested (writer_role=user), then "remember when we talked
about X?". n=90 scored (60/150 skipped — paraphrase-only answers with no
substring gold, declared), 51 turns/item.

| k | hit@k | recall@k |
|---|---|---|
| 1 | 0.389 | 0.304 |
| 5 | 0.644 | 0.505 |
| 10 | 0.822 | 0.653 |

MRR 0.506, latency 518ms. Weaker than MuSiQue (hit@10 0.99): conversational
queries are vaguer, turns are short/colloquial, and the substring gold is noisy
(marks any turn mentioning the answer word). Honest read: the answer-bearing
memory is in the top-10 82% of the time but FIRST only 39% — an area to improve
(rerank, now unblocked by C1, is the lever; it does not warm in a per-item
hermetic bench). Not a hard verdict given the heuristic gold + 40% skip.

## Corpus 3 — QuALITY (long documents, virgin) — the S2 proof

Harness `benchmark/external_f1_quality.py` (3 fn-tests green). 115 articles
(median ~27k chars, ALL > the 512-token window) in ONE shared store; 300
questions (seed 42); gold = source article id. Same haystack, two ingests:

| k | whole (1 fact/article, truncated) | chunked (chunk_text, 4249 facts) | Δ |
|---|---|---|---|
| 1 | 0.517 | **0.767** | **+25pt** |
| 3 | 0.613 | 0.867 | +25pt |
| 5 | 0.663 | 0.883 | +22pt |
| 10 | 0.860 | 0.903 | +4pt |

MRR 0.599 → **0.817** (+22pt). Latency 115ms → 452ms (4249-fact store; fair
trade, sub-second).

**Reading.** The S2 silent truncation costs 25 points of hit@1 on long
documents; the existing chunker recovers them. Together with the non-silent
store guard (c2150c1) the fall is closed: the wrong door now WARNS and points
at the right door, and the right door measurably works. Declared limit:
article-level gold (no span annotation without a judge).

**QuALITY residual (measured, declared):** 2/4249 chunks (0.05%, 1/115
articles) quarantined as `role_hijack` — FICTION DIALOGUE ("From now on,
suppose you take care of the cooking"). Tolerable: the article stays
retrievable via its other ~35 chunks, and loosening role_hijack would weaken a
real defense for 0.05%. The alternative policy (document-mode demote instead
of quarantine) is an F2 product decision, Aurelio's call.

## Adversarial scenario map (mandate: "apri gli orizzonti, non far ridere la gente")

Think as a hostile reviewer / real user, not as the author. Where would Verimem
embarrass itself publicly? Concatenating the evening's thesis (gates
mis-calibrated off agent-memory) outward:

| # | scenario | status | evidence |
|---|---|---|---|
| S1 | **Multilingual gates** — the site sells "10 languages"; do gates quarantine legit Russian/Greek/CJK/Arabic/Hebrew/Hindi? | ✅ HOLDS (verified) | 0/10 non-Latin legit texts quarantined; mixed-script check is per-word (LATIN+other in ONE token), which legit prose never hits. A strength, not a fall. |
| S2 | **Long documents** — e5 truncates at 512 tok; ingest a 30-page PDF and query page 20 | ✅ FIXED+PROVEN | Fall verified (115/115 articles > 512 tok, direct add sees ~7%) → non-silent store guard shipped (c2150c1, TDD 4) → whole-vs-chunked on the real haystack: hit@1 0.517→0.767 (+25pt), MRR +22pt. Corpus-3 section below. |
| S3 | **Scale** — tested at 20-fact hermetic stores; 100k facts? recall latency, RAM (already bitten), auto-floor stability | ⏳ open | — |
| S4 | **Contradictions on a real corpus** — Aurelio's question "siamo forti sulle contraddizioni?"; reconcile outside the in-house garden | ⏳ open | source-trust + reconcile shipped behind flags; not stressed on a virgin conflicting corpus |
| S5 | **Adversarial queries** — empty, cross-language, injection-in-the-query, 10k-char query | ⏳ open | recall has a k<=0 guard + cold-encode fallback; the rest untested |
| S6 | **Cold-start / prior-chat ingest** — new user, 0 docs; importing past chats (Aurelio asked). `conversation_ingest.py` exists | ⏳ open | — |

Priority next: S2 (verified fall, small fix), then S4/S5 as virgin-corpus
stress once MSC/QuALITY runs land.

## Next

1. ✅ DONE — n=210 A (injection ON) vs B (OFF) vs C (fixed): C4 closed, recall@20 → 1.0.
2. ✅ DONE — phase C fixes (C4/C1/C2) shipped TDD (commit 513fa9f).
3. S2 length-guard on store (non-silent), TDD.
4. Corpus 2 (MSC, harness ready) and 3 (QuALITY, needs chunk-ingest) — one heavy run at a time.
5. S4/S5 stress on the virgin corpora.
