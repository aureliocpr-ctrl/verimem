# Cycle 113 Handoff — pre-/compact 2026-05-17

**Recovery post-compact**: leggi questo + `hippo_recall("cycle 113 handoff")` → 2 tool call.

## Stato 2026-05-17 04:30Z

### MERGED in main
- PR #49 cycle 110.E (a697f60)
- PR #51 cycle 111 v2 verified_by I/O hard-gate (**282ae1d**, 1208 LOC)

### PR APERTI in CI pending (ruff fix appena pushato)
- **PR #52** cycle 113.A — branch `cycle113A-bench-groundtruth`, head `fc8beb2`
- **PR #54** cycle 113.C RRF — branch `cycle113C-rrf-fusion`, head `1cc9c50` (rebased su 113.A)

### Episode salvato
`6ca17fe0e09b4ba0b8ff56214404d2be` con 6 key_facts atomici.

## Numeri reali da non ri-confabulare

- **Bench S4-E poisoning**: 0/20 post-fix v2 vs 100% pre-fix simulato (50/50 verified_real conservati)
- **138 query ground-truth** (corpus: 292 ep / 923 facts):
  - `cosine_with_legacy`: MRR=0.467, P@10=0.102, R@10=0.305, 19ms
  - `keyword_tokens`: MRR=0.453, P@10=0.131, R@10=0.365, 97ms
  - `cosine_trusted_only`: 4% recall (88.9% corpus = legacy_unverified)
  - `keyword` naive: 0/138 (SQL LIKE su task_text intera fail)
  - `rrf_cosine_tokens`: MRR=**0.603** (+29%), P@10=0.133, R@10=0.374, 109ms
- Wilson CI 95% INDIPENDENTI: tutti OVERLAP → direzione consistente ma NON statisticamente significativo
- 68/68 test PASS sui 4 file bench (32 metrics + 9 build_gt + 16 eval_with_gt + 11 compare)
- HippoAgent corpus state: 297 ep / 945 facts / 324 skills / 209 MCP tools

## Pending sequence (in ordine)

### Immediate (waiting CI)
1. Merge **PR #52** quando CI verde
2. Merge **PR #54** quando CI verde (dopo #52)

### Next development
3. **Cycle 113.E**: aggiungere `kg_neighbors` retrieval path al bench. EntityStore (`entity_kg/entity_kg.db`) ha 26 entities + 25 edges + 1134 fact-links inutilizzati. Path: query → extract_entities(query) → entity.neighbors → linked fact_ids
4. **Cycle 113.F**: RRF 3-way (cosine + tokens + kg_neighbors)
5. **Cycle 113.D**: McNemar paired test (real significance) — richiede n≥300 query
6. **Cycle 114 legacy cleanup**: 815/923 facts legacy_unverified, audit cycle 110.D script presente ma promotion mai fatta
7. **Cross-encoder reranking** (BGE-reranker-v2-m3, ~500MB) — paper consigliava
8. **Test SSRF flaky** indagare root cause
9. **3 preexisting CI fail** (test_ide, test_real_provider, test_consolidate_refuses) — env-dependent ma da chiudere

### Parallel (non-bloccante, altra istanza)
10. **Memory-map live dashboard**: prompt completo scritto in chat (cycle 111 v2 v2 conversation), branch `feature/memory-map-live` da creare

## Anti-pattern evitati (lessons cycle 111-113)

1. ❌ **Security theater syntactic-only** (PR #50 v1): regex pattern allowlist senza I/O verify accettava 12 attack format-valid. v2 richiede filesystem + git rev-parse.
2. ❌ **Plumbing presentato come progress reale**: cycle 113.A primi numeri erano 41 test pass ma 0 misurazioni REALI fino al run su corpus.
3. ❌ **+29% MRR senza significance**: RRF direzionale ma CI overlap, paired test mancante. Dichiarato onestamente nel PR body.
4. ❌ **Chiudere sviluppo prematuro**: Aurelio stop-check #4 ha trovato 8+ cose pending non chiuse.

## Aurelio stop-check pattern (4 round in sessione)

Pattern validato: ogni `sei sicuro? è marketing?` trova problema reale. Risposta corretta = ammettere onesto, verificare empirico, iterare. Mai bluff.

## Vincoli operativi non negoziabili

- A1 anti-confabulazione tempistiche/numeri
- A2 anti-hallucinazione, verifica empirica
- A3 stop-check sincero
- A4 no marketing
- A5 agency (decidi senza chiedere quando direzione chiara)
- O1 memoria-first
- O2 TDD strict + critic gate
- O3 salva ep+fact ad ogni cycle
- O4 solo subscription, mai API key esterna
- O5 brevità 3-5 righe italiano
- O6 consolidate = pipeline hippo_dream_*

## File chiave creati questa sessione

- `engram/provenance_validator.py` (294 LOC) — cycle 111 v2
- `engram/agent.py:47` wire — cycle 111 v2
- `engram/semantic.py` __init__ + store gate — cycle 111 v2
- `benchmark/bench_verified_by_hardgate.py` — cycle 111 v2 S4-E
- `benchmark/retrieval_metrics.py` — cycle 113.A
- `benchmark/build_retrieval_groundtruth.py` — cycle 113.A
- `benchmark/eval_retrieval_with_gt.py` — cycle 113.A + 113.C RRF
- `benchmark/compare_retrieval_variants.py` — cycle 113.C
- Test file: `test_verified_by_validation.py`, `test_retrieval_metrics.py`, `test_build_retrieval_groundtruth.py`, `test_eval_retrieval_with_gt.py`, `test_compare_retrieval_variants.py`
- `benchmark/results/cycle113-groundtruth-20260517.json` — 138 query reali
- `benchmark/results/cycle113C-eval-rrf-20260517.json` — eval 5 path × 138 query
- `benchmark/results/cycle111v2-s4e-hardgate-20260517.json` — bench S4-E

## Recovery 2-step

```
hippo_recall("cycle 113 handoff")
# poi leggi questo doc
```
