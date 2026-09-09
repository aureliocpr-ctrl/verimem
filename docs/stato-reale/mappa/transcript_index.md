# mappa — `verimem/transcript_index.py`

**owner ws6 Aldo** · base `20257636` · 2026-09-09 12:26

**340 righe · 13 funzioni · 2 classi.** Contate con `ast`
(`scratchpad/inventario.py`), non con grep. **8 pubbliche, 4 private.**

Metodo e limiti: quelli dichiarati in `semantic.md`. Le quattro trappole già
pagate valgono anche qui — il nome con la parentesi non vede i **callback**;
escludere il file stesso fa sembrare morti gli helper; cercare solo in
`verimem/` e `tests/` dimentica `benchmark/`; il nome nudo dei metodi generici
pesca ogni dizionario.

## Le righe

| gruppo | test | verdetto | prova |
|---|---|---|---|
| `default_db_path` · `recall_report` e le altre 6 pubbliche | `tests/test_transcript_index_isolation.py` · `tests/test_il_tier_vuoto_non_e_nessun_risultato.py` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_transcript_index_isolation.py` → `7 passed in 7.25s` EXIT=0 · `test_il_tier_vuoto_non_e_nessun_risultato.py` → `5 passed in 6.93s` EXIT=0 |
| le 4 `_private` | via i chiamanti | **NON MISURATE** direttamente | — |

## ⚠️ Qui il righello è inutilizzabile, e va detto

Le pubbliche di questo file si chiamano `count`, `get`, `recall`, `store`,
`prune`. Cercarle col nome nudo in `tests/` dà:

```
get     635 file        store   665 file        recall  398 file
count   204 file        prune    12 file
default_db_path  2      recall_report  1
```

⇒ Il conteggio automatico diceva «0 pubbliche senza test» ed era **vero per
caso**: `get` e `store` pescano ogni dizionario e ogni store del repo. Sono i
**nomi specifici** (`default_db_path`, `recall_report`) ad aver portato al test
vero, `test_transcript_index_isolation.py`, che il conteggio non aveva
nominato.

📌 È la quarta forma della trappola del righello, e questo file è il caso più
estremo che ho incontrato: **il 100% delle pubbliche “coperte” con un metodo che
su cinque nomi su otto non misura niente.**
