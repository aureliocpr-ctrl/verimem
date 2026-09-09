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

## Inventario completo — ogni funzione per nome

**9 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 57 | `ensure_undo_table` | **pub** | Create the facts_undo_log table if it doesn't exist. | 2 — `test_undo_log.py` |
| 95 | `_is_bytes_envelope` | priv |  | 🔴 **nessuno** |
| 104 | `_row_to_dict` | priv | Serialize a single facts row to a dict, preserving all col | 🔴 **nessuno** |
| 129 | `_dict_to_row_args` | priv | Inverse of _row_to_dict: produce (cols, values) for an INS | 🔴 **nessuno** |
| 162 | `snapshot_pre_op` | **pub** | Snapshot the fact row BEFORE a destructive op. Returns op_ | 3 — `test_timone_supersede_undo.py` |
| 199 | `undo_op` | **pub** | Restore the pre-op snapshot for op_id. Returns result dict | 3 — `test_timone_non_resuscita_i_cancellati.py` |
| 258 | `list_undoable` | **pub** | Return the N most recent undoable ops (newest first, not y | 2 — `test_undo_log.py` |
| 282 | `invalidate_handles_for` | **pub** | Drop the PENDING undo handles that would resurrect ``fact_ | 🔴 **nessuno** |
| 315 | `prune_expired_undo_log` | **pub** | Delete undo entries past their TTL. Returns count deleted. | 2 — `test_undo_log.py` |

## Le classi di questo file — 1 sulla superficie

Il righello del lead conta le **classi** nel denominatore (480 sui miei 21 file
contro i 449 di sole funzioni): una classe e' superficie, e finche' non e'
nominata qui non e' mappata. Stesso patto dell'inventario sopra: la colonna
«test» dice quanti file di `tests/` **nominano** quel nome — rintracciabilita',
non un verdetto.

| riga | classe | metodi | cosa promette | test che la nominano |
|---|---|---|---|---|
| 46 | `UndoEntry` | 0 | One row from facts_undo_log. | 🔴 **nessuno** |
