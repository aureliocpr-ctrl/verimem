# Mappa di `verimem/self_heal.py` — 5 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/self_heal.py:46` `_enabled` | funzione: (nessun docstring) | `verimem/ide.py:74`; `verimem/self_heal.py:62`; `verimem/self_heal.py:107` (+10) | `tests/test_desktop_screenshot_gate_scan68.py`; `tests/test_tools_extra_full.py` | - | NON MISURATO | - |
| 2 | `verimem/self_heal.py:50` `_run_self_heal` | funzione: Heal up to ``limit`` stale rows. Returns the heal count; never raises. | `verimem/self_heal.py:114`; `verimem/self_heal.py:121` | `tests/test_il_build_dell_agent_non_tiene_il_lock.py`; `tests/test_self_heal_startup.py` | - | NON MISURATO | - |
| 3 | `verimem/self_heal.py:79` `_wait_daemon_warm` | funzione: Best-effort wait until the shared encode daemon serves the active model. | `verimem/self_heal.py:113`; `verimem/self_heal.py:121` | `tests/test_self_heal_startup.py` | - | NON MISURATO | - |
| 4 | `verimem/self_heal.py:99` `start_self_heal` | funzione: Fire the self-heal pass on a background daemon thread. Returns the | `verimem/mcp_server.py:15802`; `verimem/mcp_server.py:15803`; `verimem/self_heal.py:121` | `tests/test_self_heal_startup.py` | - | NON MISURATO | - |
| 5 | `verimem/self_heal.py:110` `start_self_heal._run` | funzione: (nessun docstring) | `verimem/ann_cache.py:74`; `verimem/flow_events.py:311`; `verimem/preload.py:354` (+2) | `tests/test_airgap_live_probe.py`; `tests/test_bench_compare.py`; `tests/test_doctor_reports_moat_coverage.py` (+11) | - | NON MISURATO | - |
