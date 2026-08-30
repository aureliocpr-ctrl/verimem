# Sa fare la cosa e non la fa: sette misure, un motivo solo

*ws6/Aldo — 30/08, notte. Sintesi dei documenti 36-46.*

Ho passato la notte a misurare sette parti diverse del prodotto — il pavimento
di rilevanza, la telemetria delle letture, il giudizio dei fatti, il rerank, la
supersessione, le contraddizioni, la quarantena, gli episodi. Erano indagini
indipendenti, aperte per ragioni diverse. **Sono finite tutte sullo stesso
motivo**, e vale la pena nominarlo, perché una classe di difetto ha più valore
di sette difetti.

## Il motivo

> **Il prodotto possiede la capacità, la implementa correttamente, la misura
> anche — e poi non la usa. E nulla, da nessuna parte, segnala che non la sta
> usando.**

Non è incapacità: in ogni caso qui sotto la cosa giusta **è già scritta e
funziona**. Non è nemmeno disonestà: quando il prodotto parla, dice il vero. È
che **una capacità spenta non emette alcun segnale** — non c'è un avviso, un
contatore, una riga di referto che dica *«questa cosa che so fare, adesso non la
sto facendo»*.

## Le cinque istanze

**1. Il pavimento di rilevanza è spento da un default.** (documento 36)
`min_relevance` è esposto, la sua descrizione lo chiama *«the abstention over
hallucination promise»*, e il prodotto sa perfino **calcolarsi la soglia da
solo**: `estimate_relevance_floor` restituisce **0,8743** dopo 32 sonde. Alla
domanda senza risposta i tre fatti serviti stavano a **0,8119 · 0,7796 ·
0,7807** — tutti sotto il rumore che il prodotto stesso ha stimato. Con il
pavimento acceso: `items: []`. **Il default è `None`.**

**2. Il regime degradato è dichiarato a chi legge una risposta e assente dalla
telemetria.** (documento 38)
Ogni item porta `ranking: "keyword"`, e c'è una guardia in `client.py` che
disattiva il pavimento in quel regime perché applicarlo sarebbe un errore di
categoria. Il prodotto **sa** di essere degradato. Ma cercando
`ranking|degraded|rerank|keyword|fusion|timeout` nelle **37.312 righe** del
journal si ottengono **zero occorrenze**, e il punto di emissione della ricerca
— `client.py:1229`, l'**81%** del traffico — non registra né il regime né
l'astensione, mentre gli altri tre punti registrano `abstained`. **Visibile a
chi guarda una risposta, invisibile a chi ne misura mille.**

**3. Il criterio che salverebbe il rilevatore di contraddizioni è già scritto,
altrove.** (documenti 42-44)
`L4.2`, in scrittura, sa dire: *«il claim riusa un numero della fonte
riferendolo a un'altra grandezza: 278 qui è "vettori", nella fonte "do"»*. Il
`numeric_clash`, che ha prodotto **93.263** conflitti irrisolti — di cui il
**93,7%** fra fatti che non parlano della stessa cosa — non fa quel controllo. E
dentro i topic affollati arriva a dichiarare in conflitto il **99,5% di tutte le
coppie possibili**. **Lo stesso prodotto, lo stesso criterio, applicato da una
parte e non dall'altra.**

**4. Il campo che dice chi ha messo un fatto in quarantena esiste, e un quinto
delle volte resta vuoto.** (documento 45)
`quarantined_by` è nato ad agosto e funziona. Ma **207 quarantinati di agosto su
912 — il 22,7% — non lo valorizzano**: un fatto su cinque viene messo da parte
senza che si sappia quale controllo l'abbia deciso.

**5. La salience degli episodi è calcolata, discrimina, e non ha un
consumatore.** (documento 46)
Su **470** episodi la salience media è **0,248** per quelli mai serviti e
**0,449** per quelli serviti: **funziona**. Gli invalidati sono **zero**.
L'oblio esiste come comando (`decay_run`) e non risulta mai eseguito.

## Un controesempio, che è la parte più importante

Se il motivo fosse una lente, dovrebbe deformare anche ciò che va bene. Il
documento 40 è lì per mostrare che non lo fa.

Il cross-encoder **non entra mai** sulle query reali: sulle 120 del banco del
prodotto, in italiano fluente, **120 su 120 superano la soglia** di 10 parole e
il rerank viene saltato. Sembra la sesta istanza dello stesso difetto. **Non lo
è**: il docstring di `_rerank_mode` documenta perché — sul traffico reale
l'effetto aggregato è nullo (ΔMRR **+0,0078**, p=**0,716**) perché due effetti
reali si annullano, le query corte guadagnano **+0,146 MRR** e le lunghe perdono
**0,080**; la soglia regge allo split-half; l'always-ON costa **+2067 ms su ogni
query**. **È una capacità disattivata di proposito, con i numeri in mano.**

La differenza fra il caso 40 e gli altri cinque non è che lì la cosa è accesa:
**è che lì qualcuno ha misurato, deciso, e scritto perché.** Negli altri cinque
non c'è una decisione documentata — c'è un default, un campo non valorizzato, un
comando che nessuno lancia.

## Il prodotto non è cieco, e va detto

Sarebbe scorretto concludere che il prodotto non si guardi. `verimem doctor`
segnala da solo il daemon di encoding assente (con la cura), il topic-crowding,
i vettori che non combaciano; la ricevuta di `verimem save` dice *che* è
degradato, *perché*, *cosa comporta* e *quale strumento lo verifica*. Molta
dell'onestà che questa serie ha usato per misurare **viene dal prodotto stesso**.

Ma lo stesso referto, in fondo, consiglia una cura — *«normalise those
statuses»* — che renderebbe ritirabili automaticamente **998 fatti** in
contraddizioni che al **93,7%** non sono contraddizioni (documento 42). **Il
presidio vede molto, e non è calibrato su quanto valgano le cose che vede.**

## Cosa costa questa classe, in concreto

Un difetto che non emette segnale non viene trovato dall'uso: viene trovato solo
da qualcuno che va a cercarlo. È il motivo per cui queste cose sono lì da mesi
senza che nessuno se ne lamenti — **non danno fastidio, non rompono niente, e
non producono un errore da leggere**. Il prodotto sembra funzionare, e funziona;
semplicemente non fa una parte di quello che sa fare.

Per un rilascio, la domanda che ne discende è precisa: **quante delle capacità
che dichiariamo sono accese nel default con cui la gente le userà?** Nessuno dei
cinque casi qui sopra si vedrebbe leggendo il README.

## E i miei sbagli, perché il resto sia credibile

Questa notte ho commesso **nove errori di misura**, tutti documentati nei pezzi
in cui sono avvenuti. Li elenco insieme perché sono la parte che rende leggibile
il resto: chi legge deve sapere quanto spesso il misuratore sbaglia.

1. Ho letto un **campo assente come valore zero**, e ho contato 279 degradati
   inesistenti.
2. Ho tenuto una popolazione estranea nel **denominatore** (3.120 invece di
   2.841).
3. Ho «falsificato» il cold start con un **proxy che non misurava la variabile**
   (lo span degli eventi al posto dell'età del processo).
4. Ho **ripetuto una riga del referto senza aprire il codice**, e ho dovuto
   rettificare pubblicamente un consiglio già dato a sette istanze.
5. Ho misurato **dopo l'auto-riparazione** e stavo per accusare il prodotto di
   mentire su una promessa che invece aveva mantenuto.
6. Ho confrontato **918 coppie contro un perimetro storico di 321**, e per un
   momento «migliorato» sembrava «peggiorato».
7. Ho separato due popolazioni **fra i gruppi e non dentro i gruppi** (54
   invece di 43), cinque minuti dopo aver denunciato quella stessa svista.
8. Ho classificato con un **criterio sintattico un fenomeno semantico**: ha
   riconosciuto 8 coppie su 2.919.
9. Ho confrontato due conteggi **in fusi orari diversi** (locale contro UTC) e
   ho preso la differenza per un'anomalia dei dati.

**Otto su nove erano nel misuratore, non nel prodotto.** E in tre casi il
prodotto aveva ragione e io torto: la ricevuta che sembrava mentire, la
falsificazione del cold start, e L4.1 che mi respingeva un claim per un'ora che
la mia source non conteneva.

## Per chi riprende

- **La cura non è cinque cure**: è un posto dove un'inerzia si veda. Un referto
  che elenchi le capacità disponibili e il loro stato — `min_relevance: off`,
  `decay_run: mai eseguito`, `quarantined_by: valorizzato nel 77% dei casi` —
  renderebbe visibile in venti secondi ciò che a me è costato una notte.
- **Niente di tutto questo l'ho applicato**: sono default e codice del gate, e
  il gate non si tocca senza mandato.
- I righelli sono in `docs/stato-reale/banchi/`, tutti in sola lettura, tutti
  eseguibili da soli.

---

**Verifica**: questo documento non introduce misure proprie. Ogni numero citato
è verificato nel documento indicato, con il suo istante e il suo righello.
