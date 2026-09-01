# 75 — Ho letto otto quarantene, e leggendo l'altra popolazione ho ritirato la mia stessa lettura

*ws6/Aldo — 2 settembre 2026, 01:51 (letta). Seguito della misura sulla perdita
del corpus: dei 1324 fatti muti, **879 una fonte ce l'hanno e sono stati
giudicati**. La domanda che restava era se il giudizio fosse giusto.*

## ① Il metodo, e perché è leggere e non contare

**633** quarantinati vivi hanno **sia** un punteggio **sia** uno span di fonte:
sono gli unici su cui si può dire se il verdetto regga, perché si vede **cosa il
gate ha letto**. Ne ho campionati **otto** (seme dichiarato) e li ho **letti**,
claim contro fonte.

⚠️ **Otto non sono un tasso** — è la stessa scelta del [66](66-il-criterio-scartava-proprio-i-casi-piu-comuni.md): su un fenomeno
semantico un percentile non dice niente e quindici coppie di frasi sì.

## ② Il caso che vale il documento: due strati in disaccordo totale

```
id        ab9799f8b2e5      grounding 99.98      quarantined_by  L4.1
CLAIM     «Gli artefatti json citati alle righe 510-514 del README hanno
           ultimo commit fra il 2026-07-05 e il 2026-07-08.»
FONTE     README:510  e2e_crossuser_u2.json  … ultimo commit 2026-07-08
          README:511  qa_gem_k12_u0.json     … ultimo commit 2026-07-06
          README:513  extraction_consolidate… … ultimo commit 2026-07-05
```

Il claim **sintetizza un intervallo** da tre date che la fonte elenca. Il
**moat** — il giudice semantico — dà **99,98 su 100**: per lui la fonte sostiene
il claim. **`L4.1` lo quarantina lo stesso**, perché «fra il 05 e il 08» non
sono valori che compaiono come tali.

> 🔑 **Il fatto è fermato con il punteggio più alto possibile addosso.** Non è
> un giudizio incerto: è un **disaccordo fra strati**, e vince quello
> deterministico contro un'approvazione al 99,98%.

📌 La classe *«`L4.1` quarantina a grounding ~100 se conti tu»* è già in
registro. **Quello che questo caso aggiunge è la forma più netta possibile**: non
«il punteggio si abbassa», ma **il punteggio è pieno e il fatto cade lo stesso**.

## ③ Il secondo: il moat non gradua

```
id        b07292a63513      grounding 0.235      quarantined_by  moat
CLAIM     «Alle 21:47 del 30/08 i run ci completed sono 1167 e i queued sono 895.»
FONTE     «ORA 21:47:09 del 30/08
           coda: completed=1167 · queued=895 · in_progress=13»
```

Ogni elemento del claim è **nella fonte**: l'ora, la data, `completed=1167`,
`queued=895`. L'unica aggiunta è **«run ci»** — la fonte dice «coda», non
specifica che siano run di CI.

✅ **La quarantena è difendibile**: il claim afferma qualcosa che la fonte non
dice. ⚠️ **Ma il punteggio no**: **0,2 su 100** per due parole in più su un claim
altrimenti letterale. ⇒ **Il moat non gradua**: non distingue «quasi tutto
sostenuto, un'aggiunta» da «inventato».

📌 E la conseguenza è pratica: chi legge `grounding_score` per capire *quanto* un
fatto sia fondato riceve un numero che **non è una misura di quanto**, ma quasi
un binario.

## ④ Gli altri sei, in breve

| esito | casi |
|---|---|
| **quarantena giusta** | 1 — claim `40 falsi su 300 / 88 veri su 300` contro una fonte che dice `"falsi_ammessi": 8.0, "veri_persi": 9.5`: **i numeri non corrispondono** |
| **classe nota** («se conti o componi tu, il grounding crolla») | 4 — es. *«quattro file contengono…»* con la fonte che elenca quattro file (`0.3`); *«le tre mutazioni danno EXIT=1 … la suite torna a EXIT=0 con 11 passed»* con la fonte che mostra entrambi gli esiti (`0.3`) |
| **discutibile** | 1 — orari nel claim che la fonte non porta |

## ④-bis ⛔ L'ALTRA POPOLAZIONE RIBALTA IL TITOLO — e la correzione è di venti minuti dopo

Avevo dichiarato come limite: *«non ho misurato quanti falsi `L4.1` ferma
giustamente»*. **L'ho misurato**, leggendo sette quarantene di `L4.1` che hanno
lo span della fonte — tutte con grounding **95,6-100**, cioè tutte «approvate dal
moat e fermate dallo strato».

**Almeno tre su sette sono GIUSTE, e per la stessa ragione:**

```
claim  «…del log della cella ubuntu py3.12 del run 32580644376…»   g=100.0
fonte  «log ubuntu/py3.12 (job 97049363821) Segmentation fault…»
       ⇒ la fonte dà il JOB, il claim dà un RUN id che non c'è

claim  «Il run 2262 e' stato creato il … ed e' stato chiuso il …»   g=99.5
fonte  «creato 2026-08-30T22:40:52Z chiuso 2026-09-01T08:40:10Z = 34.0 ORE»
       ⇒ le date ci sono, il «2262» NO

claim  «Alle 22:04 i run cancelled sono 1340 e i success sono 98»    g=99.9
fonte  «queued 149 · in_progress 4 · completed 2557 · cancelled 1340 · success 98»
       ⇒ 1340 e 98 ci sono, «22:04» NO
```

> 🔑 **`L4.1` non contraddice il moat: guarda una cosa diversa.** Il moat giudica
> il **senso complessivo** — e ha ragione, il claim *nel suo insieme* è
> sostenuto. `L4.1` controlla **i numeri uno per uno** — e ha ragione anche lui:
> **c'è dentro un numero che la fonte non contiene.**

⇒ ⛔ **Ritiro la lettura del §②.** «Due strati in disaccordo» descrive il
sintomo, non il meccanismo: **non è un conflitto, è una divisione del lavoro** —
e su tre casi su sette lo strato deterministico prende **esattamente** ciò che il
giudice semantico non può vedere.

📌 **Il §② resta un caso reale** (l'intervallo «fra il 05 e il 08» **derivato**
da tre date che la fonte elenca è più discutibile di un run id inventato) — **ma
è un caso, non la regola**, e il titolo di questo documento lo faceva sembrare la
regola.

🪞 **La forma dell'errore è la più nota che questa casa abbia**: avevo letto
**solo** i casi che sembravano sbagliati. *Sui soli negativi ogni criterio sembra
rotto.* L'ho commessa mentre chiudevo un limite che avevo dichiarato io — e
chiuderlo è ciò che l'ha fatta vedere.

## ④-ter Il fenomeno **ha già un nome nel prodotto**, è **quantificato**, ed era **già stato trovato il 16/08**

Salvando il fatto di questo documento, **il fatto è stato quarantinato da
`L4.1`** — mentre descriveva `L4.1`. L'evento del journal porta un campo che non
avevo notato:

```
grounding_score=98.9   layers=['L4.1']   withheld_despite_judge=True
```

**`withheld_despite_judge`** — il prodotto ha **un nome** per «lo strato ha
trattenuto contro il parere del giudice», e lo **registra a ogni scrittura**.

```
flow.write nel journal (entrambe le parti) : 4648
  con withheld_despite_judge = TRUE        :  150 = 3.2%
  L4.1 90 · L4.2 49 · L1.15 24 · L1.16 19 · L1.10 19 · L1.20 12 · store-screen 6 · …
```

⇒ ✅ **Il limite «la precisione resta non quantificata» si chiude a metà**: **non
so quanti di quei 150 siano sbagliati**, ma so **quanti sono** — il 3,2% delle
scritture, e `L4.1` ne fa 90.

🔑 **E il prodotto lo aveva già trovato**, `anti_confab_gate.py:2512`:

> «Misurato il 16/08 usando il prodotto: fonte «SEI combinazioni», claim «6
> combinazioni», **tre casi con `withheld_despite_judge=True` e grounding
> 99,3-99,9 — il layer tratteneva un fatto VERO mentre il giudice era
> contento**.»

**Stesso pattern, stesso intervallo di grounding, trovato due settimane fa** — e
**curato per un caso specifico** (il numero che la fonte scrive a parole). La
strategia della cura è dichiarata:

> «⚖️ **DECLASSA, non ammette**: il valore esce dal veto ed entra in un **AVVISO
> col suo nome** … *un avviso non ha bisogno della popolazione opposta, **un veto
> sì***.»

📌 **Proposta, non cura**: l'**intervallo derivato** del §② («fra il 2026-07-05 e
il 2026-07-08» da tre date che la fonte elenca) è **un altro caso della stessa
famiglia**, non ancora coperto. La strada già battuta dal prodotto sarebbe
**declassarlo da veto ad avviso**. ⚠️ **Non la implemento**: la regola scritta lì
dice che *un veto esige la popolazione opposta*, e la popolazione opposta
dell'intervallo derivato **non l'ho misurata** — è la stessa cautela che il [69](69-la-cura-che-avevo-proposto-costa-sei-ancore-vere-su-diciotto.md)
ha pagato con 6 ancore vere su 18.

🪞 **E l'ironia è il dato**: il fatto che descrive il fenomeno **è caduto nel
fenomeno**, con grounding 98,9. Non l'ho costruito: è successo salvando.

## ⑤ Cosa NON prova

⚠️ **Otto casi, scelti con un seme, su 633.** Non do nessun tasso: do due casi
letti e riproducibili per id.
❌ **Non ho ri-eseguito il gate su quei fatti**: leggo il verdetto e lo span
registrati, non rifaccio il giudizio. Il gate di oggi potrebbe decidere
diversamente — la cura dei decimali (`b12e9823`) mostra che cambia.
✅ **Quello che regge**: i due casi di §② e §③ sono **letture dirette** di
`proposition`, `grounding_span`, `grounding_score` e `quarantined_by` sulla
stessa riga. Il disaccordo fra strati del §② **non è un'inferenza**: sono due
campi dello stesso record.
✅ **L'altro lato ORA è misurato** (§④-bis) e dice il contrario di quello che il
titolo originale lasciava intendere: **`L4.1` prende ciò che il moat non può
vedere**, almeno 3 volte su 7. ⇒ **Non solo non dico che vada spento: i dati
dicono che serve.**
⚠️ **Sette casi anche di là**: la sua *precisione* resta non quantificata, e
questo documento non la quantifica. Dice che i falsi positivi esistono (§②) e che
i veri positivi pure, **entrambi letti**.

---
*Nessun banco: una query in sola lettura e otto casi letti a mano.*
