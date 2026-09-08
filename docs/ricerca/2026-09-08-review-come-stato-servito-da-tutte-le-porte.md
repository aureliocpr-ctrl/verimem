# «review» come stato SERVITO da tutte le porte — design (08/09)

*ws3 Galileo, su ordine del lead delle 19:10, con @ws7 Iris (prodotto) e @ws6
Aldo (dati). **Nessuna riga di prodotto prima dell'approvazione** (D-1: lead o
tre sì). Questo documento è il pezzo che manca al terzo stato, e nasce da un
reperto contro il mio stesso lavoro.*

## 0. Il reperto che rende necessario questo documento

Il 08/09 ho innestato il terzo stato nel gate (`ws3/3b-bis-v2`, `66311069`):
quando l'intero passa la banda e un claim decomposto cade, la ricevuta dice
`L4-review` col claim nominato invece di quarantinare col MIN. Poi ho
verificato la condizione di @ws7 Iris invece di riceverla:

```
verimem/client.py:852-853     if action == "downgrade":
                                  fact.status = "quarantined"
verimem/semantic.py:569-577   _VALID_STATUSES = {verified, model_claim, provisional,
                              legacy_unverified, orphaned, quarantined, user_belief}
verimem/review_queue.py:13-20 «there is no persisted per-fact quarantine reason […]
                              a quarantine_reason column is the complete fix;
                              it is not this cycle»
```

⇒ **oggi «review» non esiste come stato.** Il mio terzo stato cambia la
**ricevuta di scrittura**; ciò che l'utente ritrova in **lettura** è identico a
prima: quarantinato, invisibile. Iris lo ha detto nella forma giusta — «un
fatto in review servito accanto a uno verified senza differenza visibile è
peggio della quarantena, perché la quarantena almeno si vede». Il mio numero
«80 fatti veri su 127 non vengono più quarantinati» vale per il **verdetto**,
non per il **recall**, ed è corretto in `c9cae137ecbcceff`.

## 1. Il precedente da seguire, che il prodotto ha già

`user_belief` (Giro 2, 15/07) è esattamente questa operazione fatta bene:
uno stato nuovo, con **il suo rango** (`_STATUS_RANK`), **la sua opt-in di
lettura** (`include_beliefs`, default False), e **la ragione scritta accanto**
(anti-sycophancy). `orphaned` (ciclo 137) e `quarantined` (ciclo 138) hanno la
stessa forma. Il design qui sotto non inventa un meccanismo: **istanzia quello
esistente**, con una differenza che è tutto il punto — `review` è il primo
stato che deve essere **servito di default**, non nascosto dietro un'opt-in.

⚠️ **E c'è una trappola che ho trovato guardando prima di proporre**: quattro
chiamate leggono il rango con un default che vale `model_claim`, non zero —
`_STATUS_RANK.get(status or "model_claim", 2)` in `anti_confab_gate.py:755`,
`800`, `2305`, `2454`. Uno stato nuovo che la tabella non conoscesse verrebbe
trattato **come un fatto pulito** in quei quattro punti (supersessione
compresa), non come uno debole. Quindi l'ordine è: **prima il rango, poi lo
stato** — e la cella che lo prova viene prima del codice.

## 2. La proposta, in quattro pezzi

**(a) Lo stato.** `review` in `_VALID_STATUSES`. Rango: **1,5 — fra
`provisional` (1) e `model_claim` (2)**, cioè *sopra* la soglia di visibilità e
*sotto* un fatto non contestato. Conseguenza voluta: `min_status='model_claim'`
lo esclude (chi vuole solo fatti puliti lo dice), il recall di default lo
serve. ⚠️ `_STATUS_RANK` ha valori interi: o si passa a float, o si rinumera la
scala (`orphaned -20, quarantined -10, user_belief -10, legacy 0, provisional
10, review 15, model_claim 20, verified 30`). **La rinumerazione tocca ogni
confronto di rango: è la parte che chiedo ad Aldo di falsificare.**

**(b) Il perché, persistito.** Un fatto in review senza il claim che lo ha
messo lì è la stessa informazione muta della quarantena di oggi. Serve la
colonna che `review_queue.py` dichiara mancante: `held_reason TEXT` (il layer:
`L4-review`) e `held_claim TEXT` (il testo del claim caduto). Il gate li ha già
in mano (`claims_verdict[i]`, `claim_text`): oggi li butta all'uscita.

**(c) Le quattro porte.** Nessuna deve poterlo dimenticare:
| porta | cosa deve mostrare | dove |
|---|---|---|
| `recall` / `search` (SDK) | il fatto torna, con `status='review'` e `held_claim` nell'item | `semantic.recall`, `client.search` |
| `facts list` | stessa cosa, e un filtro `--status review` per drenare la coda | `list_facts` |
| CLI | la riga stampata distingue review da verified **senza colore** (un marcatore testuale, i colori si perdono in pipe) | `cli.py` |
| MCP | la risposta di lettura porta `status` e `held_claim`; la ricevuta di scrittura già li ha | `mcp_server.py` |

**(d) La coda.** `review_queue.backpressure_warning` oggi conta *tutto* il
backlog quarantinato perché non c'è una ragione per fatto (limite dichiarato
nel suo docstring). Con `held_reason` conta la classe giusta: **la cura del
limite che quel file si è scritto addosso**.

## 3. Predizioni falsificabili, PRIMA di scrivere una riga

- **P-R1** — sui 177 di P-A con l'innesto e il terzo stato, i **70 fatti in
  review tornano nel recall di default** e i 47 quarantinati no. Muore se anche
  uno dei 70 non torna, o se uno dei 47 torna.
- **P-R2** — **nessuna regressione di visibilità**: sugli 800 veri composti già
  ammessi, l'insieme servito dal recall di default **non perde nessun fatto**
  che oggi torna. Muore se il conteggio cala anche di uno.
- **P-R3** — `min_status='model_claim'` **esclude** tutti i 70. Muore se ne
  passa uno: vorrebbe dire che il rango non separa.
- **P-R4** — la riga CLI e la risposta MCP di un fatto in review **portano il
  testo del claim caduto**; quella di un fatto verified **no** (nessun campo
  vuoto in più per chi non c'entra). Muore se il campo compare su un fatto
  pulito.
- **P-R5** (contro il mio stesso design) — su un corpus dove `review` non è mai
  stato scritto, **il comportamento è identico bit per bit** a prima:
  stesso numero di righe servite, stessi id, stesso ordine. Muore se cambia
  qualcosa: sarebbe la prova che la rinumerazione del rango ha effetti che non
  ho previsto.

## 4. Il banco cieco per @ws1 Marie — specifica

**Perché cieco**: il banco delle 30 composte del 07/09 l'ho scritto io, che ho
scritto la regola, e l'ho dichiarato. Qui la posta è più alta (tocca il recall
di tutti), quindi le frasi le scrive chi non ha scritto il codice.

**Cosa serve** (Marie sceglie i testi, io non li vedo prima):
1. **20 scritture composte** «⟨A vero⟩ e ⟨B non provato⟩» con la fonte che
   prova solo A — dominio a sua scelta, purché non sia il corpus di casa.
2. **10 scritture pulite** (tutto provato) come controllo positivo: devono
   restare `model_claim` e tornare nel recall **identiche a prima**.
3. **10 scritture interamente false** come controllo negativo: devono restare
   quarantinate, non finire in review.
4. Per ognuna: **la stessa domanda di recall** posta prima e dopo l'innesto, e
   le tre porte interrogate (SDK, CLI, MCP).

**Il verdetto che il banco produce**, e che nessuno può aggiustare dopo:
per ciascuno dei 40 casi, `status` prima / `status` dopo / torna nel recall
prima / torna dopo / il claim caduto è nominato sì-no. Se una sola delle 10
pulite cambia riga, P-R2 è morta e il design torna indietro.

**Costo**: 40 scritture su uno store temporaneo + 40 recall × 3 porte, con il
giudice vero. ~15 minuti di slot, un processo.

## 5. Cosa chiedo a Iris e ad Aldo

- **@ws7 Iris (prodotto)**: ① il nome che legge l'utente — `review` o
  `held_for_review` (io preferisco il primo: è la parola che il gate già usa);
  ② la forma della riga CLI senza colore; ③ se la review va contata nel
  pannello pubblico e come, perché un numero nuovo in vetrina è una promessa
  nuova.
- **@ws6 Aldo (dati)**: ① la rinumerazione di `_STATUS_RANK` è sicura, o
  qualche confronto la assume intera? (grep su `_STATUS_RANK` e
  `_rango_di_fiducia`); ② la migrazione: due colonne nuove su un corpus di
  ~18k fatti, costo e reversibilità; ③ i 96 fatti «mai giudicati» di T29/T32 —
  se un domani venissero rigiudicati, finirebbero in review? È lo stesso stato
  o un altro?

## 6. Cosa NON propongo, dichiarato

- Non propongo di **cambiare il verdetto** dei fatti già quarantinati sul
  corpus di Aurelio: la migrazione scrive lo stato nuovo **solo sulle scritture
  future**. Rileggere 18k fatti col giudice è un'altra decisione, con un altro
  costo.
- Non propongo che `review` **sostituisca** la quarantena: i 47 di P-A restano
  quarantinati, ed è il comportamento voluto (l'intero non passa la banda).
- Non tocco lo schema di mia iniziativa. Se il gruppo approva, il primo pezzo
  che scrivo è la **cella RED** di P-R5 (nessuna regressione), non la colonna.
