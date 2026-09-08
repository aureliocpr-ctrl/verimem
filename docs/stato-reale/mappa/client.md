# Mappa — `verimem/client.py`

*ws3 Galileo. Parte assegnata: 20 file, 15.064 righe misurate sul mio albero
(l'indice dice 15.084: differenza di 20 righe, dichiarata, da riconciliare col
lead). Questo file: **4.339 righe, 80 fra funzioni e classi** (`ast`, escluse
le dunder). Ordine del mandato: prima ciò che sta dietro un claim del README.*

**Metodo, e cosa vale una riga di questa tabella.** La colonna «prova» porta il
comando eseguito e il suo esito; senza, il verdetto è `NON MISURATO` e si
scrive così. I chiamanti sono **letti**, non contati: `grep -w add` su
`verimem/` dà 200+ righe che sono `set.add`, `list.add`, `index.add` — la
regola del mandato («grep serve a trovare, non a contare») qui morde subito.

**Contatore**: 14 righe misurate su 80 · 7 claim del README collegati · i
chiamanti delle tre porte per `add` e `search` **letti con la riga** (20:59) ·
2 ticket aperti (T-MAP-1, T-MAP-2) · 2 righe dove **ho sbagliato io la
chiamata** e l'ho scritto (11, 12).

| # | funzione (file:riga) | cosa promette | chiamata da (letto) | test che la esercita | claim README (riga) | verdetto | prova (comando e esito) |
|---|---|---|---|---|---|---|---|
| 1 | `Memory.__init__` (client.py:556) | apre lo store: senza argomento «the library, the CLI and the MCP server all open the SAME store»; con un path, quello | `cli.py`, `mcp_server.py`, `gateway.py` (da leggere uno per uno: riga nella prossima passata) | `tests/test_moat_works_out_of_the_box.py` (8 passed) | README:428-429 | **FUNZIONA COME PROMESSO, con un avviso fuorviante** | `python prova_sdk.py` 08/09 20:31: `Memory(<tmp>/mappa.db)` scrive in `<tmp>/mappa.db` (106 KB creato) e **non** nello store di casa — verificato dopo: 0 righe con quei due id e 0 col topic `mappa/prova`, mtime del db di casa fermo alle 19:40. ⚠️ Ma il warning stampato dice «*using C:\Users\aurel\.engram (HIPPO_DATA_DIR wins)*» mentre il path esplicito vince davvero: il messaggio nomina un vincitore che non è quello dei fatti → **ticket T-MAP-1, owner Galileo** |
| 2 | `Memory.add` (client.py:613) | «Store `text` AFTER the anti-confab gate»; ritorna `{stored, id?, status, grounding_score, warnings, advice}` | **LETTI, con la riga**: CLI `cli.py:1373` in `remember_cmd` (1308) e `cli.py:1872` in `correct_cmd` (1822) · HTTP `gateway.py:1151` dentro `@app.post("/v1/memories")` (1047) · MCP `mcp_server.py:7875` dentro `_call_tool_impl` (7806). ⚠️ E **due punti del server MCP dichiarano di NON passare di qui**: `mcp_server.py:843` («costruisce il Fact dentro il server, non passa da `client.add()`») e `13648` («chiama `store()` senza passare da `Memory.add()`, dove viveva…») — due vie di scrittura che saltano questa funzione, da mappare quando tocca a Giano | `tests/test_moat_works_out_of_the_box.py`, `tests/test_all_write_channels_judge_a_source.py`, `tests/test_adjudication_receipt.py` | README:441-442 (quickstart: entailed → admitted, confab → QUARANTINED) | **FUNZIONA COME PROMESSO** | `python prova_sdk.py` 08/09 20:31, store temporaneo: `add("Analytics runs on Postgres.", source=…)` → `status='model_claim'`, `grounding_score=99.916`, `layers=[]`, `stored=True`; `add("Analytics runs on MongoDB.", source=…)` → `status='quarantined'`, `grounding_score=0.613`, `quarantined_by='moat'`, `layers=['L4-grounding']`. E `pytest tests/test_moat_works_out_of_the_box.py` → **8 passed, EXIT=0** |
| 3 | `Memory.search` (client.py:1217) | «Recall the top-k facts for `query`, each with its provenance — `status` + write-time `grounding_score`» | **LETTI, con la riga**: CLI `cli.py:1649` (con `as_of`, `deep`) · HTTP `gateway.py:621` (`k=4`) e `gateway.py:1185` (per tenant) · `active_probe.py:59`. ⚠️ Il server MCP **non** chiama questa: legge da `semantic.recall` direttamente (`mcp_server.py:432`, `sem.recall(query, k=3)`) — porta diversa, funzione diversa, e i due `k` di default non coincidono (SDK 5, gateway 4, MCP 3) | `tests/test_moat_works_out_of_the_box.py` | README:428-448 (l'SDK del quickstart) | **FUNZIONA COME PROMESSO (parziale: k=5 su un corpus di 2)** | stessa esecuzione: `search("Analytics", k=5)` → 1 hit, `flow.recall best=0.8424 n=1 tagliati=0`; il quarantinato **non** è servito, come promesso |
| 4 | `Memory.recall` (alias di `search`, client.py:1217) | i documenti e le porte la nominano accanto a `search`, come se fossero due letture | — (è lo stesso oggetto: chi chiama `recall` chiama `search`) | gli stessi di `search` | — | **FUNZIONA, ma è UN SOLO metodo con due nomi** | stessa esecuzione, riga finale: `Memory.recall is Memory.search` → **True**, e `[a for a in dir(Memory) if 'recall' in a]` → `['recall']`. ⚠️ **Prima avevo scritto in questa riga «NON ESISTE COME METODO SEPARATO»: sbagliato, e l'ho corretto prima di pubblicare** — l'output della prova diceva già «True» e l'ho letto male. Vale come reperto per chi legge la mappa: due nomi per una funzione fanno credere a due comportamenti |

| 5 | `Memory.index_document` (client.py, delega a `documents`) | «Documents indexed through … `Memory.index_document(path)`» | CLI `verimem index`, MCP `verimem_document_*` (da leggere) | (da leggere) | README:273-275 | **FUNZIONA COME PROMESSO** | `python prova_docs_ask.py` 08/09 21:08: un .txt di 3 righe → `{'doc_id': '1cf022a5cf1143e9', 'version': 1, 'is_new': True, 'chunks_indexed': 1, 'chunks_flagged': 0}`, log `flow.document kind=index` |
| 6 | `Memory.search_documents` (client.py:1873) | «Cerca nei documenti indicizzati. Gemello di `verimem search-docs`»; il README promette «passages with file + offset citations» | CLI `cli.py:875` (`DocumentIndex().search`) | (da leggere) | README:275, 504 | **FUNZIONA COME PROMESSO** | stessa esecuzione: 3 passaggi, campi `['doc_id','end','flagged','indexed_by','query_terms','query_terms_matched','score','source_id','start','text']`, con `uri=file://…/contratto.txt`, `start=0`, `end=167` — file e offset ci sono |
| 7 | `Memory.ask` (client.py:2048) | router di intento: COUNT → scansione dell'intero corpus, LIST_ALL → «returns the whole matching set», FIND → recall ordinario | (da leggere) | (da leggere) | — (docstring, non README) | 🔴 **NON COME PROMESSO su LIST_ALL** → ticket **T-MAP-2** | stessa esecuzione: `ask("quante volte ho parlato del capannone?")` → `intent=count`, `count=2` ✅; `ask("dove si trova il capannone 12?")` → `intent=find`, 2 risultati ✅; `ask("elenca tutti i capannoni")` → `intent=list_all`, **0 risultati** su un corpus che ne contiene 2. Causa ISOLATA con una seconda prova (`prova_listall.py`, 21:09), una variabile per volta: `elenca tutti i capannoni` → termini `capannoni` → **0**; `elenca tutti i capannone` (singolare) → **2**; `list all capannone` → **2**; `elenca tutto sul capannone` → termini `tutto sul capannone` → **0**. ⇒ LIST_ALL fa un confronto **letterale** sui termini: il plurale non trova il singolare, e le parole di riempimento entrano nei termini. Non è l'enumerazione a essere rotta, è il match |
| 8 | `Memory.answer` (client.py:1877) | risposta verificata; il README dichiara che senza `llm` solleva | (da leggere) | (da leggere) | README:705 | **FUNZIONA COME DICHIARATO (il limite è scritto)** | stessa esecuzione: `answer("…")` senza `llm` → `TypeError: Memory.answer() missing 1 required keyword-only argument: 'llm'`, esattamente ciò che il README dice |

| 9 | `Memory.count` (client.py:1742) | «Set-size, NOT top-k — the honest primitive for aggregation queries»: scandisce lo store invece di fare top-k | `ask` (COUNT) | (da leggere) | — (docstring) | **FUNZIONA COME PROMESSO**, e il numero dice una cosa che va letta bene | `prova_lettura.py` 08/09 21:37: due scritture (una ammessa, una quarantinata) → `count()` = **1**. Cioè conta ciò che il prodotto **serve**, non le righe su disco: coerente col resto (il quarantinato non è servito), ma chi legge «count» pensando a «quante righe ho scritto» prende un altro numero |
| 10 | `Memory.explain` (client.py:2230) | il dossier di provenienza di una risposta | `trust_report` (è lo stesso) | (da leggere) | README (provenienza) | **FUNZIONA COME PROMESSO** | stessa esecuzione: `explain("canone del capannone 12")` → dict con `['abstained','as_of','causal_answerable','deep','evidence_types','facts','floor_applied_by','generated_at','grounding_checked','k','min_relevance','n_disputed']`, log `flow.recall kind=explain n=1 abstained=False` |
| 11 | `Memory.trust_report` (client.py:2370) | «Il dossier di provenienza — lo STESSO di `explain`». Il docstring dice che esiste **perché il nome non tornava** a chi usava il prodotto | — (alias con altro nome) | (da leggere) | — | **FUNZIONA (è `explain` con un altro nome)** | stessa esecuzione: chiamandola senza argomenti → `TypeError: Memory.trust_report() missing 1 required positional argument: 'query'`. ⚠️ **Errore MIO di chiamata, non del prodotto**: la firma è `trust_report(query, k=5)`. Lo scrivo perché la mappa deve distinguere «il prodotto è rotto» da «l'ho chiamato male», e questa riga è il secondo caso |
| 12 | `esito_del_moat` (client.py:446, funzione di modulo) | «Che cosa ha fatto il moat, DERIVATO da ciò che il gate ha già detto» — legge i layer, non riesegue la logica | (da leggere) | (da leggere) | — | **NON MISURATO** | ho provato a chiamarla con la sola ricevuta → `TypeError: esito_del_moat() missing 1 required positional argument: 'warnings'`. Firma vera: `esito_del_moat(gate, warnings, *, source)`. **Errore mio**: la misura vera va rifatta passando i tre argomenti, ed è in coda |
| 13 | `Memory.audit_log` / `audit_verify` / `audit_head` (2627, 2643, 2653) | «The opt-in per-write audit trail (`VERIMEM_AUDIT_LOG`) … **Empty when auditing was never enabled**» | (da leggere) | (da leggere) | — | **FUNZIONA COME PROMESSO (e il default è: nessun audit)** | stessa esecuzione, store nuovo senza la variabile: `audit_log()` → `[]`, `audit_verify()` → `None`, `audit_head()` → `None`. Il docstring lo dichiara; per l'utente significa che **di default la traccia di audit non esiste**, e questa è una riga da tenere accanto ai claim di verificabilità |
| 14 | `Risultati` (client.py:326) + `sotto_il_pavimento` / `trattenuti` | il contenitore delle letture che porta il pavimento di rilevanza e il conto dei fatti trattenuti dal gate | `search` | (da leggere) | README (MCP «SERVES the results and flags them») | **FUNZIONA COME PROMESSO, ed è il pezzo che il prodotto vende** | stessa esecuzione: `search("canone capannone")` → `Risultati` len 1, `sotto_il_pavimento={'pavimento': 0.8975, 'score_migliore': 0.8566, 'tagliati': 0, 'nota': "…probabilmente la risposta NON e' in memoria. I risultati sono qui sotto, non tagliati — decidi tu."}`, `trattenuti={'quanti': 1, 'nota': "1 fatto/i … TRATTENUTI dal gate … non ti vengono serviti come veri."}` — il fatto quarantinato non è servito **ed è contato e spiegato** |

## Le altre 66 voci — `NON MISURATO`, elencate per non perderle

Estratte con `ast` (banco `ws3-mappa-base.py`), con chiamanti e test **da
leggere**: `_json_default`, `_pretty`, `_fmt_score`, `AutoMemory` e i suoi
metodi, `search_documents` (1873), `index_document`, `ask`, `explain`,
`forget`, `restore_fact`, `supersede`, `stats`, `health`, `doctor_report`,
`export`, `import_facts`, `topics`, `by_topic`, `recent`, `pin`, `unpin`, e i
privati `_gate_and_store`, `_apply_gate_result`, `_entity_link`, `_provenance`,
`_receipt`, `_gate_mode`, `_should_ground`, … (elenco completo nel banco).

**Prossima passata, in quest'ordine**: ① i chiamanti veri delle tre porte per
`add`/`search` (letti, con la riga); ② `search_documents` e `ask` (stanno
dietro i claim README su documenti e domande); ③ il resto per righe
decrescenti.

## Ticket aperti da questa passata

- **T-MAP-1** (owner Galileo, 08/09 20:31) — `Memory(path)` con path esplicito
  scrive nel path, ma il warning di risoluzione dei DATA_DIR annuncia un altro
  vincitore («HIPPO_DATA_DIR wins»). Il messaggio è vero per gli accessori e
  falso per il fatto principale, e chi legge conclude di aver scritto altrove.
  Nessuna cura durante la mappa: qui si registra.
- **T-MAP-2** (owner Galileo, 08/09 21:09) — `Memory.ask` con intento
  `LIST_ALL` fa un confronto **letterale** sui termini: «elenca tutti i
  capannon**i**» → 0 risultati, «elenca tutti i capannon**e**» → 2, sullo
  stesso corpus. Il docstring promette «returns the whole matching set», e la
  domanda al plurale — cioè la forma naturale di una richiesta di elenco —
  è quella che non trova niente. Anche le parole di riempimento entrano nei
  termini («elenca tutto sul capannone» → termini `tutto sul capannone` → 0).
  Confinato al router di intento (`query_intent.content_terms`); `FIND` e
  `COUNT` sulla stessa domanda funzionano. **Non curato**: mappa, non cure.
