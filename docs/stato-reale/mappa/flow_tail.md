# Mappa di `verimem/flow_tail.py` — 4 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/flow_tail.py:29` `_c` | funzione: (nessun docstring) | `verimem/auto_dream_worker.py:232`; `verimem/auto_dream_worker.py:234`; `verimem/auto_dream_worker.py:236` (+36) | `tests/test_adjudication_log.py`; `tests/test_il_pannello_non_esplode_senza_il_db.py`; `tests/test_inventario_dei_tier.py` (+2) | - | NON MISURATO | - |
| 2 | `verimem/flow_tail.py:33` `render_flow_line` | funzione: One feed line for a flow event; ``None`` for anything else. | `verimem/flow_tail.py:9`; `verimem/flow_tail.py:100`; `verimem/flow_tail.py:111` | `tests/test_cli_flow_tail.py` | - | NON MISURATO | - |
| 3 | `verimem/flow_tail.py:74` `_read_flow` | funzione: New complete lines after byte offset ``after_pos`` → (records, new_pos). | `verimem/flow_tail.py:99`; `verimem/flow_tail.py:109` | nessuno | - | NON MISURATO | - |
| 4 | `verimem/flow_tail.py:92` `tail_flow` | funzione: Print the last ``replay`` flow events, then (if ``follow``) keep | `verimem/cli.py:168`; `verimem/cli.py:169` | nessuno | - | NON MISURATO | - |
