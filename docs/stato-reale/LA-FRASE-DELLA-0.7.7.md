# La frase della 0.7.7 — dal lato di chi la installa

**ws7 Iris (Product Owner) · 06/09, scritta alle 08:20 e RIMISURATA alle 08:45 · base
`v0.7.6..origin/main` = `460f230e`** *(alle 08:20 era `13fa323f`: main si è mosso sotto la
pagina, ed è la ragione per cui in cima c'è un riquadro invece di una riscrittura muta)*

⚠️ **Questa pagina SOSTITUISCE la frase che avevo scritto stanotte.** Quella diceva
*«una correzione supera il vecchio»* e si appoggiava a **T14**, che **non entra**. Una
frase di vetrina che promette una cura non entrata è la cosa peggiore che questo ruolo
possa produrre: la ritiro io prima che la legga un utente.

---

## ① La frase

> ### 0.7.7 — la versione in cui il prodotto smette di tacere.
>
> Quando toglie un fatto dalla risposta, dice **quale** e **perché**.
> Quando ferma una scrittura, dice **quale pezzo** è caduto e su quale controllo.
> Quando non lo sa, risponde **«non lo so»** invece di **«nessuno»**.

> 🔁🔴 **RIMISURATO alle 08:45 su `460f230e`, e tre affermazioni di questa pagina sono
> cadute.** Alle 08:20 avevo misurato su `13fa323f`. Poi **main è andato rosso** e il lead
> ha revertato i due pezzi del muro 1 (`890a1c04` reverta 3c, `460f230e` reverta 3a).
> ⇒ **D-1 non è curato affatto** (non «in parte»), **le porte non dicono più quale claim
> è stato fermato**, e i campi `claims_verdict` · `claims` · `claim` · `decomposed` ·
> `layer` **non sono più in `main`**. Le sezioni sotto sono corrette. *La frase regge —
> il suo filo è la scadenza e `as_of`, che i revert non toccano — ma il numero no, e un
> numero che non si rimisura quando il terreno si muove è un numero falso.*

## ② Il numero dietro la frase, e come rifarlo

```
commit fra v0.7.6 e 460f230e                              125
   di questi, che toccano verimem/ (il prodotto)           32
   di questi, che aggiungono una DICHIARAZIONE al prodotto 13      ← poco più di un terzo
```

> 🪞 **E il righello si è rotto proprio qui, in un modo che vale più del numero.**
> Al primo giro contava **15**, e due di quei quindici erano **`890a1c04` (un REVERT)**
> e **`13fa323f` (il commit che quel revert annulla)**: il messaggio di un revert
> **ripete il titolo** del commit annullato, quindi un cambiamento tolto viene contato
> **due volte come aggiunto**. Un righello che legge i *messaggi* di commit sbaglia
> sistematicamente nella direzione del gonfiaggio ogni volta che qualcosa viene tolto.
> 📌 Poi ho scritto **12**, deducendolo per sottrazione invece di misurarlo: sbagliato
> anche quello. Il numero giusto — revert **e** loro bersagli esclusi, con i bersagli
> letti dal corpo (`This reverts commit …`) e non indovinati — è **13**.
> ⇒ **Il conteggio sui CAMPI, sotto, non ha questo difetto**: un revert toglie il campo
> dal diff, quindi la cosa si corregge da sola mentre il titolo no. È la ragione per cui
> i due righelli vanno tenuti entrambi.

⚠️ **I 13 li ho contati sui MESSAGGI di commit**, che sono una *rappresentazione* del
cambiamento e non il cambiamento — la forma che questo ruolo paga più spesso. Quindi ho
rifatto il conto **sulla cosa**: i campi nuovi comparsi nelle risposte del prodotto.

```
git diff v0.7.6..origin/main -- verimem/ | grep "^+" | grep -oE '"[a-z_]{4,30}":'

as_of · as_of_scartati · as_of_scartati_ignoto      cosa il filtro temporale ha tolto
esclusi · expired_reason · gia_ritirato · corrente  cosa è stato tolto, e per quale ragione
non_ancora · quarantined · grounding_score          lo stato del giudizio
```

⇒ **I due righelli concordano**, e il secondo non passa dalle mie parole né da quelle di
chi ha scritto i commit: sono le chiavi che un utente vede nella risposta.

## ③ Le quattro cose che un utente vede cambiare

1. **Guardare al passato funziona, e dice cosa ha scartato.** `as_of` era accettato e
   ignorato (**D-6**, P0): adesso le porte lo applicano, e quando non sanno quanti fatti
   ha tolto **rispondono «non lo so»** invece di «nessuno» — la differenza fra un dato e
   un'assenza travestita da zero.
2. **La scadenza non è più muta.** `recall`, `ask`, la CLI e la porta MCP dichiarano i
   fatti che la scadenza ha tolto, e la scheda di un fatto dice se è scaduto.
3. **Un fermo si può leggere — solo a metà.** La porta MCP dice **perché** il moat non è
   girato (`f1fe58e0`), e la promozione documento→fatto scrive `quarantined_by`.
   ~~Le tre porte dicono quale claim è stato fermato~~ — 🔁 **cadeva qui il 06/09 08:45**:
   quel pezzo (`13fa323f`) è stato **revertato** perché main era rosso, e con esso i campi
   `claims_verdict` · `claims` · `layer` · `decomposed`. **Torna quando il muro 1 rientra.**
4. **L'avvio dichiara il suo costo.** Prima il primo `remember` con fonte poteva bloccarsi
   per minuti **in silenzio** (**T1**, P0): adesso l'avvio dice se scalderà il giudice,
   quanto costa e come spegnerlo.

## ④ 🔴 Il perimetro — cosa la 0.7.7 NON risolve

**Va scritto accanto alla frase, non dopo.** Un annuncio che tace i P0 aperti ripete
esattamente il difetto che la 0.7.7 cura.

| ticket | stato nella 0.7.7 | in una riga |
|---|---|---|
| **D-1** self-claim in coda a una frase vera | **NON entra** | la cura (`22947ae9`) è stata **revertata alle 08:41**: fermava un **fatto di terzi VERO** — *«Il comando warmup è iniziato alle 14:50:24 ed è finito alle 14:53:19.»* — perché la coda nuda escala `L1.13` senza il soggetto. Il presidio che l'ha colto **esisteva già**. L'innesto resta sul ramo. *(Alle 08:20 questa riga diceva «curato in parte»: valeva su `13fa323f`.)* |
| **T14** il gate decide, il verdetto non arriva su MCP | **NON entra** | cura non in main |
| **T16** l'SDK scrive dove gli dici, la CLI no | **NON entra** | cura di @ws2 su ramo `16ce261e`, non in main |
| **T8-bis** l'avviso di `doctor` sulla copertura del giudice non si spegne mai | **NON entra** | `doctor.py` **invariato** fra `v0.7.6` e main — verificato col diff, dopo che una mia riga diceva il contrario. *Formulazione rifatta il 06/09 su lettura di @ws8: «l'exit code non discrimina» era falsa.* |

## ⑤ La riga onesta per il CHANGELOG (@ws8 Corrado)

> La 0.7.7 non aggiunge capacità: **rende leggibile quello che il prodotto già faceva in
> silenzio.** Quattro difetti aperti restano aperti e sono elencati in
> `docs/stato-reale/GRAVITA-DIFETTI.md`.

## ⑥ Cosa serve per poter dire di più su D-1

Un banco delle **sette forme** contro il gate — le stesse sette del reperto originale (una
frase, due, una subordinata, un soggetto non umano, tre parole, e le due in inglese) sulle
tre porte. **Non l'ho eseguito**: i banchi sono fermi per la RAM.

🔁 **E adesso serve a un'altra domanda.** Con la cura revertata, D-1 è aperto e il banco
non misura più «quante delle 7 sono curate»: misura **quante di esse la cura fermerebbe
senza fermare un vero**. Perché la cura non è caduta su una forma che *mancava* — è caduta
su un **falso positivo**, un fatto di terzi vero fermato. ⇒ **la mia scala serve anche
nell'altro verso**: un difetto P0 non giustifica una cura che ne apre un altro, e il banco
delle sette forme va accompagnato da quello dei **veri composti che devono passare**.

*(Il sospetto che la cura fosse monolingue — classe ③ del nostro metodo — l'ho falsificato
leggendo il codice: `decomponi()` tratta l'inglese esplicitamente, `[a-z]{3,}ed` e ` and `,
con i commenti che lo dicono. Il limite vero è un altro, ed è la subordinata.)*
