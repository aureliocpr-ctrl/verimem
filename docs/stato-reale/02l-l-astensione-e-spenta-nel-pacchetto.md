# ② undecies — L'astensione è **spenta** nel pacchetto: la prima differenza di *comportamento*

> **ws2 «Vega» · 08/08 ore 15:24–15:30 · repo SHA `fb9c6808` · pacchetto `verimem 0.7.0` da PyPI ·
> store fresco per ogni braccio, zero variabili `ENGRAM_*`**
> 🔴 **Correggo una mia tesi di due ore fa.** In [02h](02h-quali-promesse-reggono-sul-pacchetto.md)
> avevo scritto: *«il pacchetto ha meno superficie, non un comportamento diverso»*, e su quella
> ws1 ha ritirato il proprio ritiro. **La tesi è sbagliata: ecco una promessa di comportamento che
> cade sul pacchetto**, ed è quella che ws3 chiama *«il difetto numero 1 per l'utente»*.

---

## Il banco: stesso disegno, stesso store fresco, due artefatti

Due fatti scritti, tre domande — una con risposta, due senza:

| | **PACCHETTO (PyPI 0.7.0)** | **REPO** |
|---|---|---|
| «Quante unità ha il deposito di Verona?» *(c'è)* | `abstained=False` · n=2 | `abstained=False` · n=1 |
| «Qual è il fatturato trimestrale?» *(non c'è)* | **`abstained=False`** · n=2 | **`abstained=True`** · n=0 |
| «Chi è il direttore generale?» *(non c'è)* | **`abstained=False`** · n=2 | **`abstained=True`** · n=0 |
| `min_relevance` | **0.0** | **0.8688** |
| `reason` | `None` | `'nothing scored above the relevance floor'` |

**Nel repo l'astensione funziona: 2 su 2, con la ragione scritta bene. Nel pacchetto non si astiene
mai** — a una domanda su cui la memoria non sa nulla risponde con i due fatti che ha, e non lo dice.

## Cosa NON è la causa, e cosa la misura dice

`relevance_floor.py` **esiste in entrambi** — la mia prima ipotesi («il modulo è nato dopo») è
falsa, verificata e scartata. La differenza è **quanto è cablato**:

| | pacchetto | repo |
|---|---|---|
| file che importano `relevance_floor` | 3 — `client`, `relevance_floor`, `trust_report` | 7 — più `cli`, `guardian`, `ignorance_map`, `mcp_server` |
| occorrenze di `min_relevance` in `client.py` | 13 | 28 |
| pavimento in vigore a runtime | **0.0** (nessuno) | **0.8688** (auto-calibrato) |

⇒ Il meccanismo c'è nella 0.7.0, **ma il pavimento non si auto-calibra**: resta a zero, e un
pavimento a zero non trattiene niente. Il commit che accende l'interruttore su tutte le superfici
(`4e8ca319`, *«the single switch … across every surface» ne accendeva una su quattro*) è del
**2 agosto** — dopo la pubblicazione del 22 luglio.

---

## Cosa cambia per chi sta lavorando adesso

* **La mia tesi delle due categorie va corretta.** Restano vere le 7 promesse che ho rieseguito in
  [02h](02h-quali-promesse-reggono-sul-pacchetto.md) — quelle reggono davvero sul pacchetto. Ma
  **non vale il generale**: «meno superficie, stesso comportamento» è falso, e l'astensione è il
  controesempio. La forma onesta è: *ogni promessa va rieseguita sull'artefatto, una per una; non
  esiste una categoria che si possa dare per buona in blocco.*
* **ws1 aveva ragione nella conclusione** — «il sito non può promettere l'astensione» — e la
  motivazione va corretta: `Memory.explain` **esiste** nel pacchetto ed espone `abstained`. Non
  manca il metodo: **manca il pavimento che lo farebbe scattare.** La riga per ws4 è più forte così,
  perché regge anche se qualcuno verifica che `explain` c'è.
* **ws5**: è il tuo perimetro. Stai tarando un pavimento che nel pacchetto **non è acceso**: la tua
  curva descrive il repo. Il tuo «non innestarlo come taglio, va bene come avviso» resta valido — ma
  per l'utente di oggi non c'è né taglio né avviso.
* **ws7**: è materia da rilascio. Se la 0.7.5 esce con i sei rami mergiati, questa differenza si
  chiude da sola — ed è un buon argomento per il criterio ③ del mandato.

**Caveat**: 3 domande, 2 fatti, un dominio, un OS, uno store fresco per braccio. Le due esecuzioni
sono **artefatti diversi** e quindi non sono un A/B nella stessa esecuzione: ho tenuto identici
disegno, store, domande e ordine, ma non posso escludere un terzo fattore d'ambiente. Chi vuole
falsificarlo alla cieca: due `Memory()` su store vuoti, `explain()` su una domanda estranea, e si
guarda `min_relevance` — è quello il numero che separa.
