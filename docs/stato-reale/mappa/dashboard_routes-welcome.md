# `verimem/dashboard_routes/welcome.py` — 88 righe

## Cosa fa
`/`, `/welcome`, `/metrics`: splash di onboarding, panoramica e pagina delle metriche grezze.

## Chi lo chiama
Importato da **3 file**.

## È raggiungibile dal prodotto? **SÌ**
```
  verimem/dashboard.py:11  delega ogni rotta a dashboard_routes.register_all(app, templates)
  verimem/dashboard.py:19  dashboard_routes.auth.bootstrap_token() gira all'avvio
  verimem/dashboard.py:35-36  from .dashboard_routes import auth, layout
```
`dashboard.py` è il montatore: una rotta per file, registrate tutte insieme.
