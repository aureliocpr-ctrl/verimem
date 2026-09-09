# `verimem/dashboard_routes/__init__.py` — 54 righe

## Cosa fa
il pacchetto: espone `register_all(app, templates)`, che monta tutte le rotte.

## Chi lo chiama
Importato da **4 file**.

## È raggiungibile dal prodotto? **SÌ**
```
  verimem/dashboard.py:11  delega ogni rotta a dashboard_routes.register_all(app, templates)
  verimem/dashboard.py:19  dashboard_routes.auth.bootstrap_token() gira all'avvio
  verimem/dashboard.py:35-36  from .dashboard_routes import auth, layout
```
`dashboard.py` è il montatore: una rotta per file, registrate tutte insieme.
