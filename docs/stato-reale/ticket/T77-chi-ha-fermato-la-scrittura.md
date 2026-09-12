# T77 — «chi ha fermato la scrittura» deve dirlo il campo che si legge

*Ticket, 12/09/2026. Pagina corta per scelta: il difetto è piccolo, la conseguenza no.*

---

## 1. Il fatto, già registrato nel prodotto

Esiste un caso riprodotto e scritto nel codice in cui:

    il moat APPROVA       grounding 99,89
    a fermare la scrittura e' un LAYER LESSICALE  («il claim afferma un valore
                                                   che la fonte non contiene»)
    il campo che nomina chi ha deciso scrive      'gate'     <- generico

**Il giorno dopo**, chi rilesse quella quarantena concluse — in buona fede — *«la
causa non è registrata, e non è il layer: il moat ha giudicato 99,89, cioè l'ha
approvata»*. **Il contrario del vero.** Il nome del layer stava **nella stessa
ricevuta**, in un altro campo.

⇒ **Un'etichetta generica non si legge come «non lo so»: si legge come un'assenza**,
e da un'assenza si deduce.

## 2. Perché non è un caso isolato — è successo di nuovo oggi

Otto persone hanno passato un pomeriggio sulla stessa deduzione: *«il punteggio è
99,6 contro un taglio di 40, quindi non può essere stata la soglia, quindi la causa
è ignota»*. **La causa non era ignota: era un altro decisore.** Due decisori di
natura diversa convivono per disegno —

| decisore | come decide | cosa restituisce |
|---|---|---|
| il moat | un **punteggio** su una scala, contro un taglio | un numero e un verdetto |
| il layer lessicale | una **regola sul testo** | un avviso **con il nome del layer** |

## 3. Quello che il prodotto SA GIÀ, e che nessuno legge

Tre campi esistono già e rispondono, ciascuno a una domanda diversa:

1. **il blocco del verdetto** (`verimem/client.py:4330`) — *«ALWAYS returned to the
   caller»*: porta `judge{backend, model}`, `score`, `threshold` **risolto per
   giudice**, `reason` **con le parole del layer che ha deciso** («*Never empty*»);
2. **il contrassegno del disaccordo interno** (`verimem/client.py:1200-1209`) —
   vale `True` quando **il giudice aveva approvato e qualcos'altro ha trattenuto**,
   ed è **esattamente la domanda** che ci siamo fatti per un pomeriggio;
3. **l'avviso del layer**, che porta il nome vero (`L4.1`) nella stessa ricevuta.

⚠️ E il commento sopra il secondo dice già la cosa giusta: *«DESCRITTIVO, NON
VALUTATIVO: `True` non vuol dire che il gate abbia sbagliato — può essere il layer
ad avere ragione»*, con un esempio che è il nostro caso: **99,9 dal giudice
semantico e solo il layer lessicale vede che la cifra è 160 invece di 162.**

⇒ **Il difetto non è che manchi l'informazione: è che il campo più facile da leggere
è quello che dice meno.**

## 4. La cura — due righe, in ordine

1. **Il campo che nomina chi ha fermato deve nominare il layer vero** (`L4.1`), non
   il contenitore generico. Dove il nome non esiste, **deve restare vuoto**: un
   generico è peggio di un buco, perché il buco non fa dedurre.
2. **Chi legge va portato sul blocco del verdetto**: ogni riga di diagnosi che
   stampa l'etichetta stampi accanto **il giudice** e **la ragione**. Se i due
   discordano, *la differenza è essa stessa il reperto*.

## 5. Il RED — che cosa deve cadere, e perché non lo consegno eseguito

> **Data una scrittura in cui il giudice approva e a fermarla è un layer lessicale,
> il campo che nomina chi ha deciso deve contenere il nome del layer.**

    ARRANGIA   una fonte e un claim che differiscono per UN VALORE (la fonte dice 162,
               il claim dice 160), cosi' che il giudice semantico stia sopra il taglio
    AGISCI     scrivi il fatto con quella fonte
    PRETENDI   lo stato e' quarantined
               il campo «chi ha fermato» CONTIENE il nome del layer     <- oggi CADE
               il contrassegno del disaccordo interno e' True           <- oggi PASSA

**Controllo positivo, obbligatorio nello stesso braccio**: una seconda scrittura che
il **moat** ferma per davvero (punteggio sotto il taglio) deve far comparire il moat
e **non** il layer. Senza questo, un campo che scrivesse sempre `L4.1` passerebbe.

🚧 **Non lo consegno eseguito**: chi scrive questa pagina oggi non esegue. Il banco va
lanciato da chi ha il cartellino **prima** che entri in `tests/` — un test non provato
che nasce verde è il modo in cui i presidi muoiono. La forma `xfail(strict=True)` è la
via giusta se la cura non arriva nello stesso giro: l'XPASS diventa un fallimento, e il
giorno della cura il file lo dice da sé.

## 6. Quello che questo ticket NON dice

- **Non dice su quali porte la ricevuta arrivi davvero al chiamante**: i tre campi
  sono **letti** dove vengono costruiti e dove la riga di comando li consuma, **non
  provati** su una scrittura vera.
- **Non propone di togliere l'etichetta generica**: propone di non farle dire un nome
  che non è quello che ha deciso.
