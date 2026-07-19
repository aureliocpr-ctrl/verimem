# Phase 1.1 — write-path contradiction moat, subscription-free: evidence (2026-07-19)

What the **llm-free** contradiction moat actually does, measured on labeled data with
the shipped default judge — the local NLI cross-encoder
(`MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli`, cached, offline). No
`claude -p`, no external API.

Reproduce: `python -m benchmark.semantic_conflict_bench --judge local --min-cosine 0.7`
(result: `benchmark/results/semantic_conflict_local_2026-07-19.json`).

## Result — labeled conflict/duplicate/complementary cases (n=18)

The set separates the case the whole *lexical* stack misses (A: same subject, the
words differ but the meaning conflicts, cosine 0.80–0.87, no number / no negation
token) from the two it must NOT false-positive on (D: paraphrase duplicate; E:
complementary facts about the same subject, also high cosine).

| case | what it is | n | lexical conflict | **local-NLI conflict** | NLI duplicate |
|------|------------|--:|-----------------:|-----------------------:|--------------:|
| **A** | semantic conflict (meaning, not words) | 8 | **0.00** | **1.00** | — |
| B | numeric clash (30→5 entries) | 2 | 1.00 | 1.00 | — |
| C | explicit negation | 2 | 1.00 | 1.00 | — |
| D | paraphrase duplicate (**not** a conflict) | 2 | 0.00 | 0.00 | **1.00** |
| E | complementary, same subject (**not** a conflict) | 4 | 0.00 | **0.00** | 0.00 |

Reading it honestly:

- **The headline:** on the 8 hard semantic conflicts the lexical stack catches **0**,
  the free local NLI catches **8/8** — the whole reason the layer exists, now working
  with no subscription. B+C (already lexically caught) are also caught: **12/12** true
  conflicts.
- **No false alarms on the two hard negatives:** paraphrase duplicates (D) are labeled
  `semantic_duplicate`, not conflict; complementary same-subject facts (E) — the class
  a naive "high cosine ⇒ conflict" rule wrecks — score **0/4** conflict. Precision held.
- **Small n.** This is a labeled *smoke* certification (18 pairs), not a large corpus.
  It shows the local judge reproduces an llm judge's verdicts on these designed cases;
  it does not claim a population error rate. Larger/external contradiction corpora are
  follow-up.

## The one measured weakness — temporal evolution (why `observe` is the local default)

The same run, probed on time-ordered pairs, confirms the local cross-encoder **does not
read the `[timestamp]` prefix** `_stamp()` prepends (that prefix is for the *llm* judge,
which is prompted to treat a time-ordered value change as evolution → NEUTRAL):

| pair | verdict | correct? |
|------|---------|----------|
| `[2020] Alice lives in Rome` vs `[2024] Alice lives in Paris` (evolving) | contradiction | ✗ should be supersession |
| `Alice lives in Rome` vs `Alice lives in Paris` (same-time) | contradiction | ✓ |
| `[2020] bridge opened 1998` vs `[2024] bridge opened 2001` (immutable) | contradiction | ✓ |
| `Alice lives in Rome` vs `Alice resides in Rome` (paraphrase) | entailment | ✓ |
| `Alice lives in Rome` vs `Bob is 30` (unrelated) | neutral | ✓ |

So the llm-free path over-flags **evolving** facts as contradictions. This is why:

- **`observe` is the recommended local mode** — it surfaces the would-be block as an
  advisory (`L3-semantic-observe`) without quarantining, so the false-block rate
  (including these temporal FPs) is measured on real tenants before any enforcement.
- **enforce-with-local** suits immutable-fact topics, or should be paired with
  `Memory(llm=...)` (the llm judge is prompted for temporal evolution).
- The deterministic fix for the common case — **same-source supersession** (a source
  that updates its own earlier value supersedes it rather than conflicting) — is a
  separate, security-sensitive change to the `auto_supersede_on_contradiction` trust
  rule and is deliberately deferred to its own reviewed block, not bolted on here.

## Scope of the claim

"Verimem's write path can catch a *semantic* contradiction the lexical stack misses,
for free and offline" — **supported** by the A row (0.00 → 1.00) with precision held on
D/E. "It reconciles evolving facts on its own with the local judge" — **not yet**; that
needs the source-based supersession rule or an llm judge. Stated as such in the
CHANGELOG and README.
