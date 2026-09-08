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

**Contatore**: 47 righe misurate su 80 · 16 claim collegati (README e
istruzioni del server) · i chiamanti delle tre porte per `add` e `search`
**letti con la riga** (20:59) · **6 ticket**, di cui tre su promesse pubbliche:
T-MAP-4 (un claim del README falso a metà), T-MAP-5 (un claim che tace un
requisito), **T-MAP-6 (la retro-demozione non copre il canale che il README
insegna)** · 5 righe dove **ho sbagliato io la chiamata o l'ipotesi** e l'ho
scritto, tre chiuse · **5 TypeError in una passata** perché chiamavo per
intuizione: metodo corretto, si leggono le firme prima. Prove sul tip
`20257636`.

**Il pezzo più forte finora**: la tamper-evidence dell'audit è provata
**manomettendo la catena**, non guardandola stare ferma (riga 31).

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

| 15 | `Memory.get` (client.py) | legge un fatto per id | (da leggere) | (da leggere) | — | **FUNZIONA COME PROMESSO** | `prova_ciclo.py` 08/09 21:44 sul tip 20257636: `get(id)` → dict con `id`, `text`, `status='model_claim'`, `grounding_score=99.673`, `topic`, `asserted_at` |
| 16 | `Memory.forget` / `Memory.delete` (client.py) | tolgono un fatto | (da leggere) | (da leggere) | — | **FUNZIONA COME PROMESSO, ma il log nomina lo store sbagliato** → ticket **T-MAP-3** | stessa esecuzione: `forget(id)` → `True`, e `get(id)` subito dopo → `None`: il fatto è tolto dal db giusto (il temporaneo). ⚠️ Ma la riga di log dice `flow.forget … store=67712a7ceb5e`, mentre `add` sullo **stesso oggetto `Memory`** aveva loggato `store=b42a7895c969`: il forget riporta l'id dello store risolto dal DATA_DIR globale, non quello del path esplicito su cui ha operato. **Verificato che non ho toccato lo store di casa**: 0 righe con quell'id, 0 col topic, mtime del db fermo alle 19:40 mentre la prova è delle 21:44 |
| 17 | `open_memory` (client.py:285) | apre lo store condiviso da CLI, MCP e SDK | (da leggere) | (da leggere) | README:428 («all three surfaces open the SAME store») | **FUNZIONA COME PROMESSO** | stessa esecuzione: `open_memory()` → un `Memory`, `isinstance(m2, Memory)` → True |
| 18 | `Memory.topics` / `recent` / `stats` / `health` | — | — | — | — | **NON ESISTONO su `Memory`** (e non è un difetto: nessun documento li promette) | stessa esecuzione: `topics()` → `AttributeError: 'Memory' object has no attribute 'topics'`; `recent`, `stats`, `health` → `hasattr` False. ⚠️ **Li ho chiamati per ipotesi mia**, non perché un claim li nominasse: la riga resta per dire che l'SDK **non** ha un'introspezione dello store (la CLI ha `doctor`, l'SDK no), e perché un lettore della mappa non li cerchi |

## I RAMI di `Memory.add` — dove il prodotto decide cosa entra

*Stessa coppia in ogni riga (claim falso «7300 euro» + fonte che dice «5900
euro»), così l'unica variabile è il ramo. `prova_rami_add.py`, 08/09 21:50,
tip 20257636.*

| # | ramo | esito misurato | claim | verdetto |
|---|---|---|---|---|
| 19 | default | `quarantined`, g=1.04, `['L4.1','L4-grounding']`, stored | README:172 («the write-gate checks *source ⊢ fact*») | **FUNZIONA COME PROMESSO** |
| 20 | `gate_mode="reject"` | `rejected`, g=1.04, **stored=False** | — | **FUNZIONA COME PROMESSO**: è l'unico ramo che NON scrive su disco |
| 21 | `validate="fast"` | `quarantined`, g=1.04, `['L4.1','L4-grounding']` — **il moat ha girato** | README:194 («`Memory(preset="permissive")` / `validate="fast"` **skip the moat entirely**») | 🔴 **NON COME PROMESSO** → ticket **T-MAP-4** |
| 22 | `Memory(preset="permissive")` | `model_claim`, g=None, `[]` — il moat non gira | README:194 | **FUNZIONA COME PROMESSO** (l'altra metà dello stesso claim) |
| 23 | `ground=False` | `model_claim`, g=None, `[]` | — | **FUNZIONA COME PROMESSO** |
| 24 | senza `source` | `model_claim`, g=None, `[]` | le istruzioni del server: «without a source … stored as an unverified `model_claim`» | **FUNZIONA COME PROMESSO** |
| 25 | self-claim senza source («La funzionalità è stata implementata e verificata») | `quarantined`, `['L1.15','L1.20']` | le istruzioni: «ON EVERY WRITE … a lexical screen. Unsupported self-claims are quarantined» | **FUNZIONA COME PROMESSO** |
| 26 | la stessa self-claim con `meta_narrative=True` | `model_claim`, `[]` — lo screen **non** scatta | le istruzioni: «ONE EXCEPTION … `meta_narrative=True` … skips that screen» | **FUNZIONA COME DICHIARATO** (l'eccezione è scritta, e qui è confermata) |
| 27 | la stessa self-claim con `verified_by=["pytest: 8 passed"]` | `model_claim`, `[]` | README (la prova toglie la quarantena) | **FUNZIONA COME PROMESSO** |
| 28 | `asserted_at=…` | scritto e **riletto**: `get()` → `asserted_at=1780000001.0` | il commento in `client.py:616-628` («valorizzato su 0 fatti su 15.978») | **FUNZIONA**: il campo non è rotto, è **inutilizzato** — la conseguenza descritta nel commento (una correzione supersede in silenzio invece di andare al giudice) dipende da chi scrive, non dal codice |

## Il blocco TRUST e AUDIT (client.py 2394-2843)

*`prova_trust_audit.py` e `prova_manomissione.py`, 08/09 22:00-22:02, tip
20257636, store temporaneo con `VERIMEM_AUDIT_LOG=1` — cioè con l'opt-in
**acceso**, non guardato da spento come nel blocco precedente.*

| # | funzione (riga) | cosa promette | verdetto | prova |
|---|---|---|---|---|
| 29 | `audit_log` (2627) | «The opt-in per-write audit trail … as dicts, newest-first, filterable by disposition and/or topic» | **FUNZIONA COME PROMESSO** | 3 scritture → 3 righe, campi `['disposition','evidence_class','fact_id','id','judge','layers','pins','proposition','reason','score','threshold','topic']`; la prima è `disposition='quarantined'` (la più recente), la seconda `admitted`: newest-first confermato |
| 30 | `audit_log(disposition=…)` | il filtro | **FUNZIONA COME PROMESSO** | `audit_log(disposition="quarantined")` → 1 riga, `dispositions=['quarantined']` |
| 31 | `audit_verify` (2643) | «the id of the FIRST tampered row … or `None` if the chain is intact» | ✅ **FUNZIONA COME PROMESSO — provato manomettendo davvero la catena** | catena intatta → `None`. Poi ho aperto `adjudications.db` e cambiato la `proposition` della riga interna `d1cbd3d67d544962` (`UPDATE adjudications SET proposition=…`), riaperto lo store con un handle nuovo: `audit_verify()` → **`d1cbd3d67d544962`**, esattamente l'id manomesso. ⚠️ Il controllo serviva: `None` significa «intatta» **e anche** «audit mai acceso» — due casi in un valore solo, e senza la manomissione la riga avrebbe detto «sembra funzionare» |
| 32 | `audit_head` (2653) | «the current chain head — archive it off-box … to detect even a full-chain rewrite» | **FUNZIONA COME PROMESSO, e il suo limite si vede** | prima `543faa95d55e001f…`; **dopo** la manomissione interna la testa è **identica**: coerente col docstring (la testa non vede una modifica interna, la vede `verify`; la testa serve contro la riscrittura completa). Per distinguere «catena intatta» da «audit spento» servono **due** chiamate: `head()` è `None` solo nel secondo caso |
| 33 | `audit_head_signed` (2660) | la testa firmata | **NON MISURATO** | torna `None` sullo store di prova: manca la chiave di firma, e la misura va rifatta configurandola |
| 34 | `why_decision` (2821) | «"Why did we choose X?" → matching decisions with their cited evidence ids» | **FUNZIONA COME PROMESSO** | `record_decision("uso Postgres per l'analytics")` → id; poi `why_decision("Why did we choose Postgres?")` → 1 decisione, e lo stesso con «perche' Postgres» e «Postgres». ⚠️ Nella prova precedente le avevo passato **l'id** e tornava `[]`: **errore mio**, la firma vuole una domanda |
| 35 | `source_trust` (2833) / `consistency_trust` (2837) | «Combined (min-of-observed-channels) trust for `source`» | **NON MISURATO** | chiamate senza argomenti → `TypeError: missing 1 required positional argument: 'source'`. **Errore mio**: vogliono la fonte. Da rifare passando una `source` vera |
| 36 | `trust_report(query)` (2370) | il dossier di provenienza | **FUNZIONA COME PROMESSO** | `trust_report("canone capannone")` → dict con `query`, `as_of`, `deep`, `k`, `min_relevance=0.8975`, `ranking_degraded`, `generated_at` — è `explain` con un altro nome, come dichiara il docstring |

## Soglie, coppia del moat, contatori, AutoMemory (client.py 198-535, 2394+)

*`prova_soglie.py` e `prova_moat_pair.py`, 08/09 22:10-22:12, tip 20257636.
Questo blocco chiude anche **i tre debiti** delle prove precedenti, cioè le
funzioni che avevo chiamato con la firma sbagliata.*

| # | funzione (riga) | cosa promette | verdetto | prova |
|---|---|---|---|---|
| 37 | `esito_del_moat` (446) | «Che cosa ha fatto il moat, DERIVATO da ciò che il gate ha già detto» | **FUNZIONA COME PROMESSO — quattro casi distinti** | vuole il `GateResult`, non il dict della ricevuta (**tre miei tentativi sbagliati prima di leggerlo**): vero+fonte → `'passed'` · falso+fonte → `'failed'` · self-claim senza fonte → `'not_run:no_source'` · nota libera senza fonte → `'not_run:no_source'` |
| 38 | `chi_ha_quarantinato` (464) | «Quale layer ha deciso la quarantena: `moat` / `L1` / `gate`» | **FUNZIONA COME PROMESSO** | vuole la **stringa** che restituisce `esito_del_moat`, non la riga del fatto: le due si compongono. Stessi quattro casi → `'gate'`, `'moat'`, `'L1'`, `'gate'`: i tre valori del docstring escono tutti, e su ciascuno quello giusto |
| 39 | `soglia_fatto_lungo` (198) / `soglia_controllo_duplicati` (225) | soglie pure | **FUNZIONA (misurate)** | `2000` e `50000` |
| 40 | `Memory.trust_stats` | README:284: «persistent counters of what the gate actually *did* … writes admitted, quarantined, rejected, and honest read-path abstentions, with per-layer attribution» | **FUNZIONA COME PROMESSO** | dopo un ammesso e un quarantinato: `{'ledger': {'admitted': 1, 'quarantined': 1, 'rejected': 0, 'abstained': 0}, 'by_layer': {'L4-grounding': 1, 'L4.1': 1}, 'since': …, 'daily': [{'day': '2026-09-08', …}]}` — i contatori e l'attribuzione per layer ci sono entrambi. (`stats()` invece **non esiste**: il nome giusto è questo) |
| 41 | `Memory.source_trust` (2833) / `consistency_trust` (2837) | «Combined (min-of-observed-channels) trust for `source`» | **FUNZIONA (misurate, debito chiuso)** | `source_trust(FONTE)` → `0.5`, `consistency_trust(FONTE)` → `0.5` su una fonte mai vista prima: il valore neutro di partenza |
| 42 | `AutoMemory` (client.py) | README:280-283: «`AutoMemory(memory).observe(role, text)` watches a live conversation and remembers on its own, but through the SAME gated pipeline … Opt-in by construction» | 🔴 **NON COME PROMESSO (il claim è incompleto)** → ticket **T-MAP-5** | `AutoMemory(m)` su un `Memory()` ordinario → `ValueError: AutoMemory needs a Memory built with an extraction llm (Memory(..., llm=...)) — same requirement as add(messages)`. Il messaggio d'errore **è ottimo** (dice cosa manca e a cosa somiglia); il README, alle righe 280-283, **non dice** che serve un llm — mentre alla riga 705, per `answer()`, lo dichiara («⚠️ **needs an injected LLM**»). Il prodotto sa fare la cosa giusta altrove: qui manca |

## I privati che decidono cosa NON si vede (client.py 2400-2930)

*`prova_privati.py`, `prova_privati2.py`, `prova_retro.py`, 08/09 22:16-22:22.
Sono le funzioni che agiscono in silenzio: se sbagliano, l'utente non riceve un
errore, riceve meno memoria.*

⚠️ **Nota di metodo, contro di me**: la prima passata su questo blocco ha
prodotto **5 TypeError su 6 chiamate**, perché ho chiamato le funzioni per
intuizione invece di leggere la firma. Ho letto le sei firme in un colpo e
rifatto la passata. Le righe qui sotto sono della seconda.

| # | funzione (riga) | cosa promette | verdetto | prova |
|---|---|---|---|---|
| 43 | `_trattenuti_safe` (2909) / `_conta_trattenuti` (2923) | l'avviso «quanti fatti sono stati trattenuti» che «non deve MAI far cadere una lettura» | **FUNZIONA COME PROMESSO** | `_trattenuti_safe("canone")` → `{'quanti': 1, 'nota': "1 fatto/i … TRATTENUTI dal gate …"}`, ed è lo stesso oggetto che compare in `Risultati.trattenuti` |
| 44 | `_nascosti_per_eta` (2851) | «Quanti fatti l'ETÀ tiene fuori dalla vista, **quando non si è trovato niente**. Si chiama solo a `out` vuoto» | **FUNZIONA COME PROMESSO** | con risultati presenti → `None`, cioè l'avviso non si accende quando non serve: è il comportamento che il docstring dichiara |
| 45 | `report_outcome` (2494) | «report that a stored fact succeeded or FAILED in use. Feeds the source's outcome reputation and — on a FAILURE — marks the fact's (topic, proposition) audit-revealed FALSE» | **NON MISURATO FINO IN FONDO** | `report_outcome(id, good=False)` → `True`, ma dopo la chiamata **gli stati non cambiano** e `source_trust` resta `0.5`. Non lo chiamo difetto: il canale «outcome» può avere una soglia o pesare in combinazione con gli altri, e non l'ho isolato. Da rifare con più segnalazioni e leggendo `_source_trust_book` |
| 46 | `source_trust_observe` (2400) | il canale che muove la fiducia di una fonte | **FUNZIONA COME PROMESSO** | `source_trust_observe(contradiction=FONTE)` → `source_trust` da **0,5 a 0,333**. ⚠️ Una `confirmation=[FONTE]` subito dopo **non** la fa risalire (resta 0,333): non è detto sia un difetto (la risalita può volere tempo o più conferme), ma è asimmetrico e non l'ho misurato oltre |
| 47 | `_retro_demote_source` (2522) / `_rehabilitate_source` (2552) | «Quarantine every non-quarantined fact citing `source` — the write-time gate only stops FUTURE lies; **the crossing re-evaluates the past ones**» | **FUNZIONA — ma non sul canale che il README insegna** → ticket **T-MAP-6** | controllo a **due lati**, che è ciò che rende leggibile il risultato: (A) fatto scritto con `add(source=…)` — il quickstart del README — → dopo `_retro_demote_source` resta `model_claim`; (B) fatto con `verified_by=["source:<testo>:sha256"]` → **`quarantined`**, con il log `fact_quarantined … reason="source '…' trust sank below the floor — retroactive demotion"`, e `_rehabilitate_source` lo riporta a `model_claim` (`fact_restored`). Quindi la funzione fa esattamente ciò che promette, **sui fatti che citano la fonte in `verified_by`**; `add(source=…)` lascia `verified_by=[]` e mette la fonte in `source_signature`, e la query (`verified_by LIKE '%"source:<testo>:%'`, prefissi `source-doc/source/src/doc/file`) non li trova mai |

## Le altre 33 voci — `NON MISURATO`, elencate per non perderle

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
- 🔴🔴 **T-MAP-6** (owner Galileo, 08/09 22:22) — **la retro-demozione di una
  fonte non tocca i fatti scritti come il README insegna.**
  `_retro_demote_source` cerca `verified_by LIKE '%"source:<testo>:%'` (prefissi
  `source-doc`, `source`, `src`, `doc`, `file`), ma `add(source=…)` — il
  quickstart del README, riga 441 — lascia `verified_by=[]` e mette la fonte in
  `source_signature` (`sha256:…`). Misurato a due lati nella stessa esecuzione:
  il fatto scritto con `add(source=…)` resta `model_claim`, quello con
  `verified_by=["source:…:sha256"]` diventa `quarantined` col log
  `fact_quarantined … retroactive demotion`. ⇒ La promessa «the crossing
  re-evaluates the past ones» **non copre il canale principale**: quando una
  fonte perde fiducia, i fatti scritti nel modo che la pagina insegna restano
  ammessi. Cure possibili (non è una decisione mia): la query guarda anche
  `source_signature`/`source`, oppure `add(source=…)` popola `verified_by` col
  riferimento. Da portare al lead con @ws6 Aldo, che ha il perimetro dati.
- 🔴 **T-MAP-5** (owner Galileo, da girare a @ws7 Iris, 08/09 22:12) —
  **README:280-283 promette `AutoMemory` senza dire che serve un llm.** Il
  codice solleva `ValueError: AutoMemory needs a Memory built with an
  extraction llm (Memory(..., llm=...))`, e il messaggio è chiaro; ma chi legge
  il README installa, scrive `AutoMemory(memory)` e sbatte contro un errore che
  la pagina non prepara. Alla riga 705 lo stesso README **dichiara** il
  requisito per `answer()` («needs an injected LLM»): la forma giusta esiste
  già, va applicata anche qui. Cura: una frase nella riga 280, non codice.
- 🔴 **T-MAP-4** (owner Galileo, da girare a @ws7 Iris che tiene il README,
  08/09 21:50) — **README:194 è vero a metà**. Dice: «`Memory(preset="permissive")`
  / `validate="fast"` skip the moat entirely». Misurato con la stessa coppia
  (falso + fonte che lo smentisce), una variabile per volta:
  `preset="permissive"` → `model_claim`, g=None, nessun layer: **il moat non
  gira, come promesso**; `validate="fast"` → `quarantined`, g=1.04,
  `['L4.1','L4-grounding']`: **il moat gira eccome**. Un utente che legge quella
  riga e usa `validate="fast"` per saltare il gate si ritrova i fatti
  quarantinati e non capisce perché. Due cure possibili e non è una decisione
  mia: o `validate="fast"` salta il moat davvero, o la riga del README perde
  quella metà.
- **T-MAP-3** (owner Galileo, 08/09 21:44) — `Memory.forget` opera sul db
  giusto ma **logga un altro store**: `flow.forget … store=67712a7ceb5e`
  mentre `add`, sullo stesso oggetto `Memory` costruito con un path esplicito,
  logga `store=b42a7895c969`. Chi legge i log per sapere *dove* è stata
  cancellata una cosa legge l'id sbagliato — e su una cancellazione è il log
  che resta. Stessa radice di T-MAP-1 (la risoluzione del DATA_DIR ignora il
  path esplicito nelle superfici che *riferiscono*), lato scrittura del log.
  Verificato nella stessa esecuzione che lo store di casa non è stato toccato.
