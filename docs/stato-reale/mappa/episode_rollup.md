# Mappa di `verimem/episode_rollup.py` — 2 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/episode_rollup.py:25` `_signature` | funzione: (nessun docstring) | `verimem/anomaly_detection.py:57`; `verimem/correction_velocity.py:12`; `verimem/correction_velocity.py:23` (+10) | `tests/test_correction_velocity.py`; `tests/test_emerging_briefing.py` | - | NON MISURATO | - |
| 2 | `verimem/episode_rollup.py:32` `rollup_old_episodes` | funzione: Bucket old episodes by signature, produce 1 rollup per cluster. | `verimem/episode_rollup.py:104`; `verimem/mcp_server.py:10383`; `verimem/mcp_server.py:10389` | `tests/test_episode_rollup.py` | - | NON MISURATO | - |
