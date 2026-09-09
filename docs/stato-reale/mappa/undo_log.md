# mappa — `verimem/undo_log.py`

**owner ws6 Aldo** · base `20257636` · 2026-09-09 12:26

**335 righe · 9 funzioni · 1 classi.** Contate con `ast`
(`scratchpad/inventario.py`), non con grep. **6 pubbliche, 3 private.**

Metodo e limiti: quelli dichiarati in `semantic.md`. Le quattro trappole già
pagate valgono anche qui — il nome con la parentesi non vede i **callback**;
escludere il file stesso fa sembrare morti gli helper; cercare solo in
`verimem/` e `tests/` dimentica `benchmark/`; il nome nudo dei metodi generici
pesca ogni dizionario.

## Le righe

| gruppo | test | verdetto | prova |
|---|---|---|---|
| le **6 pubbliche** dell'undo | `tests/test_undo_log.py` · `tests/test_undo_log_prune_on_write.py` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_undo_log.py` → `15 passed, 1 warning in 11.61s` EXIT=0 · `test_undo_log_prune_on_write.py` → `1 passed in 7.48s` EXIT=0 |
| le 3 `_private` | via i chiamanti | **NON MISURATE** direttamente | — |

## `invalidate_handles_for` — la quarta volta della forma «importata, non chiamata»

Segnalata come «pubblica senza test». I cinque controlli:

```
grep -rnw invalidate_handles_for .
  → verimem/semantic.py:5529   from .undo_log import invalidate_handles_for
  → verimem/semantic.py:5530   invalidate_handles_for(conn, fact_id, …)
  → verimem/semantic.py:5584   from .undo_log import invalidate_handles_for
  → verimem/semantic.py:5585   invalidate_handles_for(conn, fact_id, keep_op_id=op_id)
```

⇒ **Viva e usata da un altro modulo**, con **import locale dentro la funzione**
— la stessa forma di `_rango_di_fiducia` (importata da `contradiction.py`) e dei
callback di `audit_head_at`. Nessun test la nomina; la esercitano i test di chi
la chiama. **NON MISURATA** direttamente, **non** morta.
