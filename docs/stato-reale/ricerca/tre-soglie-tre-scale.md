# Tre soglie, tre scale — da dove viene 99,64 e quale scala usa la rettifica

*Ricerca interna, 12/09/2026. Letto nel codice, non dedotto. La prima metà della domanda aveva
già risposta trovata da chi fa QA: qui la cito e non la rifaccio; la seconda — **quale scala usa
la rettifica** — è nuova, e la risposta cambia il modo in cui i tre numeri vanno letti.*

---

## 1. Tre numeri che sembrano la stessa cosa

Tutti e tre appaiono come «una soglia fra 0 e 100» e per questo, oggi, sono stati confrontati fra
loro per ventun minuti. **Non sono confrontabili**: appartengono a tre scale diverse.

| numero | che cos'è | su quale scala | chi lo usa |
|---|---|---|---|
| **40,0** | il taglio d'ammissione del moat locale | punteggio grezzo del cross-encoder | ogni scrittura con fonte, e la via della conversazione |
| **80,0** | il tetto della **banda incerta** | **la stessa** scala del cross-encoder | trattiene la fascia [40, 80) invece di ammetterla |
| **99,64** | il max-F1 sul VAL set del fine-tune | scala del fine-tune, **punteggi compressi vicino a 1,0** | **nessuno: il prodotto lo rifiuta** |

## 2. Da dove viene 99,64 — la risposta è scritta nel codice, con la data

Il numero arriva dal `gate_config.json` del modello e il prodotto **lo scarta come artefatto di
calibrazione**: un taglio d'ammissione sopra ~90/100 «is a calibration artifact, never a real
operating point». Quando lo trova, emette un avviso e ricade su **40,0** — il taglio validato,
lo stesso della via della conversazione.

⇒ **99,64 non è «la soglia calibrata che conta»: è precisamente ciò che il prodotto rifiuta di
usare.** Chi lo legge come soglia d'esercizio misura contro un numero che nessun percorso applica.

📌 *Questa metà della risposta l'ha trovata QA nel pomeriggio leggendo il gate; la riporto perché
la pagina serva da sola, non perché l'abbia trovata io.*

## 3. Quale scala usa la rettifica — la risposta, letta nel codice

La **rettifica** è ciò che accade a un punteggio che cade nella banda incerta: invece di parcheggiare
la scrittura, si chiede **un verdetto a un giudice llm** (un modello locale, o la riga di comando
in abbonamento come ripiego).

E qui sta il punto: **la rettifica NON lavora sulla scala del cross-encoder.**

1. il modulo riusa **la stessa rubrica del giudice llm iniettato**, e lo dichiara: *«so the score
   scale — and therefore the claude-scale admission threshold — stays calibrated»*;
2. il chiamante, dopo l'escalation, confronta il punteggio con
   **`resolve_write_threshold_for("claude")`** — cioè **la soglia della scala del giudice llm**,
   non con il 40 del cross-encoder.

⇒ **Risposta: la rettifica usa la scala del giudice llm, con la soglia di quella scala, e il
codice lo fa apposta.** Non è un difetto: è l'unica cosa corretta da fare, perché un punteggio
nato su una rubrica non si confronta con il taglio di un'altra.

## 4. Allora dov'è il difetto — perché un pomeriggio si è perso qui

Il codice tiene separate le tre scale. **È il modo in cui le espone che non le distingue**: tutti
e tre i numeri escono come `threshold`, un `float` fra 0 e 100, senza dire **di quale scala sono**.

- la ricevuta riporta il taglio **senza** il nome della scala;
- chi confronta un punteggio con «la soglia» non ha modo di sapere se sono la stessa;
- e il caso peggiore è silenzioso: un punteggio della scala A sopra la soglia della scala B
  produce **un verdetto sbagliato con l'aria di essere giusto**.

Che non sia teorico lo dice la giornata: **due pari con il codice davanti** hanno confrontato per
ventun minuti numeri di scale diverse, e una delle due autocorrezioni fatte in buona fede era
essa stessa sbagliata.

## 4-bis. E non sono solo tre numeri: c'è un giudice che non usa numeri affatto

*Portato da chi fa QA nel pomeriggio, leggendo un caso già registrato nel prodotto. Lo riporto
qui perché senza questo la pagina sarebbe vera e incompleta.*

Nel codice è documentato un caso in cui **il moat approva con 99,89** e a fermare la scrittura è
un **layer lessicale**: la regola dice *«il claim afferma un valore che la fonte non contiene»*.
Due decisori di natura diversa, che convivono **per disegno**:

| decisore | come decide | cosa restituisce |
|---|---|---|
| il moat | un **punteggio** su una scala, contro un taglio | un numero e un verdetto |
| il layer lessicale | una **regola sul testo** (un valore affermato che la fonte non ha) | un avviso con il nome del layer |

⇒ **Un punteggio alto non dimostra che la scrittura sia passata**, e — lezione del giorno —
*«il punteggio è 99,6 contro un taglio di 40, quindi non può essere stata la soglia, quindi la
causa è ignota»* è un ragionamento **sbagliato**: la causa non è ignota, è **un altro decisore**.

🔴 **E la ricevuta li appiattisce.** Nel caso registrato il campo che dovrebbe nominare chi ha
deciso riportava un generico `'gate'`, mentre il nome vero del layer stava **nella stessa
ricevuta**, in un altro campo. Chi lesse quel generico concluse, in buona fede, **il contrario
del vero**: *«non è stato il layer»*. Un'etichetta generica **si legge come un'assenza**.

## 5. La cura che propongo — è una riga di contratto, non un algoritmo

**Ogni verdetto dice CHI ha deciso e SU QUALE BASE — e ogni numero porta il nome della sua scala.** Il punteggio e la
soglia viaggiano insieme all'esecutore che li ha prodotti — la ricevuta già dice **chi** ha
giudicato (aggiunto oggi da chi tiene la piattaforma): **manca il fratello di quel campo, "su
quale scala"**.

Con quel campo:
- confrontare due numeri di scale diverse diventa **visibile** invece che plausibile;
- un banco che confronta col numero sbagliato **cade**, invece di passare;
- e il rifiuto dell'artefatto (99,64) smette di essere una regola nascosta in un `if`: diventa
  **un valore che nessuno può leggere per sbaglio come operativo**.

## 6. Quello che questa pagina NON dice

- **Non dice quale sia la soglia giusta per la scala llm**: è calibrata altrove e non l'ho
  misurata.
- **Non propone di unificare le scale**: sarebbe peggio — due giudici diversi *devono* avere
  tagli diversi. Il problema non è che siano tre, è che **si assomigliano**.
- **Non ho eseguito niente**: ogni riga qui sopra viene dal codice o da un post con l'output.
