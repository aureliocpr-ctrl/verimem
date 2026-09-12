# I difetti, e le pagine che li avevano già descritti

> **ws8 (Release), 08/09/2026.** Il contratto del rilascio completo chiede che ogni difetto
> noto sia **chiuso** (cura in main, RED/GREEN, perimetro) **oppure accettato per nome**,
> col numero che lo misura. Questo file serve a una cosa sola: **legare ogni ticket alle
> pagine che lo descrivevano già**, in ordine di data.
>
> Non è un indice per data né per autore: è **per difetto**. Nasce da un fatto misurato —
> T26a e T29 erano scritti in cinque pagine **un mese prima** che i ticket esistessero.

## T26a · T29 — la porta che non dice di non aver giudicato

| data | pagina | cosa dice |
|---|---|---|
| **08/08** | `02i-i-fatti-dei-primi-minuti-restano-non-verificati.md` | *«`warmup` risolve per il futuro; i fatti dei primi minuti restano non verificati **per sempre**»* — SHA `332a2f73`, HOME fredda, cache vuota |
| **30/08** | `39-le-finestre-cieche-della-memoria.md` | *«ventitré minuti, cinquantaquattro fatti»* — senza encode daemon il moat non gira, e i fatti scritti in quella finestra entrano `model_claim` mai giudicati |
| **30/08** | `48-ventitre-minuti-senza-daemon-hanno-spento-una-promessa-del-readme.md` | *«…e **resterà spenta**»* — **la prima metà è T26a, la seconda è T29** |
| **30/08** | `21-le-due-porte-gemelle-non-si-somigliano.md` | *«e quella sbagliata **tace**»* — misure alla porta MCP sullo store reale |
| **09/26** | `CHANGELOG.md`, voce `T26a` | il ticket, aperto **quasi un mese dopo** |

🔑 **Le misure c'erano. Mancava il filo.** Se questa tabella fosse esistita il 31 agosto, T26a
sarebbe stato aperto allora — e la **0.7.6**, pubblicata il 04/09, non sarebbe uscita con
dentro un difetto che quattro pagine avevano già descritto.

## 🧬 E non è una catena: è una CLASSE

Leggendo i titoli della famiglia «qualcosa tace» viene fuori che il difetto non è di una
porta, è **di forma**:

| pagina | l'asimmetria |
|---|---|
| `21` · `48` · `02i` · `39` | la porta MCP **non dice** di non aver giudicato — mentre la ricevuta lo saprebbe (`layers=['L4-skipped']`) |
| `31-la-porta-dei-documenti-dice-quello-che-quella-dei-fatti-tace` | **fra due porte**: quella dei documenti dichiara ciò che quella dei fatti tace |
| `38-il-regime-lo-dice-alla-risposta-e-lo-tace-alla-telemetria` | **fra due canali**: il regime arriva nella risposta e non nella telemetria |
| `70-la-cura-copre-il-caso-raro-e-tace-su-quello-frequente` | **fra due casi**: la cura parla del raro e tace sul frequente — «0 su 3» |

⇒ **La forma è una sola: il prodotto sa qualcosa e non lo dice sul canale dove qualcuno
guarda.** T26a ne è l'istanza più costosa perché il canale è `admitted`, che è quello che un
utente legge. Ma sono **quattro istanze indipendenti**, misurate da persone diverse in giorni
diversi, e nessuna delle quattro le nomina come la stessa cosa.

📌 **Questo è il pezzo che una mappa può dare e un ticket no**: il difetto non è «la porta MCP
tace», è «**questo prodotto ha l'abitudine di sapere e non dire, e succede su almeno quattro
superfici**».


## T24 · la supersessione — e qui il corpus ha fatto la cosa giusta

| data | pagina | cosa dice |
|---|---|---|
| **30/08** | `41-la-supersessione-sceglie-sei-volte-meglio-del-caso.md` | *«sceglie **sei volte meglio del caso**, e il danno è sceso di due terzi»* — e si apre con *«questo pezzo è una **buona notizia**, ed è la prima della serata»* |
| **31/08** | `64-una-catena-di-quattro-ritiri-fa-sparire-una-misura-intera.md` | *«una catena di **quattro ritiri** fa sparire una misura intera»* — e dichiara come è nato: *«**leggendo i candidati al recupero, non cercando questo**»* |
| **09/26** | `CHANGELOG.md`, voce `T24` | `replaced` nella ricevuta è sempre `False` |

🔑 **Qui il corpus si comporta all'opposto della classe «tace»**: lo stesso autore misura la
supersessione **dai due lati** a un giorno di distanza — quanto sceglie bene (41) e quanto
danno fa quando sbaglia (64) — e dichiara che il secondo reperto **non lo stava cercando**.
⇒ È il modello: **un numero che ti dà ragione e uno che te la toglie, dallo stesso righello,
scritti tutti e due.**


## D-1 · il rilevatore di conflitti

| data | pagina | cosa dice |
|---|---|---|
| **30/08** | `42-il-presidio-consiglia-una-cura-che-ritirerebbe-mille-fatti.md` | l'inizio della serie: **quante** coppie il rilevatore tocca |
| **30/08** | `44-il-rilevatore-dichiara-in-conflitto-quasi-tutte-le-coppie.md` | *«dichiara in conflitto il **99% delle coppie possibili** di un topic»* — chiude la serie iniziata dal 42 |
| **02/09** | `75-ho-letto-otto-quarantene-e-due-strati-si-contraddicono-sullo-stesso-fatto.md` | *«…e **leggendo l'altra popolazione ho ritirato la mia stessa lettura**»* |
| **09/26** | `CHANGELOG.md`, voce `D-1` | un fatto riportato da un terzo può essere scambiato per una contraddizione |

🪞 **`75` è il modello del ritiro**, e il titolo lo dice per intero: la lettura è caduta
**leggendo l'altra popolazione**. È la stessa regola che questa mappa ha dovuto imparare
sette volte stasera — *guarda anche i casi che il righello non ha segnalato* — e qui era
già applicata il 2 settembre, con il ritiro **nel titolo** invece che in fondo.

## T27 · il test escluso dalla suite

| data | pagina | cosa dice |
|---|---|---|
| **04/09** | `ticket-sigsegv-hang-watchdog.md` | il ticket, aperto da ws8: finestra dichiarata (`03/09 17:39 → 04/09 19:54`, ultimi 60 run), 3 morti di SIGSEGV su 10 falliti, e il `--deselect` registrato alla riga 139 |
| **09/26** | `CHANGELOG.md`, voce `T27` | soglia decisa **prima**: 24 job puliti consecutivi |

⇒ **Unico difetto della lista in cui documento e ticket nascono insieme**, dallo stesso
autore, con la soglia fissata prima di contare. Non c'è nessuna misura anteriore da
ricongiungere: il filo, qui, non è mai stato spezzato.


## T25 · due strati, due verdetti sullo stesso fatto

| data | pagina | cosa dice |
|---|---|---|
| **30/08** | `22-un-quarto-dei-trattenuti-recenti-e-approvato-dal-giudice.md` | ws6, 15:50, corpus **15.755** fatti, `mode=ro`: *«un quarto dei trattenuti recenti è **approvato dal giudice**»* — cioè `L4.1` ferma e il giudice promuove, sullo stesso fatto |
| **30/08** | `23-quanto-spesso-L4-1-ha-ragione.md` | chiude il limite che il 22 aveva **dichiarato**: *«non ho letto i 70»* |
| **09/26** | `CHANGELOG.md`, voce `T25` | con un daemon condiviso, punteggio e soglia possono venire da due giudici diversi |

🔑 **Il 22 dichiara il proprio limite e il 23 lo chiude il giorno dopo.** È la coppia che
questa mappa cercava: non un documento che invecchia, ma **due che si passano il testimone**
— e il secondo esiste **perché** il primo aveva scritto cosa non aveva guardato.

## T39 · T40 — nessuna pagina anteriore, e dirlo è il risultato

Cercando nei testi i termini di questi due difetti (`muore in silenzio`, `1,6 GB`,
`tokenizzatore`) escono `83-il-gate-non-converte-i-numeri-scritti-in-parola.md` (03/09) e
`SCHEDA-PRODOTTO.md` (06/09) — **ma non ho verificato se parlino davvero di questi difetti
o se il match sia solo di parole**: *cercato, non letto*.

⚠️ T39 e T40 sono nati **stasera**, dalla misura di chi tiene il giudice. Se non hanno
pagine anteriori è **la cosa giusta**: significa che la misura e il ticket sono nati
insieme — come per T27 — invece di restare separati un mese come per T26a.


## T14 · T16 — le ultime due, e quello che ho trovato NON è quello che cercavo

**T14** (il verdetto non arriva alla porta MCP): cercando nei testi escono `00-ESAME`,
`GRAVITA-DIFETTI`, `PERCORSI-UTENTE`, `LA-FRASE-DELLA-0.7.7` e **`80-la-stessa-frase-con-
otto-o-con-8-riceve-due-verdetti-opposti.md`**. L'ultimo non è T14 — è un difetto **diverso**
e più netto: *«`L4.1` vede il numero **solo col glifo 0-9**»*, misurato il 02/09 alle 04:52
con un banco nominato (`banchi/ws6-la-cifra-e-la-parola.py`) e store isolato.
⇒ **Cercando T14 ho trovato un difetto che non stavo cercando.** Lo scrivo com'è, invece di
forzarlo dentro la casella sbagliata: *«otto» contro «8»* è **una classe a sé**.

**T16** (quale store una lettura aveva aperto): `85-il-disegno-esploso-dello-store-le-
giunture-e-chi-le-presidia.md` (05/09) è il documento che risponde, e dichiara il proprio
metodo: *«ogni riga porta **o la misura che presidia la giuntura, o la parola scoperta**.
Nessuna cella è compilata a…»*. Non è una pagina anteriore al ticket: è **il livello 3 del
disegno esploso**, cioè la risposta strutturale che il ticket ha reso necessaria.

## 📐 Il conto finale delle pagine anteriori

```
  T26a · T29   4 pagine prima del ticket   (02i 08/08 · 39 · 48 · 21, tutte 30/08)
  D-1          3 pagine                    (42 · 44 30/08 · 75 02/09)
  T24          2 pagine                    (41 30/08 · 64 31/08)
  T25          2 pagine                    (22 · 23, entrambe 30/08)
  T27          0 — nato col ticket, soglia fissata PRIMA di contare
  T39 · T40    0 — nati stasera, misura e ticket insieme
  T14 · T16    nessuna pagina anteriore trovata; T16 ha una risposta POSTERIORE (85)
```
**Undici misure scritte prima che i rispettivi ticket esistessero**, e nessuno le aveva
messe in fila. I tre difetti senza pagine anteriori (T27, T39, T40) sono **i tre in cui
misura e ticket sono nati insieme** — ed è l'unico modo in cui il filo non si spezza.

## Come si continua

Per gli altri ticket (T14, T16, T24, T25, T27, T39, T40, D-1) la tabella è **da compilare**:
per ognuno, `grep` dei termini del difetto sui 287 documenti, poi **lettura** delle pagine che
escono — perché il grep trova i candidati e non li conta, ed è la lezione che questa mappa ha
pagato sette volte in una sera.
