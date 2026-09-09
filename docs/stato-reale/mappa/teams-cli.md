# `verimem/teams/cli.py` — 463 righe

## Cosa fa
la subapp Typer `engram teams`: `watch <team>` fa il tail dei messaggi, `send` permette a un operatore umano di iniettarne.

## Chi lo chiama
Importato da **3 file — ed è il punto d'ingresso vero**.

## È raggiungibile dal prodotto? **SÌ**
Il gruppo `teams` è registrato nella CLI:
```
  verimem/cli.py:99    from .teams.cli import teams_app
  verimem/cli.py:100   app.add_typer(teams_app, name="teams")
  verimem/cli.py:5694  _AGENT_RUNTIME_GROUPS = {"swarm", "teams", "lab"}
```
⇒ Si arriva qui da `verimem teams …`, e dal 2026 il gruppo vive sotto
`verimem agent <cmd>` (riga 5689). **Non è codice orfano**: a differenza di
`hooks/`, il punto d'ingresso è dichiarato e registrato.
