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

```bash
verimem save "<il fatto che l'agente ha appena stabilito>" \
  --topic <un/tuo/argomento> --lineage-to auto \
  --source "<l'output, il documento, la pagina che lo sostiene>"
```

✅ **Ammesso**, e la ricevuta porta il punteggio del giudice.
🔑 **Senza `--source` il giudice non gira e il fatto entra come claim non
verificato.** È la differenza fra un agente che ricorda e uno che si fida di sé.

### 2 · Lo richiama

```bash
verimem recall "<qualche parola del fatto>"
```

✅ Torna il fatto. ⏱️ ✅ **0,1 s** — il richiamo non è il costo di questo
percorso, la scrittura sì.

### 3 · Il mondo cambia — l'agente **corregge**

```bash
verimem correct "<il fatto nuovo>" --source "<ciò che sostiene il cambiamento>"
```

📖 La correzione passa dal giudice come una scrittura qualunque: non è un
sovrascrivere, è una scrittura che dichiara di rettificare.
❓ **Incolla la ricevuta**: serve sapere se dichiara la relazione col fatto
vecchio o solo l'ammissione del nuovo.

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

❓ **Chi esegue chiude questo punto rifacendo il passo**, non correggendo la
riga: chiedi lo stato *prima* della correzione del passo 3 e guarda se ti
risponde il vecchio valore o quello nuovo. **È l'unico passo del runbook che
vale un post da solo.**

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
