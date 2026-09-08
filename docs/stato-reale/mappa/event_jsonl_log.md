# Mappa di `verimem/event_jsonl_log.py` — 7 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/event_jsonl_log.py:60` `_cartella_dati` | funzione: La data dir del prodotto, non la home. | `verimem/event_jsonl_log.py:44`; `verimem/event_jsonl_log.py:105` | nessuno | - | NON MISURATO | - |
| 2 | `verimem/event_jsonl_log.py:118` `_maybe_rotate` | funzione: Rotate ``EVENT_LOG_PATH`` to a single ``.1`` backup once it exceeds | `verimem/event_jsonl_log.py:217` | nessuno | - | NON MISURATO | - |
| 3 | `verimem/event_jsonl_log.py:139` `_avvisa_se_diverge` | funzione: Dichiara quando il log finisce lontano dallo store in uso. | `verimem/event_jsonl_log.py:56`; `verimem/event_jsonl_log.py:212` | nessuno | - | NON MISURATO | - |
| 4 | `verimem/event_jsonl_log.py:175` `_con_i_tag_ambient` | funzione: I tag che dicono DOVE e' successo, aggiunti solo se mancano. | `verimem/event_jsonl_log.py:220` | nessuno | - | NON MISURATO | - |
| 5 | `verimem/event_jsonl_log.py:202` `append_event` | funzione: Append one event line to ``EVENT_LOG_PATH``. | `verimem/event_jsonl_log.py:273`; `verimem/gateway.py:628`; `verimem/observability.py:304` (+1) | `tests/test_event_log_divergenza_dichiarata.py`; `tests/test_event_log_rotation.py`; `tests/test_gateway_flow_events.py` (+3) | - | NON MISURATO | - |
| 6 | `verimem/event_jsonl_log.py:235` `tail_events` | funzione: Read events newer than ``since_ts``, up to ``limit`` records. | `verimem/dashboard_routes/memory_map.py:41`; `verimem/dashboard_routes/memory_map.py:427`; `verimem/dashboard_routes/memory_map.py:456` (+1) | `tests/test_event_log_rotation.py` | - | NON MISURATO | - |
| 7 | `verimem/event_jsonl_log.py:265` `log_size_bytes` | funzione: Return current log size in bytes — 0 if file missing. | `verimem/event_jsonl_log.py:273` | `tests/test_event_log_rotation.py` | - | NON MISURATO | - |
