# Un agente che lavora un'ora — runbook

Percorso **U-A** di `docs/stato-reale/PERCORSI-UTENTE.md` (definizione, criterio
di arrivo e stato stanno lì). Qui: i comandi, la ricevuta attesa, il tempo.

**⚠️ REGIME DELLA MISURA CHE CITIAMO** — e va letto prima dei numeri: gli otto
passi sono stati eseguiti il **04/09 sul pacchetto `0.7.6` da PyPI**, store
isolato, **con il modello del giudice già in cache** (28 GB sulla macchina di
chi misurava) e **senza daemon**. **Non è il regime di chi installa oggi**: la
prima scrittura con fonte a giudice freddo è un'altra cosa (vedi il passo 1).

**Legenda dei marchi**: `00-COME-SI-LEGGE.md`. ✅ misurato · 📖 letto dal codice ·
❓ da riempire.

> ⚠️ **Passo 0 obbligatorio**: `00-COME-SI-LEGGE.md`, togliere la classe di
> variabili del prodotto. Un agente che lavora un'ora eredita l'ambiente della
> shell che lo ha lanciato per tutta l'ora.

---

## I tempi che abbiamo, e quello che non coprono

✅ **Giro intero 40 s** alla seconda esecuzione, **62 s** alla prima. Prima
scrittura con fonte **16,2 s** · seconda **12,8 s** · richiamo **0,1 s** ·
CLI **1,5 s**.

🔴 **Quei 16,2 s valgono SOLO a giudice caldo.** Dalla porta degli agenti a
giudice freddo la stessa prima scrittura ha preso **313-903 s** — e in fondo
all'attesa il fatto può entrare **non giudicato**. Se stai cronometrando questo
percorso e il primo passo non torna, non è appeso: sta scaricando il giudice.

🔑 **Quindi il warmup non è un optional di questo percorso**: è ciò che sposta
quei minuti fuori dal cronometro. `00-COME-SI-LEGGE.md` lo mette al passo 2 di
`01`; qui vale uguale.

---

## Gli otto passi

### 1 · Registra un fatto **con la sua fonte**

🔴 **ANCHE QUESTA RIGA NON FUNZIONA AL PRIMO FATTO**, e cade proprio per chi
installa oggi — eseguita dal wheel `0.7.6` in un ambiente pulito il 17/09:

```
verimem save "…" --topic prova/percorso1 --lineage-to auto --source "…"
  EXIT=1
  lineage 'auto': no prior fact under topic segment 'prova'
  (omit --lineage-to for a root checkpoint)
```

⇒ `--lineage-to auto` cerca un fatto **precedente** sotto quell'argomento. Su uno
store vuoto — cioè quello di chiunque abbia appena installato — non ce n'è, e il
primo comando del percorso esce **1**. Il messaggio del prodotto è ottimo e dice
già la cura; è la pagina che prescriveva l'opzione sbagliata per il primo fatto.

```bash
verimem save "<il fatto che l'agente ha appena stabilito>" \
  --topic <un/tuo/argomento> \
  --source "<l'output, il documento, la pagina che lo sostiene>"
```

✅ **Ammesso**, e la ricevuta porta il punteggio del giudice. Misurato dal wheel
il 17/09: **26 s**, `grounding_score=98.87`, `judged=True`, `status=model_claim`,
e in fondo `root checkpoint (no prior session fact under 'prova')` — il prodotto
dichiara da sé che questo è il primo.
🔑 **Senza `--source` il giudice non gira e il fatto entra come claim non
verificato.** È la differenza fra un agente che ricorda e uno che si fida di sé.

### 2 · Lo richiama

```bash
verimem recall "<qualche parola del fatto>"
```

✅ Torna il fatto. ⏱️ ✅ **0,1 s** — il richiamo non è il costo di questo
percorso, la scrittura sì.

### 3 · Il mondo cambia — l'agente **corregge**

🔴 **LA RIGA CHE QUESTA PAGINA AVEVA SCRITTO NON FUNZIONA**, ed è una caduta
della **pagina**, non del prodotto — trovata eseguendola:

```
verimem correct "<il fatto nuovo>" --source "..."
  EXIT=2
  Usage: verimem correct [OPTIONS] {old_id} {text}
  Error: Missing argument 'text'.
```

⇒ `correct` vuole **DUE argomenti posizionali**: l'id del fatto vecchio **e** il
testo nuovo. Chi seguiva questa pagina alla lettera si fermava qui.

```bash
verimem correct <id_del_fatto_vecchio> "<il fatto nuovo>" \
  --source "<ciò che sostiene il cambiamento>"
```

✅ **Ricevuta attesa, misurata con la forma vera** (EXIT=0):

```
superseded 98893a394f53 -> 97cf616e9fc6 topic=<il tuo argomento>
branch='same-source evolution' reversible=True undo_op_id=<16 hex>
```

🔑 La ricevuta **dichiara la relazione**, non solo l'ammissione: dice quale
fatto ha superato quale, che il ramo è un'evoluzione sulla stessa fonte, e che
l'operazione è **reversibile** con un id per disfarla. Era la ❓ di questa
pagina, e la risposta è migliore di quanto chiedesse.

### 4 · Richiama di nuovo

✅ **Torna solo il corrente** (`nuovo: True · vecchio: False`). È il passo che
distingue una memoria da un archivio.

### 5 · Chiede la **storia**

```bash
verimem recall "<le stesse parole>" --with-history
```

✅ Racconta la transizione: il vecchio c'è, ma dichiarato come superato.

### 6 · 🔴 Chiede **lo stato di allora**

⚠️ **QUESTO PASSO VA RIFATTO, NON LETTO.** Nella misura del 04/09 le due porte
degli agenti **accettavano la richiesta del passato e rispondevano col presente,
senza dirlo** — il difetto peggiore della lista, perché chi chiede non ha modo
di accorgersene.

✅ **La cura è entrata** dopo quella misura. ⇒ **La riga rossa qui sopra descrive
un albero che non esiste più, e il «7 passi su 8» della pagina dei percorsi è il
conteggio di prima.**

✅ **RIFATTO IL 17/09 DAL WHEEL `0.7.6`, E IL PASSO È VERDE.** Chiesto lo stato a
un istante *precedente* alla correzione del passo 3, sulla riga di comando:

```
verimem recall "capannone 12" --as-of 1789673040
  EXIT=0
  - Il capannone 12 misura 400 metri quadri. [0.88] moat 98.9
```

⇒ Torna **il valore di allora** (400), non quello corrente (450). Il difetto del
04/09 **non si riproduce dalla riga di comando**. Resta da rifare sulle altre due
porte: è lì che era stato misurato.

🔴 **MA IL FORMATO NON È QUELLO CHE VIENE IN MENTE**, e la pagina non lo diceva:

```
verimem recall "capannone 12" --as-of 2026-09-17T21:24:00
  EXIT=2
  --as-of non e' un epoch: '2026-09-17T21:24:00' — atteso un numero di secondi
  (es. 1785518205)
```

⇒ `--as-of` vuole un **epoch in secondi**, non una data leggibile. Chi scrive la
data si ferma con un errore che sembra suo. Per ottenerlo:
`python -c "import datetime;print(int(datetime.datetime(2026,9,17,21,24).timestamp()))"`

### 7 · Prova a scrivere una **falsità**

Scrivi di proposito una proposizione che la fonte **non** sostiene.

✅ **Ricevuta attesa**: `quarantined`, fermato da `moat`, grounding **0.19**.

⚠️ **Guarda lo `status`, non l'assenza del testo** — vale qui come in `01`: una
lettura che rende zero risultati soddisfa qualunque controllo che cerchi
un'assenza, anche quando a mancare è l'intero store.

### 8 · Rifà la stessa domanda **dalla CLI**

✅ Serve il corrente, non il superato. ⏱️ **1,5 s**.

📖 Il senso del passo non è la CLI: è che **la stessa domanda su tre porte deve
dare la stessa risposta**. Due porte concordi e una no è il difetto che un
utente scopre per ultimo.

---

## Sei arrivato quando

1. gli otto passi arrivano in fondo;
2. **le tre porte danno la stessa risposta alla stessa domanda**;
3. il passo 6 risponde col **passato** quando gli chiedi il passato.

❓ **Il criterio della pagina dei percorsi è il 1 + il 2.** Al 06/09 il percorso
risultava **ESEGUITO e non passato**. Chi lo rifà oggi ha in mano il dato che
manca a tutti: **se il passo 6 sia diventato verde.**

⚠️ **Un difetto che NON blocca ma si vede subito**: se un fatto è scaduto, la
lettura non lo dichiara — l'agente riceve meno di quello che c'era e non sa
perché. Se ti succede, non stai sbagliando il comando.
