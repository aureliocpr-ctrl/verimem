# `verimem/dashboard_routes/auth.py` — 143 righe

## Cosa fa
autenticazione a token di sessione per le rotte che cambiano stato (CVE-009).

## Chi lo chiama
Importato da **13 — il più importato del gruppo file**.

## È raggiungibile dal prodotto? **SÌ**
```
  verimem/dashboard.py:11  delega ogni rotta a dashboard_routes.register_all(app, templates)
  verimem/dashboard.py:19  dashboard_routes.auth.bootstrap_token() gira all'avvio
  verimem/dashboard.py:35-36  from .dashboard_routes import auth, layout
```
`dashboard.py` è il montatore: una rotta per file, registrate tutte insieme.
