# Decision chain — decisions as first-class, explainable memory objects

Status: DESIGN (task #15, mandate Aurelio 2026-07-10). Implementation AFTER
the trust-core block. Deliberately reuses existing bricks — no new subsystem.

## Why

"Salvare la catena delle decisioni: il perché di errori o cose scelte, per
scalare la concatenazione e l'intelligenza" (Aurelio). Today verimem answers
*"how do you know X?"* (explain → chain of custody). A decision record makes
it answer *"why did we choose X?"* — with the same custody discipline: the
evidence considered, the alternatives rejected, the expected outcome, and —
later — what actually happened.

## Record shape (v1)

A decision is a FACT (typed by topic `decisions/<area>`) whose proposition is
the choice itself, plus structured fields:

| field | meaning |
|---|---|
| `decision` | one sentence, the choice made (the fact's proposition) |
| `alternatives[]` | options considered and rejected, one line each |
| `evidence[]` | fact ids CITED at decision time (KG edges decision→fact) |
| `expected` | falsifiable expected outcome + horizon (`revisit_at`) |
| `outcome` | added LATER via a dedicated call, requires `verified_by` |

Storage options (decide at implementation, verify code first):
- **A — typed fact + KG edges** (preferred if fact meta supports the fields):
  zero new tables, recall/graph/console work immediately;
- **B — dedicated table** mirroring `documents.py` isolation, promoted into
  facts on demand (if fact meta is too rigid).

## Reuse map

- *"why did we choose X?"* → `explain(query)` already builds the dossier; a
  decision fact carries its evidence edges, so `reasoning_dossier` walks
  decision → evidence → provenance with zero new query machinery.
- Graph v3 console: decisions appear as nodes; chain-of-custody lighting
  already visualises the evidence trail (the "volto" shows the why).
- Write gate: decision facts pass the SAME admission gate (a decision with a
  fabricated evidence id must fail exactly like any unsupported claim).

## The outcome loop and the guard-rail (binding)

Recording outcomes invites source-scoring ("decisions citing source S went
badly → distrust S"). That is the measured catastrophic path
(TRUST_CORE.md guard-rails; Vivarium RQ1: outcome-only collapses 32% of
worlds, EWMA 40%, inversion trap). Binding rules, v1:

1. an outcome updates ONLY its decision record — never the cited sources;
2. staleness lives on the claim (`expected` vs observed at `revisit_at`),
   never on a source wholesale;
3. any future source-weighting needs the inter-source-agreement signal
   FIRST (use-independent, rehabilitating) — same spec the Vivarium graft
   (vivarium-verimem, seeds 801+) must satisfy.

## API sketch (v1, subject to code verification)

```python
mem.record_decision(decision, *, alternatives=[...], evidence=[fact_ids],
                    expected="...", revisit_at=ts, topic="decisions/arch")
mem.decision_outcome(decision_id, outcome_text, *, verified_by=[...])
mem.explain("why did we choose the e5 embedder?")   # existing call, richer answer
```

## Non-goals v1

No automatic decision scoring; no source reputation; no LLM-generated
retrospectives (an outcome without `verified_by` is a model_claim like any
other). Measure of success: on 10 real decisions from the dev journal, the
dossier answers "why" with the evidence that was actually cited, and one
recorded outcome per decision survives the gate.
