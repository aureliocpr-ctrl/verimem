# Le contraddizioni sono log: il 94% a quattro token di distanza

*ws6/Aldo — 30/08, notte. Perimetro: archivio, memoria, corpus, quarantena.*

Il documento 42 ha stabilito che il 93,7% delle contraddizioni registrate mette a
confronto due fatti che **parlano d'altro** — jaccard sotto 0,15, mediana 0,039.
E si chiudeva con un limite dichiarato: le poche coppie con jaccard **alto**,
quelle in cui i due fatti parlano davvero della stessa cosa, non le avevo
guardate. Se lì dentro ci fossero contraddizioni vere, sarebbero **errori nella
nostra memoria che nessuno ha mai visto**.

Le ho guardate. Non sono errori: sono **log**.

## Prima correzione: erano molte più di quello che avevo stimato

Nel 42 avevo scritto «~137 nel campione». Il campione erano le prime 4.000
coppie per `id`, e non era rappresentativo. Contate su **tutte** le 93.263
irrisolte, alle **22:06:46 del 30/08**:

    coppie irrisolte con jaccard >= 0,50 : 3.021
    di cui con un topic test/…           :   190
    fatti distinti coinvolti             :   389

*(Ripetendo la misura pochi minuti dopo escono 2.919 e poi 2.774: il corpus
cresce mentre lo si legge, ed è il motivo per cui ogni numero qui porta il suo
istante.)*

## Che cosa sono, misurato e non dedotto

Leggendo le prime a occhio si vede subito che non sono conflitti, ma otto
esempi non sono una misura. La misura è questa: **quanti token esclusivi
separano le due frasi** — cioè quanto è grande, in parole, l'intera differenza
fra i due fatti.

Sulle **2.774** coppie non-test:

| token di differenza | coppie | cumulato |
|---|---|---|
| 2 | 261 | 9,4% |
| 3 | 808 | 38,5% |
| **4** | **1.544** | **94,2%** |
| 5-12 | 154 | 99,7% |

**Il 94,2% delle coppie differisce per al massimo quattro parole.** E quelle
quattro parole sono queste:

    2 token: solo-A=['ts=1779017247.725']    solo-B=['ts=1779017247.677']
       "Lab stress test worker 1 write 9 ts=1779017247.725"

    3 token: solo-A=['49','ts=1779017248.684']   solo-B=['ts=1779017247.725']
       "Lab stress test worker 1 write 49 ts=1779017248.684"

    4 token: solo-A=['@23:46:35','stopped']   solo-B=['@23:39:18','starting…']
       "[swarm-fixer @23:46:35] session 89e1ee25 state: working → stopped"

**Timestamp. Contatori. Orari. Stati di transizione.**

Non sono contraddizioni: sono **la stessa riga di log a due istanti diversi**,
salvata come fatto. Il rilevatore le confronta, trova `9` contro `49` e
`1779017247.725` contro `1779017247.677`, e dichiara un `numeric_clash`.

## Il pattern, che è più generale dei log

Le coppie che non sono log seguono la stessa forma. In tutte, la frase è
identica e cambia **un identificatore**:

| A | B | cosa cambia |
|---|---|---|
| `crea il file critic_live2.txt` | `crea il file critic_live.txt` | il file |
| `pytest su …_g5.py: 3 passed` | `pytest su …_g3.py: 3 passed` | il file (e l'esito è **uguale**) |
| `non compare fra i FAILED del run 3235…` | `compare … del run 3228…` | il run CI |
| `slot 'lay2'` | `slot 'lay1'` | lo slot |
| `guardia SPENTA: ritirati 1` | `guardia ACCESA: ritirati 0` | la condizione dell'A/B |
| `EN PASSIVA 0/10` | `IT PASSIVA 2/10` | la lingua |

> **Il rilevatore confonde «stessa frase, oggetto diverso» con «stessa frase,
> valore contraddittorio».**

Il caso di `_g5.py` contro `_g3.py` è quello che lo mostra meglio: i due fatti
riportano **lo stesso identico esito** — `3 passed con EXIT 0` — su due file di
test diversi, e vengono dichiarati in conflitto numerico.

E questo estende il documento 42 invece di correggerlo: il rumore non è solo
**sotto** soglia (fatti che parlano d'altro) ma anche **sopra**, per una causa
diversa. Delle 93.263 contraddizioni irrisolte, **praticamente tutte** sono
rumore — per due motivi distinti.

## Un difetto mio, l'ottavo della serata

Prima di misurare i token avevo provato una scorciatoia: cercare nelle parole
esclusive delle due frasi una **coppia di opposti noti** (acceso/spento, EN/IT,
con/senza, prima/dopo). Ne ha riconosciute **8 su 2.919**.

Un criterio sintattico su un fenomeno semantico sbaglia in entrambe le
direzioni: è una lezione che abbiamo in memoria da settimane, e l'ho ri-pagata
stasera. La misura che ha funzionato non chiede *che cosa* cambia — chiede
**quanto** cambia, e lascia che siano gli esempi a dire il resto.

## Quello che ho trovato di vero, e che non tocco

Un solo candidato mi sembra un conflitto autentico, e lo riporto senza
intervenire — correggere la memoria non è una scrittura che mi è stata chiesta:

- **`project/verimem/i-miei-verdi-reggono-senza-le-env`**
  A: *«La riga da confrontare riporta fermati 4 su 4 con env nostre attive **0**»*
  B: *«La riga da confrontare riporta fermati 4 su 4 con env nostre attive **7**»*
  Stessa identica frase, un numero diverso. O è un A/B scritto senza dire quale
  sia la condizione, o uno dei due è sbagliato.

Un secondo, più debole:

- **`project/verimem/autocorrezione-notte-29-08`**
  «Delle **33** celle mie nate stanotte, **20** sono state toccate» contro
  «Delle celle mie nate stanotte, **19** sono state toccate e **3** ritirate».
  Il secondo è già `quarantined`: il sistema aveva dubitato da solo.

## Il reperto di sistema

Lo store di produzione contiene **fatti di test e righe di log**.

- `test/cap20/system/cap20-test`, con proposizioni che sono letteralmente
  `cap20 0`, `cap20 1`, `cap20 18` — 190 coppie in conflitto fra loro.
- `Lab stress test worker 1 write 9 ts=…` — le righe di uno stress test.
- E all'altro estremo, le coppie con **73 token** di differenza sono
  `TEST 6 proposition lunga ASCII…` contro `TEST 5 proposition lunga +
  caratteri speciali…`, **con il topic vuoto** — quindi invisibili anche a chi
  filtra su `test/`.

Non è un difetto del motore: è materiale di prova rimasto in casa.

## Ma quanto pesa davvero? Poco — e va detto

Stavo per chiudere scrivendo che ripulire log e fatti di test «costa meno che
spiegarlo», e lasciando la stima come limite dichiarato. Un limite che si chiude
con una query non è un limite: è pigrizia. L'ho fatta.

Su **93.241** contraddizioni irrisolte:

    con un topic test/…            :    191 =  0,2%
    con un TIMESTAMP nella frase   :  2.623 =  2,8%
    => togliendo entrambi resterebbero: 90.427 = 97,0%

**La cura economica non risolve niente.** Log e materiale di test sono il **3%**
del problema. Il restante 97% sono le coppie a jaccard basso del documento 42 —
fatti che parlano d'altro e vengono dichiarati in conflitto perché contengono
numeri diversi.

Quindi questo pezzo descrive un fenomeno **reale ma marginale in volume**: ha
spiegato cosa sono le 3.021 coppie ad alto jaccard (il 3,2%), non le 90.000
restanti. **La cura che conta resta quella del documento 42**, e questa misura
la rafforza: non c'è una scorciatoia di pulizia che eviti di sistemare il
criterio del rilevatore.

## Per chi riprende

- Il righello è `docs/stato-reale/banchi/ws6-le-contraddizioni-sono-log.py`
  (sola lettura). Misura la distanza in token, non prova a indovinare la
  semantica.
- **La cura vera resta quella del documento 42**: portare nel rilevatore il
  criterio che `L4.2` già applica in scrittura — verificare che i due numeri
  parlino **della stessa grandezza e dello stesso soggetto** prima di dichiarare
  un conflitto. **Non l'ho fatta: è codice del gate, e il gate non si tocca
  senza mandato.**
- **Quello che non ho misurato**: se le 90.427 coppie che restano dopo aver
  tolto test e timestamp abbiano a loro volta una struttura ricorrente. Il
  documento 42 dice cosa **non** sono (fatti che parlano d'altro, mediana 0,039);
  nessuno ha ancora guardato **cosa siano**, e con quel volume una forma
  dominante è probabile.

---

**Verifica**: `~/.engram/semantic/semantic.db` in `mode=ro`, sole `SELECT`.
Istanti dichiarati in linea; il corpus cresce mentre si misura. Nessuna
scrittura, nessuna correzione applicata.
