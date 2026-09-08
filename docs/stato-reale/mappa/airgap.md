# Mappa di `verimem/airgap.py` — 7 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/airgap.py:50` `_is_local_base_url` | funzione: True iff ``url`` targets a loopback/local endpoint (vLLM / LM Studio / | `verimem/airgap.py:102`; `verimem/airgap.py:205` | `tests/test_airgap.py` | - | NON MISURATO | - |
| 2 | `verimem/airgap.py:88` `_llm_locality` | funzione: Return (is_local, reason) for the configured LLM provider. | `verimem/airgap.py:127` | nessuno | - | NON MISURATO | - |
| 3 | `verimem/airgap.py:109` `airgap_status` | funzione: Structured verdict on whether the current config can run air-gapped. | `verimem/airgap.py:14`; `verimem/airgap.py:219`; `verimem/cli.py:777` (+1) | `tests/test_airgap.py`; `tests/test_airgap_no_egress.py`; `tests/test_engram_mode.py` | - | NON MISURATO | - |
| 4 | `verimem/airgap.py:156` `_default_exercise` | funzione: Exercise the core write+read path with a mock LLM so a clean, offline | `verimem/airgap.py:210` | nessuno | - | NON MISURATO | - |
| 5 | `verimem/airgap.py:171` `probe_live_egress` | funzione: LIVE no-egress proof: run ``exercise`` (default: a real write+search) while | `verimem/airgap.py:18`; `verimem/airgap.py:219`; `verimem/cli.py:761` (+1) | `tests/test_airgap_live_probe.py` | - | NON MISURATO | - |
| 6 | `verimem/airgap.py:190` `probe_live_egress._host_of` | funzione: (nessun docstring) | `verimem/airgap.py:200` | nessuno | - | NON MISURATO | - |
| 7 | `verimem/airgap.py:196` `probe_live_egress._audit` | funzione: (nessun docstring) | `verimem/airgap.py:208`; `verimem/gateway.py:886`; `verimem/gateway.py:888` (+457) | `tests/security/test_pentest_validation.py`; `tests/test_audit_log_rotation.py`; `tests/test_dashboard_bus_coverage.py` (+6) | - | NON MISURATO | - |
