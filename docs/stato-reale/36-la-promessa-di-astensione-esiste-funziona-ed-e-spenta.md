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

· ~~**Non ho calibrato niente… `relevance_floor.py` esiste proprio per stimarlo, e non l'ho
  eseguito.**~~ **Eseguito — vedi l'aggiunta in fondo.**
· `ranking` riportava **`rerank: timeout`** in entrambe le chiamate: il contrasto regge lo stesso
  (la differenza è il pavimento, non il rerank), **ma i punteggi sono un pavimento, non il meglio**.
· **Non ho verificato se qualche superficie imposti il floor per conto suo** (CLI, gateway,
  `guardian`): l'ho visto citato in cinque file e ne ho letti due.
· **L'istante è parte del dato**: 31/08 ore 00:25.


---

## Aggiunta dell'01:00 — eseguito lo stimatore: il rumore vale 0,8743, e la porta serve 0,78

`estimate_relevance_floor` è **sola lettura** (32 `recall` con `rerank=False`, nessuna scrittura),
quindi l'ho eseguito **sul corpus vero**.

```
   PAVIMENTO STIMATO (32 sonde, quantile 0,95)      0,8743      in 39,6 s
   valore citato nel commento del codice (19/08)    0,8321

   quantile 0,50 -> 0,8645     0,90 -> 0,8758     0,95 -> 0,8743     0,99 -> 0,8854
```

**Che cos'è quel numero.** Il docstring lo dice: *«the store's **noise ceiling**: quantile of the max
recall score of **scrambled probes**»*. Si generano sonde **senza senso**, si guarda **quanto in alto
punteggia il rumore**, e quello diventa il pavimento. ⇒ **Sopra 0,87 c'è segnale; sotto, c'è ciò che
il rumore raggiunge da solo.** *(E la funzione restituisce `0.0` — floor spento — se lo store è
troppo piccolo: «a floor guessed from nothing would be worse than none». È progettata bene.)*

## 🔑 Il confronto che chiude il documento

I tre fatti che la porta mi ha servito alla domanda **«quanto costa un biglietto per Saturno»**
avevano punteggio **0,8119 · 0,7796 · 0,7807**.

```
   rumore misurato dal prodotto stesso    0,8743
   ────────────────────────────────────────────────
   "…il primo write costa 25.94 secondi"  0,8119   ↓ sotto il rumore
   "…magazzini token NUOVO (Bologna)…"    0,7796   ↓ sotto il rumore
   "…ripetitore di Bologna trust_report…" 0,7807   ↓ sotto il rumore
```

⇒ 🔑 **Tutte e tre le risposte stanno SOTTO il livello che il prodotto stesso misura come rumore.**
Col pavimento che il prodotto sa calcolare, **quella risposta sarebbe stata vuota** — cioè giusta.

⇒ **Non è più «decidere un default»: il valore lo calcola il prodotto, in 40 secondi, con un modulo
scritto apposta.** La decisione residua è **se accenderlo**, e ogni quanto ricalcolarlo.

## 📌 E il pavimento si muove col corpus

**0,8321 il 19/08** (commento nel codice) contro **0,8743 oggi**: il corpus nel frattempo è passato
da circa settemila a **sedicimila** fatti. ⇒ **Più fatti ci sono, più è probabile che una sonda
casuale ne agganci uno simile: il rumore cresce.** Un pavimento fissato una volta **invecchia**, ed
è lo stesso motivo per cui `"auto"` esiste.

⚠️ **Limiti che restano**: non ho misurato **quante risposte buone** un pavimento a 0,87 farebbe
sparire — il numero misura il rumore, **non il costo del silenzio** · una sola esecuzione per
quantile, `seed=0` · durante la corsa è comparso `PPR fusion exceeded 2.00s budget`, quindi i
punteggi sono presi **in regime degradato**, come tutte le mie letture di oggi.
