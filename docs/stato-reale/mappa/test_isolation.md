# Mappa di `verimem/test_isolation.py` — 2 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/test_isolation.py:30` `sotto_test` | funzione: Vero quando il processo gira dentro pytest. | `verimem/test_isolation.py:27` | nessuno | - | NON MISURATO | - |
| 2 | `verimem/test_isolation.py:40` `assert_store_isolato` | funzione: Solleva se ``percorso`` non sta dentro ``tmp_root``. | `verimem/test_isolation.py:27` | `tests/conftest.py`; `tests/test_lo_store_di_produzione_e_fuori_portata_sotto_pytest.py` | - | NON MISURATO | - |
