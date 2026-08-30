# 18 — Quante volte scriviamo, per ogni volta che leggiamo

**ws6 · 30/08 ore 13:36** · journal `~/.engram/events.jsonl` + `events.jsonl.1` (**il journal ruota**:
letti entrambi, **35.731 righe**).

> Nasce da una domanda di Aurelio, riportata verbatim perché è il metro: *«si ma sta memoria la state
> usando? state concatenando tutto? sta memoria serve? per cosa la usate?»*

---

## La risposta dipende da chi conti, e i due conti dicono il contrario

| righello | letture | scritture | letture/scritture |
|---|---|---|---|
| **A** — livello **MCP**: le chiamate che facciamo **noi**, dall'esterno | **245** | **140** | **1,75** |
| **B** — livello **flow**: **tutto**, comprese le operazioni interne del prodotto | **3.387** | **10.199** | **0,33** |

· **Righello A**: `audit_tool_call` con un tool di lettura (`facts_search`, `facts_recall`, `recall`,
  `search`, `document_search`, `recall_explain`, `briefing`, `recall_history`, `trust_report`)
  contro `hippo_remember`. È **ciò che fanno le istanze**.
· **Righello B**: `flow.recall` contro `flow.write`. È **ciò che fa la casa**, noi compresi.

🔑 **Fattore 5,3 fra i due.** A dice *«leggiamo quasi il doppio di quanto scriviamo»*; B dice *«si
scrive tre volte più di quanto si legge»*. **Un numero solo, senza dire a che livello è preso,
avrebbe risposto alla domanda di Aurelio in due modi opposti** — ed entrambi sarebbero stati veri.

⇒ La risposta onesta è: **noi la interroghiamo più di quanto la riempiamo; la casa la riempie più
di quanto la interroghi.** La differenza sono le scritture che non partono da noi (consolidamento,
gateway, banchi).

---

## Perché questo conta per il difetto del documento 17

[`17-la-ricerca-ordina-per-data-non-per-pertinenza.md`](17-la-ricerca-ordina-per-data-non-per-pertinenza.md)
misura che la porta di ricerca ordina i candidati per `created_at DESC`, e che **una parola sbagliata
manda un fatto vecchio in posizione 4.965 su 4.972**.

⇒ **Ogni scrittura seppellisce.** Non per un difetto della scrittura: per l'ordinamento della
lettura. **10.199 scritture in dieci giorni** sono la quantità di terra che si posa sopra una
lezione, ed è il motivo aritmetico per cui quella di tre giorni fa non torna su.

Le due cose vanno lette insieme: il ritmo di scrittura non è un problema **finché** la lettura
ordina per pertinenza. Con l'ordinamento per data, **è il ritmo di scrittura a decidere quanto dura
una lezione**.

---

## Cosa NON dico, e perché

· ❌ **Non ho misurato quante query reali finiscono nel ripiego AND→OR**, che era il disegno con cui
  ero partito. **Il journal non registra il testo delle query** — solo `tool`, `outcome`,
  `latency_ms`, `error`. Il disegno cade lì, e non lo sostituisco con una popolazione inventata.
· ⚠️ **`surface` delle scritture**: `unknown` 6.690 · `cli` 2.504 · `gateway` 987 · `sdk` 18. **Lo
  riporto e non lo uso**: è la stessa popolazione mista per cui @ws2 ha ritirato oggi il suo
  «surface unknown 96%» (il journal mescola gli eventi dei banchi con quelli di casa, `_IMPRONTA` in
  `flow_events.py:57` è fissata all'import). Il **confronto fra i due righelli** invece regge, perché
  entrambi leggono lo stesso journal contaminato allo stesso modo.
· 👀 Il 30/08 `recall` (38) supera `search` (21), mentre il 29/08 era il contrario (20 contro 25).
  **È una correlazione e la lascio tale**: ho pubblicato stamattina un post che diceva «usate
  `recall`, non `search`», e non ho modo di separare l'effetto di quel post da qualsiasi altra causa.
· ⏱️ **L'istante è parte del dato**: 30/08 ore 13:36. Il journal cresce mentre lo si legge.
