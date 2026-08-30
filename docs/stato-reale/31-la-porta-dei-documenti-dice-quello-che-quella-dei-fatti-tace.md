# 31 — La porta dei documenti dice quello che quella dei fatti tace

**ws6 · 30/08 ore 20:40** · porte MCP interrogate davvero, non lette nel codice.

Il [documento 30](30-la-porta-dei-documenti-e-costruita-meglio-e-l-indice-e-fatto-di-scratchpad.md)
si chiude con un limite dichiarato: *«ho letto il criterio nel codice, non l'ho provata — e oggi ho
imparato tre volte che sono due cose diverse»*. **Provata.**

---

## Il quadro a tre caselle, replicato sui documenti

Chunk bersaglio: `docs/ROADMAP-v0.7.md`, che contiene
*«Both models independently scored the product **6/10**»*.

| domanda | `document_search` (lessicale) | `document_semantic_search` |
|---|---|---|
| **parole esatte** — «Nothing silent nothing mislabeled» | ✅ trova | — |
| **parole mie, stessa lingua** — «the external reviewers gave the product six out of ten» | ❌ **`[]` vuoto** | ✅ **primo posto**, `rerank_score` **1,94** (il secondo: −2,26) |

⇒ **Identico ai fatti**: la porta lessicale non trova se non indovini le parole; la semantica regge.
**Il difetto non è dell'archivio né del concetto di ricerca: è di come cerca la porta lessicale**, e
si ripete su due store diversi.

---

## 🔑 Ma qui la porta DICE tre cose che quella dei fatti non dice

**①** **`query_terms: 7 · query_terms_matched: 2`** — la risposta dichiara **quanti termini della
domanda hanno agganciato**. Su `hippo_facts_search` **questo campo non esiste**: è esattamente
l'informazione che manca per capire se un risultato è pertinente o è un ripiego.

**②** **`rerank_score` separato da `score`**, e separa davvero: **1,94** il pertinente, **−2,26** e
**−3,10** gli altri. Chi legge vede **dove cade il taglio**.

**③** — ed è quella che conta —

```json
"hidden_chunks": 1,
"note": "1 chunk(s) hidden: injection signals detected at index time.
         These results are PARTIAL — the document is indexed but part of it
         is withheld from default search."
```

**La porta dichiara che la risposta è parziale, quanto le manca, e perché.**

---

## Che cosa ne segue, ed è la cosa più utile di tutta la giornata

Ho passato dodici documenti a misurare che **`hippo_facts_search` ripiega dall'AND all'OR in
silenzio**, ordina per data senza dirlo, e ignora `limit` senza protestare. La cura che ho scritto
stamattina (`5219443a`) aggiunge un avviso di ripiego.

🔑 **Quella cura non era un'invenzione mia: era portare la porta dei fatti dov'è già quella dei
documenti.** Il prodotto **sa** avvisare — dichiara i risultati parziali, conta i termini
agganciati, tiene i punteggi separati. **Lo fa su una porta e non sull'altra.**

⇒ **Il modello per curare `facts_search` esiste già dentro il prodotto**, e chiunque lo faccia non
deve progettare niente: deve **copiare `document_semantic_search`**.

## Limiti

· **Poche query, non una popolazione**: una per casella, su un solo documento bersaglio. Il
  contrasto vuoto/primo-posto è netto, **ma è un contrasto, non un tasso**.
· Ho scelto **query nella stessa lingua del testo** (inglese) per non confondere «parole proprie»
  con «cross-lingua»: sul secondo asse **non ho misurato niente**.
· **`indexed_by: null`** compare anche qui, nei risultati serviti: il campo esce dalla porta
  **sempre vuoto** (683 chunk su 683 nello store).
· **L'istante è parte del dato**: 30/08 ore 20:40.
