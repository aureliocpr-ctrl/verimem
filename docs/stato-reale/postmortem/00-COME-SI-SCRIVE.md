# Postmortem — come si scrive (R7)

**Owner del template**: ws1 Marie (QA) · **09/09/2026** · regola R7 dello
`STUDIO-METODO-09-09.md`, adottata su mandato di Aurelio.

Un postmortem si scrive **per ogni**: rosso su `main` · revert · perdita di dati ·
degrado visibile all'utente · **misura mancante scoperta dopo** (una promessa che
nessuno stava misurando).

**Sei righe. Non cinque, non una relazione.** Il lead non apre la finestra su main
finché il postmortem dell'ultimo rosso non esiste — quindi la lunghezza è un
freno alla finestra, e sei righe si scrivono in cinque minuti.

Nome del file: `AAAA-MM-GG-<tre-parole>.md`. Uno per rosso, non uno per giornata.

---

## Il modulo

```markdown
# <cosa si è rotto, in una riga che si capisce senza contesto>

**Data** AAAA-MM-GG HH:MM (letta con `date`) · **owner** <ws> <nome> · **ticket** T<n>

1. **COSA** — che cosa ha visto chi guardava: il job, il comando, l'output.
   Con lo SHA lungo e il link al run. Niente diagnosi qui.
2. **CLASSE** — una delle quattro (sotto), scelta **prima** di spiegare.
3. **CAUSA** — la riga di codice o la condizione. Se non la so: «NON TROVATA»,
   e che cosa servirebbe per trovarla.
4. **CURA** — che cosa è cambiato, con lo SHA. Se non è entrata: «NON ENTRATA»
   e dove sta il ramo.
5. **CONTROLLO AGGIUNTO** — il test o il righello che **torna rosso se il
   difetto torna**. Se non c'è: «NESSUNO», ed è un debito con un nome sopra.
6. **QUANTO È RIMASTO ROSSO** — da quando a quando, e chi se n'è accorto (un
   allarme, o una persona che guardava).
```

---

## Le quattro classi del rosso, e perché si sceglie PRIMA di spiegare

Un rosso si classifica **prima** di raccontarne la causa, perché la classe decide
dove guardare. Chi spiega prima di classificare finisce sempre nel codice di
prodotto, che è il posto giusto solo in un caso su quattro.

| classe | che cosa vuol dire | come si riconosce |
|---|---|---|
| **① ROSSO VERO** | il prodotto è rotto: l'utente vedrebbe la stessa cosa | il caso si riproduce **fuori** dalla suite, dalla porta |
| **② TRAPPOLA ARMATA** | il test è giusto e coglie una condizione vera ma rara (orologio, ordine, concorrenza, fuso) | cambia esito **senza** che il codice cambi: rilancialo e guarda |
| **③ SENSORE SCOLLEGATO** | il test non misura ciò che dice: perimetro sbagliato, doppio, mock, montaggio non esercitato | **spegni la riga che dovrebbe accendere il rosso**: se resta verde, il sensore era scollegato |
| **④ GUARDIANO CHE MENTE** | il test passa e non dovrebbe: asserzione debole, `assert True`, eccezione ingoiata | il rosso non arriva mai: si scopre solo rompendo il prodotto apposta |

🔑 **Il controllo che decide fra ① e ③**: rompi **una riga sola** del presidio in
esame e guarda chi si accende. Se non si accende nessuno, il rosso non accusava
il prodotto.

🔑 **② non è «instabile»**, ed è la parola che fa perdere le giornate: «instabile»
chiude la domanda, «trappola armata» la apre. Un test a orologio che passa con
10 ms di margine su una piattaforma la cui grana è 15,6 ms **non è instabile: è
sbagliato**, e lo è sempre stato.

---

## Un esempio compilato — così si vede la lunghezza giusta

> # `ci windows` rossa su un test del breaker, con zero file di prodotto cambiati
>
> **Data** 2026-09-08 14:10 · **owner** ws1 Marie (QA) · **ticket** T38
>
> 1. **COSA** — il job `ci / windows` sul candidato `5ac8d9f1` va rosso su un
>    test del circuit breaker. Il commit **non cambia nessun file di prodotto**;
>    su ubuntu e macos lo stesso job è verde.
> 2. **CLASSE** — **② TRAPPOLA ARMATA**. Scelto prima di spiegare, perché il
>    diff non tocca il prodotto: il sospetto passa al banco, non al codice.
> 3. **CAUSA** — il test aspetta un cooldown di 50 ms e verifica con **10 ms di
>    margine**; la grana del contatore di sistema su Windows è **15,6 ms**. Il
>    margine è più piccolo della risoluzione dell'orologio con cui si misura.
> 4. **CURA** — cella con orologio finto, scritta su `HA-ws1-asof` (`cbede6a9`),
>    **NON ENTRATA**: la sto passando a @Tara col ticket.
> 5. **CONTROLLO AGGIUNTO** — **NESSUNO** finora. Il controllo giusto non è un
>    margine più largo (rimanda il problema): è che il test **non dipenda
>    dall'orologio di sistema**. Debito a nome mio finché la cura non entra.
> 6. **QUANTO È RIMASTO ROSSO** — dal 08/09 14:10; se n'è accorto un umano
>    leggendo i job uno per uno, **non un allarme**: un rosso solo-Windows in
>    una matrice a tre non emette nessun segnale suo.

---

## Tre errori che questo formato serve a impedire

- **«instabile»** scritto al posto di una classe. Vietato: se non sai
  classificarlo, scrivi «CLASSE NON DECISA» e che cosa serve per deciderla.
- **La riga 5 lasciata vuota.** Un rosso curato senza un controllo che lo
  riprenda è lo stesso rosso che torna fra un mese con un altro nome.
- **Il postmortem scritto dal solo autore della cura.** Chi ha scritto la cura
  vede la causa che la cura risolve. La riga 2 e la riga 5 le rilegge un altro.
