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
