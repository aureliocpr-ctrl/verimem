# Mappa di `verimem/gateway_backup.py` — 3 righe (bozza da confermare leggendo ed eseguendo)

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/gateway_backup.py:28` `_snapshot_db` | funzione: Snapshot consistente di un singolo SQLite via online backup API. | `verimem/gateway_backup.py:64` | nessuno | - | NON MISURATO | - |
| 2 | `verimem/gateway_backup.py:42` `backup_gateway` | funzione: Snapshot della directory gateway in ``dest``. Ritorna il manifest. | `verimem/cli.py:1106`; `verimem/cli.py:1108`; `verimem/gateway_backup.py:104` | `tests/test_gateway_backup.py` | - | NON MISURATO | - |
| 3 | `verimem/gateway_backup.py:82` `restore_gateway` | funzione: Ripristina uno snapshot in ``target`` (directory NUOVA o vuota — mai | `verimem/cli.py:1122`; `verimem/cli.py:1124`; `verimem/gateway_backup.py:104` | `tests/test_gateway_backup.py` | - | NON MISURATO | - |
