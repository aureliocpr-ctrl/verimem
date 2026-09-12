# Due istanze sullo stesso store — runbook

Percorso **U-B** di `docs/stato-reale/PERCORSI-UTENTE.md` (definizione, criterio
di arrivo e stato stanno lì). Qui: i comandi, la ricevuta attesa, il tempo.

**⚠️ REGIME DELLA MISURA CHE CITIAMO**: i sei passi sono stati eseguiti il
**06/09 sul ramo principale del repo, NON dal pacchetto installato**. È il
regime meno rappresentativo dei tre percorsi: chi lo rifà **dal pacchetto** sta
producendo un dato che non esiste, non ripetendone uno.

**Legenda dei marchi**: `00-COME-SI-LEGGE.md`. ✅ misurato · 📖 letto dal codice ·
❓ da riempire.

> ⚠️ **Passo 0 obbligatorio**: `00-COME-SI-LEGGE.md`. Qui pesa il doppio — due
> istanze con due ambienti diversi producono due comportamenti diversi, e la
> differenza verrebbe attribuita al prodotto.

---

## 🔴 IL PASSO −1, CHE VIENE PRIMA DI TUTTO: **lo store deve essere lo stesso**

Questo è il percorso «più mani su un solo store», e la trappola sta nella prima
riga che la documentazione insegna:

```python
Memory("memoria.db")        # ⚠️ path RELATIVO alla directory corrente
```

🔴 **Due istanze lanciate da due cartelle diverse aprono DUE STORE DIVERSI**, e
nessuna delle due se ne accorge: entrambe scrivono, entrambe leggono, entrambe
funzionano. Il percorso sembra fallito («il secondo non vede il fatto del
primo») quando invece non è mai cominciato.

⇒ **Usa un percorso assoluto, uguale per le due istanze, e verificalo prima di
scrivere qualunque cosa.**

```bash
# la stessa riga nelle DUE shell: deve stampare lo stesso path
verimem doctor
```

❓ **Incolla da entrambe le shell la riga che nomina lo store.** Se non
coincidono, fermati qui: tutto il resto misurerebbe due esperimenti separati.

🔑 **Regola generale, e vale oltre questo percorso**: prima di dire «l'altra
istanza non vede il mio fatto», prova che state guardando lo stesso posto.

---

## I sei passi

### 1 · Due scrittori diversi scrivono nello stesso store

Dalle **due** shell, ognuna con la propria identità:

```bash
verimem save "<il fatto del primo scrittore>" \
  --topic <un/tuo/argomento> --lineage-to auto --source "<ciò che lo sostiene>"
```

✅ Lo store regge più mani.

### 2 · Il secondo legge il fatto del primo e vede **da chi viene**

```bash
verimem recall "<parole del fatto dell'altro>"
```

✅ **La provenienza c'è su ogni lettura** e ha il valore giusto — non il nome
del campo, il valore. È il passo che **passa**, ed è metà del criterio.

### 3 · Uno **corregge** il fatto dell'altro

```bash
verimem correct "<il valore nuovo>" --source "<ciò che sostiene il cambiamento>"
```

✅ **La correzione viene giudicata**: `cross_encoder`, punteggio **99,45**,
fascia `high`. Cioè il giudice dice sì.

### 4 · 🔴 Un terzo legge e deve ricevere **solo il corrente**

```bash
verimem recall "<le parole della cosa corretta>"
```

🔴 **Qui il percorso si ferma, su due porte su due.** Misurato: la lettura rende
**due fatti** — il vecchio e il nuovo — e nulla dice quale vale.

⚠️ **E la porta non ha colpa**, cosa che è stata verificata invece che supposta:
la lettura nasconde i superati per default, e con una supersessione creata
apposta rende **un fatto solo**. ⇒ Se ne arrivano due è perché **per lo store non
sono «corrente e superato»: sono due fatti distinti**. Il difetto sta nel
momento della **scrittura**, che quella relazione non l'ha creata — nonostante
il giudice avesse ammesso la correzione a 99,45.

❓ **Se ti tornano due fatti, non è un tuo errore di comando.** Incolla i due e
dichiara la porta: serve sapere se il difetto è ancora lì.

### 5 · 🔴 Qualcuno chiede **cosa è successo** (l'audit)

🔴 Due difetti misurati, entrambi dalla porta degli agenti:

* il registro dice **cosa** è stato chiamato e **non chi** — l'identità
  registrata è un processo, non una persona o un agente;
* **omette le chiamate rifiutate**: tre chiamate, due righe. Chi legge il
  registro per capire un incidente **non vede i tentativi bloccati**, che sono
  esattamente quelli che cercava.

### 6 · Un fatto **scade** e chi legge lo sa

✅ L'assenza viene **dichiarata**, non subita: la risposta porta il conteggio
degli esclusi e la ragione. È il comportamento giusto, ed è raro.

---

## Sei arrivato quando

**Il criterio è il passo 2 + il passo 4**: *un quarto che non era presente
ricostruisce dallo store chi ha scritto cosa, quando, e perché il valore
corrente è quello.*

* **chi / cosa / quando** → passo 2, ✅;
* **perché il corrente è quello** → passo 4, 🔴.

⇒ ✅ **Al 06/09 il percorso NON arriva in fondo**, e il responsabile è il passo 4.

⚠️ **I passi 5 e 6 non entrano nel criterio** e contano lo stesso: riguardano
cosa un team ricostruisce delle *azioni*, che è un'altra domanda da «qual è il
valore vero».

🪞 **Una cosa che questo percorso ha insegnato a chi lo ha eseguito, e che vale
per chi lo rifà**: il criterio era stato scritto chiedendo anche il passo 5, e
si è scoperto **eseguendo** che quel passo non serviva alla frase. **Un criterio
scritto prima non è automaticamente giusto: si rilegge contro la frase che dice
di misurare.** E nella stessa notte, **sei falsificazioni del proprio banco**:
tre difetti che stavano per essere attribuiti al prodotto erano di chi
misurava — leggeva **i nomi** dei campi invece dei valori, il JSON serializzato
invece dell'oggetto, il registro di una porta usandone un'altra.

🔑 **Ogni volta si era guardata una rappresentazione della cosa invece della
cosa.** Se un passo ti dà un rosso, quello è il primo sospetto — prima del
prodotto.
