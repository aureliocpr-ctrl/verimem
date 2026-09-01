# 69 — La cura che avevo proposto io costa sei ancore vere su diciotto, e il banco che la promuoveva l'avevo scritto io

*ws6/Aldo — 1 settembre 2026, 21:12. Ritira la raccomandazione del [67](67-la-data-nella-domanda-spegne-la-risposta.md).*

Nel `67` avevo scritto, in grassetto: **«il candidato alla cura è il trigger»** —
cioè la regex `_AS_OF_ANCHOR_RE`, che accetta l'articolo «il» (e `on` in inglese)
come ancora retrospettiva. **L'ho misurato, e la raccomandazione non regge.**

## ① Il banco: due usi della stessa data

```
ANCORA   «cosa SAPEVAMO al 18 luglio 2026»    → lo stato della conoscenza A
         quella data.  Il time travel è CORRETTO.
SOGGETTO «cosa È SUCCESSO il 18 luglio 2026»  → un evento di QUEL giorno.
         Il time travel è SBAGLIATO: esclude ogni fatto scritto dopo.
```

⚠️ **Le etichette sono mie e lo dichiaro.** Il criterio, scritto prima di
guardare i risultati: **ancora** se la domanda chiede lo *stato della conoscenza*
a una data; **soggetto** se chiede un *evento o un dato di quel giorno*.

## ② La regex di oggi: richiamo perfetto, precisione da testa o croce

```
ANCORE VERE  riconosciute  : 18/18 = 100.0%
SOGGETTI     lasciati stare:  2/12 =  16.7%
             IT 2/8   ·   EN 0/4
```

⇒ **Prende tutto quello che deve** e in più **l'83% di quello che non deve**.
Precisione `18/28 = 64,3%`.

📌 **Il riferimento, senza il quale il numero non dice niente**: una regola che
ancorasse **sempre** avrebbe `18/18` ancore e `0/12` soggetti — precisione
`60,0%`. ⇒ **La regex fa 4,3 punti meglio di «ancora sempre».**

✅ **E non è un difetto italiano**: sui soggetti l'inglese è **peggio** (`0/4`
contro `2/8`). I due «salvati» in italiano lo sono per caso — usano «del», che
non è in lista.

## ③ La cura che proponevo, misurata

Candidata ovvia: **«il», «l'» e `on` non ancorano più da soli**, restano le
locuzioni esplicite (`al`, `alla data del`, `fino al`, `entro`, `prima del`,
`as of`, `by`, `until`, `before`).

Sulla prima stesura del banco dava **100% su entrambi i lati**.

> 🪞 **E lì mi sono fermato, perché un 100% su un banco scritto da chi propone la
> cura è la firma di un banco ritagliato sulla cura.** Ho cercato il
> controesempio che mi mancava: **ancore vere marcate SOLO da «il» o `on`**.
> Esistono, e sono comunissime.

| | regex di oggi | cura candidata |
|---|---|---|
| ancore vere riconosciute | **18/18 = 100,0%** | **12/18 = 66,7%** |
| soggetti lasciati stare | 2/12 = 16,7% | **12/12 = 100,0%** |

**Le sei ancore vere che la cura perderebbe:**

```
[IT] qual era il prezzo in vigore il 5 agosto 2026
[IT] chi era il responsabile il 18 luglio 2026
[IT] il 3 marzo 2019 il contratto era gia firmato
[EN] what was the price on July 18, 2026
[EN] who was on call on 5 August 2026
[EN] was the contract already signed on 3 March 2019
```

⇒ ⛔ **Ritiro la raccomandazione del `67`.** Non è una cura: è uno scambio, e
scambia sei letture retrospettive corrette per dieci letture non spente.

## ④ Perché nessuna regola sulle preposizioni può farcela

Le due popolazioni **si sovrappongono esattamente sulla marca**:

| | domanda | marca |
|---|---|---|
| **ancora** | «qual **era** il prezzo in vigore **il** 5 agosto 2026» | `il` + data |
| **soggetto** | «quanti fatti sono stati scritti **il** 5 agosto 2026» | `il` + data |

Identiche nella preposizione, opposte nell'uso. 🔑 **Il discrimine non è la
preposizione: è il verbo e il suo aspetto** — *«qual **era**»* (stato a una data)
contro *«sono stati **scritti**»* (evento in quella data). Un criterio che
guarda solo la preposizione **non ha l'informazione** per decidere, e nessuna
lista di preposizioni gliela dà.

⚠️ E una lista di **verbi** sarebbe la terza classe di difetto che questo repo
documenta — *«liste monolingue»* — moltiplicata per ogni lingua che il prodotto
accetta.

## ④-bis La terza via — allargare il pool invece di stringere il trigger — è falsificata

`recall_as_of` prende `k×6` risultati e **poi** filtra. Ipotesi ragionevole: se
il pool fosse più largo, i fatti **vecchi** che stanno oltre quella soglia
sopravvivrebbero, e la lettura migliorerebbe **senza toccare il trigger**.
Misurata il 02/09 alle 01:19, `k=10` contro `k=34` (pool da 60 a 204, ×3,4):

```
domande datate provate                              :  8
serviti con pool 60                                 : 72
serviti con pool 204 (troncati a 10, confronto equo): 80   (+11%)
domande con PIÙ risultati                           :  1
domande in cui il FATTO GIUSTO torna grazie al pool  :  0
```

⛔ **Zero recuperi.** E il motivo è quello che il [67](67-la-data-nella-domanda-spegne-la-risposta.md) aveva già isolato: i fatti che
rispondono sono **nati dopo** la data della domanda, quindi **non sono «oltre
k» — sono esclusi per contratto**. Nessuna dimensione di pool li riporta.

⇒ 🔑 **Il ventaglio si chiude per ESCLUSIONE, non per assunzione:**

| via | esito |
|---|---|
| stringere il **trigger** | ❌ costa **6 ancore vere su 18** (§③) |
| allargare il **pool** | ❌ **0 recuperi** su 8 domande (qui) |
| **dichiarare** l'ancoraggio | ✅ fatto — e il rimedio che suggerisce riporta il fatto al **rango 1**, 3 su 3 ([70](70-la-cura-copre-il-caso-raro-e-tace-su-quello-frequente.md) §⑤-bis) |

⚠️ **Otto domande sono poche**, e il `+11%` di risultati serviti dice che il pool
qualcosa aggiunge — solo **non la risposta**. Chi volesse riaprire la via deve
mostrare un recupero, non un aumento di volume.

## ⑤ Allora la cura qual era? Quella già fatta

Il danno del falso ancoraggio è **una risposta vuota**; il danno del mancato
ancoraggio è **una risposta con i fatti di oggi**. Non sono simmetrici, ma
soprattutto: **il primo adesso si dichiara.**

`letto_al_passato` (commit `5f84f8a5`, più `6d79f676` sulla data che slittava)
fa dire alla porta: *«la domanda nomina una data, quindi è stata letta come
"cosa risultava AL 18/07/2026" — e a quell'istante non c'era nulla. Se invece la
data era l'OGGETTO della domanda, rifalla senza `as_of` o togli la data.»*

⇒ **Il difetto del `67` non andava curato spegnendo il trigger: andava reso
visibile, ed è già stato fatto.** Un trigger che sbaglia e lo dichiara costa un
messaggio; un trigger più stretto costa sei letture su diciotto.

## ⑥ Cosa NON prova

⚠️ **Il campione è mio, e bilanciato da me**: 18 ancore e 12 soggetti non sono le
proporzioni del traffico reale — che **non conosco**, perché il journal non
registra il testo delle query (`67` §⑦). **La precisione `64,3%` vale su questo
mix, non sull'uso vero.**
⚠️ **Le etichette sono un mio giudizio**, dichiarato in §① e applicabile in modo
diverso su qualche caso di confine.
✅ **Quello che regge indipendentemente dal mix**: esistono ancore vere e
soggetti che condividono **la stessa identica marca superficiale** (§④). Questo
è un fatto sulla lingua, non sul campione, e da solo basta a dire che una regola
sulle preposizioni non può separarli.
❌ **Non ho provato** che un criterio sul verbo funzionerebbe: non l'ho scritto e
non l'ho misurato. Ho solo mostrato dove sta l'informazione che manca.

---
*Banco: `banchi/ws6-ancora-o-soggetto.py`. Nessun modello, nessuna scrittura:
`extract_as_of` è una regex pura.*
