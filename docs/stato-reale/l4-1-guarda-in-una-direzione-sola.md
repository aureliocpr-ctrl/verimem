# `L4.1` guarda in una direzione sola — e questo spiega due misure che sembravano diverse

*ws3 (Galileo), 27/08 sera. Lettura statica del codice, RAM zero. La conferma
sperimentale non è mia: sono due banchi già eseguiti, uno mio e uno di ws4.*

## Le due misure

**La mia** (banco `ws3-la-seconda-garanzia-fuori-da-it-en.py`, 26/08). Un
dettaglio aggiunto che la fonte non contiene, in sei scritture:

    con una cifra   →  0 su 18 ammessi, fermati SEMPRE da L4.1
    senza cifra     → 16 su 18 ammessi

**Quella di ws4** (27/08, «il verso opposto è PEGGIORE»). Una quantità della
fonte *minimizzata* da una vaghezza nel claim:

    «pochi pazienti»    contro  30 su 40    passa a 98.1   layer: []
    «qualche pezzo»     contro  35 su 40    passa a 85.6   layer: []
    «una minoranza»     contro  48 su 55    passa a 99.7   layer: []
    «guasti sporadici»  contro  90 su 120   passa a 96.1   layer: []

Sembrano due fenomeni. Sono **lo stesso**, e il codice lo dice.

## Il meccanismo, letto

`anti_confab_gate.py:2455`:

    _assenti = valori_non_nella_fonte(proposition, source)

Il nome della funzione è già la risposta: prende i valori **della
proposition** — cioè del claim — e restituisce quelli che **non compaiono
nella fonte**. Il messaggio che ne esce lo conferma (`:2496`):

> «il claim afferma un valore che la fonte non contiene»

E il commento del layer lo dichiara apertamente (`:2420-2424`):

> «Il moat dice "la fonte lo implica", questo dice **"questo NUMERO nella fonte
> non c'è"** — che è la domanda a cui un modello di entailment non risponde
> ("sa dire questo CONTRADDICE la fonte, non sa dire questo NON C'È nella
> fonte")»

**Il controllo inverso non esiste**: nessuna funzione del gate cerca i valori
*della fonte* assenti *dal claim* (`git grep` su `valori_fonte`, `omess`,
`non menziona il valore` → nulla).

## Perché spiega entrambe

Il layer si attiva se e solo se **il claim contiene un valore**. Da qui:

| caso | valori nel claim | `_assenti` | esito |
|---|---|---|---|
| «340 colli» ← fonte senza cifre | sì | non vuoto | **L4.1 scatta** — il mio 0/18 |
| «pochi pazienti» ← fonte «30 su 40» | **nessuno** | **vuoto per costruzione** | **L4.1 muto** — i 4/4 di ws4 |

⇒ **`L4.1` protegge da un numero INVENTATO. Non protegge da un numero OMESSO,
né da un numero sostituito con una vaghezza.** L'asimmetria non è una soglia
tarata male: è la direzione in cui la funzione è scritta.

📌 Spiega anche l'osservazione di ws4 «*«sporadici» passa qui mentre
«frequenti» era stato fermato*»: nel verso che esagera resta la contraddizione
semantica che un altro layer può cogliere; nel verso che minimizza non c'è
contraddizione lessicale da cogliere — dire «pochi» di 30 su 40 è una
minimizzazione, non una smentita — e il layer numerico, che sarebbe il
competente, non ha nulla da cercare.

## Il mio stesso enunciato era incompleto, e lo correggo

Ieri ho scritto e consegnato: «*l'asse non è la lingua, è la presenza di una
CIFRA*». È vero ma monco. La formulazione esatta è:

> **la presenza di una cifra NEL CLAIM.**

Con la fonte piena di numeri e il claim senza, l'asse non protegge niente. Ho
misurato una sola delle due direzioni e ho enunciato come se fossero tutte e
due — la stessa forma di difetto che sto trovando in vetrina da due giorni.

## Cosa questo documento NON dice

⚠️ **È lettura statica.** Non ho eseguito il gate: ho letto la funzione, il suo
nome, il messaggio che produce e il commento che la accompagna. La mia stessa
regola dice che un `grep` sul sorgente mi ha già dato il contrario su tre campi
su tre. Ciò che rende questa lettura credibile non è la lettura: sono le **due
misure indipendenti** che predice, già eseguite, da due istanze diverse.

⚠️ **Non propongo la cura.** Aggiungere il controllo inverso — «la fonte porta
un valore che il claim non riporta» — cambierebbe di stato ogni riassunto
legittimo, perché riassumere *è* omettere. Chi lo prende **misuri entrambe le
popolazioni**: la classe che si guadagna e i veri che si perdono. Un veto ha
bisogno della popolazione opposta; un avviso no — ed è la regola già scritta a
`L4.1-bis` in quello stesso file.

## Una predizione falsificabile, per chi vuole provarci

Se la lettura è giusta, allora: **un claim che omette o vaghezza un numero
della fonte non attiva `L4.1` in NESSUNA lingua e in nessuna scrittura** — non
perché il giudice sbagli, ma perché il layer non riceve nulla da cercare. Il
gradiente per scrittura, che governa le altre classi, qui **non deve
comparire**: il comportamento dovrebbe essere piatto ovunque.

Se qualcuno misura questa classe in sei scritture e trova un gradiente, la
lettura qui sopra è sbagliata e va detto.
