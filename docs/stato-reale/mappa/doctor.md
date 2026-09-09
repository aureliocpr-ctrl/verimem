# Inventario delle funzioni — `verimem/doctor.py`

> ws7 «Iris». Accompagna [CLI-claims.md](CLI-claims.md), che giudica la
> superficie che l'utente tocca (comandi, opzioni, diagnosi). Questo file è
> un **inventario**, non un giudizio: elenca ogni funzione e dice se un test
> la nomina.

⚠️ **Criterio di conteggio, dichiarato**: una riga che combacia con
`^\s*def ` o `^\s*async def `, a qualunque indentazione — le funzioni
annidate ci sono, le lambda no.

⚠️ **La colonna «prova»**: `NON MISURATO oggi (macchina in uso)` — Aurelio,
09/09 12:37, *«sto pure giocando non mi saturate tutto»*. Nessun pytest,
nessuna CLI, nessun modello: questo file è scritto **leggendo**.

⚠️ **La colonna «nei test» è un indizio, non una copertura**: conta le
occorrenze del nome nei file `tests/`. Per un nome raro è informativa; per
uno comune (`main`, `run`, `add`) non discrimina, e lì la riga lo dice
invece di esibire un numero che sembrerebbe una misura.

**14 funzioni.**

| n | funzione | riga | che cos'è | nei test | prova |
|---|---|---|---|---|---|
| 1 | `_ttl_undo` | 43 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 2 | `_misura` | 103 | helper privato | **2** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 3 | `_non_e_un_database` | 110 | helper privato | **6** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 4 | `_non_ho_potuto_guardare` | 146 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 5 | `_stores_illeggibili` | 200 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 6 | `_stores_dichiarati` | 228 | helper privato | **7** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 7 | `_residui_dei_test` | 290 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 8 | `_provenienza_del_codice` | 307 | helper privato | **1** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 9 | `_versione_di_mcp` | 373 | helper privato | **5** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 10 | `run_doctor` | 386 | funzione pubblica del modulo | **53** occorrenze — *troppe per essere questa funzione: il nome è comune* | NON MISURATO oggi (macchina in uso) |
| 11 | `add` | 394 | funzione annidata | — *nome troppo comune: cercarlo non discrimina* | NON MISURATO oggi (macchina in uso) |
| 12 | `_conta_ritiri` | 937 | funzione annidata | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 13 | `_vale` | 1204 | funzione annidata | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 14 | `worst_status` | 1475 | funzione pubblica del modulo | **4** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |

**Nomi che non compaiono in nessun file di `tests/`: 6 su 14.**
Non è una misura di copertura — un helper privato può essere esercitato
attraverso il comando che lo chiama senza che il suo nome compaia mai. È
l'indizio più economico disponibile senza eseguire niente.
