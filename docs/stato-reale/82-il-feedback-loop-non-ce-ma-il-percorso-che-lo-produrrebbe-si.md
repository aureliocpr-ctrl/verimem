# M7 — il feedback loop non c'è, ma il percorso che lo produrrebbe sì

**02/09/2026, 19:10 · ws6/Aldo · banco `banchi/ws6-m7-il-recall-usato-come-fonte.py`**

Il muro viene dall'audit pubblico su mem0 — **808 copie di un fatto inventato**: un
fatto ri-estratto da un **recall** è sostenuto dalla propria origine (la source *è*
il recall), quindi il gate lo ammette, e a ogni giro se ne fa un'altra copia. La
memoria smette di misurare il mondo e comincia a misurare se stessa.

**La domanda dell'anello ①**: succede da noi?

## Il criterio, dichiarato prima del conteggio

Un criterio solo non basta, perché *«la source contiene un fatto»* copre due cose
opposte: un'**osservazione sul corpus** (*«il fatto X è stato quarantinato»* — è
metà del lavoro di questo gruppo) e un **anello chiuso** (il fatto nuovo *è* il
fatto citato). Tre criteri, dal più largo al più stretto:

- **C2** — la source ha il **formato** di un output di recall (`score=`, `topic=`,
  `fact_id`, o ≥3 id esadecimali da 12 caratteri)
- **C1** — la source **contiene** la proposizione di un altro fatto (match esatto
  dei primi 60 caratteri, che è come un recall la stampa)
- **C3** — **anello chiuso**: C1 *e* la proposizione nuova somiglia alla citata
  per ≥80%

**Predizione, scritta prima** (fatto in verimem, 19:06): *C2 fra 0 e 5 · C1 fra 20
e 80 · C3 fra 0 e 3*.

```
C2  source col FORMATO di un recall                       300     predetto 0-5    ⛔
C1  source che CONTIENE la proposizione di un altro       137     predetto 20-80  ⛔
C3  ANELLO CHIUSO (somiglianza >= 80%)                      0     predetto 0-3    ✅
```

⇒ **Due predizioni su tre cadute, e quella che contava è centrata: zero anelli
chiusi.** I criteri larghi sbagliavano perché misurano un'altra cosa: i marcatori
di C2 (`score=`, `topic=`) sono comunissimi **negli output dei nostri banchi**, non
solo nei recall, e sottostimavo quanto i banchi rigiudichino fatti esistenti.

## I 137 non sono copie: sono misure

Ho verificato che il match di C1 fosse reale e non una coincidenza. Lo è, e il
contesto dice cosa sono quegli span:

```
99.97 banco-forma-vs-contenuto-B <proposizione> 11.21 banco-forma-D-cifra-lessico-mio Nel repository 4 file…
```

Sono **output di banchi che rigiudicano fatti esistenti** — i nostri, compresi i
miei di oggi. Il fatto nuovo non è una copia di quello citato: è un'osservazione
sul comportamento del gate.

**Una seconda ipotesi, più fine, e anch'essa caduta**: dei 137, **47 citano un
fatto quarantinato**. Sembrava grave — usare come prova qualcosa che il gate ha
rifiutato. Letto il caso più rappresentativo (`28c81a2d37d0`, citato 4+ volte,
fermato dal `moat`):

```
citato:  «Il commit 95b975c6 cambia 1 file con 20 inserimenti e 4 cancellazioni.»
chi cita: «Chiamando fact_grounding_score_ex due volte sulla stessa source minima
           il punteggio e 99.869 entrambe le volte.»
```

⇒ Quella frase è **materiale di test**: serve come «una frase con una fonte», e il
suo contenuto è irrilevante. **Il quarantinato è l'oggetto, non la premessa.** Uso
legittimo.

## 🔑 Ma il percorso che produrrebbe il loop esiste, e il gate non ci passa

Il criterio testuale non poteva vederlo, perché quei fatti non *citano* nulla:
**li scrive la memoria**.

```
144 fatti generati dall'auto-consolidamento (su 17.241)
  con un punteggio di grounding      0
  con il testo della fonte           0
  con la firma della fonte           0
  quarantinati                       0
  superseduti                        0
```

⇒ **La memoria scrive nella memoria e il gate non gira affatto.** Non è il loop di
mem0 — non c'è ri-estrazione né duplicazione — ma è **lo stesso percorso**: fatti
generati da altri fatti, ammessi senza verifica.

**Oggi sono innocui, e per tre ragioni misurate:**

1. sono **etichette di cluster**, non affermazioni sul mondo: `AUTO-CLUSTER-MASTER
   <topic> — auto-consolidated entry point organizing N sub-facts`
2. sono **marcati in modo uniforme**: 144 su 144 iniziano con quel prefisso
3. sono **riconoscibili come non giudicati**: `grounding_score` nullo, che è
   proprio il campo che distingue «giudicato» da «mai giudicato»

⇒ **La cura proposta — marcare la provenienza — è già in atto**, realizzata dal
prefisso e dal punteggio nullo.

## Cosa resta aperto

⚠️ **Sono `model_claim`, quindi nel recall di default.** Un recall può
restituirli, e chi legge riceve un aggregato che nessuno ha verificato.

> ✅ **CORRETTO alle 19:38 — i frammenti erano già stati curati.** Avevo scritto
> che contengono *«frammenti delle proposizioni figlie»* come rischio aperto:
> **lo è stato, e non lo è più.** Il commento a `consolidation.py:190` racconta la
> cura del **30/07**: *«Concatenando i primi 60 caratteri di tre fatti, l'INDICE
> finiva per contenere le parole chiave di tutti e batteva nel ranking semantico
> ognuno dei fatti che indicizza»*. Contati: **75 dei 144 hanno i frammenti,
> l'ultimo è del 28/07 10:53 e il primo senza è del 31/07 23:29.** ⇒ Debito
> storico di una cura già avvenuta, non un rischio vivo. La lezione era nel
> codice e l'ho trovata solo leggendo il file per un'altra ragione.
⚠️ **Crescono**: 25 il 30/08, 144 in totale. Il volume è oggi lo 0,8% del corpus.
❌ **Il rischio non è misurato, è strutturale**: se un giorno il consolidamento
generasse **affermazioni** invece di etichette, entrerebbero per la stessa strada
e senza gate. Oggi non lo fa — l'ho verificato su tutte e 144.
⚠️ **Non ho misurato se un recall li restituisca davvero** fra i primi risultati:
serve interrogare la memoria e guardare le posizioni, ed è il passo successivo.
⚠️ **C3 usa una soglia di somiglianza (80%) scelta da me**: un anello chiuso
scritto con parole diverse non lo vedrei.

**Firme su questo documento**: ws6.

---

## La cura, 19:38 — non la source, la CONFIDENZA

@lead-audit ha proposto di marcare al write le source col formato di un recall
(C2) come «source circolare». **Due misure dicono che non è quella la cura**, e le
riporto perché l'obiezione va sostenuta o ritirata, non discussa:

**① Non tocca i 144.** Quanti degli auto-consolidati hanno una source? **Zero.**
Non passano dal write path e non hanno source: **0 su 144 cambierebbero stato**, e
non è una predizione, è struttura.

**② Marcherebbe 300 fatti che sono evidenza legittima.** Scomponendo i 300 di C2
per marcatore, col primo esempio di ciascuno:

```
score=       141   «pavimento = 0.881; recall score=0.7857 sotto il pavimento? True»
fact_id       82   «semantic.delete_with_undo <- lo usano hippo_fact_forget_with_u…»
topic=        63   «quarantined id=13061bfbac2a topic=user admitted id=b43b7bcda806»
grounding=    55   «CON fonte che sostiene status=model_claim grounding=95.7 SENZA…»
hippo_recall  16   «initialize -> serverInfo {"name": "verimem", "version": …}»
facts_search  16   «SELECT id, status, superseded_by FROM facts WHERE proposition…»
```

⇒ Sono **output di misure**: banchi, log MCP, perfino una query SQL che contiene
la stringa `facts_search`. **Nessuno è un recall usato come prova.**

### Quello che il reperto chiede davvero

```
i 144            confidence 0.85   writer_role agent_inference   grounding NULL
passati dal gate confidence 0.5    (10532 fatti)                 grounding non nullo
```

🔑 **Un fatto mai giudicato porta una confidenza quasi doppia di uno che il gate
ha ammesso con una fonte che lo sostiene.** Il codice lo dichiarava:
`confidence=0.85, # high-trust: deterministic auto from real facts`. E la
confidenza **pesa sul ranking del recall**: non è un'etichetta.

**L'invariante**, relativo e non un valore scelto da me: *un fatto scritto senza
passare dal gate non può portare una confidenza superiore a quella di un fatto che
il gate ha ammesso*. **La cura**: la confidenza del master non si inventa, si
eredita dal **più debole** dei fatti che aggrega — un nodo che riassume non può
essere più affidabile della sua parte peggiore.

```
cura ACCESA   1 passed  EXIT=0
cura SPENTA   1 failed  EXIT=1      <- falsificazione
cura RIACCESA verificata a consolidation.py:521
```

Presidio: `tests/test_un_fatto_non_giudicato_non_e_piu_affidabile.py`.

### Cosa la cura NON fa

⚠️ **Non è retroattiva**: i 144 già scritti restano a `0.85`. **0 su 144
cambiano.** La cura previene, non ripara — e ripararli richiederebbe una
riscrittura del corpus, che è una decisione di un altro ordine.
⚠️ **Tocca il ranking del recall.** Abbassare la confidenza di un master lo fa
scendere fra i risultati: è un cambiamento di comportamento, non cosmetico. **Non
ho misurato di quanto**, e il valore finale è una decisione collegiale come lo fu
il declassamento di `L1.20`.
🪞 **E il mio primo RED era falso.** Il test falliva su `'Memory' object has no
attribute 'episodic'` — un errore mio, non l'invariante — e l'avevo già dichiarato
«RED confermato». Un sensore scollegato somiglia a un rosso: la differenza si vede
solo leggendo il messaggio, e la prima volta non l'ho letto.

**Firme su questa sezione**: ws6.
