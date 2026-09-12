# Tre soglie, tre scale — da dove viene 99,64 e quale scala usa la rettifica

*Ricerca interna, 12/09/2026. Letto nel codice, non dedotto.*

---

## 0. Correzione dell'autore, un'ora dopo la consegna — **questa pagina non conteneva niente di nuovo**

Avevo scritto qui che la seconda metà della domanda era «nuova». **Non lo era**, e l'ho scoperto
facendo *dopo* la ricerca il controllo che andava fatto *prima*: cercare il sintomo nei nostri
documenti, con le parole del sintomo.

| quello che questa pagina «trovava» | dove era già scritto | da quando |
|---|---|---|
| la rettifica segue il giudice che ha davvero dato il punteggio | `docs/BENCHMARKS.md:818-821` | **04/07/2026** |
| il giudice approva e a fermare è un layer lessicale | `docs/stato-reale/00-ESAME.md:74-80` | **28/08/2026** |
| 99,64 è un artefatto del *val set*, con cap e avviso | `docs/stato-reale/00-ESAME.md:2925-2940`, `:14533` | **cap: 18/07/2026** |

⇒ **Il difetto che questa pagina descrive l'ha subìto la pagina stessa**: un pomeriggio speso in
otto a ri-derivare due documenti che erano in casa. Resta valida la ricognizione — è utile avere
le tre scale in una tabella sola — ma va letta come **un riassunto con i riferimenti**, non come
un reperto. La cura di §5 è riscritta di conseguenza: *era già implementata*.

📌 **La regola che ne esce, e costa poco**: prima di aprire un'indagine, due ricerche nei nostri
documenti **con le parole del sintomo** (qui sarebbero bastate `99.64` e `L4.1`), non con il nome
del proprio piano — cercare col nome del proprio piano non trova il lavoro di nessun altro.

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

📎 **E non è una scoperta di oggi**: il principio è scritto nei nostri numeri pubblici dal
**04/07/2026** — *«the cut now always follows the judge that actually scored, at every call site
including production L4 and the fail-over path»* (`docs/BENCHMARKS.md:818-821`), che nomina
anche il pericolo simmetrico: **taglio di scala llm sul ripiego anche quando una configurazione
del cross-encoder esiste**.

## 4. Allora dov'è il difetto — perché un pomeriggio si è perso qui

Il codice tiene separate le tre scale, **e la ricevuta le distingue** (§5: il taglio viaggia con
il giudice che l'ha risolto). Il difetto sta un passo più in là, ed è di lettura:

- **il numero, preso da solo, non porta la sua scala**: `threshold` è un `float` fra 0 e 100, e
  fuori dal blocco che lo accompagna non si distingue da un altro `threshold`;
- chi cita «la soglia» in un post, in un banco o in una riga di diagnosi **stacca il numero dal
  suo contesto**, e da quel momento sembra confrontabile con qualunque altro;
- il caso peggiore è silenzioso: un punteggio della scala A sopra la soglia della scala B
  produce **un verdetto sbagliato con l'aria di essere giusto**.

⚠️ *Rettifica del 12/09, §0*: la prima versione di questa pagina scriveva «la ricevuta riporta il
taglio senza il nome della scala». **Falso, e trovato leggendo**: il blocco lo porta. A non
portarlo è **il numero citato fuori dal blocco** — cioè quasi sempre noi.

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

## 5. La cura che avevo proposto — **c'è già, e si chiama `adjudication`**

Avevo scritto: *«ogni verdetto dica chi ha deciso e su quale base, e ogni numero porti il nome
della sua scala»*. È il contratto giusto, e **il prodotto lo implementa**: il blocco costruito in
`verimem/client.py:4330` — *«The write verdict, ALWAYS returned to the caller»* — porta

    disposition · evidence_class · judge{backend, model, version}
    score · threshold · margin · reason · confidence_tier

e nel proprio docstring dice, scritto prima di oggi, **esattamente la lezione che è costata il
pomeriggio**: *«margin … is INTRA-JUDGE only: the local-CE and the llm judge use different score
scales (threshold is resolved per-judge at decision time), so margins are NOT comparable across
`evidence_class` values. `judge.backend` distinguishes them.»*

Il campo `reason`, poi, è costruito **con le parole del layer che ha deciso**, non con
un'etichetta di categoria, ed è marcato *«Never empty»*; una guardia esplicita gli impedisce di
scrivere «sotto soglia» su un fatto che il giudice **aveva ammesso**.

🔑 **Quindi la cura non è aggiungere un campo: è leggere quello giusto.** Nel caso registrato, chi
indagava ha letto `quarantined_by` — l'etichetta generica — mentre accanto c'era il blocco che
rispondeva alla domanda. *Un campo stampato e non letto è un campo assente*, e qui è peggio: il
campo assente stava **di fianco** a quello che ha ingannato.

Resta quindi, in ordine di valore:
1. **`quarantined_by` deve nominare il layer vero**, non il generico contenitore;
2. **i lettori vanno portati su `adjudication`** — banchi, registro delle quarantene, riga di
   diagnosi: se stampano un'etichetta, stampino accanto `judge.backend` e `reason`;
3. **la copertura per porta va misurata, non supposta**: qui è *letta* nel client e nella riga di
   comando, **non eseguita** su una scrittura vera (§6).

## 6. Quello che questa pagina NON dice

- **Non dice quale sia la soglia giusta per la scala llm**: è calibrata altrove e non l'ho
  misurata.
- **Non propone di unificare le scale**: sarebbe peggio — due giudici diversi *devono* avere
  tagli diversi. Il problema non è che siano tre, è che **si assomigliano**.
- **Non dice su quali porte la ricevuta arriva davvero al chiamante**: il blocco è *letto* dove
  viene costruito e dove la riga di comando lo consuma, **non provato** su una scrittura vera.
  Chi ha il cartellino lo esegua prima che diventi un ticket.
- **Non ho eseguito niente**: ogni riga qui sopra viene dal codice, da un documento del repo o da
  un post con l'output.
