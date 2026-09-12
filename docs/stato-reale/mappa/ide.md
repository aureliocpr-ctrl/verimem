# `verimem/ide.py` — 1.271 righe, 22 funzioni (+1 annidata), 3 modelli Pydantic

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) ·
**08/09**.

## Il claim del README: **nessuno**

```
grep -nw "IDE\|ide" README.md      → 0 occorrenze
grep -nw "IDE" CHANGELOG.md        → 0 occorrenze
```

⇒ **1.271 righe di interfaccia web — editor, terminale, git — che nessun claim
pubblico promette.** Il file è **vivo**, non morto: `dashboard.py:39-40` importa
`ide_html`, `ide_js` e `router`, e `dashboard.py:129` fa
`app.include_router(ide_router)`. Codice montato e servito, ma fuori dalla
vetrina. È un dato per chi decide che cosa il prodotto dichiara di essere, non un
difetto.

⚠️ Il grep sul nome va **ancorato**: senza `-w`, «IDE» compare dentro
`cons**ide**red`, `prov**ide**`. La prima volta l'avevo cercato così e avevo
letto cinque righe che non c'entravano.

## Il perimetro della misura, scritto accanto al numero

```
8 file di test  (tests/test_ide.py, test_ide_file_write_cap_audit3.py,
                 test_ide_no_root_mutation.py, test_ide_path_injection.py,
                 tests/security/test_pentest_validation.py,
                 test_windows_no_console_popup.py, + 2 pescati per errore)
130 passed in 87,36 s                                          EXIT=0
verimem\ide.py   328 stmts   125 miss   100 branch   12 BrPart   61,0%
```

⚠️ **Il perimetro è costruito, non trovato**: il glob `tests/test_ide*.py` pesca
`test_ide**mpotency**_race` e `test_ide**ntifier**_only_as_subject` (con `*ide*`
erano 35 file su 6). **Un prefisso senza confine di parola non è un perimetro.**
I due file in più non falsano il numero — allargano solo il perimetro — ma li
dichiaro perché il numero sia riproducibile.

## La tabella

Verdetti dati con `coverage` per riga, attribuita alle funzioni con l'`ast`
(non a occhio): `attribuisci_coverage.py`.

| # | funzione (file:riga) | cosa promette | chiamata da (LETTO) | esercitata? | claim | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/ide.py:55` `_require_session_auth` | dipendenza FastAPI: sessione autenticata su ogni endpoint di lettura | `Depends(...)` in 7 decoratori (`:271, 307, 333, 350, 368, 619, 640`) | ESEGUITA | — | **FUNZIONA COME PROMESSO** | `test_ide.py:108` → `/api/ide/git/status` senza auth dà **401** |
| 2 | `verimem/ide.py:73` `_shell_enabled` | rispecchia `tools_extra._enabled('shell')`: opt-in via `HIPPO_ENABLE_SHELL` | `:406` (`ide_run`), `:481` (`ide_term`) | ESEGUITA | — | **FUNZIONA COME PROMESSO** | `test_ws_requires_shell_enabled` chiude 4403 senza la variabile |
| 3 | `verimem/ide.py:80` `_expected_token` | il bearer token da `HIPPO_AUTH_TOKEN`; senza, l'endpoint rifiuta di servire | `:91` (`_require_token`), `:505` (dentro `ide_term`) | ESEGUITA | — | **FUNZIONA COME PROMESSO** | 130 passed; `_require_token` alza 503 se vuoto |
| 4 | `verimem/ide.py:90` `_require_token` | 503 se il token non è configurato, 403 se non combacia (`compare_digest`) | `:409` (`ide_run`) | ESEGUITA | — | **FUNZIONA COME PROMESSO** | idem |
| 5 | `verimem/ide.py:99` `_shell_argv` | `shlex.split` + allowlist di binari al posto di `shell=True` (CVE-001) | `:413` (`ide_run`), `:544` (`ide_term`) | PARZIALE (1 riga: 114) | — | **FUNZIONA COME PROMESSO** | `TestCVE001ShellRun` in `test_pentest_validation.py`, 73 passed |
| 6 | `verimem/ide.py:137` `_check_ws_origin` | l'Origin del WebSocket deve stare in `HIPPO_IDE_ORIGIN_ALLOWLIST` | `:484` (`ide_term`) | ESEGUITA | — | **FUNZIONA COME PROMESSO** | 5 test la chiamano **direttamente** (no origin, origin estraneo, sottostringa, slash finale, default) |
| 7 | `verimem/ide.py:158` `workspace_root` | la radice del workspace servito | `:213, 274, 410, 539` | PARZIALE (168) | — | **FUNZIONA COME PROMESSO** | 130 passed |
| 8 | `verimem/ide.py:173` `_safe_path` | nessuna fuga con `..` fuori dalla radice (CVE-001) | `:309, 342, 352` (+ docstring :19) | PARZIALE (217-218) | — | **FUNZIONA COME PROMESSO** | `test_ide_path_injection.py` e `test_ide_no_root_mutation.py` verdi dentro i 130 |
| 9 | `verimem/ide.py:237` `_tree_node` | un nodo dell'albero dei file, con profondità massima | `:266` (ricorsiva), `:277` (`ide_tree`) | **PARZIALE — 11 righe** (247-265) | — | **NON MISURATO** sui rami scoperti | i rami di esclusione/simlink non sono percorsi dai 130 |
| 10 | `verimem/ide.py:272` `ide_tree` | `GET /api/ide/tree` | router (`dashboard.py:129`) | ESEGUITA | — | **FUNZIONA COME PROMESSO** | 130 passed |
| 11 | `verimem/ide.py:293` `_is_text` | vero se il file è testo (per decidere se aprirlo nell'editor) | `:314` (`ide_file_read`) | **PARZIALE — 8 statement scoperti su 10** (296-304) | — | **NON MISURATO** | nessuno degli 8 file la percorre |
| 12 | `verimem/ide.py:308` `ide_file_read` | `GET /api/ide/file` | router | ESEGUITA | — | **FUNZIONA COME PROMESSO** | 130 passed |
| 13 | `verimem/ide.py:334` `ide_file_write` | `PUT /api/ide/file` | router; importata anche da `test_ide_file_write_cap_audit3.py` | ESEGUITA | — | **FUNZIONA COME PROMESSO** | il file di test dedicato è dentro i 130 |
| 14 | `verimem/ide.py:351` `ide_file_delete` | `DELETE /api/ide/file` | router | ESEGUITA | — | **FUNZIONA COME PROMESSO** | 130 passed |
| 15 | `verimem/ide.py:369` `ide_file_new` | `POST /api/ide/file/new` | router | PARZIALE (374) | — | **FUNZIONA COME PROMESSO** | 130 passed |
| 16 | `verimem/ide.py:392` `ide_run` | `POST /api/ide/run`, gated da `_shell_enabled` + `_require_token` | router | PARZIALE (412, 428-429, 442) | — | **FUNZIONA COME PROMESSO** | `TestCVE001ShellRun` |
| 17 | `verimem/ide.py:464` `ide_term` | terminale WebSocket, tre porte: shell abilitata · Origin · token nel primo messaggio | router | **PARZIALE — 64 statement scoperti su 82** | — | **NON MISURATO nel percorso autenticato** (vedi sotto) | 485-487, 492-494, 497-499, **511-600** mai eseguite |
| 18 | `verimem/ide.py:565` `ide_term._pump` (annidata) | pompa stdout/stderr del processo verso il WebSocket | `ide_term` | **MAI ESEGUITA** (dentro 511-600) | — | **NON MISURATO** | — |
| 19 | `verimem/ide.py:606` `_git` | esegue un comando git nel workspace e torna `(rc, out, err)` | `:622` (`ide_git_status`), `:649` (`ide_git_diff`) | PARZIALE (612-613) | — | **NON MISURATO** | il corpo dei due chiamanti non è eseguito |
| 20 | `verimem/ide.py:620` `ide_git_status` | `GET /api/ide/git/status` | router | **PARZIALE — 12 statement su 16** (626-637) | — | **NON MISURATO** | `test_ide.py:108` prova solo il **401 senza auth**: la dipendenza rifiuta prima che il corpo giri |
| 21 | `verimem/ide.py:641` `ide_git_diff` | `GET /api/ide/git/diff` | router | **CORPO MAI ESEGUITO** (642-652) | — | **NON MISURATO** | nessun test chiama l'endpoint con auth |
| 22 | `verimem/ide.py:841` `ide_html` | la pagina HTML dell'IDE (una stringa) | `dashboard.py:39` | ESEGUITA | — | **FUNZIONA COME PROMESSO** | 130 passed |
| 23 | `verimem/ide.py:1270` `ide_js` | il JavaScript dell'IDE (una stringa) | `dashboard.py:39` | ESEGUITA | — | **FUNZIONA COME PROMESSO** | 130 passed |
| 24 | `verimem/ide.py:328` `FileWriteBody` | il corpo di `PUT /api/ide/file`: `path` + `content` | `ide_file_write` (:334); importato da `tests/test_ide_file_write_cap_audit3.py` | ESEGUITA | — | **FUNZIONA COME PROMESSO** | 130 passed |
| 25 | `verimem/ide.py:363` `FileCreateBody` | il corpo di `POST /api/ide/file/new` | `ide_file_new` (:369) | ESEGUITA | — | **FUNZIONA COME PROMESSO** | 130 passed |
| 26 | `verimem/ide.py:385` `RunBody` | il corpo di `POST /api/ide/run`: il comando e la cwd | `ide_run` (:392) | ESEGUITA | — | **FUNZIONA COME PROMESSO** | `TestCVE001ShellRun` |

## Il reperto: un docstring di test che promette una copertura che non c'è

`tests/security/test_pentest_validation.py`, classe `TestCVE002WebSocketTerm`,
docstring:

> «TestClient has no straightforward WS Origin spoofing, but we verify the helper
> directly. **We also drive a full roundtrip with a valid Origin + valid token to
> confirm the happy path doesn't accidentally regress.**»

**Quel roundtrip non c'è.** La classe ha 8 test, elencati uno per uno, e sono
**tutti di rifiuto**: `no_origin_header_rejected`, `foreign_origin_rejected`,
`origin_substring_attack`, `origin_trailing_slash_normalised`,
`origin_default_localhost_allowed`, `ws_requires_shell_enabled`,
`ws_rejects_no_auth_message`, `ws_rejects_wrong_token`. Nessuno completa
l'autenticazione.

E la `coverage` lo conferma dall'altro lato: **le righe 511-600** di `ide.py` —
il loop del terminale, cioè esecuzione del comando, pompaggio di stdout/stderr,
`kill`, limite di dimensione dell'output, rate limit — **non sono mai eseguite**.

⇒ **verdetto: NON MISURATO**, non «rotto». Il percorso felice del terminale
WebSocket può funzionare benissimo; nessuno lo sa. È la forma che ho in memoria
come **«una misura che non c'è si legge come perfetta»**, aggravata dal fatto che
il docstring dice che la misura c'è. 73 test passano, e uno che legge la classe
crede che il roundtrip sia coperto.

📌 **Non lo curo** (regola 2 del mandato: nessuna cura durante la mappa). Lo
segno come il candidato numero uno fra i miei, quando si passerà ai rossi.

## E i tre rami di rifiuto del WebSocket che nessuno percorre

- **485-487** — Origin non permesso *nell'endpoint*: i 5 test dell'Origin
  chiamano `_check_ws_origin` **direttamente** con un `_FakeWS`, e lo dichiarano.
  L'helper è provato; **il ramo dell'endpoint che lo usa no**.
- **492-494** — timeout dei 5 secondi sull'attesa del primo messaggio.
- **497-499** — primo messaggio con JSON malformato.

Tre rami di sicurezza **NON MISURATI**. Il resto della catena di auth
(`kind != auth` → 4401, token errato → 4403) è invece esercitato.

## Che cosa NON ho misurato, detto invece che indovinato

- **Il perimetro non è provato esaustivo**: 8 file trovati con due criteri
  (contenuto + nome ancorato). Un test che monta l'app senza nominare l'IDE
  potrebbe esercitare altre righe. Sette file montano `dashboard.app` senza
  citare `/api/ide` — **non li ho inclusi**, e lo scrivo invece di dichiarare
  chiuso il conto.
- **Le tre porte le ho lette, non rotte.** Per `prompt_injection.py` ho
  falsificato rompendo la riga; qui no, e quindi «le tre porte ci sono» resta una
  lettura del codice (per il WebSocket la terza è in linea a **:505-507**,
  `compare_digest` sul primo messaggio, non `_require_token`).
- La sicurezza dichiarata nel docstring del modulo (CVE-001/CVE-002) è
  **parzialmente** provata: gli helper sì, l'endpoint WebSocket in gran parte no.

---

### Nota sullo strumento che ha prodotto queste etichette

`attribuisci_coverage.py` ha sbagliato **tre volte** prima di dare i numeri di
questa tabella, e tutte e tre in modo che valeva la pena inseguire:

1. misurava l'ampiezza di una funzione come `fine - inizio`, cioè **righe
   fisiche**, incluse la riga del `def` e il docstring — che sono eseguite
   all'import, sempre. Così `syscall_bridge.py:373 engram_rate_stats`, il cui
   corpo è **un solo statement e quello statement è scoperto**, usciva
   «PARZIALE — 1 riga» invece di «corpo mai eseguito»: l'etichetta **più mite
   proprio nel caso peggiore**;
2. corretto a statement, la soglia era **80%**, e `ide_term` usciva «CORPO MAI
   ESEGUITO» mentre le sue prime righe girano eccome: etichetta **più dura del
   vero**, stavolta a sfavore del codice;
3. portata la soglia a 100%, il confronto era ancora `len(scoperti) >=
   len(statement)` — **due insiemi diversi confrontati per dimensione**: fra le
   righe scoperte ci sono le continuazioni, che non sono statement, e 99 ≥ 90
   dava di nuovo il verdetto sbagliato. Ora il confronto è per **inclusione**.

🔑 Una soglia arbitraria mente in **entrambi** i versi, e le due volte in cui il
mio righello ha sbagliato non ha sbagliato dalla stessa parte. È il motivo per
cui questa tabella porta **due numeri** (`N statement scoperti su M`) e non
un'etichetta sola: chi legge può rifare il conto.
