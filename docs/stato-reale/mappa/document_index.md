# mappa — `verimem/document_index.py`

**owner ws6 Aldo** · base `20257636` · 2026-09-09 12:26

**587 righe · 17 funzioni · 4 classi.** Contate con `ast`
(`scratchpad/inventario.py`), non con grep. **5 pubbliche, 9 private.**

Metodo e limiti: quelli dichiarati in `semantic.md`. Le quattro trappole già
pagate valgono anche qui — il nome con la parentesi non vede i **callback**;
escludere il file stesso fa sembrare morti gli helper; cercare solo in
`verimem/` e `tests/` dimentica `benchmark/`; il nome nudo dei metodi generici
pesca ogni dizionario.

## Le righe

| gruppo | test | verdetto | prova |
|---|---|---|---|
| le **5 pubbliche** dell'indice documenti | `tests/test_document_index.py` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_document_index.py` → `8 passed, 1 warning in 7.x` EXIT=0 |
| le 9 `_private` | via i chiamanti | **NON MISURATE** direttamente | — |

**Zero pubbliche senza test.** ⚠️ 4 classi in questo file: il rapporto
classi/funzioni più alto della mia parte.
