# La prova conservata basta a rifare il giudizio? Sì al tetto di oggi, no se lo si abbassa

**02/09/2026, 12:55 · ws6/Aldo · muro M6, anelli ①②③ · banchi `ws6-m6-*.py`**

Il muro M6 era *«su 9426 fatti che dichiarano una fonte, 1692 non ne conservano
il testo»*. L'anello ① l'ha riprodotto e **spaccato in due**: la fonte perduta è
debito storico già curato, il **tetto dei 400** è vivo. Gli anelli ②③ chiedono se
quel tetto costi qualcosa, con due predizioni scritte **prima**.

## ① La baseline si riproduce — ma non con la definizione ovvia

```
python docs/stato-reale/banchi/ws6-m6-baseline-fonte-non-conservata.py

«dichiara una fonte» =                     totale   senza    =400
source_signature  (la FIRMA — def. del fatto) 9487    1692     189
grounding_score   (il GIUDIZIO)              10573    2778     189
```

**`1692` identico** al fatto originale. Con la definizione naturale
(`grounding_score`) il numero è `2778`: la definizione del fatto era
`source_signature`, e l'ho trovata **leggendo la source del fatto** invece di
indovinarla. Le due non sono lo stesso insieme, e nella differenza c'è un reperto
che il muro non contava: **1167 fatti hanno un punteggio e né firma né testo**,
575 di essi a `100.0` — un voto e nulla con cui rivederlo.

✅ **Non sono un artefatto**: chiesto al prodotto in store isolato, una scrittura
senza fonte lascia **tutti e tre i campi NULL** (`score`, firma, span). Il
punteggio implica una fonte ⇒ **quei 1167 ne avevano una**.

**Vivo o storico: storico**, con due date e due commit già in main — e le due
condizioni vanno separate, perché mescolarle attribuisce la cura al giorno
sbagliato:

```
FIRMA   100% fino al 08-03 · 65,0% il 08-04 · 0% dal 08-05   <- 7bb4df42 (04/08 16:40)
SPAN    100% fino al 08-07 · 50,6% il 08-08 · 1,8% il 08-12  <- 35dd263f (08/08 14:13)
```

`35dd263f` **è** M6, dichiarato con le stesse parole: *«verimem usa la fonte per
giudicare e poi la BUTTA … la verifica c'era, la PROVA no»*. Dichiara anche che
**il debito è irrecuperabile** — la fonte non è nel journal, e il commit fa solo
`ALTER TABLE ADD COLUMN`. ⇒ **Nessun backfill è possibile.**

## ② La prima predizione: falsificata

`grounding_gate.py:404` dice che lo span salvato *«dice cosa è stato SALVATO, non
cosa il giudice ha VISTO»* — il giudice legge fino a ~1500 caratteri, la
persistenza ne salva 400. Ne avevo tratto una predizione:

> **A (troncati)** mediana della caduta ≥ 5 punti, ≥3 su 10 sotto 90 ·
> **B (interi)** mediana < 2, ≤1 sotto 90

```
A troncati (=400)    mediana caduta 0.02 · sotto 90: 0/10
B interi  (<300)     mediana caduta 0.00 · sotto 90: 0/10
```

⛔ **Falsificata.** Il punteggio di grounding **non cade**. E il controllo è
pulito: `0.00` esatto su 10 su 10 nel braccio B, cioè giudizio deterministico su
input identico — il banco discrimina, la predizione era sbagliata.

## ③ Ma avevo guardato il campo sbagliato

Nella stessa tabella, **lo status cambiava**: `L4.1` si attivava **3 volte su 10**
fra i troncati e **1 su 10** fra gli interi, a punteggio invariato (~99,98).

⚠️ **Tre contro uno su dieci non decide nulla**, e i due gruppi non sono lo stesso
materiale: i fatti con span lungo hanno fonti più ricche di numeri, quindi danno
a `L4.1` più occasioni **indipendentemente dal troncamento**. Serviva un
confronto appaiato — e il taglio posso farlo io.

**Seconda predizione, scritta prima** (fatto `3be3e49bc45f`, 12:54): *span intero
≤1 su 12 · span tagliato ≥4 su 12*. Dodici fatti con span **non troncato**
(300-399 caratteri), ognuno rigiudicato **due volte**, unica variabile il taglio:

```
L4.1 si attiva:   span INTERO 2/12   ·   span TAGLIATO a 200  9/12
quarantinati:     span INTERO 2/12   ·   span TAGLIATO        9/12
```

⇒ **Tagliare la prova fa accusare fatti già ammessi: da 2 su 12 a 9 su 12.** La
predizione coglie direzione e grandezza; sbaglia il controllo di uno (2 invece di
≤1). Il meccanismo è quello che il codice già descriveva: `L4.1` chiede allo span
se contiene i numeri del claim, e la porzione tagliata non li contiene più.

## Cosa questo dice, e cosa NON dice

✅ **Il meccanismo è dimostrato**: la riverificabilità dipende da **quanta** prova
si conserva, e sotto una certa soglia il gate accusa fatti veri.

⚠️ **Il tetto di OGGI non è dimostrato dannoso.** Ho tagliato a **200**, non a
400. Al tetto reale il confronto dava 3 contro 1 su 10 — troppo debole per
concludere. I fatti che toccano il tetto sono **189 su 7802 = 2,4%**.

🔑 **E il commento di `_GROUNDING_SPAN_BUDGET` è vero ma incompleto.** Dice: *«Non
è una soglia di comportamento: alzarlo conserva più contesto, abbassarlo meno, e
nessun verdetto si muove in nessuno dei due casi»*. È **corretto per il verdetto
live**, che usa la fonte piena e non lo span. **Non vale per il verdetto
rifatto** — che è esattamente ciò per cui lo span esiste, visto che `35dd263f` lo
introdusse come *«la PROVA della verifica»*. ⇒ **Abbassare quel budget è una
scelta a costo non nullo, e la riga accanto dice il contrario.**

❌ **Non ho trovato la soglia**: fra 200 (9/12) e ~340 (2/12) c'è un punto di
rottura che non ho cercato. Servirebbe una scala di tagli — 350, 300, 250, 200 —
sugli stessi fatti, ed è il passo naturale successivo.
⚠️ **Dodici fatti, italiano, una sola classe di fonte.**
⚠️ **Il rigiudizio non è la riverifica reale**: nessuno oggi rigiudica i fatti
salvati. Il costo misurato è potenziale — si paga se e quando la riverifica (o la
cache su `hash(source, fatto)` di T4.4) verrà attivata.

## Ricaduta su T4.4 (@ws5)

La cache del verdetto su `hash(source, fatto)` presuppone la fonte conservata:
**vale per i fatti dall'08/08 in poi**, non per i 2859 storici — ed è un limite
del denominatore, da dichiarare, non da curare. La mia ipotesi che il tetto
producesse **collisioni di hash** è **falsificata**: sui 40 gruppi di span
troncati che condividono il testo, **zero** hanno firme diverse.

**Firme su questo documento**: ws6.
