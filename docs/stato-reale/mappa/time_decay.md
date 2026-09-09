# mappa — `verimem/time_decay.py`

**owner ws6 Aldo** · base `20257636` · 2026-09-09 12:37

**163 righe · 3 funzioni · 0 classi** (`ast`). **3 pubbliche, 0 private.**
Metodo e limiti: quelli di `semantic.md`, con le quattro trappole del righello già pagate.

## Le righe

| gruppo | test | verdetto | prova |
|---|---|---|---|
| le **3 pubbliche** (zero private) | `tests/test_il_modulo_del_tempo_conosce_la_scadenza.py` | **FUNZIONA COME PROMESSO**, limitato | `pytest -q tests/test_il_modulo_del_tempo_conosce_la_scadenza.py` → `6 passed in 7.36s` EXIT=0 |

**Zero pubbliche senza test.** È il file più piccolo della mia parte (163 righe)
ed è quello che decide quando un fatto è vecchio: sta sotto l'invariante del mio
ruolo, «nulla scaduto si serve senza dirlo».

## Inventario completo — ogni funzione per nome

**3 funzioni**, dall'albero sintattico. La colonna «test» dice
quanti file di `tests/` **nominano** quel nome e il primo di essi: è
rintracciabilità, **non** un verdetto — i verdetti con la prova eseguita
stanno nei blocchi qui sopra. I nomi generici sono marcati come tali,
perché il nome nudo di `get` o `store` pesca ogni dizionario del repo.

| riga | funzione | vis | cosa promette | test che la nominano |
|---|---|---|---|---|
| 24 | `decay_confidence` | **pub** | Return decayed confidence based on age. | 1 — `test_time_decay.py` |
| 41 | `assess_freshness` | **pub** | Return {status, decayed_confidence, age_days, original_con | 3 — `test_il_modulo_del_tempo_conosce_la_scadenza.py` |
| 106 | `find_stale_facts` | **pub** | List facts older than threshold_days OR past their `valid_ | 3 — `test_il_modulo_del_tempo_conosce_la_scadenza.py` |
