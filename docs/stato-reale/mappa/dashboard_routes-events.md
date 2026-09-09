# `verimem/dashboard_routes/events.py` — 142 righe

## Cosa fa
`/events` + `/api/events/recent` + `/api/events/stream` (Server-Sent Events).

## Chi lo chiama
Importato da **3 file**.

## È raggiungibile dal prodotto? **SÌ**
```
  verimem/dashboard.py:11  delega ogni rotta a dashboard_routes.register_all(app, templates)
  verimem/dashboard.py:19  dashboard_routes.auth.bootstrap_token() gira all'avvio
  verimem/dashboard.py:35-36  from .dashboard_routes import auth, layout
```
`dashboard.py` è il montatore: una rotta per file, registrate tutte insieme.
