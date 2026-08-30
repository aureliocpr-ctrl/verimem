# 21 — Le due porte gemelle non si somigliano, e quella sbagliata tace

**ws6 · 30/08 ore 15:10** · misure alla porta MCP, sullo store reale in sola lettura.

---

## ① Correggo una nota che ho messo in TRE documenti: il rerank non è rotto

Nei documenti [17](17-la-ricerca-ordina-per-data-non-per-pertinenza.md),
[19](19-la-cura-del-ranking-peggiora-il-caso-reale.md) e
[20](20-l-archivio-vecchio-ha-gia-una-porta-e-si-chiama-auto-master.md) ho scritto, come limite,
che **«`recall` gira degradato»**, citando `rerank: timeout_cold` e
`skipped_long_query` + `fusion: timeout`. L'ho scritto **come se fosse una condizione permanente**.

**Non lo è.** Alle 15:05, stessa porta, stesso store:

```
   ranking: { "rerank": "applied", "fusion": "applied" }
```

stabile su chiamate ripetute. Le mie letture precedenti cadevano nel **caricamento del modello**:
un costo di avvio, non un guasto.

⇒ **La formulazione giusta è «era degradato alle ore X», non «gira degradato».** I numeri di quei
documenti non cambiano — restano un **pavimento**, misurato mentre il reranker si scaldava — ma la
frase prometteva un difetto che non c'è.

---

## ② Le due porte gemelle usano due nomi diversi, e la sbagliata non protesta

Misura a variabile singola, stessa query (`quarantena gate`), stessa porta:

```
   hippo_facts_recall   limit=3   ->   5 items
   hippo_facts_recall   limit=2   ->   5 items      <- 'limit' IGNORATO
   hippo_facts_recall   k=2       ->   2 items      <- il nome giusto
```

Lo schema del tool (`verimem/mcp_server.py`, intorno a riga 2591) dichiara
**`"k": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5}`**.

· **`hippo_facts_search` usa `limit`.**
· **`hippo_facts_recall` usa `k`.**
· **Chi passa `limit` a `recall` non riceve nessun errore**: il parametro viene ignorato e la porta
  restituisce il default, cinque.

🔑 **È la classe di difetto di tutta questa giornata**: *la porta accetta e non dice*. La stessa del
ripiego AND→OR silenzioso, curato in `5219443a`. Qui però il costo è più subdolo, perché **chi
sbaglia crede di aver ottenuto ciò che ha chiesto** — e il numero di risultati è proprio ciò su cui
si costruiscono poi le percentuali.

⚠️ **Ha ingannato me, che questa porta la sto misurando da sei ore.** Per due letture consecutive ho
creduto di avere un difetto del prodotto («`limit` non rispettato») quando avevo un errore mio che
il prodotto non segnalava.

---

## Cure possibili — non misurate, quindi non proposte come fatte

· accettare `limit` come **alias** di `k` (le gemelle si somiglierebbero);
· oppure **rifiutare** i parametri sconosciuti con un errore esplicito;
· oppure **segnalarli** fra gli avvisi di lettura, dove già escono `trattenuti` e
  `sotto_il_pavimento` — e ora anche il ripiego.

**Nessuna delle tre è misurata**, e la scelta fra «alias» e «errore» non è ovvia: la prima è comoda
e nasconde l'asimmetria, la seconda la fa vedere ma rompe chi oggi passa parametri in più senza
saperlo. **Va decisa, non indovinata.**

## Limiti

· Misurato su **una** query e **una** porta. Non ho verificato se altri tool MCP hanno la stessa
  tolleranza silenziosa: **probabile, ma non misurato.**
· L'istante conta: il rerank risulta `applied` **alle 15:05**; una sessione appena avviata lo
  ritroverà `timeout_cold` finché il modello non è caricato.
