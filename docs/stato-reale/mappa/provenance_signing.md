# Mappa di `verimem/provenance_signing.py` — 7 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/provenance_signing.py:50` `provenance_key` | funzione: ``VERIMEM_PROVENANCE_KEY`` — None means signing is not configured. | `verimem/provenance_signing.py:43`; `verimem/provenance_signing.py:74` | nessuno | - | NON MISURATO | - |
| 2 | `verimem/provenance_signing.py:62` `signature_offenders` | funzione: The refs on ``fact`` that CLAIM a signature and fail to back it. | `verimem/provenance_signing.py:23`; `verimem/provenance_signing.py:43`; `verimem/semantic.py:3133` (+1) | nessuno | - | NON MISURATO | - |
| 3 | `verimem/provenance_signing.py:89` `_mac` | funzione: (nessun docstring) | `verimem/provenance_signing.py:98`; `verimem/provenance_signing.py:108` | nessuno | - | NON MISURATO | - |
| 4 | `verimem/provenance_signing.py:94` `sign_ref` | funzione: Attach the channel signature to a provenance ref. The proposition is | `verimem/provenance_signing.py:43` | `tests/test_provenance_signing.py`; `tests/test_verimem_provenance_wiring.py` | - | NON MISURATO | - |
| 5 | `verimem/provenance_signing.py:101` `verify_ref` | funzione: True iff ``ref`` carries a signature valid for this proposition+key. | `verimem/provenance_signing.py:44`; `verimem/provenance_signing.py:84`; `verimem/provenance_signing.py:125` | `tests/test_provenance_signing.py`; `tests/test_verimem_provenance_wiring.py` | - | NON MISURATO | - |
| 6 | `verimem/provenance_signing.py:111` `verify_fact_refs` | funzione: Audit one fact's refs: ``{signed, unsigned, invalid, exempt, ok}``. | `verimem/provenance_signing.py:44`; `verimem/provenance_signing.py:82`; `verimem/provenance_signing.py:147` | `tests/test_provenance_signing.py`; `tests/test_verimem_provenance_wiring.py` | - | NON MISURATO | - |
| 7 | `verimem/provenance_signing.py:133` `audit_store` | funzione: Walk the live store and report signature coverage — the deployment | `verimem/provenance_signing.py:43` | `tests/test_provenance_signing.py` | - | NON MISURATO | - |
