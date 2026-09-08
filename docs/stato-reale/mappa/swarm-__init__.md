# `verimem/swarm/__init__.py` — 25 righe

## Cosa fa
il pacchetto: orchestratore costruito sopra le primitive native di Claude Code. Cycle #148, 18/05/2026.

## Chi lo chiama
Importato da **1 file**.

## È raggiungibile dal prodotto? **SÌ**
```
  verimem/cli.py:93   from .swarm.cli import swarm_app
  verimem/cli.py:94   app.add_typer(swarm_app, name="swarm")
  verimem/cli.py:5694 _AGENT_RUNTIME_GROUPS = {"swarm", "teams", "lab"}
```
Si arriva qui da `verimem swarm …`, e il gruppo vive sotto `verimem agent <cmd>`.

## ⚠️ Una dipendenza che vale la pena dichiarare
Questo gruppo **avvolge un programma esterno** — il binario `claude` e i file che
il suo supervisore scrive sotto `~/.claude/jobs/`. Non è codice orfano: è codice
il cui **consumatore c'è** e la cui **controparte è fuori dal pacchetto**. Se quel
formato cambia, qui non se ne accorge nessuno finché non si esegue.
