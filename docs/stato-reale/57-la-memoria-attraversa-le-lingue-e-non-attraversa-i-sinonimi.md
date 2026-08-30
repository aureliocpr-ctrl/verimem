# 57 — La memoria attraversa le lingue e non attraversa i sinonimi

*ws6/Aldo — 31 agosto 2026, notte. Chiude il limite dichiarato nel [55](55-non-e-la-forma-della-domanda-e-il-vocabolario.md), e ne CORREGGE la spiegazione.*

Il `55` finiva con un limite e con una spiegazione. **Il limite l'ho chiuso e la
spiegazione è caduta**, il che è il modo in cui volevo che andasse: era proprio
la parte che avrei difeso.

Il limite era: *«non ho misurato l'inglese, e il corpus è misto»*. Il timore che
lo accompagnava — scritto nel mio wakeup, non nel documento — era grosso: **se
il richiamo è lessicale, una domanda in inglese non vede i fatti in italiano, e
metà memoria è invisibile all'altra metà.**

## ① Il disegno, migliore di quello del `55`

Nel `55` i bracci differivano anche per lunghezza, e l'avevo dichiarato («non è
un esperimento a un fattore solo»). **Qui il fattore è uno**: stesso fatto,
**stessa domanda**, cambia **solo la lingua**. 24 fatti, tutti in italiano nel
corpus, `k=10`, confronto appaiato.

| la domanda | ritrovati | al 1º posto | sovrapposizione lessicale |
|---|---|---|---|
| in **italiano** | 22/24 = **91,7%** | 87,5% | 85,9% |
| la **stessa in inglese** | 21/24 = **87,5%** | 62,5% | **22,7%** |

**La traduzione costa quattro punti**, e la sovrapposizione lessicale nel
frattempo crolla da 85,9% a 22,7%.

⚠️ **Controllo necessario**: dieci di quelle domande contengono identificatori
che *sopravvivono* alla traduzione (`EncodeDelegateUnavailable`, `flow.recall`,
`2f92d9e5`, `jaccard`, `768`). Senza separarle misurerei la presenza di un token
identico invece della lingua. Separate:

| | ritrovati | sovrapposizione |
|---|---|---|
| **con** identificatori — IT | 10/10 = 100% | 83,2% |
| **con** identificatori — EN | 10/10 = **100%** | 36,1% |
| **senza** identificatori — IT | 12/14 = 85,7% | 87,7% |
| **senza** identificatori — EN | 11/14 = **78,6%** | **13,2%** |

**Anche senza un solo token in comune, l'inglese regge al 78,6%.** Il controllo
tiene.

## ② E qui la spiegazione del `55` cade

Nel `55` avevo scritto: *«su questo corpus e a questo `k`, il richiamo è
governato dal lessico, non dal concetto»*. **Falsificato**, e dal confronto più
crudele possibile — due misure quasi alla stessa sovrapposizione:

| | sovrapposizione | ritrovati |
|---|---|---|
| sinonimi lontani, italiano (`55`) | **16,1%** | **20,8%** |
| stessa domanda tradotta, inglese (qui) | **22,7%** | **87,5%** |

**Sovrapposizione lessicale quasi uguale, risultato opposto.** Se fosse il
lessico di superficie a decidere, l'inglese dovrebbe crollare come i sinonimi.
Non crolla.

## ③ L'esperimento decisivo: i sinonimi lontani IN INGLESE

L'ipotesi da falsificare: **l'encoder (`multilingual-e5-base`) allinea le
TRADUZIONI, che è il suo mestiere, e non le PARAFRASI con sinonimi lontani.**
Predizione registrata prima di eseguire: allora i sinonimi *in inglese* devono
crollare **come** quelli italiani, perché il problema sarebbe la parafrasi e non
la lingua.

| sui 16 fatti del sottoinsieme | ritrovati | sovrapposizione |
|---|---|---|
| sinonimi lontani in **italiano** | 4/16 = **25,0%** | 15,6% |
| gli stessi sinonimi in **inglese** | 1/16 = **6,2%** | 2,1% |

**Non solo crollano: crollano di più.** La predizione regge.

## ④ Il quadro, sugli stessi fatti italiani

| la domanda è… | ritrovati |
|---|---|
| col vocabolario del dominio, in italiano | **91,7%** |
| col vocabolario del dominio, **tradotta in inglese** | **87,5%** |
| con sinonimi lontani, in italiano | 25,0% |
| con sinonimi lontani, **tradotta in inglese** | **6,2%** |

> 🔑 **La traduzione costa 4 punti. La parafrasi ne costa 67. La traduzione di
> una parafrasi costa tutto.**

⇒ **Il confine non è la lingua, e non è la sovrapposizione lessicale: è quali
trasformazioni l'encoder ha imparato ad allineare.** Cambiare *tutte* le parole
traducendo non fa quasi danno; cambiarne poche con dei sinonimi lo fa.

## ⑤ Ricaduta pratica — ed è l'opposto del timore

- ❌ **Non c'è «metà memoria invisibile all'altra metà» per la lingua.** Chi
  interroga in inglese un corpus italiano lo vede: **87,5%**. Il timore che
  aveva motivato questo banco era infondato, e dirlo vale quanto un allarme.
- ⚠️ **Il rischio vero è il sinonimo, in qualunque lingua.** «Contraddizioni» e
  «liti» sono più lontane, per questa memoria, di *contraddizioni* e
  *contradictions*.
- 📉 **Ma il RANGO paga il passaggio**: i primi posti scendono da 87,5% a 62,5%
  attraversando la lingua. **Trova, e posiziona peggio.** Con `k` piccolo la
  differenza si vedrebbe di più di quanto si veda qui.

## ⑥ Che cosa NON dico

- **L'ipotesi «l'encoder allinea le traduzioni perché le ha viste in
  addestramento» NON è misurata.** È coerente con i quattro bracci e col nome
  del modello, ma non ho accesso al suo addestramento: **è una spiegazione che
  regge alla falsificazione che le ho fatto, non un fatto verificato.**
- **I fatti sono tutti in italiano.** La direzione opposta — domande italiane su
  fatti inglesi — **non l'ho misurata**, e il corpus ne contiene.
- **Le traduzioni le ho scritte io**, e sono traduzioni *fedeli*: una traduzione
  sciatta è una parafrasi, e cadrebbe nell'altro braccio.
- **n=24 e n=16.** Reggono i divari da 60-80 punti, non i quattro punti fra
  91,7% e 87,5%: quelli sono un fatto solo, e non li interpreto.
- **`k=10`**, e il rango dice che con `k` più piccolo il quadro cambia.

---
*Banchi: `banchi/ws6-cross-lingua.py`, `banchi/ws6-sinonimi-in-due-lingue.py`.
Store di Aurelio in sola lettura.*
