# mappa — `verimem/truth_reconciliation.py`

**owner ws6 Aldo** · base `20257636` · 2026-09-09 12:26

**421 righe · 17 funzioni · 0 classi.** Contate con `ast`
(`scratchpad/inventario.py`), non con grep. **6 pubbliche, 11 private.**

Metodo e limiti: quelli dichiarati in `semantic.md`. Le quattro trappole già
pagate valgono anche qui — il nome con la parentesi non vede i **callback**;
escludere il file stesso fa sembrare morti gli helper; cercare solo in
`verimem/` e `tests/` dimentica `benchmark/`; il nome nudo dei metodi generici
pesca ogni dizionario.

## Le righe

| gruppo | test | verdetto | prova |
|---|---|---|---|
| le **6 pubbliche** della riconciliazione | `tests/test_reconcile_evidence_gate_writepath.py` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_reconcile_evidence_gate_writepath.py` → `7 passed, 1 warning in 1x.x` EXIT=0 |
| le 11 `_private` | via i chiamanti | **NON MISURATE** direttamente | — |

## `find_similarity_candidates` (331) — pubblica di nome, interna di fatto

Il mio script l'ha segnalata come «pubblica senza test». I cinque controlli:

```
grep -rnw find_similarity_candidates .   (ogni tipo di file, tutto il repo)
  → verimem/truth_reconciliation.py:331   la definizione
  → verimem/truth_reconciliation.py:393   la chiamata
```

⇒ **Nessun test la nomina, ma è chiamata dentro il proprio file** (riga 393) e
la esercita il test del suo chiamante. Non è morta e non è senza porta: è una
funzione **pubblica di nome e interna di fatto** — non ha l'underscore, ma
nessuno la usa da fuori. **NON MISURATA** direttamente.

## Inventario completo — ogni funzione per nome

**17 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 36 | `_is_reconcilable` | priv | Tier guard (2026-07-02): the knowledge-reconcile judge act | 🔴 **nessuno** |
| 45 | `_conflict_tokens` | priv |  | 1 — `test_la_guardia_dell_overlap_parlava_solo_inglese.py` |
| 49 | `_default_max_diff` | priv | Token-difference tolerance for looks_like_conflict, env-tu | 🔴 **nessuno** |
| 66 | `looks_like_conflict` | **pub** | Best-effort token heuristic: True when the two proposition | 3 — `test_reconcile_nli_judge.py` |
| 86 | `_authority` | priv |  | 🔴 **nessuno** |
| 91 | `_has_evidence` | priv | A fact carries EVIDENCE iff it cites a verified source or  | 🔴 **nessuno** |
| 100 | `classify_conflict` | **pub** | Classify a conflict between an older fact and a newer one. | 6 — `test_asserted_at_bitemporal.py` |
| 152 | `reconcile_fact_on_write` | **pub** | Reconcile ``new_fact`` against conflicting older ``candida | 4 — `test_fact_tier_guard.py` |
| 230 | `_content_tokens` | priv | Lowercased content tokens (stopwords removed) for the over | 🔴 **nessuno** |
| 235 | `_content_overlap` | priv | Jaccard overlap of content tokens. A same-attribute VALUE  | 4 — `test_la_guardia_dell_overlap_parlava_solo_inglese.py` |
| 243 | `_min_conflict_overlap` | priv | Precision guard on the JUDGE path (default 0.0 = OFF, unch | 1 — `test_verimem_env_thresholds.py` |
| 256 | `_is_conflict` | priv | Conflict confirmation. With a semantic ``judge`` (Relation | 2 — `test_reconcile_nli_judge.py` |
| 281 | `find_related_candidates` | **pub** | Find older facts that could be an update of ``new_fact``:  | 1 — `test_truth_reconciliation_matching.py` |
| 323 | `_sim_fallback_enabled` | priv | ENGRAM_RECONCILE_SIM_FALLBACK=1 — similarity candidates wh | 🔴 **nessuno** |
| 331 | `find_similarity_candidates` | **pub** | Similarity fallback for candidate discovery (task #21). | 🔴 **nessuno** |
| 368 | `reconcile_against_corpus` | **pub** | End-to-end P1: FIND shared-entity candidates for ``new_fac | 4 — `test_fact_tier_guard.py` |
| 130 | `_event_time` | priv |  | 🔴 **nessuno** |
