# `verimem/dashboard_routes/settings.py` — 529 righe

## Cosa fa
`/settings` e le API di provider, modello, permessi, preset e fallback.

## Chi lo chiama
Importato da **5 file**.

## È raggiungibile dal prodotto? **SÌ**
```
  verimem/dashboard.py:11  delega ogni rotta a dashboard_routes.register_all(app, templates)
  verimem/dashboard.py:19  dashboard_routes.auth.bootstrap_token() gira all'avvio
  verimem/dashboard.py:35-36  from .dashboard_routes import auth, layout
```
`dashboard.py` è il montatore: una rotta per file, registrate tutte insieme.
