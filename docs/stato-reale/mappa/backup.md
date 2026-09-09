# mappa — `verimem/backup.py`

**owner ws6 Aldo** · base `20257636` · 2026-09-09 12:26

**546 righe · 12 funzioni · 1 classi.** Contate con `ast`
(`scratchpad/inventario.py`), non con grep. **6 pubbliche, 6 private.**

Metodo e limiti: quelli dichiarati in `semantic.md`. Le quattro trappole già
pagate valgono anche qui — il nome con la parentesi non vede i **callback**;
escludere il file stesso fa sembrare morti gli helper; cercare solo in
`verimem/` e `tests/` dimentica `benchmark/`; il nome nudo dei metodi generici
pesca ogni dizionario.

## Le righe

| gruppo | test | verdetto | prova |
|---|---|---|---|
| le **6 pubbliche** del backup | `tests/test_backup_all_dbs.py` · `tests/test_engram_backup.py` · `tests/test_backup_follows_the_data_dir.py` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_backup_all_dbs.py` → `3 passed in 7.75s` EXIT=0 · `test_engram_backup.py` → `11 passed in 13.39s` EXIT=0 |
| le 6 `_private` | via i chiamanti | **NON MISURATE** direttamente | — |

**Zero pubbliche senza test**, e **tre** file di test dedicati — è il file con
la copertura nominale più larga fra i piccoli della mia parte. Ha senso: è ciò
che deve funzionare quando tutto il resto è già andato storto.
