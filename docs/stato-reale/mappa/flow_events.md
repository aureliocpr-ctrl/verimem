# `verimem/flow_events.py` — 362 righe, 11 funzioni

**Il file che fa sì che un evento non arrivi mai senza la propria provenienza.**
*«Flow-event fan-out for the LIVE Engine Room — emitted at the CORE.»* Mappato su
`7b9e8ca1`. 6 pubbliche, 5 private.

---

## 1. 🔑 Ogni evento porta TRE risposte che nessuno dovrà dedurre

| funzione | risponde a |
|---|---|
| `_store_fingerprint` (103) | *«QUALE memoria ha prodotto questo evento — **impronta, non percorso**»* |
| `_build` (215) | *«DA QUALE CODICE viene questo evento»* — calcolato una volta per processo |
| `_run` (256) | *«DA QUALE ESECUZIONE viene»* — una volta per processo |

**Impronta e non percorso** è la scelta che conta: due store possono stare allo stesso path
in momenti diversi, e un path uguale non prova che sia la stessa memoria. È esattamente la
trappola che sui nostri appunti costa di più — *«ogni store ha due DB e quello alla radice è
vuoto»*: con l'impronta, un banco che misura la memoria sbagliata **si vede**.

📌 `_revisione_git` (172) torna la revisione corta **o `None`** invece di indovinare: un
evento non dichiara un codice che non sa.

---

## 2. `emit_write` (321) — **l'UNICO emettitore**, e oggi è stato esteso

> *«L'UNICO emettitore di `flow.write` — una funzione, più porte.»*

È la superficie unica: le porte non costruiscono l'evento ciascuna a modo suo. E il file
dichiara **perché** i campi si derivano invece di accettarli:

> *«`judged` e `withheld_despite_judge` si DERIVANO qui e non si accettano dal chiamante: se
> una porta potesse dichiarare `judged=True` senza un punteggio, il campo mentirebbe — ed è
> il campo su cui questo prodotto si vende.»*

⚠️ E qui c'era il buco curato oggi: **il journal derivava `judged` da mesi, mentre la
ricevuta della porta MCP non portava la chiave affatto** — misurato l'08/09 nello stesso
banco (`flow.write … grounding_score=98.5 judged=True` contro `grep '"judged"'
mcp_server.py` → 0). ⇒ Il prodotto lo sapeva, lo registrava **per sé**, e non lo diceva a
chi aveva appena scritto. Curato in `f19f067f`, con `judged_at_all` come unica definizione
usata da entrambe le superfici.

---

## 3. `emit_flow` (353) — *«Never raises»*

La telemetria non può rompere ciò che osserva. È la stessa regola dei warm best-effort in
`preload`: **un difetto dell'osservatore non deve diventare un difetto del prodotto.**

📌 `set_flow_context` / `reset_flow_context` (46, 55) sovrappongono campi ambientali a
**tutti** gli eventi di un contesto — e `reset_store_fingerprint` (73) esiste **per i
banchi**, dichiarato nel docstring: ricalcola l'impronta alla prossima emissione. Una
funzione che ammette di servire ai test è più onesta di una che finge di no.

---

## 4. Le 11 funzioni

**Pubbliche (6)**: `set_flow_context` · `reset_flow_context` · `reset_store_fingerprint` ·
`impronta_di_percorso` · `emit_write` · `emit_flow`.
**Private (5)**: `_store_fingerprint` · `_revisione_git` · `_build` · `_run` · `_ambient`.

---

## 5. Quello che questa mappa NON dice — dichiarato

- ~~Non ho verificato che `emit_write` sia l'unico emettitore~~ → **VERIFICATO, e la
  promessa regge.** In tutto il prodotto `"flow.write"` compare **due volte**:

      verimem/flow_events.py:343   emit_flow("flow.write", …)   <- l'unica EMISSIONE
      verimem/flow_tail.py:48      if name == "flow.write":     <- un LETTORE

  e i chiamanti di `emit_write` sono le due porte: `client.py` (SDK, tre punti — rifiuto,
  telemetria, scrittura) e `mcp_server.py:13739`. *(Il limite era scritto qui e l'ho chiuso
  con un comando invece di lasciarlo: costava cinque secondi.)*
- **Non so quanto costi `_store_fingerprint`** per evento: è cacheata «una volta per
  processo» per build e run, ma sull'impronta dello store non l'ho letto.
- **Non ho controllato dove finiscono gli eventi** (file, SSE, entrambi): il fan-out è nel
  nome del modulo, non nella mia mappa.

---

*Mappato da ws5 (Piattaforma) su `7b9e8ca1`. La misura del §2 è mia, dell'08/09.*

---

<!-- TABELLA-FUNZIONI ws5 -->

## Dove sta ogni funzione, e con che verdetto

*Rubrica generata dall'AST. Cosa e' misurato e cosa no, per colonna:*

- **dove e chi** — `file:riga` dall'AST: misurato.
- **cos'e'** — tipo e prima riga del docstring: e' cio' che la funzione
  PROMETTE, non cio' che fa.
- **nominata da** — file che NOMINANO il nome corto: chiamate, ma anche
  riferimenti nudi, property e annotazioni. Gli alias di import sono
  risolti (senza, `emit_write` risultava a zero). Contando solo le
  chiamate, 17 funzioni su 27 risultavano morte e non lo erano: Protocol,
  property e callback non passano da una `ast.Call`. Include il file
  stesso. ⚠️ Un nome che vive in piu' classi (`call`, `to_dict`) somma
  usi non suoi: e' un TETTO, non una misura.
- **test** — file sotto `tests/` che lo nominano: dice che e' TOCCATA,
  non che sia coperta.
- **verdetto** — `MAI CHIAMATA` = zero riferimenti nel prodotto E zero nei
  test (i dunder esclusi: li chiama il linguaggio). `NON MISURATO` =
  tutto il resto, ed e' lo stato onesto: sapere chi la nomina non e'
  sapere che funziona.


### `verimem/flow_events.py` — 11 fra funzioni e classi

| # | dove e chi | cos'e' | nominata da | test | verdetto |
|---|---|---|---|---|---|
| 1 | `verimem/flow_events.py:46` `set_flow_context` | funzione: Overlay ambient fields onto every flow event in this context | `verimem/client.py`; `verimem/gateway.py` | `tests/test_flow_events_core.py` | NON MISURATO |
| 2 | `verimem/flow_events.py:55` `reset_flow_context` | funzione: Clear the overlay (or restore to ``token`` if given). | `verimem/gateway.py` | `tests/test_flow_decay_dichiarato.py`; `tests/test_flow_documenti.py` (+15) | NON MISURATO |
| 3 | `verimem/flow_events.py:73` `reset_store_fingerprint` | funzione: Ricalcola l'impronta e il build alla prossima emissione (banchi, e chi | **nessuno** | `tests/test_l_evento_dice_a_quale_store_appartiene.py`; `tests/test_l_impronta_segue_lo_store_aperto_per_path.py` (+1) | NON MISURATO |
| 4 | `verimem/flow_events.py:82` `impronta_di_percorso` | funzione: L'impronta della memoria che si apre con un PATH esplicito. | `verimem/client.py` | `tests/test_l_impronta_segue_lo_store_aperto_per_path.py` | NON MISURATO |
| 5 | `verimem/flow_events.py:103` `_store_fingerprint` | funzione: QUALE memoria ha prodotto questo evento — impronta, non percorso. | `verimem/event_jsonl_log.py`; `verimem/flow_events.py` | `tests/test_l_impronta_segue_lo_store_aperto_per_path.py` | NON MISURATO |
| 6 | `verimem/flow_events.py:172` `_revisione_git` | funzione: La revisione corta dell'albero da cui gira il pacchetto, o ``None``. | `verimem/flow_events.py` | **nessuno** | NON MISURATO |
| 7 | `verimem/flow_events.py:215` `_build` | funzione: DA QUALE CODICE viene questo evento — calcolato una volta per processo. | `verimem/band_escalation.py`; `verimem/event_jsonl_log.py` (+2) | `tests/test_community_causal_edges.py`; `tests/test_llm_client.py` (+13) | NON MISURATO |
| 8 | `verimem/flow_events.py:256` `_run` | funzione: DA QUALE ESECUZIONE viene questo evento — una volta per processo. | `verimem/ann_cache.py`; `verimem/flow_events.py` (+2) | `tests/test_airgap_live_probe.py`; `tests/test_bench_compare.py` (+11) | NON MISURATO |
| 9 | `verimem/flow_events.py:291` `_ambient` | funzione | `verimem/flow_events.py` | `tests/test_flow_surface_onesta.py`; `tests/test_gli_eventi_non_dicevano_da_quale_esecuzione_venivano.py` (+1) | NON MISURATO |
| 10 | `verimem/flow_events.py:321` `emit_write` | funzione: L'UNICO emettitore di ``flow.write`` — una funzione, piu' porte. | `verimem/client.py`; `verimem/mcp_server.py` | `tests/test_l_evento_dice_a_quale_store_appartiene.py`; `tests/test_la_porta_mcp_non_emetteva_nulla.py` | NON MISURATO |
| 11 | `verimem/flow_events.py:353` `emit_flow` | funzione: Emit one flow event (ambient tags + ``payload``). Never raises. | `verimem/auto_dream_worker.py`; `verimem/client.py` (+10) | `tests/test_l_evento_dice_a_quale_store_appartiene.py`; `tests/test_ogni_evento_dice_quale_build_lo_ha_scritto.py` | NON MISURATO |

<!-- /TABELLA-FUNZIONI ws5 -->





