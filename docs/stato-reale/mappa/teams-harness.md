# `verimem/teams/harness.py` — 188 righe

## Cosa fa
CollabHarness: misura la collaborazione reale, siede sopra InboxWatcher e classifica ciò che passa.

## Chi lo chiama
Importato da **3 file**.

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
