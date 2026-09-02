# Blocco vetrina 0.8.0 — il trade-off in copertina

**Stato**: PROPOSTA di ws7, pronta da incollare. **Non l'ho messa nel README**:
il README pubblicato descrive la 0.7.x e questi numeri sono per la 0.8.0.
Chi tiene il rilascio decide se e quando.

**Perché esiste**: direttiva @lead-audit del 01/09 23:57, mandato di Aurelio
«valore REALE, basta fuffa». Due reviewer convergono: *pubblicare il trade-off
è più credibile di ogni slogan*.

---

## Il blocco (EN, pronto da incollare)

> ### What it costs
>
> A gate that keeps falsehoods out also rejects true things. We publish both
> numbers, because one without the other is advertising.
>
> On **TruthfulQA held-out, 600 claims** (300 true + 300 false), through the
> full write gate, no external API:
>
> | | verimem | the same corpus, no filter |
> |---|---|---|
> | of what is **served**, false | **15.9%** (40/252) | **50.0%** (300/600) |
> | **true** claims rejected | **29.3%** — 95% CI [24.5, 34.7] | 0% |
> | false claims admitted | **13.3%** — 95% CI [9.9, 17.6] | 100% |
>
> **Read the two columns together.** We serve roughly **one third** of the
> falsehood an unfiltered store would serve, and we pay for it by refusing
> **about three true claims in ten**.
>
> ⚠️ **The right-hand column is not a competitor benchmark.** It is what any
> store that does not filter on write serves *by construction* — a difference
> in **promise**, not a measured win in engineering. We have not run a
> head-to-head against another product on this population, and we will not
> describe this as beating one.
>
> **What the numbers do not say**: this is one English public dataset; short
> factual claims, not conversation. A different distribution moves both
> figures — on an Italian corpus whose sources are terminal output the same
> gate rejects about **19%** of what is already stored. And we do not fully
> know *why* we lose 29.3%: the entailment moat is the first decider in
> **73 of 88** cases, but a lexical layer had already flagged **68 of those
> 73** — so «fix the moat» would not recover most of them.
>
> Reproduce: `python benchmark/c10_falsita_servite_vs_mem0.py --popolazione
> truthfulqa --n 300` (~70 min, Wilson CIs printed by the bench).

---

## Le tre decisioni che ho preso scrivendolo, e il perché

**① Il 50,0% NON è scritto come confronto competitivo.** L'ordine diceva «+ il
confronto 50,0%», ma `LANT-91` lo dichiara: quel numero è ciò che un sistema
senza filtro serve **per costruzione** (`infer=False` non filtra) ⇒ **è una
differenza di promessa, non di ingegneria**, e scriverla come «tre volte meglio
di X» sarebbe **esattamente la figura che quel numero serve a contare**. Nella
tabella la colonna si chiama *«the same corpus, no filter»* e ha sotto
un'avvertenza esplicita.

**② La coppia è nella STESSA tabella, non in due sezioni.** «Inseparabile»
significa che non si può citare una riga senza vedere l'altra: due paragrafi
distanti si scindono al primo copia-incolla.

**③ Ho aggiunto due cose che l'ordine non chiedeva**, perché senza il blocco è
citabile male:
- **il numero italiano (~18%)**, altrimenti un lettore trasferisce il 29,3% a
  una distribuzione che non l'ha prodotto;
- **il 73/88 e il 68/73**, perché «29,3% di veri persi» invita a concludere
  «curate il moat» — e la misura dice che non basterebbe.

---

## Cosa NON ho verificato, e chi deve

- **Il 13,3% e il 15,9% vengono dallo stesso run** di `LANT-109`; il **50,0%**
  è il criterio cieco dello stesso banco. **Non ho rieseguito niente stanotte**:
  cito la cella, che porta gli IC di Wilson stampati dal banco.
- ✅ **CORRETTO il 02/09 alle 01:04**: il **~18% italiano** di `W7-89` (@ws4) è
  **una media APPAIATA** — il banco tratta le due classi 50/50, ma nel corpus
  pesano **1,74%** e **98,26%** ⇒ la stima **pesata** è **19,27%**, non 18,42%.
  **Nel blocco ora c'è «about 19%».** ⚠️ **Lo scarto è 0,85 punti e non cambia
  il messaggio** («circa un fatto su cinque»), **ma cambia la NATURA del
  numero**: 18,4% è la media di un disegno costruito per confrontare due
  classi, non una stima di popolazione — e il punto del mattino l'aveva già
  citata in buona fede come se lo fosse. ⇒ **Un campione dichiarato non basta:
  va dichiarato anche l'USO per cui la media è valida.**
- **Il claim «one third»**: 15,9 contro 50,0 è **0,318** ⇒ «roughly one third»
  regge, ma è un rapporto fra una proporzione **con** intervallo e una **per
  costruzione**: non ha un IC e non va presentato come se ce l'avesse.
