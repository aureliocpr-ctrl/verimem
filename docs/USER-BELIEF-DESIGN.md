# Design: `user_belief` — a third epistemic class against sycophancy (Giro 2)

**Status**: FOUNDATION + INGEST TAGGING SHIPPED (`af22b04`, `0e670e1`), rest is DESIGN. 2026-07-16.
**Resolved empirically** (the load-bearing §3.1 caveat): a probe confirmed `quarantined`
is hidden from default recall via explicit SQL `status NOT IN (...)` filters (five of
them), NOT the opt-in rank floor. `user_belief` was added to all five; §5 steps 1-4 are
GREEN (status valid, ranked, hidden, stored) AND the ingest now PRODUCES it:
`ingest_conversation(..., tag_beliefs=True)` maps a `BELIEF:`-tagged extraction line to
`user_belief` instead of `model_claim` (opt-in, default off, the bench constant
`ATOMIC_EXTRACT_SYSTEM` untouched — `0e670e1`, 4 TDD tests). The read-side opt-in is
SHIPPED too: `include_beliefs=True` on `recall`/`search_facts`/`recall_as_of`/
`client.search` surfaces beliefs on EVERY branch (warm cache bypassed — the cache
stays the default view; cold-encode fallback and time travel forward the flag;
narrow: orphaned/quarantined stay hidden) — 7 TDD tests in
`tests/test_include_beliefs.py`. The hidden-set SWEEP then found and closed two real
side-doors the SQL filters don't cover (both demonstrated RED first): the default-ON
PPR/BM25 fusion resurrected beliefs via `get(live_only=True)`, and `compose_once`
could LAUNDER a belief into a derived fact without its label; plus CLI `facts list`,
BM25 `_CURATED`, `active_probe` rival parity (9 tests total in the contract file).
GUARDIAN SHIPPED (§3.4): `correct_read` opts into beliefs — the one reader allowed to,
because its job is to correct them: a belief participates in conflict DETECTION but
never WINS (corroborated rival served, belief cited in the new `uncorroborated` field,
reason "not corroborated"); a beliefs-only subject ABSTAINS
(`only_unverified_user_assertion`); an agreeing belief never flips ACCEPT→CORRECT
(3 TDD tests, honest copula-only scope unchanged). Still open: MemSyco delta.
**Goal**: stop the memory from laundering an unverified USER assertion into a stored
*fact* the recall then serves back as truth — the systemic sycophancy gap the external
review flagged (README claims "anti-sycophancy on the write path"; today that is only an
indirect side-effect of the L1 keyword detectors, not a mechanism).

## 1. The problem, precisely

When `Memory.add(messages)` extracts facts from a conversation, every extracted fact
lands with `status="model_claim"`, `writer_role=INGEST_WRITER_ROLE`
(`conversation_ingest.py:271-273`). The pipeline does **not** distinguish:

- **verifiable claim** — "the deploy is green", "Q3 revenue was 1.2M" (checkable, datable);
- **user opinion / preference** — "Python is better than Go", "I prefer morning meetings";
- **unverified user assertion of fact** — "the vendor's API is the fastest on the market".

All three become `model_claim` and enter default recall. The third is the sycophancy
trap: a future query retrieves it and the answering model treats it as an established
fact. MemSyco-Bench (2607.xxxxx) shows memory layers *amplify* sycophancy; our write gate
catches "it works" self-claims (L1) but not "the user asserted X as fact".

## 2. The distinction that must NOT be lost

Naively quarantining everything a user says would **kill personalization** — preferences
("I work in CET", "no meetings on Friday") are the primary value of a memory layer and
MUST stay in default recall. So the split is:

| kind | example | disposition |
|---|---|---|
| preference / subjective | "I prefer X", "I like Y", "my style is Z" | **stays** in default recall (the value) |
| verifiable fact w/ evidence | "moved to Berlin in March" (dialogue grounds it) | `model_claim`/`verified` as today |
| **unverified factual assertion** | "X is faster than Y", "the deploy is green" (no source) | **`user_belief`** — out of default recall until corroborated |

The classifier's default on doubt: a **factual-shaped** claim with no evidence → `belief`;
anything clearly subjective/preference → stays. Conservative toward *keeping*
personalization, strict toward *unverified factual assertions*.

## 3. Mechanism (four small hooks, no new subsystem)

1. **New status `user_belief`** in `_VALID_STATUSES` (`semantic.py:542`), ranked in
   `_STATUS_RANK` below `model_claim` (2). **VERIFIED CAVEAT (load-bearing):** the
   recall rank-filter at `semantic.py:3084-3086` runs ONLY when `exclude_legacy` or
   `min_status` is set — both opt-in. So `recall()`'s DEFAULT applies no rank floor,
   and it is NOT established that `quarantined` is actually hidden from default recall
   (the README claims it is; `client.search` calls `recall` with neither flag). Two
   possibilities, both to be settled empirically by the FIRST TDD test (§5 step 1):
   (a) an ANN-index / write-time mechanism already drops rank<0 rows — then
   `user_belief` reuses it; (b) it does not, and hiding `user_belief` (and, separately,
   `quarantined`) needs the default recall to grow a rank floor — a bigger, opt-out
   change. Do NOT assume (a). This is why the design ships behind a test that asserts
   the real default-recall behaviour before any status is added.
2. **Extraction tags it** — the extraction prompt (`extraction_system_for`,
   `conversation_ingest.py:93`) gets one instruction: mark each extracted item
   `factual | preference | opinion`; the ingest maps `factual-without-source`
   (from a user turn) → `status="user_belief"`, everything else unchanged.
   `writer_role` stays `INGEST_WRITER_ROLE` (no gate bypass).
3. **Recall opt-in** — `search(..., include_beliefs=False)` default. `True` surfaces
   them for explicit personalization. Mirrors the existing `deep=` archaeology switch.
4. **Guardian corrects** — when a `user_belief` conflicts with a `verified`/higher-rank
   fact on the same subject, `guardian.correct_read` serves the verified one and cites
   the belief as "previously asserted, not corroborated" (reuses the existing
   copula-parse path; **honest scope**: copula-only today, so non-"S is O" beliefs fall
   through to ACCEPT — documented, not hidden).

## 4. Why this is cheap and in-thesis

- Reuses the epistemic-label machinery already shipped (`_STATUS_RANK`, `writer_role`
  in `classify_admission` `admission_gate.py:100`, `FLAG_LOW_PROVENANCE`).
- No LLM call added on the read path; the one extraction LLM call already happens.
- It is the honest completion of the write→read thesis: a claim's *origin* (user vs
  corroborated) becomes first-class, exactly what a "trust layer" should encode.

## 5. Implementation plan (TDD, next Giro)

1. RED: test that `add([{user: "X is faster than Y"}])` (no source) stores `user_belief`
   and is **absent** from default `search`, **present** with `include_beliefs=True`.
2. RED: test that `add([{user: "I prefer dark mode"}])` (preference) **stays** in default
   recall (personalization not broken).
3. RED: test guardian serves a `verified` fact over a conflicting `user_belief`.
4. GREEN (SHIPPED `0e670e1`): status + rank + recall filter [`af22b04`] +
   extraction-prompt tag + ingest mapping [`0e670e1`, behind `tag_beliefs`, default off].
4b. GREEN (SHIPPED): `include_beliefs` retrieval opt-in across recall/search_facts/
   recall_as_of/client.search — every branch, cache-bypass, narrow (7 TDD tests).
5. MEASURE (SHIPPED `benchmark/memsyco_user_belief.py`): the LLM-dependent link
   (does the extractor tag the right things?) measured TWO-SIDED on claude-opus-4-8,
   n=15+15 (belief→out-of-recall is already 100% deterministic, test_include_beliefs):
   **belief-catch-rate 0.933** (14/15 unverified factual assertions tagged) and
   **preference-preservation 1.000** (15/15 preferences kept as model_claim — no
   personalization collateral). The one miss ("Everyone knows that framework is
   dead") is a social/opinion generalization, caught by the deliberate "when unsure,
   do NOT tag" bias, not a mechanism failure. The "anti-sycophancy on the write path"
   claim now has its number attached.

## 6. Open decisions (need a call, not a guess)

- **Rank slot**: `user_belief` == `quarantined` rank (-1), or a new -0.5 between
  quarantined and legacy? (affects `min_status` recall semantics — VERIFY current
  default-recall floor first).
- **Preference classifier**: prompt-only (cheap, ~90% by the extraction LLM) vs a tiny
  local classifier. Start prompt-only; measure misclassification on MemSyco-Bench.
- **Migration**: existing `model_claim` facts are untouched (no retro-reclassification —
  the class applies to NEW writes; a backfill is a separate, opt-in pass).
- **The 2% biography FP** (FLAGS-AUDIT §8): third-person biographies trip L1 dev-claim
  detectors. Related but SEPARATE from `user_belief`; fold the fix in or defer.

## 7. Non-goals

- Not touching existing `model_claim`/`verified` semantics.
- Not a general opinion-mining system — only the write-time origin tag + recall gate.
- Not claiming to solve sycophancy end-to-end; this closes the WRITE origin half. The
  retrieval-time caveat and answer self-verification (review §2.3) are later, separate.
