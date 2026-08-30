# 36 — La promessa di astensione esiste, funziona, ed è spenta di default

**ws6 · 31/08 ore 00:25** · porte MCP interrogate davvero.

Il [documento 32](32-il-rerank-sa-quando-non-ha-trovato-e-la-porta-serve-lo-stesso.md) si chiude
così: *«la porta ha già in mano il numero per astenersi. Le manca solo la riga che lo legge»*.

🔴 **Era sbagliato. La riga c'è, è documentata, funziona — ed è spenta di default.**

---

## Il prodotto la promette, con queste parole

Schema MCP di **`hippo_facts_recall`** (`mcp_server.py:2645`), descrizione di `min_relevance`:

> *«Retrieval floor: below it this returns **NOTHING** instead of the nearest neighbours — the
> **'abstention over hallucination' promise**, on this surface»*

E su **`hippo_trust_report`** (`mcp_server.py:2741`): `{"type": "number", **"default": 0.0**,
"description": "retrieval floor: hits below it are dropped so an absent-attribute query ABSTAINS
without an LLM (**opt-in**…)"}`.

**Non è un'idea: è un modulo.** `verimem/relevance_floor.py` con
`estimate_relevance_floor(n_probes=32, quantile=0.95)`, più `_auto_relevance_floor()` in
`client.py:2426` e il valore speciale `"auto"`.

## L'A/B alla porta, stessa domanda senza risposta

Domanda: **«quanto costa un biglietto per Saturno partendo da Bologna»** — nel corpus non c'è nulla.

```
   con min_relevance=0.9   ->  items: []                      SI ASTIENE
   senza (default null)    ->  3 fatti:
        "Il primo write giudicato costa 25.94 secondi."          score 0,81   <- ha «costa»
        "Il caso magazzini token NUOVO (Bologna)…"                score 0,78   <- ha «Bologna»
        "Alla domanda sul ripetitore di Bologna trust_report…"    score 0,78   <- ha «Bologna»
```

⇒ **Alla domanda su un biglietto per Saturno, la porta risponde con la latenza di una scrittura.**
È esattamente il difetto che il [doc 04](04-percorso-di-lettura.md) descriveva: *«un fatto che non
c'entra niente, presentato come il migliore che ha»*.

📌 **E il terzo risultato parla di `trust_report` che NON si astiene** (`abstained=False`) quando
dovrebbe. **Non astenendosi, la porta mi ha restituito un fatto su una porta che non si astiene.**

---

## 🔑 Che cosa cambia, e cambia parecchio

Per tutta la giornata ho scritto che **manca** qualcosa: un avviso, un ranking, una soglia. **Su
questo punto non manca niente:**

| pezzo | c'è? | attivo? |
|---|---|---|
| la **promessa** («abstention over hallucination») | ✅ scritta nello schema | — |
| il **meccanismo** (`min_relevance`, anche `"auto"`) | ✅ esposto su MCP | ❌ **default `0.0` / `null`** |
| lo **stimatore** (`relevance_floor.py`, 32 probe, quantile 0,95) | ✅ modulo dedicato | ❌ non invocato di default |
| la **prova che funziona** | ✅ `items: []` alla porta | — |

⇒ **La cura non è codice: è un default.** Nessuno deve progettare né scrivere logica — va **deciso
un valore** (o `"auto"`), e la decisione è di prodotto.

⚖️ **Va detto in entrambi i versi**: un pavimento troppo alto fa sparire risposte utili, e il default
`0.0` **è la scelta prudente di chi non vuole falsi negativi**. Ma **non è neutra**: significa che
la promessa scritta nello schema — *«returns NOTHING instead of the nearest neighbours»* — **per
chi non passa il parametro non è mai in vigore.**

## Limiti

· **Una domanda, una soglia** (`0.9`): il contrasto è netto, **ma non ho calibrato niente** — non so
  quale valore separi bene, né quante risposte buone perderebbe. **`relevance_floor.py` esiste
  proprio per stimarlo, e non l'ho eseguito.**
· `ranking` riportava **`rerank: timeout`** in entrambe le chiamate: il contrasto regge lo stesso
  (la differenza è il pavimento, non il rerank), **ma i punteggi sono un pavimento, non il meglio**.
· **Non ho verificato se qualche superficie imposti il floor per conto suo** (CLI, gateway,
  `guardian`): l'ho visto citato in cinque file e ne ho letti due.
· **L'istante è parte del dato**: 31/08 ore 00:25.
