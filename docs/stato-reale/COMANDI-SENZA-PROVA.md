# I comandi della CLI senza una prova alla porta

**Albero** `20257636044a98ec0ba7fd2fea4bfc3ada0cfe1a` · **owner** ws1 Marie (QA) ·
**09-10/09/2026** · chiesto da @lead (post delle 23:34, punto 7) ·
**la gravita' la fissa @Iris (Product Owner)**, questa lista non la ordina.

## Come si rifa' questa misura

```bash
PYTHONPATH=. python scripts/porte_provate.py            # la colonna «livello»
# e l'esecuzione, su uno store isolato:
HIPPO_DATA_DIR=<tmp> env -u ENGRAM_DATA_DIR -u VERIMEM_DATA_DIR verimem <comando>
```

Il righello conta **98** comandi registrati dal parser Typer (tre file:
`verimem/cli.py`, `verimem/swarm/cli.py`, `verimem/teams/cli.py`, con i montaggi
`add_typer` risolti anche a due livelli). **57** hanno un test che li invoca
dalla porta con argomenti veri. Gli altri **41** sono qui.

⚠️ **«Senza prova» non vuol dire «rotto».** Eseguiti uno per uno su uno store
isolato, **1 su 35 cade**. La colonna «eseguito» dice cosa succede
davvero: serve a non trattare un `--help` mancante come un difetto, e a non
trattare un difetto come un dettaglio.

## La lista

| comando | livello di prova | che cosa manca | eseguito da me |
|---|---|---|---|
| `verimem backup-all` | ①h AIUTO | solo `--help`: prova che ESISTE, non che funzioni | `verimem backup-all` → gira (EXIT=0) |
| `verimem benchmark` | ①h AIUTO | solo `--help`: prova che ESISTE, non che funzioni | **non eseguito** (vedi sotto) |
| `verimem chat` | ①h AIUTO | solo `--help`: prova che ESISTE, non che funzioni | `verimem chat` → gira (EXIT=0) |
| `verimem code` | ①h AIUTO | solo `--help`: prova che ESISTE, non che funzioni | `verimem code` → gira (EXIT=0) |
| `verimem console` | ③ NOMINATO | il nome compare nei test e nient'altro | `verimem console` → server/TUI: non misurabile cosi' |
| `verimem episodes show` | ①h AIUTO | solo `--help`: prova che ESISTE, non che funzioni | `verimem episodes show ep-inesistente` → errore leggibile, corretto |
| `verimem facts archive-narration` | ③ NOMINATO | il nome compare nei test e nient'altro | `verimem facts archive-narration` → gira (EXIT=0) |
| `verimem facts backup` | ③ NOMINATO | il nome compare nei test e nient'altro | `verimem facts backup` → gira (EXIT=0) |
| `verimem facts capability` | MAI TOCCATO | nessun test lo nomina | `verimem facts capability` → gira (EXIT=0) |
| `verimem facts restore` | ③ NOMINATO | il nome compare nei test e nient'altro | **non eseguito** (vedi sotto) |
| `verimem facts safety` | MAI TOCCATO | nessun test lo nomina | `verimem facts safety` → gira (EXIT=0) |
| `verimem gateway backup` | MAI TOCCATO | nessun test lo nomina | `verimem gateway backup C:/Users/aurel/AppData/Local/Temp/claude/C--Users-aurel-Desktop-ProgettiAI/811d4eda-76dd-4222-b989-2aa7e22c1cb5/scratchpad/gwb2` → gira (EXIT=0) |
| `verimem gateway keys create` | ③ NOMINATO | il nome compare nei test e nient'altro | `verimem gateway keys create --tenant t1` → gira (EXIT=0) |
| `verimem gateway keys list` | MAI TOCCATO | nessun test lo nomina | `verimem gateway keys list` → gira (EXIT=0) |
| `verimem gateway keys revoke` | MAI TOCCATO | nessun test lo nomina | `verimem gateway keys revoke k-inesistente` → errore leggibile, corretto |
| `verimem gateway restore` | MAI TOCCATO | nessun test lo nomina | **non eseguito** (vedi sotto) |
| `verimem gateway serve` | ② FUNZIONE | la funzione e' chiamata a mano, la porta no | `verimem gateway serve` → server/TUI: non misurabile cosi' |
| `verimem health` | ①h AIUTO | solo `--help`: prova che ESISTE, non che funzioni | `verimem health` → gira (EXIT=0) |
| `verimem lab live` | ③ NOMINATO | il nome compare nei test e nient'altro | `verimem lab live` → server/TUI: non misurabile cosi' |
| `verimem metrics` | ①h AIUTO | solo `--help`: prova che ESISTE, non che funzioni | `verimem metrics` → gira (EXIT=0) |
| `verimem providers check` | MAI TOCCATO | nessun test lo nomina | `verimem providers check anthropic` → errore leggibile, corretto |
| `verimem providers models` | ①h AIUTO | solo `--help`: prova che ESISTE, non che funzioni | `verimem providers models` → il parser chiede un argomento: **non e' stato eseguito** |
| `verimem providers scan` | ①h AIUTO | solo `--help`: prova che ESISTE, non che funzioni | `verimem providers scan` → gira (EXIT=0) |
| `verimem reset` | ①h AIUTO | solo `--help`: prova che ESISTE, non che funzioni | `verimem reset` → errore leggibile, corretto |
| `verimem run` | ①h AIUTO | solo `--help`: prova che ESISTE, non che funzioni | `verimem run` → il parser chiede un argomento: **non e' stato eseguito** |
| `verimem skills dedup` | MAI TOCCATO | nessun test lo nomina | `verimem skills dedup` → gira (EXIT=0) |
| `verimem skills show` | ①h AIUTO | solo `--help`: prova che ESISTE, non che funzioni | `verimem skills show s-inesistente` → errore leggibile, corretto |
| `verimem sleep` | ①h AIUTO | solo `--help`: prova che ESISTE, non che funzioni | **non eseguito** (vedi sotto) |
| `verimem sleep-now` | ③ NOMINATO | il nome compare nei test e nient'altro | `verimem sleep-now` → gira (EXIT=0) |
| `verimem swarm clean` | ③ NOMINATO | il nome compare nei test e nient'altro | `verimem swarm clean r-inesistente` → gira (EXIT=0) |
| `verimem swarm kill` | ①b GRUPPO | invocato sulla sotto-app: il montaggio su `app` non e' provato | `verimem swarm kill r-inesistente` → gira (EXIT=0) |
| `verimem swarm logs` | ①b GRUPPO | invocato sulla sotto-app: il montaggio su `app` non e' provato | `verimem swarm logs abc12345` → errore leggibile, corretto |
| `verimem swarm respawn` | MAI TOCCATO | nessun test lo nomina | **non eseguito** (vedi sotto) |
| `verimem swarm run` | ①b GRUPPO | invocato sulla sotto-app: il montaggio su `app` non e' provato | **non eseguito** (vedi sotto) |
| `verimem swarm status` | ①b GRUPPO | invocato sulla sotto-app: il montaggio su `app` non e' provato | `verimem swarm status r-inesistente` → gira (EXIT=0) |
| `verimem teams charter` | ①b GRUPPO | invocato sulla sotto-app: il montaggio su `app` non e' provato | `verimem teams charter` → gira (EXIT=0) |
| `verimem teams collab-test` | ①b GRUPPO | invocato sulla sotto-app: il montaggio su `app` non e' provato | `verimem teams collab-test` → il parser chiede un argomento: **non e' stato eseguito** |
| `verimem teams send` | ①b GRUPPO | invocato sulla sotto-app: il montaggio su `app` non e' provato | `verimem teams send` → il parser chiede un argomento: **non e' stato eseguito** |
| `verimem teams watch` | ①b GRUPPO | invocato sulla sotto-app: il montaggio su `app` non e' provato | `verimem teams watch` → il parser chiede un argomento: **non e' stato eseguito** |
| `verimem tui` | ①h AIUTO | solo `--help`: prova che ESISTE, non che funzioni | `verimem tui` → server/TUI: non misurabile cosi' |
| `verimem wake` | ①h AIUTO | solo `--help`: prova che ESISTE, non che funzioni | **non eseguito** (vedi sotto) |

## Le quattro cose da sapere prima di ordinarli per gravita'

1. **①h AIUTO (15)** — `tests/test_cli.py:83` li invoca **solo** con `--help`, e il
   suo docstring lo dichiara: «Each subcommand must have a --help that prints
   and exits 0», col commento «catches import errors». Prova che il comando
   esiste e che il modulo si importa. **Non e' un test finto: e' un test di
   un'altra cosa.**
2. **①b GRUPPO (8)** — `tests/swarm/test_cli.py` e `tests/test_teams_cli.py`
   invocano `swarm_app` e `teams_app` **direttamente**: il montaggio
   (`app.add_typer(swarm_app, name="swarm")`, `cli.py:94`) non e' esercitato da
   nessuno. Togli quella riga e **otto test restano verdi mentre
   `verimem swarm *` e `verimem teams *` spariscono per l'utente.**
3. **CHIEDE ≠ provato** — cinque comandi rispondono `Usage: … [OPTIONS] X`: il
   parser ha fatto il suo mestiere e **il comando non e' mai partito**. Vanno
   rilanciati con l'argomento: e' cosi' che e' saltato fuori T55.
4. **APPESO ≠ rotto** — `console`, `tui`, `lab live`, `gateway serve` sono
   server e interfacce: restano in ascolto. Non hanno un verdetto **con questo
   metodo**, e va scritto cosi' invece di dargliene uno.

## I cinque che non ho eseguito, e perche'

| comando | perche' |
|---|---|
| `verimem benchmark` `wake` `sleep` | caricano i modelli: servono il claim `banco-torch` e la macchina libera |
| `verimem swarm run` `swarm respawn` | **lanciano istanze Claude vere** sulla macchina di Aurelio: non si provano qui |

Restano **NON MISURATI**. Un verdetto che non ho non lo scrivo.

## L'unico che cade: T55

`verimem introspect <topic>` lascia risalire `EncodeDelegateUnavailable` fino a
Typer — ~40 righe di traceback con i locals — mentre l'eccezione dice
testualmente «caller must degrade» e `warmup`, **dodici righe piu' su nello
stesso file**, gestisce lo stesso `encode` con
`except Exception as exc:  # noqa: BLE001 — report cleanly, no traceback`
(`cli.py:534`). RED alla porta: `tests/test_introspect_degrada_invece_di_esplodere.py`
(`xfail(strict=True)`). Senza il flag `HIPPO_ENCODE_DELEGATE_ONLY=1` il comando
gira, EXIT=0: **e' rotto per chi ha la configurazione con cui gira il server MCP**.
