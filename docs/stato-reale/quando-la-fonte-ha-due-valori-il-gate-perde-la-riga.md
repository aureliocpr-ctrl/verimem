# Quando la fonte ha due valori, il gate perde la riga

**ws4 «Paragone» — consolidamento della notte 30-31/08.** Cinque celle
(`W7-91`, `W7-92`, `W7-98`, `W7-99`, `W7-102`) misurano cose diverse e
descrivono **un solo fenomeno**. Questo documento lo mette per iscritto con i
numeri, gli id e i limiti — perché nessuna delle cinque, da sola, lo dice.

---

## La tesi

> **Il moat verifica se la fonte SUPPORTA il claim, non a QUALE RIGA della
> fonte il claim si riferisca.** Su una fonte che contiene un solo valore per
> ogni grandezza la distinzione non esiste. Su una fonte che ne contiene due —
> una tabella di confronto, due esecuzioni incollate, un prima/dopo — il gate
> **perde la riga**, e sbaglia **in entrambe le direzioni**.

⚖️ **Non è una violazione della promessa.** Le istruzioni del server dicono:
*«the fact is admitted only if the source TEXT actually supports it»*. Con due
valori presenti, **il testo supporta davvero entrambi i claim**. È un **limite
non dichiarato**, non un difetto — e la distinzione conta, perché una cura al
gate sarebbe fuori perimetro mentre una riga di documentazione no.

---

## Le prove

### ① Nella direzione permissiva: passa anche il valore sbagliato

`W7-98`, moat caldo, A/B nella stessa esecuzione:

    fonte unica: «…la linea 4 ha prodotto 318 pezzi conformi durante la
                  sessione del mattino.  …la linea 4 ha prodotto 250 pezzi
                  conformi durante la sessione del mattino.»

    claim «318 pezzi»  ->  persist     99,98   layers []
    claim «250 pezzi»  ->  persist     97,97   layers []
    claim «400 pezzi»  ->  downgrade    0,66   layers ['L4.1','L4-grounding']

Il terzo è il **controllo positivo**: un valore assente viene fermato, quindi i
due `persist` non sono un gate spento. E il conflitto **non morde a nessuna
distanza**: adiacente o a 11000 caratteri, la caduta è **0,00**.

⇒ **`L4.1` protegge dal numero ASSENTE, non da quello SBAGLIATO.**

### ② Nella direzione restrittiva: cade anche il valore giusto

`W7-102`, corpus vero, SQL puro:

    fatti vivi con fonte                          6975
    quarantinati                                   607
    …con numeri nel claim                          237
    …con TUTTI i numeri presenti nella fonte       111
         di cui SOTTO il cut 40 (il moat)           72
         di cui SOPRA il cut (altri layer)          39

⇒ **72 fatti (30,4% dei quarantinati con numeri) hanno tutti i numeri nella
fonte e il moat li boccia comunque.**

E l'esempio che lega le due direzioni:

    g=35,51  «Nel job ubuntu i test passati sono 10208 e nel job windows
              sono 10210.»

Due numeri, **entrambi nella fonte**, riferiti a **due righe diverse**. Il
claim è vero. Il moat si ferma a 35,51, appena sotto il cut di 40.

### ③ Quanto è frequente quella forma di fonte

`W7-99`:

    fatti vivi con fonte                     6870
    …con coppie chiave=numero                3423
    …con la STESSA chiave e valori DIVERSI    711   (20,8%)

⚠️ **Sei esempi letti a mano: sei su sei sono LEGITTIMI** — `grounding` a
`1.0` e `95.7` da una fonte che confronta *«CON fonte | SENZA fonte | fonte che
SMENTISCE»*; `wheel` a `40.0, 70.0, 85.0`, tre soglie del prodotto. **Sono
tabelle di confronto: come scriviamo i banchi.**

⇒ **Il 20,8% misura una CONDIZIONE, non un errore.** Ma è la condizione che
espone alle direzioni ① e ②.

### ④ E un terzo effetto, indipendente e non spiegato

`W7-91` e `W7-92`: esistono **valori numerici su cui il giudice collassa**,
anche quando sono nella fonte.

    alfa=1167   ->   0,52      alfa=1168   ->  99,96     (stessa source e claim)
    tratto 1160-1199   42,5% dei valori cade
    tratto 1500-1539    0,0%   ·   1860-1899   0,0%   ·   160-199   0,0%

**Otto ipotesi linguistiche cadute prima di arrivarci** (cinque di @ws8, tre
mie: la parola, la posizione nella source, il prefisso). **Non sono gli anni** —
mia ipotesi, falsificata dai miei stessi dati.

---

## Cosa questo NON dice

* **«Tutti i numeri nella fonte» non significa «claim vero».** Un numero può
  esserci ed essere riferito ad altro — che è ciò che `L4.2` segnala. I 72 di
  `W7-102` sono **casi in cui il criterio è rispettato e il fatto cade**, non
  72 falsi negativi: **per saperlo bisogna leggerli, e non l'ho fatto**.
* I 711 di `W7-99` **non sono 711 difetti**: sei su sei letti erano legittimi.
* Le euristiche vedono **una sola forma** (`chiave=numero`, `chiave: numero`):
  una contraddizione in prosa non la vedono.
* `grounding_span` è un **estratto** (`W7-90`: budget **400** salvato contro
  **1500** giudicato, massimo osservato **932** su 7030) ⇒ tutti i conteggi su
  quel campo **sottostimano** la condizione nel documento originale.
* La cecità numerica di ④ **non è spiegata**: so che c'è e che è a chiazze, non
  perché.

---

## Cosa se ne fa

**Non una cura al gate.** Il gate fa ciò che promette, e chiedergli di
distinguere la riga significherebbe chiedergli un compito diverso.

**Una riga nella documentazione** e **una nella nostra disciplina**:

> Il prodotto controlla le contraddizioni **fra fatti**, non **dentro una
> fonte**. Se la fonte confronta più valori, **tagliala alla riga che sostiene
> il claim** — che è poi ciò che `select_relevant_span` fa bene quando può
> (`W7-97`: trova l'evidenza a 12000 caratteri, in coda, dentro una tabella,
> 30 celle su 30 sopra 99,78).

📌 **E riguarda noi più di chiunque**: `O3` ci impone di incollare l'output
grezzo, e un output di terminale contiene spesso la stessa misura ripetuta.
**È l'errore che ho fatto il 30/08 alle 14** — numeri di un'esecuzione con la
source di un'altra: `L4.1` mi ha presa **solo perché quel valore non c'era**.
Se ci fosse stato per un'altra riga, sarei passata con la ricevuta verde.

---

## Ritiri, perché il documento non nasconda il percorso

Durante questa notte ho **ritirato quattro affermazioni mie**, tutte
pubblicate prima di avere la successiva:

    «curare il cut è motivato» come guida      22:32
    «il giudice premia chi ricopia»            23:36   (letti 9 casi: 3 giusti)
    «il moat boccia le sintesi da tabella»     00:08   (8,9% contro 10,0%)
    la cura proposta per diagnose_failure      03:41   (il campo esisteva già)

E **otto errori di criterio di lettura**, tutti trovati rileggendo il mio
output. Il tasso di errore sui **criteri** è stato molto più alto di quello sui
**dati** — e la contromisura che ha funzionato è pubblicare ogni passaggio
prima di avere il successivo, così l'errore dura minuti invece di ore.

---

*Celle: `W7-90`, `W7-91`, `W7-92`, `W7-97`, `W7-98`, `W7-99`, `W7-102`.
Banchi rieseguibili in `docs/stato-reale/banchi/`.*
