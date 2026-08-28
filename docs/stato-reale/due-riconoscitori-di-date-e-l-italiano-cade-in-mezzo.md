# Due riconoscitori di date nello stesso modulo, e **l'italiano cade in mezzo**

*ws3 (Galileo), 28/08 ~21:40, finestra macchina libera. **Eseguito**: è il
debito che avevo dichiarato in regime risparmio, quando avevo scritto «*è
lettura di codice, non evidenza di comportamento*». Pagarlo ha smentito il mio
meccanismo e trovato qualcosa di peggio.*

## Prima: il mio meccanismo era sbagliato

In `340fb2bf` avevo scritto che `date_conflict` **si astiene per costruzione**
sullo scambio, perché la sua prima guardia è `if … (da & db): return None` e la
fonte contiene **entrambe** le date.

**Falso.** Non arriva mai a quella guardia:

    extract_dates(«Art. 5 - Il termine di consegna e' fissato al 12 marzo 2027.
                   Art. 6 - … al 30 aprile 2027.»)          ->  []

Torna `None` alla condizione **precedente**, `if not da or not db`. ⇒ **la
conclusione reggeva, il meccanismo che le avevo attribuito no.** È esattamente
la ragione per cui una lettura di codice non è una misura.

## Il fatto: `extract_dates` vede l'inglese e **non vede l'italiano**

    IT testuale     «12 marzo 2027»       ->  []                    ← non vista
    IT testuale     «Scadenza 12 marzo 2027.»  ->  []               ← non vista
    IT numerico     «12/03/2027»          ->  []                    ← non vista
    IT numerico     «12-03-2027»          ->  []                    ← non vista
    IT mese solo    «marzo 2027»          ->  []                    ← non vista
    ISO             «2027-03-12»          ->  [(2027, 3, 12)]       ✓
    EN testuale     «March 12, 2027»      ->  [(2027, 3, 12)]       ✓
    EN testuale     «12 March 2027»       ->  [(2027, 3, None)]     ✓ ma perde il GIORNO

## E il modulo ne ha **DUE**, con copertura diversa

|  | `_DATA_RE` — *sopprime* i numeri dalle quantità | `extract_dates` — *rileva* i conflitti di data |
|---|---|---|
| IT «12 marzo 2027» | ✅ `'12 marzo'` | ❌ `[]` |
| IT «12/03/2027» | ✅ `'12/03/2027'` | ❌ `[]` |
| EN «March 12, 2027» | ✅ `'March 12'` | ✅ `(2027, 3, 12)` |

> 🔑 **In italiano il prodotto SOPPRIME la data dai numeri ma NON la riconosce
> come data.** Il numero sparisce da `L4.1` **e** non arriva a `date_conflict`:
> **la data italiana cade in un buco fra due riconoscitori**, e nessuna delle
> due difese la copre.

⇒ Conseguenza concreta, e non serve costruirla: un fatto «*la scadenza è il 12
marzo 2027*» superseduto da «*la scadenza è il 30 aprile 2027*» **non produce
alcun conflitto di data in italiano**, mentre lo produrrebbe in inglese.
**`date_conflict` non può scattare su testo italiano.**

📌 È la nostra **classe ③** — *liste monolingue in un prodotto mondiale* — e la
**classe «due nozioni diverse sotto lo stesso nome»**: due riconoscitori di
date, stesso modulo, coperture diverse, e nessuno dei due sa dell'altro.

## Un difetto GEMELLO, in inglese, e ha la forma di quello che ho appena curato

    extract_quantities(«The deadline is March 12, 2027.», come_fonte=True)
        ->  [('', 2027.0)]

**L'anno diventa un numero nudo.** `_DATA_RE` prende `'March 12'` ma **non
l'anno**, quindi `2027` esce dalla soppressione e finisce fra le quantità senza
unità — **lo stesso identico meccanismo dei numeri d'articolo** che ho curato in
`29ab5544`, dove `Art. 4` produceva `('', 4.0)` e copriva un numero inventato.

⚠️ **Ipotesi, NON misurata**: un claim che inventa «2027» riferito ad altro
troverebbe `2027` fra i valori della fonte e `L4.1` tacerebbe. **Non l'ho
provato al gate**, e finché non lo faccio è un'ipotesi con un meccanismo
plausibile, non un difetto misurato. *(Il difetto dei numeri d'articolo l'ho
dichiarato solo dopo l'A/B alla porta: stesso metro qui.)*

## Cosa NON propongo

**Non tocco `extract_dates` stasera.** È usata da `date_conflict` e dallo
scanner retroattivo (`facts_conflict.py:487`): allargarla alle date italiane
**cambia il comportamento di un rilevatore di conflitti su tutto il corpus**, e
un rilevatore che comincia a vedere date che prima non vedeva può **iniziare a
ritirare fatti** che oggi convivono. Su una coda di revisione già a **1057
contro soglia 500**, è precisamente il tipo di cura che va misurata prima e
non dopo.

## Limiti, dichiarati

⚠️ **Nove forme provate**, scelte da me: IT testuale/numerico/mese-solo, ISO,
EN in due ordini. **Non ho provato** francese, spagnolo, tedesco — che il
prodotto dichiara altrove — né i formati con mese abbreviato («12 mar 2027»),
né le date con l'ora.
⚠️ **Non ho misurato quanti fatti del corpus reale contengono una data
italiana**: senza quel numero, «`date_conflict` non scatta in italiano» è vero
ma **non so quanto pesa**.
⚠️ Il difetto gemello dell'anno inglese è **un'ipotesi**, non una misura.
