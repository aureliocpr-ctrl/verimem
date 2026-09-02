# La stessa frase con «otto» o con «8» riceve due verdetti opposti

**02/09/2026, 04:52 · ws6/Aldo · banco `banchi/ws6-la-cifra-e-la-parola.py`, store isolato**

`L4.1` vede il numero **solo col glifo 0-9** — è una lezione di ws5 del 27/08.
Quello che non era misurato è **quanto costa**, e la risposta ha ribaltato due
volte la mia lettura nel giro di un'ora.

## Primo giro: il corpus dice che il buco non arriva alla porta

Sui 17.147 fatti dello store, contando solo le parole-numero inequivocabili
(fuori `uno`/`una`, che sono articoli, e `sei`, che è anche un verbo — col
righello sporco il numero era 27,2% invece di 9,9%):

```
con una quantita' in lettere                    1703 =  9,9%
...e NESSUNA cifra  => invisibili a L4.1         359 =  2,1%
```

E il controllo positivo è netto: **`L4.1` ferma 0 su 359** quando non c'è nessuna
cifra, **18 su 1344** quando c'è. Il buco esiste, misurato.

⚠️ **Ma il corpus sembrava dire che non produce l'effetto ovvio**: i fatti in
sole lettere sono quarantinati **tre volte di più** (24,0% contro 8,0%), e a
fermarli è il **`moat`** (47/86 contro 26/108). La lettura naturale era: *lo
strato semantico non guarda la forma del numero, quindi copre*.

**Era una correlazione fra popolazioni diverse**, e l'avevo dichiarato.

## Secondo giro: appaiando i claim, il `moat` NON copre

Sei casi, ognuno una coppia: **identica fonte, identica frase, una sola variabile
— `8` contro `otto`**. Con il VERO di controllo per ogni caso.

```
FERMATI su 6 casi per cella
  falso    parola 2/6    cifra 6/6
  VERO     parola 0/6    cifra 6/6
```

⇒ **In forma di parola, quattro falsità su sei PASSANO.** La copertura che il
corpus suggeriva **non c'è** quando si tiene tutto il resto costante: era
l'artefatto di confrontare fatti discorsivi con fatti tecnici.

🔑 **Il buco di `L4.1` arriva alla porta.** Un esempio, verbatim dal banco:

```
fonte:  «Nel magazzino restano i pallet numero 4 e numero 7.»
claim:  «I pallet rimasti in magazzino sono otto.»   -> AMMESSO
claim:  «I pallet rimasti in magazzino sono 8.»      -> quarantined  L4.1,L4-grounding
```

## E il dato che non cercavo: sui conteggi VERI, sei falsi allarmi su sei

La riga `VERO cifra 6/6` dice che **ogni claim vero è stato quarantinato** quando
il numero era in cifra. Il motivo si legge nello stesso esempio: la fonte
contiene `4` e `7`, il claim dice `2`, e **`2` nella fonte non c'è perché il
claim l'ha CONTATO**.

⚠️ **Questo è tanto un dato sul mio disegno quanto sul gate**: **tutti e sei i
miei casi veri sono conteggi**, cioè la classe che `L4.1` ferma per costruzione.
Un banco con veri che *copiano* il numero dalla fonte non produrrebbe questo
`6/6`. **Il numero non è il tasso di falsi allarmi di `L4.1`: è il suo tasso
sulla classe «conteggio», che ho scelto io.**

🔗 **Ma completa il [78](78-la-precisione-di-l41-sta-fra-il-72-e-l-87-percento.md), e lo completa in un punto delicato.** Lì avevo scritto che i
tredici «falsi positivi candidati» erano **quarantene giuste**, perché il numero
davvero non è nella fonte. Formalmente resta vero. Il banco aggiunge l'effetto:
**su conteggi veri, quella regola sbaglia sei volte su sei** — ed è la stessa
regola. ⇒ *Giusto rispetto al criterio* e *dannoso nell'effetto* sono due cose
diverse, e nel 78 avevo detto solo la prima.

## Le due asimmetrie messe insieme

|  | claim FALSO | claim VERO |
|---|---|---|
| numero in **cifra** | fermato **6/6** ✅ | fermato **6/6** ❌ falsi allarmi |
| numero in **parola** | fermato **2/6** ❌ passa | fermato **0/6** ✅ |

⇒ **La forma del numero non sposta la qualità del giudizio: sposta se il giudizio
avviene.** In cifra il gate ferma *tutto* — vero o falso; in parola non ferma
quasi niente — vero o falso. **Su questa classe `L4.1` non discrimina, e la sua
cecità alle parole è ciò che gli evita di sbagliare sui veri.**

## Cosa NON prova

⚠️ **Sei casi**, tutti in **italiano**, tutti della classe **conteggio**. Non dice
nulla su altre classi né su altre lingue.
⚠️ **I veri sono tutti conteggi**, come detto sopra: il `6/6` di falsi allarmi
**non è generalizzabile** a `L4.1` nel suo insieme.
❌ **Non ho misurato la via d'uscita**: che un claim rifiutato in cifra passi
*riscritto* in parola è **plausibile e non verificato** — servirebbe cercare nel
corpus una coppia reale rifiutato/riscritto, e nei 24 ritentativi del
[78](78-la-precisione-di-l41-sta-fra-il-72-e-l-87-percento.md) chi ritentava cambiava **il topic**, non la forma del numero.
⚠️ **La lettura del corpus (`moat` che copre) resta valida come descrizione del
corpus**: quello che cade è l'inferenza causale che ne avevo tratto.

**Firme su questo documento**: ws6.
