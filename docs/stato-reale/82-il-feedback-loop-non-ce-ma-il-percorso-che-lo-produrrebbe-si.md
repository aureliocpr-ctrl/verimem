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

⚠️ **Sono `model_claim`, quindi nel recall di default**, e contengono **frammenti
delle proposizioni figlie** (*«Top representative atomi: … | … | …»*). Un recall
può restituirli, e chi legge riceve un aggregato che nessuno ha verificato.
⚠️ **Crescono**: 25 il 30/08, 144 in totale. Il volume è oggi lo 0,8% del corpus.
❌ **Il rischio non è misurato, è strutturale**: se un giorno il consolidamento
generasse **affermazioni** invece di etichette, entrerebbero per la stessa strada
e senza gate. Oggi non lo fa — l'ho verificato su tutte e 144.
⚠️ **Non ho misurato se un recall li restituisca davvero** fra i primi risultati:
serve interrogare la memoria e guardare le posizioni, ed è il passo successivo.
⚠️ **C3 usa una soglia di somiglianza (80%) scelta da me**: un anello chiuso
scritto con parole diverse non lo vedrei.

**Firme su questo documento**: ws6.
