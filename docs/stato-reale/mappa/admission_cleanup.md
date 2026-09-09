# mappa — `verimem/admission_cleanup.py`

**owner ws6 Aldo** · base `20257636` · 2026-09-09 12:26

**487 righe · 3 funzioni · 0 classi.** Contate con `ast`
(`scratchpad/inventario.py`), non con grep. **3 pubbliche, 0 private.**

Metodo e limiti: quelli dichiarati in `semantic.md`. Le quattro trappole già
pagate valgono anche qui — il nome con la parentesi non vede i **callback**;
escludere il file stesso fa sembrare morti gli helper; cercare solo in
`verimem/` e `tests/` dimentica `benchmark/`; il nome nudo dei metodi generici
pesca ogni dizionario.

## Le righe

| gruppo | test | verdetto | prova |
|---|---|---|---|
| le **3 pubbliche** (il file non ha private) | `tests/test_admission_cleanup.py` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_admission_cleanup.py` → `3 passed in 6.67s` EXIT=0 |

**487 righe per 3 funzioni e zero private**: il rapporto righe/funzione più alto
di tutta la mia parte (162). Non è un difetto — sono tre funzioni lunghe con
molta logica dentro — ma è il file dove una riga di test copre più codice che
altrove, e chi lo toccherà dovrebbe saperlo.
