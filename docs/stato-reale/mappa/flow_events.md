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

*Mappato da ws5 (Tara) su `7b9e8ca1`. La misura del §2 è mia, dell'08/09.*
