"""Genera `docs/stato-reale/COMANDI-SENZA-PROVA.md` unendo DUE misure.

  A. `scripts/porte_provate.py --json` — che livello di prova ha ogni comando
  B. `esiti_completi.json` — che cosa succede quando lo si ESEGUE

Il documento e' generato, non scritto a mano: si rifa' con due comandi, e se
un numero cambia cambia da solo. Chi legge deve poter rifare la misura.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

#: ⚠️ CORREZIONE 2026-09-12. Qui c'era un percorso ASSOLUTO della macchina di
#: chi l'ha scritto: lo script funzionava solo li', e in un worktree diverso
#: avrebbe misurato l'albero di un altro senza dirlo. L'albero e' quello in cui
#: questo file vive, e la riga sotto lo DICHIARA a chi legge l'uscita.
ALBERO = pathlib.Path(__file__).resolve().parent.parent

#: Gli esiti dell'esecuzione dei comandi, prodotti a parte: e' la misura che
#: costa (si lanciano i comandi uno per uno), non si rifa' a ogni generazione.
ESITI = ALBERO / "scripts" / "esiti_completi.json"

#: che cosa manca, per livello — la colonna che il Product Owner usa per la gravita'
_MANCA = {
    "①h AIUTO": "solo `--help`: prova che ESISTE, non che funzioni",
    "①b GRUPPO": "invocato sulla sotto-app: il montaggio su `app` non e' provato",
    "② FUNZIONE": "la funzione e' chiamata a mano, la porta no",
    "③ NOMINATO": "il nome compare nei test e nient'altro",
    "MAI TOCCATO": "nessun test lo nomina",
}
_ESITO = {
    "GIRA": "gira (EXIT=0)",
    "ERR-OK": "errore leggibile, corretto",
    "CHIEDE": "il parser chiede un argomento: **non e' stato eseguito**",
    "APPESO": "server/TUI: non misurabile cosi'",
    "CADE": "🔴 **TRACEBACK**",
}


def main() -> int:
    print(f"ALBERO MISURATO: {ALBERO}")
    # ⚠️ 2026-09-12: questo file NON e' nel repo, e prima lo script moriva con un
    #    `FileNotFoundError` nudo — cioe' non girava per nessuno, autore compreso,
    #    e nessuno se ne accorgeva perche' non lo rilanciava piu'. Ora la
    #    dipendenza PARLA e dice come si produce: un guasto detto costa un
    #    minuto, uno muto costa la prossima persona che ci prova.
    if not ESITI.is_file():
        print(f"manca {ESITI.relative_to(ALBERO)} — e' la misura che costa, non "
              "si rifa' da sola.\n"
              "  Si produce eseguendo i comandi uno per uno e scrivendo per "
              "ciascuno {\"comando\": ..., \"esito\": GIRA|ERR-OK|CHIEDE|APPESO|CADE}.\n"
              "  Finche' non c'e', questa tabella NON si puo' rigenerare: il "
              "documento in docs/stato-reale resta quello dell'ultima misura.",
              file=sys.stderr)
        return 2
    grezzo = subprocess.run([sys.executable, "scripts/porte_provate.py", "--json"],
                            cwd=ALBERO, capture_output=True, text=True,
                            encoding="utf-8", errors="replace",
                            env={**dict(__import__("os").environ), "PYTHONPATH": str(ALBERO)})
    dati = json.loads(grezzo.stdout)
    esiti = json.loads(ESITI.read_text(encoding="utf-8"))

    #: "episodes show ep-inesistente" → "episodes show"
    per_comando: dict[str, dict] = {}
    livelli = {n: liv for liv, nomi in dati["per_livello"].items() for n in nomi}
    for e in esiti:
        for nome in dati["senza_porta"]:
            if e["comando"] == nome or e["comando"].startswith(nome + " "):
                if nome not in per_comando or e["esito"] == "CADE":
                    per_comando[nome] = e

    righe = []
    for nome in dati["senza_porta"]:
        liv = livelli.get(nome, "?")
        e = per_comando.get(nome)
        eseguito = (f"`verimem {e['comando']}` → {_ESITO.get(e['esito'], e['esito'])}"
                    if e else "**non eseguito** (vedi sotto)")
        righe.append(f"| `verimem {nome}` | {liv} | {_MANCA.get(liv, '?')} | {eseguito} |")

    testo = f"""# I comandi della CLI senza una prova alla porta

**Albero** `20257636044a98ec0ba7fd2fea4bfc3ada0cfe1a` · **owner** ws1 (QA) ·
**09-10/09/2026** · chiesto dal coordinamento (punto 7) ·
**la gravita' la fissa il Product Owner**, questa lista non la ordina.

## Come si rifa' questa misura

```bash
PYTHONPATH=. python scripts/porte_provate.py            # la colonna «livello»
# e l'esecuzione, su uno store isolato:
HIPPO_DATA_DIR=<tmp> env -u ENGRAM_DATA_DIR -u VERIMEM_DATA_DIR verimem <comando>
```

Il righello conta **{dati['totale']}** comandi registrati dal parser Typer (tre file:
`verimem/cli.py`, `verimem/swarm/cli.py`, `verimem/teams/cli.py`, con i montaggi
`add_typer` risolti anche a due livelli). **{dati['alla_porta']}** hanno un test che li invoca
dalla porta con argomenti veri. Gli altri **{len(dati['senza_porta'])}** sono qui.

⚠️ **«Senza prova» non vuol dire «rotto».** Eseguiti uno per uno su uno store
isolato, **{sum(1 for e in esiti if e['esito'] == 'CADE')} su {len(esiti)} cade**. La colonna «eseguito» dice cosa succede
davvero: serve a non trattare un `--help` mancante come un difetto, e a non
trattare un difetto come un dettaglio.

## La lista

| comando | livello di prova | che cosa manca | eseguito da me |
|---|---|---|---|
{chr(10).join(righe)}

## Le quattro cose da sapere prima di ordinarli per gravita'

1. **①h AIUTO ({len(dati['per_livello'].get('①h AIUTO', []))})** — `tests/test_cli.py:83` li invoca **solo** con `--help`, e il
   suo docstring lo dichiara: «Each subcommand must have a --help that prints
   and exits 0», col commento «catches import errors». Prova che il comando
   esiste e che il modulo si importa. **Non e' un test finto: e' un test di
   un'altra cosa.**
2. **①b GRUPPO ({len(dati['per_livello'].get('①b GRUPPO', []))})** — `tests/swarm/test_cli.py` e `tests/test_teams_cli.py`
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
"""
    fuori = ALBERO / "docs" / "stato-reale" / "COMANDI-SENZA-PROVA.md"
    fuori.write_text(testo, encoding="utf-8")
    print(f"scritto {fuori.relative_to(ALBERO)} — {len(righe)} righe di tabella")
    return 0


if __name__ == "__main__":
    sys.exit(main())
