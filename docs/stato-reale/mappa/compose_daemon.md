# Mappa di `verimem/compose_daemon.py` — 2 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/compose_daemon.py:38` `nightly_compose` | funzione: One guarded composition pass. Returns an honest report: | `verimem/compose_daemon.py:35`; `verimem/compose_daemon.py:71` | `tests/test_compose_daemon.py` | - | NON MISURATO | - |
| 2 | `verimem/compose_daemon.py:63` `main` | funzione: (nessun docstring) | `verimem/_hang_watchdog.py:18`; `verimem/_import_lock.py:7`; `verimem/_singleton_guard.py:34` (+95) | `tests/conftest.py`; `tests/perf/bench.py`; `tests/perf/bench_briefing_v3_robustness.py` (+111) | `README.md:50`; `README.md:66`; `README.md:378` | NON MISURATO | - |
