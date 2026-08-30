# 17 — La ricerca ordina per data, non per pertinenza

**ws6 · 30/08** · misure sul corpus reale in `mode=ro` (15.578 fatti alle 12:25), codice su `origin/main`.

> Questo documento nasce da una domanda di Aurelio, che riporto verbatim perché è il criterio con
> cui va giudicato: *«si ma sta memoria la state usando? state concatenando tutto? sta memoria
> serve? per cosa la usate? ad esempio è capitato ogni 3 o 4 giorni o 3 volte al giorno o nello
> stesso giorno tutte le istanze di attribuirmi la bump 0.»*

---

## ① La forma del difetto era già scritta, e non è mia

**[`04-percorso-di-lettura.md`](04-percorso-di-lettura.md), righe 52-68**, lo dice di `recall`:

> «`recall` risponde **«La polizza assicurativa copre fino a 2 milioni di euro»**, con punteggio
> 0.77. Non è una risposta sbagliata *per poco*: è un fatto che non c'entra niente, **presentato
> come il migliore che ha**.»
>
> «**La capacità di dire "non lo so" esiste, è misurata, e funziona 4 volte su 4. Solo che è dentro
> una porta sola, e non è quella che si usa per prima.**»

⇒ La classe — *una porta che, non avendo la risposta, serve il meglio che ha invece di astenersi* —
**era già censita**. Quello che segue è una **seconda faccia** con un meccanismo diverso, e va letto
dopo, non al posto.

---

## ② Su `search` il meccanismo è un altro: non c'è nessun punteggio

`verimem/semantic.py`, coda di `search_facts`:

```sql
ORDER BY created_at DESC LIMIT ?
```

**Il LIKE sceglie i candidati; la DATA sceglie quali vedi.** Non esiste ranking di rilevanza.
`verimem/mcp_server.py:12380-12394`: il tool prova `require_all_tokens=True` (AND su tutti i token)
e, se dà zero, ripiega su `tokenize=True` (OR).

🔑 **Differenza da ①, e conta**: in `04` c'è un punteggio (0.77) senza una soglia, quindi la cura è
una soglia — ed è quella che `trust_report` applica. **Qui non c'è nessun punteggio su cui metterla.**

### La misura

Query: `TBook 11 Teclast Atom senza AVX interrupt counter` — otto parole, tema reale del 23-24/08.

| ramo | esito |
|---|---|
| AND (8 token) | **0 hit** — nessun fatto contiene tutti i termini |
| OR | **2575 hit** = **16,5% del corpus intero** |
| posizione dei fatti TBook | **147, 148, 149** |
| ciò che esce con `limit=5` | `run ci 1121` · `ordine INVERTITO` · `_l1_domain_precision` |

Quei cinque sono **esattamente** quelli che il tool vero mi aveva restituito: la replica SQL
riproduce la porta, quindi il modello del difetto è giusto e non è un'inferenza.

**I fatti cercati erano agganciati. Sono stati sepolti da 147 fatti più recenti.**

⚠️ `bm25_rank._tokens` **non toglie nulla** su questa query: AND e OR hanno gli **stessi otto**
token, «senza» compresa. La cura del 2026-08-02 (togliere le funzionali, commentata nel codice) è
sul ramo OR e **non morde qui**.

✅ **`hippo_facts_recall` trova** gli stessi fatti (`b0851e7c5123`, `f7bd5b5da84c`).
**La memoria ha i fatti: è `search` che non li serve.**

---

## ③ La prova che la domanda di Aurelio chiedeva — e il soggetto sono io

Fatto **`1aa23dd4f2b5`**, **12 agosto**, topic `project/archivio/la-porta-non-serve-il-ritirato`,
`writer_principal: cli:local/ws6:mnemo` — **l'ho scritto io**:

> «Interrogando `hippo_facts_search` con la frase che sul database appartiene al solo fatto
> `356fb41daf4c`, il fatto `356fb41daf4c` **non compare fra gli items**.»

Il suo `grounding_span` contiene **lo stesso esperimento che ho rifatto ieri sera credendolo nuovo**.

🔴 **Avevo già misurato questo difetto diciotto giorni fa, e il 29-30/08 l'ho riscoperto da zero in
due ore.** La ragione per cui non me l'ha restituito **è il difetto stesso**: ieri l'ho cercato con
`hippo_facts_search`, che mi ha dato i fatti di ieri. L'ho ritrovato solo oggi, usando `recall`.

**Il difetto della memoria impedisce di ricordare il difetto della memoria.**

📌 E la mia diagnosi del 12/08 era **incompleta**: dal topic si vede che avevo attribuito la causa
alla *supersessione* («non-serve-il-ritirato»). La causa vera è l'ordinamento per data.

---

## Che cosa risponde, di preciso, alla domanda

| la domanda | la risposta misurata |
|---|---|
| «state concatenando tutto?» | **Sì.** 15.578 fatti, `lineage_to` popolato su tutti quelli letti. |
| «sta memoria serve?» | **In scrittura sì.** In lettura **dipende dalla porta**, e le due non si somigliano. |
| «per cosa la usate?» | Per scrivere molto. Per rileggere, dalla porta sbagliata. |
| «ogni 3 o 4 giorni…» | Il tempo perché ~150 fatti nuovi che condividono **una parola comune** scendano sopra la lezione e la spingano sotto il taglio. |
| «…o nello stesso giorno tutte le istanze» | Tutte interrogano lo stesso store e ricevono **lo stesso set recente**: sbagliano insieme, non per caso. |

🔑 **Le due frequenze non sono due fenomeni: sono due regimi dello stesso difetto.**

⚖️ **E la causa non è la disciplina.** La regola `O1` e la skill `hippoagent-memory` indicano
`hippo_facts_search` **per prima** (la skill dice testualmente «instant keyword — *then fall back to*
`hippo_facts_recall`»). **Chi obbedisce alla regola usa la porta che fallisce in silenzio**, e
conclude che in memoria non c'è nulla.

---

## Limiti di questo documento — dichiarati, non nascosti

· **Campione mio, non popolazione**: 5 query, 4 falliscono e **1 riesce**. Quella che riesce
  (`aiOS RISC-V shell interattiva UART`) restituisce fatti **del 24 giugno**, due mesi fa: quando i
  token sono **rari**, l'ordinamento per data non fa danno perché i candidati sono pochi. ⇒ **il
  difetto morde in funzione della frequenza delle parole, e questa curva non l'ho misurata.**
· **Il numero 147 dipende dall'istante**: 30/08 ore 12:25, corpus 15.578. Domani è un altro numero.
· **`recall` gira degradato** in entrambe le mie letture (`rerank: timeout_cold`, poi
  `rerank: skipped_long_query, fusion: timeout`) ⇒ i suoi risultati sono un **pavimento**, non il suo meglio.
· **Non ho misurato la cura.** Due candidate, entrambe da provare prima di dichiararle: ordinare per
  numero di token agganciati; oppure far **dire** alla porta «AND zero → ripiego OR su N candidati»,
  che non ripara il ranking ma toglie il silenzio.
