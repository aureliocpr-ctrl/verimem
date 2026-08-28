# ⑮ La banda decide, e **nessuno decide la banda**

**Misurato il 29/08/2026 fra le 00:45 e le 01:44** · SHA per cella nel registro
(`5dc1a20c` → `90fc7fa8`) · tutte le misure **fuori da pytest**, un processo per
caso · celle **W7-39 · W7-42 · W7-43 · W7-47**.

Il dossier ⑬ ha un asse: **quanto** testo circonda la prova. Il ⑭ un secondo:
**com'è fatto** quel testo. Questo chiude tutti e due, e la risposta è che
**cercavano nel posto sbagliato**.

---

## In una riga

Il gate ha una **banda di incertezza `[40, 80]`**: sotto rifiuta, sopra ammette,
**in mezzo non decide**. Il punteggio di una famiglia intera sta a cavallo di
quel bordo, e **il testo lo sposta di 10–20 punti per pochi caratteri**. Chi
dovrebbe decidere quei casi — la *band escalation* — ha **due fragilità in
serie**, e quando non consegna il fatto **resta fermo per sempre**.

---

## 1. Quattordici ipotesi cadute, e il presupposto che nessuna aveva verificato

Il dossier ⑬ elencava **14 ipotesi** cadute nel predire quali scambi di
attribuzione entrano, e concludeva: «*nessuna regola sui testi predice il
verdetto*».

**Tutte e quattordici davano per buono che il verdetto fosse una FUNZIONE del
testo. Nessuna l'aveva verificato** (cella **W7-39**):

```
   5 ripetizioni ALTERNATE, due coppie
   VERO     score 99.97941589355469  × 5     ampiezza 0.0000   sd 0.0000
   SCAMBIO  score  1.9731502532958984 × 5    ampiezza 0.0000   sd 0.0000
```

⇒ **Ripetibile al bit.** La variabile **è** nel testo — e le 14 cadute **non
hanno la scusa del rumore**: il risultato negativo ne esce **più forte**.

⚠️ **Limite che vale quanto il risultato**: qui il giudice è il **CE locale**,
deterministico per costruzione ⇒ la ripetibilità è l'esito **atteso**. La *band
escalation* usa `claude -p` **senza `--model`**: lì non è misurata.

## 2. La risposta: non c'era nessuna variabile del testo da trovare

Cella **W7-42**. Letto il gate: `band_enforced=True` · `cut=40.0` ·
**`tau_hi=80.0`**.

E i punti che mi avevano sorpreso si spiegano **tutti**:

```
   nuda    72.1   DENTRO la banda   → trattenuto
   +6      90.0   sopra tau_hi      → ammesso
   +18     77.4   DENTRO la banda   → trattenuto      ← il «rientro» era questo
   +24     93.9   sopra tau_hi      → ammesso
   assente  0.4   sotto il cut      → rifiutato
```

⚖️ **Ma sette punti spiegati DOPO non sono una predizione**: qualunque regola
inventata dopo i dati li spiega. Quindi la regola è stata **dichiarata prima** —
`persist ⇔ score ≥ 80`, **senza usare niente del testo** — e verificata su **12
delta mai misurati × 2 popolazioni**:

```
   giuste 24    sbagliate 0
   delta=2 → 78.6 → downgrade        delta=4 → 80.7 → persist
```

🔑 **Le quattordici ipotesi cercavano una regola sul TESTO per un fenomeno che è
una soglia sul PUNTEGGIO.** Il contorno non «apre» niente: **muove un numero
attraverso un confine**.

## 3. E non è un caso di laboratorio: è la coda

Cella **W7-43**, misurata sul corpus vero. **Due denominatori dichiarati** —
citarne uno solo è il modo classico di ingannare senza mentire.

```
   1079 quarantinati vivi · 608 giudicati (56,3%) · 471 SENZA punteggio (43,7%)

   fascia                  n     su giudicati    su tutti
   sotto il cut (<40)     424       69,7%         39,3%     il gate ha lavorato
   IN BANDA [40, 80)       79       13,0%          7,3%     il gate NON ha deciso
   sopra tau_hi (≥80)     105       17,3%          9,7%     il moat li approvava
```

⇒ **184 su 608 (30,3%) non sono stati giudicati insostenibili**: 79 aspettano un
verdetto che non arriva, 105 hanno il moat favorevole e sono fermati da altro
(di cui **53 da `L4.1`**).

## 4. 🔴 E chi dovrebbe decidere quei 79 ha due fragilità **in serie**

Cella **W7-47**, letta nel codice, **zero esecuzioni del giudice**.

`anti_confab_gate.py:2691` chiama `escalate_band` nel ramo della banda, **solo se
`grounding_llm is None`**. E il commento a `:2681` dichiara l'esito del
fallimento:

> «*Fail-soft: **None → held for review exactly as before**; an unreadable
> verdict never admits.*»

**Le tre vie, chieste al prodotto su questa macchina:**

```
   _mode()                    = 'auto'      accesa
   _local_ollama_available()  = False       la via LOCALE non esiste qui
   _resolve_cli()             = claude.EXE  resta solo quella senza --model
   _timeout_s()               = 90.0        fino a 90 s PER SCRITTURA
```

**E il parser accetta due sole forme:**

```
   'SCORE: 85'                  → 85.0        'The score is 85.'          → None
   'Score: 85'                  → 85.0        'I would say 85 out of 100' → None
   '85'                         → 85.0        ''                          → None
```

🔑 **Le due in serie**: ① il **modello non è fissato**, quindi non si sa in che
**forma** risponde; ② il **parser non tollera la prosa**, e una risposta
discorsiva vale `None`. ⇒ **`None` significa fatto trattenuto, e i 90 secondi
sono spesi per niente.**

📌 È la stessa dipendenza dal modello che `docs/CLAIM-RECEIPTS.md:24` misura sul
**merito** — «*dei 19 confab che sonnet ammetteva a 70, **opus ne chiude 9***» —
qui applicata alla **forma**.

---

## 5. Cosa NON dice questo dossier

- **Non ho eseguito il giudice della banda.** Che i 79 siano fermi *per* le due
  fragilità è **plausibile e non misurato** — e stanotte ho già ritirato due
  spiegazioni (celle W7-35 e W7-45), quindi questa non la pubblico come tale.
- La ripetibilità del §1 vale **sul CE locale**, non sul giudice della banda.
- ~~I **471 senza punteggio** non sono stati indagati.~~ **Indagati alle 01:55
  (cella W7-48): sono ARCHEOLOGIA, e senza un giorno di sovrapposizione** —
  senza giudizio dal **2026-05-10 al 2026-07-19**, giudicati dal **2026-07-28**
  in poi. Il campo ha iniziato a popolarsi fra il 19 e il 28 luglio, e da allora
  **ogni quarantinato ha un punteggio**.
  🔑 **E questo corregge il §3 qui sopra**: il denominatore dello **stato
  attuale** non è 1080, è **609**. La colonna «su tutti» è **diluita da un'era
  chiusa** — le quote da citare sono quelle **sui giudicati**.
- Il §3 fotografa le **01:18**; il corpus si muove — 1074 a mezzanotte, 1079
  un'ora dopo, e siamo in otto a scrivere.

## 6. Cosa servirebbe, e non è mio da scrivere

Qui **non serve una cura di layer**. Servono **due righe**, in due punti diversi:

1. **fissare il modello** della band escalation — il codice per farlo esiste già
   in casa, `llm.py:244-245` (`cmd += ["--model", str(model)]`), e
   `swarm/spawn.py:66` lo usa;
2. **allargare il parser** a una risposta che *contenga* un punteggio.

⚠️ **La seconda ha un rischio da misurare prima**: un numero in prosa può non
essere il punteggio. Chi la scrive misuri **entrambe le popolazioni**.

## 7. I banchi

`il-verdetto-e-una-funzione-del-testo.py` ·
`bisezione-quale-articolo-fa-entrare-lo-scambio.py` ·
`dove-sta-la-soglia-e-serve-che-il-testo-porti-numeri.py` ·
`non-e-una-soglia-di-caratteri-e-la-banda-a-80.py` ·
`quanti-quarantinati-sono-IN-BANDA-e-non-sotto-il-cut.py`

Ognuno porta **un controllo che poteva fallire**, e stanotte **tre hanno
fallito**: uno mi ha impedito di pubblicare «zero falsi allarmi» misurando un
layer spento, uno ha ribaltato un aggregato che nascondeva due comportamenti
opposti, uno ha falsificato la mia spiegazione sui 53.

🔑 **La lezione di metodo**: **quattordici congetture in due giorni, una
bisezione in dieci minuti.** Una congettura cerca *una regola* e la si può
sbagliare quattordici volte; una ricerca cerca *il punto*, e o lo trova o dice
che non c'è.
