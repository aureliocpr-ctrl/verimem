# mappa — `verimem/admission_cleanup.py`

**owner ws6 Dati** · base `20257636` · 2026-09-09 12:26

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

## Inventario completo — ogni funzione per nome

**3 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 47 | `cleanup_telemetry` | **pub** | Route existing telemetry facts out of ``facts`` into ``tel | 4 — `test_admission_cleanup.py` |
| 149 | `cleanup_episode_telemetry` | **pub** | Route existing call-telemetry episodes out of ``episodes`` | 3 — `test_audit_mutations_episodic.py` |
| 239 | `requalify_quarantined` | **pub** | Re-evaluate quarantined facts with the CURRENT gate and pr | 6 — `test_il_riesame_della_quarantena_lascia_traccia.py` |
