# Mappa di `verimem/daemon_runner.py` — 7 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/daemon_runner.py:46` `DaemonSpec` | classe: (nessun docstring) | `verimem/daemon_runner.py:13`; `verimem/daemon_runner.py:109`; `verimem/daemon_runner.py:173` (+3) | `tests/test_daemon_runner.py` | - | NON MISURATO | - |
| 2 | `verimem/daemon_runner.py:54` `DaemonSpec.state_filename` | funzione: (nessun docstring) | `verimem/daemon_runner.py:137` | nessuno | - | NON MISURATO | - |
| 3 | `verimem/daemon_runner.py:64` `_is_enabled` | funzione: (nessun docstring) | `verimem/daemon_runner.py:134` | nessuno | - | NON MISURATO | - |
| 4 | `verimem/daemon_runner.py:78` `_load_last_ts` | funzione: Read the last-spawn timestamp; ``None`` on missing / corrupt / future. | `verimem/daemon_runner.py:138` | nessuno | - | NON MISURATO | - |
| 5 | `verimem/daemon_runner.py:98` `_save_last_ts` | funzione: (nessun docstring) | `verimem/daemon_runner.py:157`; `verimem/daemon_spawn.py:19` | nessuno | - | NON MISURATO | - |
| 6 | `verimem/daemon_runner.py:108` `maybe_spawn_daemon` | funzione: Decide + (optionally) spawn one daemon. Never raises. | `verimem/daemon_runner.py:207`; `verimem/daemon_runner.py:212`; `verimem/daemon_runner.py:223` (+2) | `tests/test_daemon_runner.py` | - | NON MISURATO | - |
| 7 | `verimem/daemon_runner.py:198` `maybe_spawn_all_default_daemons` | funzione: Fan-out wrapper: try each ``DEFAULT_DAEMONS`` entry. | `verimem/daemon_runner.py:14`; `verimem/daemon_runner.py:222` | `tests/test_daemon_runner.py`; `tests/test_session_start_hook_daemons.py` | - | NON MISURATO | - |
