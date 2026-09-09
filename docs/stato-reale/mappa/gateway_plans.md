# Mappa di `verimem/gateway_plans.py` — 6 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/gateway_plans.py:27` `Plan` | classe: A subscription tier. ``None`` limits mean unlimited. | `verimem/chain_render.py:23`; `verimem/chain_render.py:34`; `verimem/gateway_plans.py:47` (+11) | `tests/security/test_saas_surface_break.py`; `tests/test_chain_render.py`; `tests/test_collapse_autohook.py` (+5) | - | NON MISURATO | - |
| 2 | `verimem/gateway_plans.py:36` `Plan.allows` | funzione: (nessun docstring) | `verimem/dashboard_routes/layout.py:38`; `verimem/gateway.py:743`; `verimem/mcp_server.py:1507` (+1) | `tests/test_fact_chain.py`; `tests/test_gateway_plans.py`; `tests/test_gateway_tenant_reserved.py` (+2) | - | NON MISURATO | - |
| 3 | `verimem/gateway_plans.py:39` `Plan.within_facts` | funzione: (nessun docstring) | `verimem/gateway.py:578`; `verimem/gateway_plans.py:86` | `tests/test_gateway_plans.py`; `tests/test_gateway_quota_toctou.py` | - | NON MISURATO | - |
| 4 | `verimem/gateway_plans.py:67` `get_plan` | funzione: Resolve a plan name to its Plan; unknown/empty → the ``free`` default (fail | `verimem/cli.py:1067`; `verimem/cli.py:1068`; `verimem/gateway.py:296` (+7) | `tests/test_gateway_plans.py`; `tests/test_gateway_quota_toctou.py` | - | NON MISURATO | - |
| 5 | `verimem/gateway_plans.py:73` `is_plan` | funzione: (nessun docstring) | `verimem/gateway_plans.py:93` | `tests/test_gateway_plans.py` | - | NON MISURATO | - |
| 6 | `verimem/gateway_plans.py:77` `quota_status` | funzione: A tenant-facing snapshot of headroom — what a dashboard/402 shows. | `verimem/gateway.py:965`; `verimem/gateway.py:967`; `verimem/gateway.py:1125` (+2) | `tests/test_gateway_plans.py` | - | NON MISURATO | - |
