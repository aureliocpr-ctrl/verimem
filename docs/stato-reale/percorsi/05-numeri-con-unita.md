# Numeri con unità — runbook

**Chi è.** Un agente che raccoglie misure: metri quadri, euro, giorni, pezzi. Per
lui una cifra senza unità non è un dato, e **due unità diverse sulla stessa cifra
sono due fatti diversi**, non un aggiornamento.

Eseguito dal wheel `verimem 0.7.6` da PyPI, ambiente pulito, il 18/09.

## Il preambolo
Come in `04`: venv, `pip install verimem`, `verimem doctor`.

## I passi

### 1 · Scrivi una misura con la sua fonte
```bash
verimem save "Il capannone 12 misura 450 metri quadri." \
  --topic <un/tuo/argomento> \
  --source "Perizia del 2026-09-01: il capannone 12 misura 450 mq."
```
✅ `admitted`, `grounding_score=99.64`, `judged=True`.

### 2 · 🔴 Scrivi la STESSA CIFRA con un'UNITÀ DIVERSA, e la stessa fonte
```bash
verimem save "Il capannone 12 misura 450 metri cubi." \
  --topic <lo stesso argomento> \
  --source "Perizia del 2026-09-01: il capannone 12 misura 450 mq."
```

**Ricevuta attesa**: fermato, oppure ammesso **ma segnalato**, e la ricevuta
nomina la grandezza in conflitto.

🔴 **MISURATO IL 18/09 — non succede né l'uno né l'altro:**
```
admitted id=32e2cbc406a6 topic='prova/percorso1'
  L3-supersession — a newer same-source value supersedes a stored fact
     this write updates an earlier value from the same source; the older value
     is superseded.
  grounded 97.3 — scored as supported by the source
  superseded 63bb19bf7697 — no longer served by default recall
```

⇒ **Un cambio di UNITÀ a parità di cifra viene letto come un'evoluzione della
stessa fonte.** Il fatto giusto (`450 metri quadri`) viene **superato** da uno che
la fonte non sostiene, e il giudice gli dà **97.3**. Un metro cubo non è un metro
quadro: non è un aggiornamento, è un'altra grandezza.

### 3 · Guarda che cosa serve adesso il richiamo
```bash
verimem recall "<le parole della misura>"
```
🔴 **Misurato**: `- Il capannone 12 misura 450 metri cubi. [0.87] moat 97.3`
La memoria serve come **corrente** il valore con l'unità sbagliata.

### 4 · Chiedi il verdetto di fiducia sulla stessa affermazione
```bash
verimem trust "<l'affermazione>" --source "<la stessa fonte>"
```
🔴 **Misurato**:
```
Anti-confab trust check   TRUSTED ✓
  checked:     L1 lexical screens, L4 moat
  the moat judged the source at 97.3
```

🔑 **La riga `checked:` è il meccanismo**: hanno girato **lo screen lessicale e il
moat**.

## ⚠️ QUELLO CHE AVEVO CONCLUSO DA QUESTA RIGA ERA SBAGLIATO

Il 18/09 avevo scritto: *«il controllo che confronta le quantità non compare fra
quelli eseguiti»*. **È falso, e l'ho falsificato la sera stessa dalla porta
libreria.** `L4.1` **esiste, gira e funziona**: sei scritture, una sola fonte
(*«Perizia del 2026-09-01: il capannone 12 misura 400 mq.»*), wheel `0.7.6`.

    caso                                              esito         punteggio  layer che gira
    A  sostenuta dalla fonte (400 mq)                 admitted          98.55  []
    B  CONTRADDICE: 900 metri quadri                  quarantined        0.81  L4-grounding, L4.1
    C  INVENTA: tre piani interrati e un eliporto     admitted          89.98  []
    D  FUORI TEMA: la torre Eiffel è alta 330 m       quarantined        0.24  L4-grounding, L4.1
    E  stessa CIFRA, unità diversa: 400 metri CUBI    admitted          96.01  []
    F  cifra diversa di UNO: 401 metri quadri         quarantined        5.53  L4.1, L4-grounding

**Una differenza di UN metro quadro viene fermata (5.53). Il passaggio da
superficie a volume passa con 96.01.** Il motivo sta scritto nei rifiuti: B e D
cadono con *«il claim afferma un valore che la fonte non contiene: 900 metro /
330 metro»*. ⇒ **`L4.1` confronta il VALORE, non l'unità**: `400 == 400`, quindi
non ha nulla da segnalare.

🔴 **Non era un'assenza: era una cecità.** La differenza cambia la cura — non
«aggiungere un controllo sulle quantità», ma **far confrontare anche l'unità a
quello che c'è già**. Chi cura guardi lì.

📌 **E il caso C va letto con la difesa che il prodotto dichiara.** «tre piani
interrati e un eliporto» passa a 89.98 con `layers=[]` — nessun controllo gira,
perché non c'è una quantità da confrontare. Ma la ricevuta della CLI dice:

    grounded 98.5 — scored as supported by the source
                    (the judge's score, not a check that it follows)

⇒ Il prodotto **non promette** che la fonte implichi la proposizione: dichiara che
quello è il voto del giudice. È un **limite dichiarato**, e va difeso da chi lo
scambia per un difetto — cosa che stavo per fare io. ⚠️ **Quell'avvertenza c'è
sulla CLI e NON nel dict della libreria**, che porta `score`, `threshold`,
`margin` e `confidence_tier` senza la riga che dice come si legge quel numero.

## ✅ LE TRE PORTE CONCORDANO BIT PER BIT, e questo è il verde

    caso                       CLI               libreria          MCP               uguale
    A  400 metri quadri        adm  98.5478515625  adm  98.5478515625  adm  98.5478515625   SI
    C  eliporto (inventa)      adm  89.9788284301  adm  89.9788284301  adm  89.9788284301   SI
    E  400 metri CUBI          adm  96.0053558349  adm  96.0053558349  adm  96.0053558349   SI
    F  401 metri quadri        qua   5.5289530754  qua   5.5289530754  qua   5.5289530754   SI

**Verdetto e punteggio coincidono a tutte le cifre decimali.** Quello che cambia
fra le porte non è il giudizio: è **quanta della sua ragione la ricevuta ti fa
vedere**, e la porta che ne mostra meno è quella che un agente usa di più:

| | come dichiara il limite |
|---|---|
| **MCP** | `"moat": "judged 96.0 — the source SCORES as supporting this fact: that is the judge's score, not a check that the fact follows from it"` |
| **CLI** | `grounded 96.0 — scored as supported by the source (the judge's score, not a check that it follows)` |
| **libreria** | 🔴 `{"moat": "passed", "grounding_score": 96.005…}` — **l'avvertenza non c'è** |

⚠️ **I VERBI sono diversi anche in scrittura**: `save` (CLI), `add(content=…)`
(libreria), `hippo_remember(proposition=…)` (MCP). Tre nomi per la stessa cosa —
ma la porta MCP rifiuta bene: *«the required key `proposition` is missing or
blank; these keys were not recognised and were IGNORED: ['content']»*.

## 🔑 IL PRODOTTO SA GIÀ CHE QUESTA SCRITTURA È SOSPETTA, E NON LO DICE

Dal log della porta MCP, sul caso E:

    coherence_warning  details='jaccard=0.75'  kind=near_duplicate
                       fact_id=af2a01ff644f  other_fact_id=f62eed3830d6

⇒ «400 metri cubi» **viene riconosciuto come quasi-duplicato** di «400 metri
quadri», con il suo punteggio. Ma la ricevuta che l'agente riceve porta:

    "anti_confab_warnings": []

**Il segnale è calcolato, finisce nel log, e non entra nella ricevuta.** È la
classe della *giuntura* — un verdetto calcolato e non letto — e qui vale doppio,
perché è esattamente il caso che `L4.1` non vede.

🎯 **La cura più economica non è scrivere un controllo sulle unità: è far
arrivare alla ricevuta un segnale che il prodotto già produce.** Chi cura ha il
`fact_id`, il `jaccard`, la riga di log e il campo vuoto da riempire.

⚠️ **Il limite di questa misura**: le tre porte sono confrontate **in scrittura**,
su quattro casi e una fonte sola. Il resto del percorso ① (correzione, storia,
`as-of`) è stato fatto su CLI e libreria, **non** su MCP.

## Tre modi di cadere
1. **Il comando non esiste** → la pagina è sbagliata.
2. **La ricevuta è diversa dall'attesa** → difetto del prodotto. **È il caso dei
   passi 2, 3 e 4, ed è aperto su tre comandi.**
3. **È un rosso già noto** → si annota e si prosegue.

## Sei arrivato quando
1. la scrittura del passo 2 è **fermata o segnalata**;
2. la ricevuta **nomina la grandezza** in conflitto, non solo «contraddizione»;
3. il richiamo serve **il valore con l'unità giusta**;
4. le tre porte si comportano **uguale**.

Al 18/09, **sera** (dopo il giro sulla seconda porta):

- **(1) e (2) rossi**, e ora con il meccanismo: `L4.1` gira ma confronta la cifra,
  non l'unità.
- **(3) rosso**: il richiamo serve il valore con l'unità sbagliata.
- **(4) VERDE su TUTT'E TRE le porte**: CLI, libreria e MCP danno lo stesso
  verdetto con lo stesso punteggio a tutte le cifre decimali, sui quattro casi
  qui sopra. ⚠️ Misurato **in scrittura**; il resto del percorso non su MCP.

⇒ Resta il percorso messo peggio, ed è quello su cui il prodotto ha più prove
interne — 221 test interni misurati il 15/09, 33 file su 37 senza una riga che
tocchi una porta. **Il prodotto sa distinguere le unità a livello di funzione; a
livello di porta, a parità di cifra, no.** È la ragione per cui questo percorso
esiste, e ora ha i suoi numeri invece del suo sospetto.
