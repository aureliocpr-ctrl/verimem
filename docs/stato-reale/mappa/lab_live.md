# Mappa di `verimem/lab_live.py` — 5 righe, 168 righe di codice (lead, 09/09 12:22)

Letto per intero. Prova: pytest del lotto H sul tip `20257636` (`81 passed in 88.10s`, EXIT=0, con `tests/test_lab_live.py`). Chiamante letto: `run_live` ← `verimem/cli.py:193,196` (il comando `lab live`); `fetch_chat_since` e `parse_role` usate da `run_live` e dai test. Ciclo #146 (18/05): cruscotto Rich che polla `semantic.db` ogni N secondi e mostra i fatti-chat di un topic con il ruolo estratto dal prefisso `[ROLE @HH:MM:SS]`. Claim README: nessuna riga.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/lab_live.py:48` `parse_role` | il tag ROLE dal prefisso; «Unknown» altrimenti | `_build_table` (114) | `tests/test_lab_live.py` | - | FUNZIONA COME PROMESSO | pytest 81 passed |
| 2 | `verimem/lab_live.py:59` `fetch_chat_since` | i fatti vivi del topic con `created_at > since_ts` in ordine cronologico (strettamente maggiore: nessuna riga due volte fra un poll e l'altro) | `run_live` (147, 161) | `tests/test_lab_live.py` | - | FUNZIONA COME PROMESSO | pytest 81 passed |
| 3 | `verimem/lab_live.py:95` `_fmt_ts` | `HH:MM:SS` locale | `_build_table` (116) | via il test | - | NON MISURATO (presentazione; letto) | letto |
| 4 | `verimem/lab_live.py:99` `_build_table` | la tabella Rich degli ultimi 30 con il colore per ruolo e `[quarantined]` in rosso | `run_live` (154, 165) | nessuno | - | NON MISURATO (presentazione; letto) | letto |
| 5 | `verimem/lab_live.py:127` `run_live` | il ciclo Live con watermark `since_ts`, semina con tutta la storia, uscita pulita su Ctrl-C o `max_seconds` | `verimem/cli.py:196` | nessuno | - | NON MISURATO (ciclo interattivo non eseguito qui) | letto |

Reperti: (a) usa `sm._connect()` (privato) e legge `status`: i quarantenati si VEDONO, marcati in rosso — qui è la scelta giusta (un cruscotto di laboratorio deve mostrarli), ed è l'unico chiamante di stasera che etichetta lo status invece di nasconderlo o servirlo muto (confronto con T49); (b) `ROLE_COLORS` conosce quattro ruoli del ciclo 145: gli altri escono bianchi, dichiarato «extensible». Nessun P0.
