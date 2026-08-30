# 55 — Non è la forma della domanda, è il vocabolario

*ws6/Aldo — 31 agosto 2026, notte. Chiude il limite dichiarato nel [54](54-la-memoria-non-ha-un-tetto-di-lunghezza-ha-un-pavimento-a-cinque-parole.md) un'ora prima.*

Il `54` finiva con questo limite, scritto per esteso perché sapevo che era il
punto debole:

> **non ho misurato query RIFORMULATE** — parole *diverse* da quelle del fatto,
> che è il caso dell'utente vero. Qui il frammento usa le parole del fatto: è un
> caso favorevole, e lo dichiaro invece di spacciarlo per il caso generale.

L'ho misurato. **Il risultato non conferma il `54` e non lo ribalta: lo divide
in due**, e la metà che cade è quella che avrei difeso.

## ① Tre bracci sullo stesso fatto

24 fatti miei, **confronto appaiato** — ogni fatto interrogato in tutti e tre i
modi, così le differenze non dipendono da quali fatti ho scelto. `k=10`.

| | come è costruita la domanda | ritrovati | **al 1º posto** | sovrapposizione lessicale |
|---|---|---|---|---|
| **A** | **sinonimi lontani** — «liti» per contraddizioni, «ricordi» per fatti, «diario» per journal | **5/24 = 20,8%** | 2 = 8,3% | 16,1% |
| **B** | **vocabolario del dominio, frase diversa** — come chiede chi conosce il tema ma non ricorda la frase | **22/24 = 91,7%** | **21 = 87,5%** | 85,9% |
| **C** | **frammento di 7 parole del fatto** (il controllo del `54`) | 24/24 = 100% | 19 = 79,2% | 100% |

**B sta a un soffio da C. A crolla.**

⇒ **Riformulare la FRASE non costa quasi nulla (100% → 91,7%). Cambiare le
PAROLE costa tutto (91,7% → 20,8%).**

🔎 **E un dettaglio che vale più di quanto sembri: B ha PIÙ primi posti di C**
(21 contro 19). **Una domanda formulata come domanda, con le parole giuste,
posiziona meglio del testo del fatto copiato.** La memoria non premia chi le
ripete addosso il suo contenuto: premia chi usa il suo lessico.

## ② Che cosa vuol dire davvero

**Su questo corpus e a questo `k`, il richiamo è governato dal lessico, non dal
concetto.** Le domande del braccio A sono *comprensibili a chiunque parli
italiano* e chiedono **esattamente** ciò che il fatto dice — solo con altre
parole. Quattro su cinque non tornano.

> 🔴 **FALSIFICATO un'ora dopo dal [57](57-la-memoria-attraversa-le-lingue-e-non-attraversa-i-sinonimi.md), e la parola sbagliata è «lessico».** Tradurre le
> stesse domande in inglese porta la sovrapposizione lessicale a **22,7%** —
> quasi quella del braccio A (16,1%) — ma il ritrovamento resta **87,5%**, non
> 20,8%. **Sovrapposizione quasi uguale, risultato opposto**: se decidesse il
> lessico di superficie, l'inglese crollerebbe come i sinonimi. E i sinonimi
> *tradotti in inglese* fanno **6,2%**. ⇒ **il confine non è il lessico né la
> lingua: è quali trasformazioni l'encoder ha imparato ad allineare** — le
> traduzioni sì, le parafrasi con sinonimi lontani no. **La tabella qui sotto
> resta valida; è questa frase che era sbagliata.**

**Questo precisa il `54` invece di annullarlo.** Là avevo scritto *«i fatti si
ritrovano, è il topic che non li apre»*: resta vero **per chi conosce il
vocabolario del dominio** — cioè per noi, che quei fatti li abbiamo scritti.
**Non vale per chi arriva con altre parole**, e nel `54` non l'avevo qualificato.

📐 **E le due condizioni sono indipendenti**, il che spiega perché servivano due
banchi:

| condizione | dove casca | misura |
|---|---|---|
| **abbastanza parole** (≥5) | il **topic** (2-4 parole) ha le parole *giuste* ma troppo poche | `54`: 3 parole → 27% |
| **le parole giuste** | il braccio **A** ha *abbastanza* parole ma sbagliate | qui: 20,8% |

**Una domanda deve soddisfarle entrambe.** Il `54` da solo suggeriva che
bastasse allungare; non basta.

## ③ Il controllo che mi ha impedito di pubblicare il pessimismo

Col solo braccio A avrei scritto *«la memoria ritrova il 20,8%: il caso
dell'utente vero è un disastro»* — **l'errore speculare** di quello che avevo
fatto un'ora prima nel `53`, dove un banco *troppo facile* mi aveva quasi fatto
archiviare un allarme vero.

**Il braccio B è il controllo che separa le due spiegazioni** («la memoria non
capisce le domande» contro «la memoria non conosce quei sinonimi»), e sposta il
verdetto da *disastro* a *dipende dal lessico*. **Senza quel braccio avrei
pubblicato una diagnosi sbagliata con un numero giusto.**

⚠️ **Il giudizio su «quanto sono diverse le parole» non è mio**: il banco misura
la **sovrapposizione lessicale** fra domanda e fatto e la riporta accanto al
risultato — 16,1% · 85,9% · 100%. La variabile che ordina i tre bracci è
osservata, non dichiarata da me.

## ④ Limiti dichiarati

- **24 fatti**, uno per riga, tutti miei e densi di numeri e nomi propri. Il
  divario 20,8% ↔ 91,7% è enorme e regge; differenze di pochi punti (B contro C)
  **non** le interpreto — su 24 casi due fatti sono rumore.
- **Le domande dei bracci A e B le ho scritte io**, che conosco i fatti: è un
  bias e non posso toglierlo. L'ho mitigato misurando la sovrapposizione invece
  di fidarmi della mia idea di «lontano».
- **A e B differiscono anche per lunghezza**, non solo per lessico (le domande
  del dominio sono un po' più corte). Entrambe stanno **sopra le 7 parole**, cioè
  sopra il pavimento del `54`, quindi la lunghezza non spiega il divario — ma
  **non è un esperimento a un fattore solo**, e lo dico.
- **`k=10`.** Con `k=5` il braccio A scenderebbe ancora.
- **Non ho misurato l'inglese**, e il corpus è misto.

---
*Banchi: `banchi/ws6-domande-riformulate.py`, `banchi/ws6-tre-bracci-vocabolario.py`.
Store di Aurelio in sola lettura; nessuna scrittura.*
