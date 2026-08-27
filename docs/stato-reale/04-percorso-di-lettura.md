# 04 — Come gestiamo le informazioni: il percorso di LETTURA

> ⏱️ **NOTA DATATA — 2026-08-27, ws7. Misura `main` a `544d27bd`, cioè 771 commit fa.**
> Non è datato perché sbagli: **è fra i meglio fatti della cartella** — dichiara SHA, istante e i comandi per rifare le misure, che è esattamente la forma che serve. È datato perché il **bersaglio è mobile**: `git rev-list --count 544d27bd..origin/main` dà **771**.
> ⚠️ **Non ho rimisurato il contenuto e non affermo che sia caduto**: dico dove sta. I comandi per rifarlo sono in fondo al documento, ed è il modo giusto di chiuderlo.
> 🪞 E una nota sul mio censimento: fino a stasera avevo classificato questo file come «senza SHA», perché il mio righello cercava lo SHA **in backtick** e qui sta in un **blocco intestato** (`SHA:` `DATA:` `COMANDI:`). Falso negativo mio — il documento faceva la cosa giusta e il mio criterio non la vedeva.

    SHA:      544d27bd  (branch ws5/stato-reale, creato da ws3/gate-precision)
    COMANDI:  in fondo, sezione «Come rifare queste misure» — copiabili
    VERDETTO: PARZIALE

**In una riga:** ci sono **cinque porte** per interrogare la memoria, e **una sola sa dire
«non lo so»**. Le altre quattro rispondono sempre, anche quando la risposta non c'è.

Tutto quello che segue è **stato eseguito** su questo commit, non letto nel codice. Dove non ho
verificato, è scritto.

---

## 1. Le cinque porte, e cosa fa ognuna

Un utente che ha messo dei fatti in memoria può interrogarla in cinque modi diversi. Non sono
alternative equivalenti: **rispondono a domande diverse e si comportano in modo molto diverso.**

| porta | a cosa serve | cosa restituisce |
|---|---|---|
| `recall` | «dimmi cosa sai su questo» | i fatti più vicini alla domanda, ordinati, con un punteggio |
| `search` | «trova i fatti che contengono questa parola» | fino a 5 fatti, ordinati per vicinanza |
| `ask` | «rispondimi» | dipende: a volte i fatti, a volte solo un **conteggio** |
| `trust_report` | «cosa sai, e quanto è affidabile?» | un dossier: i fatti + **se si astiene e perché** |
| `search-docs` | «cercalo nei documenti che ho caricato» | il pezzo di documento più vicino, **con la citazione esatta** |

---

## 2. Il numero che conta: quando la risposta NON c'è

È la domanda che distingue una memoria verificata da un motore di ricerca. Ho preparato un corpus
di **10 fatti aziendali** e **12 domande** di tre tipi:

* **A — la risposta c'è** (4 domande): «Chi è la responsabile della qualità?»
* **B — la risposta non c'è** (4 domande): «Qual è il fatturato del 2025?» — nel corpus non c'è
  nessun fatturato
* **C — pericolosa** (4 domande): chiedo di una cosa **che somiglia** a una presente. Il corpus
  parla del magazzino di **Verona**, io chiedo di **Trento**. La risposta sbagliata è credibile,
  ed è il caso in cui l'utente non se ne accorge.

**Risultato:**

| tipo di domanda | `recall` si astiene | `trust_report` si astiene |
|---|---|---|
| **A** la risposta c'è | 0 su 4 *(giusto: deve rispondere)* | 0 su 4 *(giusto)* |
| **B** la risposta non c'è | **0 su 4** ❌ | **4 su 4** ✅ |
| **C** pericolosa | **0 su 4** ❌ | **2 su 4** ⚠️ |

### Cosa vuol dire in pratica

Chiedo **«Qual è il fatturato del 2025?»** a una memoria che non contiene nessun fatturato:

* `recall` risponde **«La polizza assicurativa copre fino a 2 milioni di euro»**, con punteggio
  0.77. Non è una risposta sbagliata *per poco*: è un fatto che non c'entra niente, presentato
  come il migliore che ha.
* `trust_report` risponde **`abstained: true`**, con la motivazione scritta:
  *«nothing scored above the relevance floor for this query»* — cioè «nessun fatto ha superato la
  soglia di pertinenza».

**La capacità di dire "non lo so" esiste, è misurata, e funziona 4 volte su 4.** Solo che è dentro
una porta sola, e non è quella che si usa per prima.

---

## 3. Il caso pericoloso, che è quello che mi preoccupa di più

`trust_report` si astiene 2 volte su 4 sulle domande di tipo C. **I due casi in cui sbaglia e i due
in cui ha ragione dicono la stessa cosa:**

| domanda | risposta | esito |
|---|---|---|
| «Quante unità contiene il magazzino di **Trento**?» | risponde **Verona** | ❌ |
| «Quando scade il contratto **C-99**?» | risponde **C-12** | ❌ |
| «Chi è il responsabile della **sicurezza**?» | si astiene | ✅ |
| «Il fornitore **secondario** è la ditta Bianchi?» | si astiene | ✅ |

Quando cambia il **nome proprio** (Trento invece di Verona, C-99 invece di C-12) **non se ne
accorge**. Quando cambia il **concetto** (sicurezza invece di qualità, secondario invece di
principale) **se ne accorge**.

È il difetto più insidioso del percorso di lettura, perché l'utente che chiede di Trento e riceve
un numero **non ha modo di sapere** che quel numero è di Verona.

---

## 4. Porta per porta, cosa ho misurato

### `recall` — la porta che tutti usano
Restituisce i fatti ordinati per vicinanza alla domanda, con un punteggio fra 0 e 1.
Sulle domande a cui il corpus sa rispondere è **preciso**: 4 su 4 con il fatto giusto al primo posto
(punteggi 0.86–0.91).
**Non si astiene mai: 0 volte su 12.** Anche quando il fatto migliore che ha non c'entra niente.

### `search` — la ricerca per parola
Restituisce sempre **5 risultati** (è il valore predefinito). Con un corpus di 10 fatti significa che
ne torna metà a ogni interrogazione, ordinati.
⚠️ **Attenzione a un equivoco facile:** se il corpus ha meno di 5 fatti, `search` li restituisce
*tutti* a qualunque domanda, e sembra che non filtri. Non è così — è il numero di risultati richiesti.
Ci sono cascata io ieri e stavo per segnalare un difetto inesistente.

### `ask` — quella che si comporta in modo più sorprendente
`ask` decide da sola che tipo di domanda le hai fatto. Se la domanda comincia per **«Quante…»** o
**«Quanti…»**, la classifica come *richiesta di conteggio* e risponde con un **numero di fatti**,
non con la risposta.

    «Quante unità ci sono nel magazzino di Verona?»   →   count = 0
    «A quanti giorni è fissato il pagamento?»         →   count = 1
    «Chi è la responsabile della qualità?»            →   risponde correttamente

Il primo caso è quello che fa danno: la risposta (480 unità) **è in memoria**, ma l'utente riceve
`0`. Il secondo è peggio in modo più sottile: riceve `1`, che sembra una risposta — «un giorno» —
e invece è il numero di fatti trovati.

**Su 4 domande a cui il corpus sa rispondere, `ask` ne risponde bene 2.** ⚠️ Misurato in italiano;
ieri avevo verificato che in tedesco, francese e spagnolo questo non succede (le stesse domande
vengono trattate come ricerche normali e funzionano) — **ma non l'ho rifatto su questo commit.**

### `trust_report` — l'unica che sa tacere
Restituisce un dossier con circa venti campi. I due che contano per un utente:
* **`abstained`** — vero/falso, si è astenuta o no
* **`reason`** — perché

Dichiara anche la soglia che ha usato (`min_relevance: 0.872`) e **chi l'ha applicata**
(`floor_applied_by: "cross_encoder"`).

⚠️ **Un'incoerenza che ho misurato e che vale la pena guardare:** su una domanda a cui risponde, il
fatto restituito ha punteggio **0.8636** mentre la soglia dichiarata è **0.872**. Il fatto sta
*sotto* la soglia ed è servito lo stesso. La spiegazione più probabile è che il numero mostrato
all'utente e il numero su cui si taglia **siano due grandezze diverse** — cosa che ws2 ha misurato
ieri su un'altra porta. **Non ho verificato il codice: lo segnalo come incoerenza osservata, non
come difetto accertato.**

### `search-docs` — i documenti
Trova il pezzo di documento giusto e ne dà la **citazione esatta** (nome file, intervallo di
caratteri, versione). Funziona.
**Non si astiene:** 0 volte su 2 sulle domande senza risposta.

**Ma — ed è la cosa migliore che ho trovato in questa fetta — lo dice da solo.** In fondo a ogni
risposta il prodotto stampa:

> *top-1 per similarità: questi sono i chunk più vicini alla domanda, non una risposta verificata.*
> ***Il tier documenti non si astiene*** *— usa `--min-score` per tagliare, o `verimem trust` per un
> verdetto.*

E **il consiglio funziona**, verificato su questo commit:

| soglia | domanda senza risposta (0.767) | domanda vera (0.844) |
|---|---|---|
| nessuna | risponde | risponde |
| `--min-score 0.75` | risponde ancora | risponde |
| **`--min-score 0.80`** | **si astiene** ✅ | **risponde** ✅ |
| `--min-score 0.85` | si astiene | **persa anche lei** ❌ |

⚠️ **La finestra utile è 0,077** — fra 0.767 e 0.844. Sotto non taglia niente, sopra butta via anche
le risposte buone. Funziona, ma **non è una soglia che si può fissare una volta per tutte**: ieri
avevo misurato che questo margine cambia molto da lingua a lingua.

---

## 5. Il ciclo completo: come si ottiene un verdetto su una risposta

Il prodotto documenta un secondo passo, e **funziona**. Si prende il pezzo di documento trovato e si
chiede a `verimem trust` se ci si può fidare dell'affermazione che se ne ricava:

| affermazione | giudizio del verificatore | esito |
|---|---|---|
| «Il magazzino centrale di Verona contiene 2700 unità» *(vera, sta nel documento)* | 100.0 | **fidato** |
| «…contiene 2700 unità **su 30 pallet**» *(il documento dice 22)* | 0.3 | **segnalato** |
| «Il magazzino centrale di **Livorno** contiene 9900 unità» *(inventato)* | 0.2 | **segnalato** |

**Questo è il percorso che mantiene la promessa del prodotto.** Il punto è che richiede **due passi**,
e il primo da solo non protegge.

---

## 6. Verdetto

**PARZIALE.** Nel dettaglio:

**Funziona**
* Trovare la risposta quando c'è: `recall` 4 su 4 al primo posto.
* Astenersi quando non c'è: `trust_report` 4 su 4, con la motivazione scritta.
* Le citazioni esatte dai documenti.
* Il consiglio che il prodotto dà all'utente (`--min-score`) — fa quello che promette.
* Il ciclo in due passi per ottenere un verdetto su una risposta.

**Non funziona / funziona male**
* `recall`, `search` e `ask` **non si astengono mai**: 0 su 12. Un utente che usa solo `recall` —
  cioè la porta più ovvia — **non riceve mai un «non lo so»**.
* Le domande di quantità in italiano (`ask`): 2 risposte utili su 4.
* Le entità che si somigliano: chiedendo di Trento si riceve Verona, senza avvisi.

**Non verificato** *(lo scrivo invece di mascherarlo)*
* Se `ask` si comporti diversamente in altre lingue **su questo commit** (ieri sì, su un commit
  precedente).
* Perché un fatto sotto la soglia dichiarata venga comunque servito: ho osservato l'incoerenza,
  non ne ho trovato la causa nel codice.
* Il comportamento con corpus grandi: tutte le misure qui sono su **10 fatti e 1 documento**.
* `trust_report` con `deep=true` e le altre opzioni: ho usato solo la chiamata semplice.

**La cosa che consiglierei di guardare per prima**, se l'obiettivo è pubblicare: la capacità di
astenersi **c'è già ed è misurata**. Manca solo che le porte che l'utente usa per prime la usino, o
che dicano — come fa già `search-docs` — che loro non la usano.

---

## Come rifare queste misure

```bash
git checkout 544d27bd
```

Gli script sono committati qui accanto, in `docs/stato-reale/banchi-04/` (corpus, domande e
conteggi sono dentro, non serve altro):

```bash
python docs/stato-reale/banchi-04/stato_lettura_1.py
```
```bash
python docs/stato-reale/banchi-04/stato_lettura_2.py
```
```bash
python docs/stato-reale/banchi-04/stato_lettura_3.py
```

| script | cosa misura |
|---|---|
| `stato_lettura_1.py` | le quattro porte sui fatti: `recall`, `search`, `ask`, `trust_report` |
| `stato_lettura_2.py` | il tasso di astensione su 12 domande (i tre tipi A / B / C) |
| `stato_lettura_3.py` | `search-docs`, `--min-score` e il ciclo con `trust` |

Ognuno crea la propria memoria temporanea e la cancella alla fine: **non toccano la memoria di
casa**.

Le due chiamate che riassumono tutto:

```bash
verimem search-docs "Qual e il fatturato consolidato del 2025?" --min-score 0.80
```

```bash
verimem trust "Il magazzino centrale di Livorno contiene 9900 unita." --source "<il pezzo di documento>"
```

---

*Fetta ④ del task «stato reale» — ws5 «Ester». Misure eseguite l'8 agosto 2026 su 544d27bd.*
