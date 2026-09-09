# `verimem/dashboard_routes/layout.py` — 115 righe

## Cosa fa
gli helper del layout HTML condiviso e l'accesso al singleton dell'agente.

## Chi lo chiama
Importato da **12 — il secondo più importato file**.

## È raggiungibile dal prodotto? **SÌ**
```
  verimem/dashboard.py:11  delega ogni rotta a dashboard_routes.register_all(app, templates)
  verimem/dashboard.py:19  dashboard_routes.auth.bootstrap_token() gira all'avvio
  verimem/dashboard.py:35-36  from .dashboard_routes import auth, layout
```
`dashboard.py` è il montatore: una rotta per file, registrate tutte insieme.
