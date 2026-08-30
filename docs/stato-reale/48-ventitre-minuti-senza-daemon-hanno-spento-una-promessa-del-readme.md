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

## ⚠️ Rettifica: su MCP la causa è un'altra, e non è questa

**Segnalato da ws3 dopo la prima versione di questo pezzo, e verificato da me.**
Il blocco che emette l'avviso è preceduto da una ricerca del metodo:

```python
mem = None
for cand in (agent, getattr(agent, "memory", None)):
    if callable(getattr(cand, "_auto_relevance_floor", None)):
        mem = cand
        break
if mem is not None and query:
```

E il metodo, su quegli oggetti, non c'è:

    verimem.agent.VerimemAgent     ha _auto_relevance_floor: False
    verimem.memory.EpisodicMemory  ha _auto_relevance_floor: False
    verimem.client.Memory          ha _auto_relevance_floor: True

`mem` resta `None`, il blocco **non entra mai**, e **`sotto_il_pavimento` non è
mai stato emesso su MCP — da sempre, e indipendentemente dal valore del
pavimento.** Il metodo vive su `Memory` (`client.py`), che su quella porta non
compare.

**Quindi la mia diagnosi qui sotto era sbagliata per la porta MCP**: avevo
attribuito il silenzio al file `floor: 0.0`, e il file lì non c'entra. Il
reperto — «il README promette un campo che non arriva» — resta vero; **la causa
è un difetto di collegamento, non un valore di cache.**

**Ciò che regge, e va tenuto distinto**: il gateway *sì* passa da `Memory`
(`gateway.py:377`, `mem = Memory(db, …)`), quindi lì il file da 32 byte conta
davvero, e la sezione sul gateway più sotto rimane valida.

> **Una promessa, due difetti indipendenti**: su MCP l'avviso non è collegato,
> sul gateway il filtro è disattivato da un valore degenere. Trovarne uno non
> spiegava l'altro, e io avevo usato il secondo per spiegare il primo.

### E la cura è già scritta due volte nello stesso file

Il pezzo che chiude questo l'ha portato **ws2**, e l'ho verificato. Nello stesso
`mcp_server.py`, in altri due punti, il pavimento si ottiene **costruendo**
l'oggetto giusto invece di cercarlo:

```python
from .client import Memory as _MemFloor        # :8161-8162
_mrh = _MemFloor(path=a.semantic.db_path)._auto_relevance_floor()

from .client import Memory as _MemForFloor     # :13830-13832
_mr = _MemForFloor(path=a.semantic.db_path)._auto_relevance_floor()
```

**Non manca il metodo: manca l'oggetto.** E la via corretta è in uso, due volte,
a poche righe di distanza dal blocco che non funziona — con **due alias diversi
per lo stesso import**, che è la classe «una copia invece della superficie
unica» in miniatura.

⚠️ **I numeri di riga di questo documento sono invecchiati in due ore.** Nella
prima stesura avevo scritto `:8139` e `:13778`; le cure di un'altra istanza
hanno spostato il file mentre scrivevo, e ora sono `:8162` e `:13832`. **In un
repo che otto istanze modificano in parallelo, un numero di riga è un
riferimento a scadenza**: quello che regge è il testo da cercare
(`_auto_relevance_floor`, `_MemFloor`), non la posizione. Verificato che il
blocco difettoso (righe 321-336) è **ancora invariato**.

Il codice, sopra quelle righe, **tiene il conto delle proprie ripetizioni**:

    :8105   «…divergono, ed è la quinta generazione di questa stessa cura»
    :8136   «a critic flagged SDK-only three weeks ago,
             min_relevance got wired, ce_gate did not»
    :13776  «racconta la terza ("la cura di un'ora prima non lo raggiungeva");
             questa è la quarta, e per lo stesso identico motivo»

**Terza, quarta, quinta.** Il prodotto sa di ripetere lo stesso difetto, lo
numera nei commenti, e il caso che abbiamo trovato è **un'occorrenza ulteriore
che nessuna di quelle cinque cure ha raggiunto**. È la classe che la nostra
memoria chiama *«una copia invece della superficie unica»*, documentata dal
codice stesso mentre accade. E la riga 8136 aggiunge che perfino la cura
precedente fu parziale: *min_relevance* fu collegato, *ce_gate* no.

**Un mio scivolone, per il registro**: le righe 8139 e 13778 **erano già
nell'output di un mio `git grep` di due ore prima**, in questa stessa indagine.
Le avevo sotto gli occhi e non le ho collegate — ho letto la riga che cercavo e
non quelle accanto.

### E anche questa cura è verificata

Stessa disciplina della prima: provata **su una copia**, chiamando
`_avvisi_di_lettura` due volte — una con un agente come quello che la porta
passa oggi, una con un agente che espone il metodo (cioè che ha costruito un
`Memory`, come le righe 8139 e 13778):

```
pavimento nella copia: 0.8881

OGGI    chiavi del payload: ['trattenuti']
        sotto_il_pavimento ASSENTE

CURATO  chiavi del payload: ['sotto_il_pavimento', 'trattenuti']
        sotto_il_pavimento = {'pavimento': 0.8881, 'score_migliore': 0.844,
          'nota': "nessun risultato supera la soglia di rilevanza calibrata su
          questo corpus: probabilmente la risposta NON e' in memoria.
          I risultati sono qui sotto, non tagliati — decidi tu."}
```

**Con l'oggetto giusto il campo compare**, e contiene esattamente ciò che il
README promette — *floor, best score, and what it means* — con una nota che dice
all'agente la cosa utile: *probabilmente la risposta non è in memoria, e i
risultati non sono stati tagliati*.

**Un incastro che vale da solo**: `score_migliore: 0.844` è **lo stesso
punteggio** che avevo ottenuto due ore prima interrogando la porta MCP vera con
la query su Saturno. La prova alla porta e la prova sul banco si chiudono l'una
sull'altra.

> **Entrambe le cure sono provate**: cancellare il file rimette in funzione il
> filtro del gateway; costruire l'oggetto giusto fa comparire l'avviso su MCP.
> Sono indipendenti, e servono tutte e due.

## Perché non compare (la parte che vale per il gateway)

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
finestra misurata nel documento 39 è esatta e il meccanismo è coerente, ma
l'attribuzione resta un'inferenza, non un'osservazione.)*

**Il meccanismo però è documentato dal prodotto stesso, in un terzo posto.**
Cercando altri file di stato scritti quella sera ho trovato
`~/.engram/consolidate_last.json`, **scritto alle 20:45** — dentro la stessa
finestra:

```json
{"consolidate": {"clusters_detected": 133, "masters_proposed": 11,
                 "masters_persisted": 11, …},
 "heal_err": "encode daemon unavailable and in-process cold-load is disabled
              (HIPPO_ENCODE_DELEGATE_ONLY=1) — call…"}
```

Due cose, entrambe verifiche incrociate di misure fatte con altri righelli:

- **`heal_err` è il messaggio esatto** di `verimem/embedding.py:283`, che il
  documento 38 aveva trovato leggendo il codice. Non è più solo un'ipotesi sul
  perché il calcolo fallisse: **in quella finestra il prodotto riceveva
  davvero quell'eccezione, e l'ha registrata.**
- **`masters_persisted: 11`** — e il documento 39, contando i fatti nello store,
  aveva trovato che il blocco 20:30:10-20:53:20 conteneva «54 fatti: **11
  MASTER** e 43 di lavoro». **Gli undici MASTER sono questo consolidamento**,
  girato mentre l'encoding era rotto.

Tre strade diverse — gli eventi del journal, i fatti nello store, i file di
stato — che si incontrano sulla stessa finestra di ventitré minuti.

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

**Controllato quattro ore dopo, a guasto finito.** `verimem doctor` alle 00:55
del 31/08:

    ✓ daemon  shared encode daemon warm on :61574
    ✓ embedding-model  all 16654 vectors match the engine in use (768d: 16654)

**Il daemon è tornato, i vettori si sono riallineati, e il file è ancora
`{"floor": 0.0, "n_facts": 13795}` con mtime 20:32.** La causa è sparita da ore
e l'effetto no: **il valore degenere non si ripara quando si ripara il guasto
che l'ha prodotto.** È la differenza fra un'interruzione e un danno persistente,
e questo è il secondo.

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
  prodotto ricalcola. **Non l'ho fatto sullo store di Aurelio** — una
  cancellazione non mi è stata chiesta — **ma l'ho verificato su una copia**,
  perché proporre una cura senza provarla è mezzo lavoro:

```
copia dello store in …\ws6-floor-9vd0ttxz\semantic\semantic.db   (129.4 MB)

1) col file presente ({"floor": 0.0, "n_facts": 13795})
   _auto_relevance_floor() -> 0.0

2) file cancellato NELLA COPIA
   _auto_relevance_floor() -> 0.8881
   il file e' stato riscritto: True
   nuovo contenuto: {"floor": 0.8881, "n_facts": 14278}
```

  **La diagnosi è confermata e la cura funziona**: col file presente la funzione
  restituisce `0.0`, senza il file ricalcola **0,8881** e lo ripersiste. Lo
  store di Aurelio è rimasto intatto (`{"floor": 0.0}`, mtime 20:32) — la prova
  è stata fatta interamente su una copia in `tempdir`, con `HIPPO_DATA_DIR`
  impostata **prima** degli import del prodotto.

  > ⚠️ **RETTIFICA IMPORTANTE, dopo un dato di ws2: cancellare il file NON
  > BASTA, e da solo può peggiorare.** ws2 ha misurato le tre popolazioni su
  > domande vere: **dentro dominio 0,840-0,868**, fuori dominio 0,797-0,821,
  > non-parole fino a 0,834. **Il pavimento auto-calibrato (0,8881) sta SOPRA il
  > massimo delle risposte buone.** Cancellando il file, il gateway passerebbe
  > da «non filtra niente» a «**filtra tutto**».
  >
  > E la causa è nella calibrazione stessa: `estimate_relevance_floor` prende il
  > **95° percentile del massimo ottenuto da sonde SCRAMBLATE**
  > (`relevance_floor.py:210`, `probes = scrambled_probes(...)`). ws2 aveva
  > osservato, senza spiegarselo, che **le non-parole punteggiano più alto delle
  > domande vere fuori dominio**: è lo stesso fenomeno — un testo senza
  > argomento è equidistante da tutto, e il coseno gli assegna punteggi medi
  > alti invece di penalizzarlo. **Il pavimento è calibrato su una popolazione
  > che punteggia più alto di quella che deve proteggere.**
  >
  > Questo spiega anche il documento 50 (quattro fatti pertinenti a
  > 0,8388-0,8421, tutti sotto la soglia): non erano un caso sfortunato, stanno
  > dove la misura di ws2 dice che devono stare.
  >
  > **Quindi l'azione non è `rm` e basta: è `rm` più decidere la soglia.**
  > *(Limiti: 15 query di ws2 scelte da lui, il mio 0,8881 da 32 sonde su copia,
  > il documento 50 è un caso singolo. Ipotesi coerente con tre misure
  > indipendenti, non una dimostrazione — e nessuno di noi due propone un
  > valore.)*

  *(Il valore ricalcolato, 0,8881, non coincide con lo 0,8743 del documento 36:
  il corpus è cresciuto nel frattempo. Sono la stessa grandezza a due istanti
  diversi, non due misure in disaccordo.)*
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
- **Il limite che avevo lasciato qui l'ho chiuso subito, e la risposta è
  peggiore**: vedi la sezione seguente.

## Il gateway legge lo stesso file, e lì la promessa è più forte

Avevo lasciato come limite la domanda se anche `gateway/console` — che secondo
il README **filtra** invece di segnalare — leggesse lo stesso pavimento. Si
chiude leggendo tre righe:

- `verimem/gateway.py:461` — `_gateway_min_relevance()` legge
  `ENGRAM_GATEWAY_MIN_RELEVANCE` con **default `"auto"`**;
- `verimem/client.py:1112` — `if min_relevance == "auto": min_relevance =
  self._auto_relevance_floor()`, cioè **lo stesso file**;
- `verimem/client.py:1200` — `if min_relevance and not _degradato:` — e
  **`0.0` è falsy**.

**Quindi il gateway, nella configurazione di default, non filtra nulla.**

E qui la promessa non è «ti do il righello»: il README dice *«gateway/console
FILTER — results under the self-calibrated floor are **not served at all**»*, e
il docstring della funzione è ancora più esplicito:

> *«**Making the enterprise API abstain by default is the point of a TRUST
> product**»*

**Il punto di un prodotto di fiducia, secondo le sue stesse parole, è
disattivato da un file di 32 byte scritto durante un guasto di ventitré
minuti.**

Un file, due porte su tre: su MCP non arriva il righello, sul gateway non
avviene il filtro. La terza — l'SDK — è permissiva per scelta dichiarata, quindi
lì non cambia niente.

---

**Verifica**: README.md righe 180-201; `verimem/mcp_server.py:326-334`;
`verimem/client.py:2455-2519`; `~/.engram/semantic/semantic.db.floor.json`
(mtime 30/08 20:32); conteggi sullo store in `mode=ro`. Nessuna scrittura,
nessun file cancellato.
