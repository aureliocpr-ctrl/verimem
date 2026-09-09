# Inventario delle funzioni — `verimem/tui.py`

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

**26 funzioni.**

| n | funzione | riga | che cos'è | nei test | prova |
|---|---|---|---|---|---|
| 1 | `_sync_to_thread` | 39 | helper privato | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 2 | `compose` | 54 | metodo di `ChatPane` | — *nome troppo comune: cercarlo non discrimina* | NON MISURATO oggi (macchina in uso) |
| 3 | `on_mount` | 60 | metodo di `ChatPane` | — *nome troppo comune: cercarlo non discrimina* | NON MISURATO oggi (macchina in uso) |
| 4 | `append_log` | 64 | metodo di `ChatPane` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 5 | `submit` | 69 | metodo di `ChatPane` | **31** occorrenze in `tests/` | NON MISURATO oggi (macchina in uso) |
| 6 | `compose` | 124 | metodo di `SkillsPane` | — *nome troppo comune: cercarlo non discrimina* | NON MISURATO oggi (macchina in uso) |
| 7 | `refresh_skills` | 129 | metodo di `SkillsPane` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 8 | `compose` | 144 | metodo di `EpisodesPane` | — *nome troppo comune: cercarlo non discrimina* | NON MISURATO oggi (macchina in uso) |
| 9 | `refresh_episodes` | 149 | metodo di `EpisodesPane` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 10 | `compose` | 170 | metodo di `SettingsPane` | — *nome troppo comune: cercarlo non discrimina* | NON MISURATO oggi (macchina in uso) |
| 11 | `on_button_pressed` | 225 | metodo di `SettingsPane` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 12 | `on_select_changed` | 235 | metodo di `SettingsPane` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 13 | `_apply_preset` | 239 | metodo di `SettingsPane` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 14 | `_unleash` | 261 | metodo di `SettingsPane` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 15 | `_lockdown` | 283 | metodo di `SettingsPane` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 16 | `_collect` | 308 | metodo di `SettingsPane` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 17 | `v` | 309 | metodo di `SettingsPane` | — *nome troppo comune: cercarlo non discrimina* | NON MISURATO oggi (macchina in uso) |
| 18 | `_save` | 322 | metodo di `SettingsPane` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 19 | `_test` | 357 | metodo di `SettingsPane` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 20 | `__init__` | 392 | metodo di `HippoTUI` | **454** occorrenze — *troppe per essere questa funzione: il nome è comune* | NON MISURATO oggi (macchina in uso) |
| 21 | `compose` | 399 | metodo di `HippoTUI` | — *nome troppo comune: cercarlo non discrimina* | NON MISURATO oggi (macchina in uso) |
| 22 | `on_mount` | 415 | metodo di `HippoTUI` | — *nome troppo comune: cercarlo non discrimina* | NON MISURATO oggi (macchina in uso) |
| 23 | `action_send` | 421 | metodo di `HippoTUI` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 24 | `action_refresh` | 429 | metodo di `HippoTUI` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 25 | `action_sleep` | 435 | metodo di `HippoTUI` | **nessuna occorrenza** in `tests/` | NON MISURATO oggi (macchina in uso) |
| 26 | `main` | 441 | funzione pubblica del modulo | — *nome troppo comune: cercarlo non discrimina* | NON MISURATO oggi (macchina in uso) |

**Nomi che non compaiono in nessun file di `tests/`: 15 su 26.**
Non è una misura di copertura — un helper privato può essere esercitato
attraverso il comando che lo chiama senza che il suo nome compaia mai. È
l'indizio più economico disponibile senza eseguire niente.
