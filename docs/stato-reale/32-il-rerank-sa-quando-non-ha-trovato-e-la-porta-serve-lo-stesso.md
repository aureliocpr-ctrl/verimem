# 32 — Il rerank sa quando non ha trovato, e la porta serve lo stesso

**ws6 · 30/08 ore 21:15** · porte MCP interrogate davvero. Chiude l'asse che il
[documento 31](31-la-porta-dei-documenti-dice-quello-che-quella-dei-fatti-tace.md) dichiarava
**non misurato**: il cross-lingua.

---

## Le due domande, e il contrasto

Stesso contenuto, due direzioni di lingua, stessa porta (`hippo_document_semantic_search`):

| domanda | bersaglio | esito | `rerank_score` del 1º |
|---|---|---|---|
| **inglese** → «the external reviewers gave the product six out of ten» | chunk **inglese** (ROADMAP) | ✅ **primo posto** | **+1,94** |
| **italiana** → «i due modelli esterni hanno dato sei su dieci al prodotto» | lo stesso chunk **inglese** | ❌ **non compare** | **−3,27** (e tutti gli altri peggio) |
| **inglese** → «four out of five facts served by the product were never judged» | chunk **italiano** (PER-WS3) | ✅ **primo posto** | **+8,46** |

## ⚠️ Perché NON concludo «l'embedding è asimmetrico»

**Il corpus è sbilanciato**: **40 documenti su 42 sono italiani** (doc 30). La domanda italiana
aveva **un solo bersaglio inglese possibile** — la ROADMAP; quella inglese ne aveva **quaranta**.

⇒ **L'asimmetria osservata può essere l'effetto dello sbilanciamento, non del modello.** Con questo
corpus **non è separabile**, e chi volesse deciderlo deve indicizzare un corpus bilanciato.
**Quello che posso dire è solo**: *in questo corpus, una domanda in italiano non ha raggiunto il
contenuto inglese; una in inglese ha raggiunto quello italiano al primo posto.*

---

## 🔑 Il reperto robusto, che NON dipende dal bilanciamento

**Il rerank distingue benissimo il caso riuscito da quello fallito:**

```
   trovato          rerank del 1º:  +8,46   ·  +1,94
   non trovato      rerank del 1º:  −3,27   (2º −4,23 · 3º −4,47 · 4º −5,05 · 5º −5,13)
```

**Undici punti di distanza fra «l'ho trovato» e «non c'è».** Il segnale **esiste, è calcolato, ed
esce nella risposta**.

⇒ **E la porta serve i cinque risultati in entrambi i casi, allo stesso modo.** Quando tutti i
punteggi sono negativi — cioè quando il modello sta dicendo *«nessuno di questi risponde»* — la
risposta **non lo dichiara**.

🔑 **È lo stesso difetto del [documento 04](04-percorso-di-lettura.md)**, che lo aveva trovato su
`recall`: *«è un fatto che non c'entra niente, presentato come il migliore che ha»*. Qui è
**quantificato**, e su una porta che per il resto **è la più onesta del prodotto**: quella che
dichiara `query_terms_matched`, tiene `score` e `rerank_score` separati e avvisa
«these results are PARTIAL».

⇒ **La porta ha già in mano il numero per astenersi. Le manca solo la riga che lo legge.**

## Limiti

· **Tre domande, non una popolazione.** Il contrasto +8,46 / −3,27 è netto, **ma è un contrasto**:
  non ho una soglia calibrata né so dove cada il confine fra «trovato» e «no».
· **Il confondente del corpus sbilanciato è dichiarato sopra e non è risolvibile qui.**
· Non ho provato la stessa cosa su `hippo_facts_recall`: **là il campo `rerank_score` non compare
  nemmeno** nella risposta, quindi il confronto non è possibile senza toccare il codice.
· **L'istante è parte del dato**: 30/08 ore 21:15.
