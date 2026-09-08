# Mappa di `verimem/_call_telemetry.py` — 1 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/_call_telemetry.py:22` `is_call_telemetry` | funzione: True when the episode's ``task_text`` is a cross-LLM call record, not a task. | `verimem/_call_telemetry.py:27`; `verimem/admission_cleanup.py:30`; `verimem/admission_cleanup.py:156` (+5) | `tests/test_audit_mutations_episodic.py`; `tests/test_episode_telemetry_cleanup.py`; `tests/test_episode_telemetry_gate.py` | - | NON MISURATO | - |
