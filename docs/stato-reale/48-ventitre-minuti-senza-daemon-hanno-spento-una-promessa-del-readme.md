# Ventitré minuti senza daemon hanno spento una promessa del README, e resterà spenta

*ws6/Aldo — 30/08, notte. Perimetro: archivio, memoria, corpus, recall.*

Questo pezzo lega tutto quello che ho misurato stanotte, e finisce su un file da
32 byte.

## La promessa

Il README, alla voce **Abstention by design**, distingue le porte — ed è
preciso, molto più preciso di come l'avevo riassunto io nel documento 36:

> *«**gateway/console FILTER** — results under the self-calibrated floor are not
> served at all; **MCP SERVES the results and flags them** — **every read carries
> `sotto_il_pavimento`** (floor, best score, and what it means) **so the agent
> has the yardstick**, plus `trattenuti` when the gate withheld facts on that
> topic; **the embedded SDK** … is left permissive by default … one switch
> away.»*

**Va detto subito, perché corregge me**: nel documento 36 avevo scritto che la
promessa di astensione è «spenta di default». Il README **lo dichiara**, per
l'SDK, e spiega perché (un archivio nuovo e quasi vuoto si asterrebbe troppo).
Su quel punto la vetrina è onesta e il mio pezzo era ingeneroso.

La promessa che riguarda la porta MCP è un'altra, ed è precisa: **ogni lettura
porta il righello**.

## Non lo porta

In tutte le letture che ho fatto stanotte dalla porta MCP, il payload contiene
`ranking`, `trattenuti`, `min_relevance`, `items` — e **mai** `sotto_il_pavimento`.
Una prova diretta, fatta apposta con una domanda senza risposta possibile:

    query: "come si compra un biglietto ferroviario per Saturno"
    ranking: {rerank: timeout_cold, fusion: applied}      ← non degradato
    items: score 0.8440 · 0.8100 · 0.7804

I tre fatti serviti parlano di Cline e Goose, e di un job CI chiamato
`saturno-latest` che combacia per omonimia. **È il caso esatto per cui il
pavimento esiste.** Il pavimento vale **0,8743** (misurato nel documento 36
chiamando `estimate_relevance_floor`): **0,8440 < 0,8743**, quindi l'avviso
sarebbe dovuto comparire.

## Perché non compare

Il codice che lo emette è in `verimem/mcp_server.py:326-334`:

```python
pav = float(mem._auto_relevance_floor() or 0.0)
hits = mem.semantic.recall(query, k=3) if pav else []
…
if pav and hits and best < pav:
    out["sotto_il_pavimento"] = {…}
```

Con `pav = 0` la condizione è **sempre falsa**. E il pavimento è **persistito in
un file**:

    ~/.engram/semantic/semantic.db.floor.json
    {"floor": 0.0, "n_facts": 13795}

**Il valore salvato è zero.**

## E qui il cerchio si chiude

Quel file è stato scritto **oggi alle 20:32**.

Il documento 39 misura, in modo indipendente e con un altro righello, che
**dalle 20:30:10 alle 20:53:20 l'encode daemon era assente**: 43 fatti di lavoro
sono entrati senza giudizio, e `verimem doctor` alle 20:53 riportava
`no encode daemon is running`.

**Il pavimento si stima con 32 sonde giudicate dal cross-encoder.** Senza daemon
quelle sonde non hanno un vettore. La stima ha prodotto **0,0** — che non è un
pavimento basso, è **il segno che il calcolo non è potuto avvenire** — e quel
risultato è stato **scritto su disco come se fosse una stima valida**.

*(Quello che non posso provare direttamente: chi abbia chiamato la funzione alle
20:32. Non ho un log di quella chiamata. La coincidenza temporale con la
finestra misurata nel documento 39 è esatta e il meccanismo è coerente, ma lo
dichiaro come inferenza, non come osservazione.)*

## E resterà spento

La cache si invalida su una condizione sola (`client.py:2500`):

```python
if abs(n - n_salvato) <= max(1, n_salvato) * self._FLOOR_DRIFT:
    return salvato
```

`_FLOOR_DRIFT = 0.05`, e `n` è `semantic.count()`, cioè i fatti non quarantinati.

| | |
|---|---|
| salvato nel file | 13.795 |
| non quarantinati oggi | **13.888** |
| differenza | **93** |
| soglia per ricalcolare | **689,8** |

**Mancano quasi seicento fatti** prima che il prodotto si accorga di dover
rifare il conto. Fino ad allora serve `0.0`, e `sotto_il_pavimento` non può
comparire in nessuna lettura MCP.

> **La condizione di invalidazione guarda quanti fatti ci sono, non se il valore
> salvato abbia senso.** Un `0.0` è indistinguibile, per quella riga, da una
> stima legittima.

## Il difetto in una frase

**Un guasto transitorio di ventitré minuti si è cristallizzato in un file, e ha
disattivato una promessa del README per un tempo che dipende da quanti fatti
scriveremo.**

Nessuno se ne è accorto perché — ed è la classe che il documento 47 nomina —
**una capacità spenta non emette segnale**. Il payload non dice «il pavimento
non è calcolabile»: semplicemente non contiene il campo, e l'assenza di un campo
non è un errore che qualcuno legga.

C'è anche una conferma che il difetto è isolato e non generale: `sotto_il_pavimento`
e `trattenuti` sono stati aggiunti **insieme**, l'8 agosto, e il commento nel
codice dice che furono messi in **due `try` separati** proprio perché *«un
guasto nel primo spegnerebbe silenziosamente il secondo»*. **Quella precauzione
ha funzionato**: `trattenuti` compare in ogni mia lettura. Ma nessuno controlla
che l'altro parli.

*(Nota personale: la funzione che emette questi avvisi, `_avvisi_di_lettura`, è
la stessa che ho curato io il 30/08 aggiungendoci il campo `ricerca`. Il campo
che ho aggiunto funziona; quello accanto è muto, e non me n'ero accorto fino a
stanotte.)*

## Cosa proporrei, e cosa non ho fatto

- **Rifiutare di persistere una stima degenere.** `estimate_relevance_floor` che
  restituisce `0.0` su un corpus di quattordicimila fatti non è un risultato: è
  un fallimento. Non scriverlo, o scriverlo con un marcatore che la lettura
  distingua.
- **Invalidare anche sul valore, non solo sul conteggio.**
- **Il rimedio immediato è cancellare quel file**: alla prima lettura il
  prodotto ricalcola. **Non l'ho fatto** — è lo store di Aurelio e una
  cancellazione non mi è stata chiesta.
- Niente di tutto questo è codice che posso toccare: sta nel percorso del gate.

## Per chi riprende

```bash
cat ~/.engram/semantic/semantic.db.floor.json     # {"floor": 0.0, …}
python -c "from verimem.relevance_floor import estimate_relevance_floor; \
           from verimem.semantic import SemanticMemory as S; \
           print(estimate_relevance_floor(S()))"   # il valore vero, ~0.87
```

- **Da controllare su ogni installazione**, non solo qui: se il pavimento è
  stato calcolato una volta sola in un momento sfortunato, il file resta zero e
  nessuno lo vede.
- **Quello che non ho misurato**: se anche `gateway/console` — che secondo il
  README **filtra** invece di segnalare — legga lo stesso file. Se lo legge, con
  `floor = 0.0` non filtra niente, e lì la promessa è ancora più forte.

---

**Verifica**: README.md righe 180-201; `verimem/mcp_server.py:326-334`;
`verimem/client.py:2455-2519`; `~/.engram/semantic/semantic.db.floor.json`
(mtime 30/08 20:32); conteggi sullo store in `mode=ro`. Nessuna scrittura,
nessun file cancellato.
