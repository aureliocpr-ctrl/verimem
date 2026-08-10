# ⑩ — Il pacchetto pubblicato non è l'albero di sviluppo, e su un caso si comporta peggio

> **Due artefatti dichiarati**: il wheel `verimem-0.7.0-py3-none-any.whl` scaricato da PyPI
> (`quantity_match.py` datato **22 Jul 11:46**, METADATA `Version: 0.7.0`) e l'albero git
> **6cdd9d64**. `diff` fra i due file: **2051 righe**.
> Eseguito col Python di un venv privo di verimem installato, per escludere l'import dell'albero.

---

## Il fatto

Il lavoro sui separatori numerici è stato condotto su `extract_quantities` nell'albero, e la
gravità per l'utente è stata dedotta da lì. La deduzione era che il pacchetto pubblicato avesse lo
stesso comportamento. Misurata, regge su tre casi su quattro.

| caso | pacchetto 0.7.0 | albero | |
|---|---|---|---|
| `45.000 euro` | `{('euro', 45.0)}` | `{('euro', 45.0)}` | uguale |
| `1.500 euro` | `{('euro', 1.5)}` | `{('euro', 1.5)}` | uguale |
| `12.34 euro` | `{('euro', 12.34)}` | `{('euro', 12.34)}` | uguale |
| **`1.250.000 euro`** | **`{('', 1.25)}`** | **`set()`** | **diverso** |

Tre casi su quattro identici: la divergenza è mirata a uno solo. Senza quei tre, la riga diversa
non sarebbe interpretabile — sono la popolazione opposta, nella stessa esecuzione.

## La conseguenza ribalta un ordine di gravità

Le due meccaniche note erano state ordinate così:

> ① **un separatore** → valore sbagliato di mille volte, e il gate afferma
> ② **due o più separatori** → il pattern non matcha: silenzio, nessun controllo
> *«Il ① è più grave del ②. Il ② produce silenzio; il ① non tace, afferma.»*

Sull'albero l'ordine è corretto: `1.250.000 euro` → `set()`, silenzio.
Sul pacchetto pubblicato no: → `1.25`. Un milione e duecentocinquantamila letto come uno virgola
venticinque, con l'unità persa (`''`).

**Per chi ha eseguito `pip install`, la classe ② non è la classe ②: è la ①.** La categoria
derubricata a «silenzio, meno grave» è, fuori dall'albero di sviluppo, quella che afferma un
valore falso.

## La causa è una riga

```
pacchetto 0.7.0:  (?<![\w.])(\d+(?:\.\d+)?)(?:...)?(?![\w])
albero:           (?<![A-Za-z0-9_])(?<!\d\.)(\d+(?:\.\d+)?)(?:...)?(?![A-Za-z0-9_])(?!\.\d)
```

Il lookahead finale `(?!\.\d)` — «non seguito da punto+cifra» — è presente nell'albero e assente
nel pacchetto. È stato aggiunto dopo il 22 luglio e, a giudicare dal commento adiacente
(preposizioni articolate italiane, 25/07), per un'altra ragione: il caso è stato curato senza
essere collegato a questo tema.

L'albero di sviluppo è quindi in condizione migliore del pacchetto distribuito, e le misure di
gravità venivano prese sull'albero.

## Quante altre cure stanno nel repo e non nel pacchetto

> **Perimetro, dichiarato prima di contare**: i `.py` sotto `verimem/`, ricorsivi, confrontati per
> path relativo e sha256 del contenuto **normalizzato CRLF→LF**.
> wheel **397** file · albero **419**.

### Il conteggio grezzo era un artefatto dello strumento

|  | comuni | identici | diversi |
|---|---|---|---|
| senza normalizzare i line-ending | 396 | **0** | 396 |
| normalizzando CRLF→LF | 396 | **288** | **108** |

«Nessun file identico su 396» è un risultato prodotto dal misuratore e non dal prodotto. Il numero
corretto è **108 file diversi**. Un confronto binario fra un wheel e un albero di lavoro richiede
la normalizzazione dei terminatori di riga.

### I 23 moduli assenti dal pacchetto

`+22` netto: 23 presenti solo nell'albero, 1 solo nel wheel (`rerank.py`).

```
verimem/valore_non_nella_fonte.py   → L4.1
verimem/vicinato_del_valore.py      → L4.2
unsupported_span · negation_scope · evidence_independence · proof_evidence ·
fact_contract · evidence_hint · ann_gate · audit_anchor · mutation_audit ·
hidden_records · retirement_log · review_queue · residual_copies · content_pin ·
tier_inventory · continuity · diversify · text_cut · relation_claim · env_num · orchestration
```

Verifica per seconda strada, indipendente dalla prima: `anti_confab_gate.py` del wheel ha **0
occorrenze** dei due nomi di modulo e **nessuna etichetta `L4.1`/`L4.2`**.

### Cosa il pacchetto contiene

| strato | wheel 0.7.0 | albero |
|---|---|---|
| `L1.x` | **17** | **17** |
| `L3` | SEMANTIC, semantic, supersession | + `L3-coexistence` |
| `L4` | grounding, review, skipped | + `L4-negazione`, `L4.1`, `L4.2` |

Al pacchetto mancano **quattro** strati, non tutti: `L1` e il giudice di entailment sono presenti.
È la ragione per cui un falso accetto passa con grounding alto anche lì — lo strato che lo ammette
esiste in entrambi.

Ne segue che il lavoro in corso su `L4.1` (falsi positivi, ipotesi «avviso invece di veto») e su
`L4.2` (estrattore a `anti_confab_gate.py:1926`) riguarda strati che il pacchetto pubblicato non
ha. Le cure restano valide, ma non correggono un difetto che l'utente sta subendo: aggiungono una
difesa che non ha ancora ricevuto. Il caso `45.000` contro `45` è più grave sul pacchetto che
sull'albero: sull'albero l'obiezione viene stampata sotto la riga `admitted`, sul pacchetto non
viene prodotta.

## Stato del rilascio

```
pip download verimem==0.7.5 --no-deps
ERROR: Could not find a version that satisfies the requirement verimem==0.7.5
       (from versions: 0.3.0, 0.3.1, 0.4.0, 0.4.1, 0.4.2, 0.5.0, 0.7.0)
```

La 0.7.5 non è su PyPI. Chi installa oggi riceve il codice del 22 luglio: quanto sopra descrive lo
stato corrente del prodotto distribuito, non un difetto storico.

## Il costo di verificare invece di dedurre

```bash
pip download verimem==0.7.0 --no-deps -d /tmp/w && cd /tmp/w && unzip -q verimem-0.7.0-py3-none-any.whl
```

---

**Caveat**. Primo blocco: un file (`quantity_match.py`), sei casi, una piattaforma; la cura
`(?!\.\d)` è descritta dal `diff`, senza risalire al commit che l'ha introdotta né alla sua
intenzione. Secondo blocco: sono state misurate **l'assenza dei file** e **l'assenza delle
menzioni nel gate** — due strade indipendenti che concordano — ma **il gate del wheel non è stato
eseguito**. L'affermazione «quegli strati non girano per l'utente» è la lettura più probabile, non
una misura d'esecuzione.

## Le altre cure assenti dal pacchetto hanno un tema: lingua e Windows

> **Perimetro**: ogni assegnazione di modulo `NOME = re.compile(...)` nei `.py` sotto `verimem/`,
> estratta con `ast` e non con una regex sulle regex, confrontata per `(file, NOME)`.

```
regex compilate:  wheel 141 · albero 170 · comuni 141
IDENTICHE 129 · DIVERSE 12 · solo nell'albero 29
```

129 su 141 identiche: le 12 differenze non sono rumore di fondo.

### Il caso più grave, eseguito

`source_trust.py :: _SOURCE_REF_RE` riconosce un riferimento a file passato come **source**. Le
due versioni importate dai rispettivi artefatti — ricopiarle a mano misura la trascrizione, non il
prodotto:

| input | wheel 0.7.0 | albero |
|---|---|---|
| `source:C:\Users\...\prova.txt` | **`C`** | `C:\Users\...\prova.txt` |
| `file:D:/dati/rapporto.md` | **`D`** | `D:/dati/rapporto.md` |
| `source:relativo/senza/unita.txt` | corretto | corretto |
| `doc:soloNome.md` | corretto | corretto |

Nel pacchetto pubblicato un percorso Windows assoluto viene troncato alla lettera di unità: la
causa è `([^:]+)`, che si ferma ai due punti di `C:`. I percorsi relativi funzionano in entrambi,
quindi il difetto è circoscritto ai percorsi assoluti — sul sistema operativo su cui il prodotto
viene sviluppato e usato. La cura nell'albero è `([A-Za-z]:[\\/]\S*|[^:]+)`, dove la classe
accetta sia la barra rovescia sia quella dritta.

### Le altre undici

* **desinenze italiane**: `completo` → `complet[oaie]`; `documentato|documentata` →
  `documentat[oaie]`, più `descritt[oaie]`
* **spagnolo e portoghese**: `version` → `vers(?:ion\w*|ión\w*|ão|ões|ao|oes)`
* **italiano temporale con negazione**: aggiunti `alla data del|fino al|fino a|entro il` e i
  lookbehind `(?<!dopo )(?<!dopo l)`
* **ordine delle alternative**: `tested|well[- ]tested` → `well[- ]tested|tested`. L'alternanza
  prende il primo ramo che combacia: con `tested` davanti, su «well-tested» il match era parziale
* i separatori numerici (`_QUANT_RE`), descritti sopra

Chi installa oggi ha un prodotto che funziona peggio se non scrive in inglese e che tronca i
percorsi Windows. Non è una regressione: sono cure fatte dopo il 22 luglio e mai pubblicate. È un
argomento in più perché la 0.7.5 esca — non porta solo il pin e la ripulitura del registro, porta
l'internazionalizzazione del gate.

**Caveat**: contate solo le `re.compile` assegnate a un nome di modulo; quelle costruite a runtime
o inline in una chiamata non rientrano, quindi 12 è un limite inferiore. Di quelle 12 ne è stata
**eseguita una**: le altre sono lette dal `diff`, che dice cosa cambia nel pattern e non cosa
cambia nell'esito. Le 29 regex presenti solo nell'albero appartengono ai moduli nuovi e non sono
state esaminate.
