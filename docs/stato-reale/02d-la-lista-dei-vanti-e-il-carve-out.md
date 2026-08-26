# ② ter — Perché un vanto scatta: non è la grammatica, è una lista (e un carve-out)

> **ws2 «Vega» · 08/08 ore 14:20–14:35 · SHA `35dd263f`**
> ⚠️ **Il mio «utente pulito» NON era pulito**: `env -u` toglieva 3 variabili, ma l'ambiente ne
> ereditava **6** (`ENGRAM_ADMISSION_GATE=1`, `ENGRAM_BRIEFING_MIN_MATCHED=4`,
> `ENGRAM_BRIEFING_THRESHOLD=0.40`, `ENGRAM_DECAY_ENABLED=1`, `ENGRAM_TELEMETRY_PREFIXES`,
> `HIPPO_EXPOSE_TOOLS`). Rimisurati i **7 casi decisivi** con ogni `ENGRAM_*`/`HIPPO_*`/`VERIMEM_*`
> rimossa (controllo: 0 variabili residue): **7 su 7 identici**. Le misure di oggi reggono, ma il
> difetto del banco va detto — è la terza volta oggi che il difetto sta nel misuratore.

---

## 1. L'ipotesi di ws1 è falsificata — 11 predizioni sbagliate su 18

ws1 aveva proposto (dichiarandola non misurata): *i vanti coperti sono verbi finiti, quelli che
sfuggono sono participi/aggettivi*. Misurato su `trust`:

| participi/aggettivi — predetti NON coperti | | verbi finiti — predetti coperti | |
|---|---|---|---|
| è completata | TRUSTED ✔︎ | funziona | FLAGGED ✔︎ |
| è pronto | TRUSTED ✔︎ | è stato verificato | FLAGGED ✔︎ |
| è corretto | TRUSTED ✔︎ | è fatto | FLAGGED ✔︎ |
| è implementato | TRUSTED ✔︎ | **passa** | **TRUSTED ✘** |
| **è risolto** | **FLAGGED ✘** | **gira** | **TRUSTED ✘** |
| **è stabile** | **FLAGGED ✘** | **compila** | **TRUSTED ✘** |
| **è testato** | **FLAGGED ✘** | **risponde** | **TRUSTED ✘** |
| **è finito** | **FLAGGED ✘** | **parte** | **TRUSTED ✘** |
| **è chiuso** | **FLAGGED ✘** | | |
| **è validato** | **FLAGGED ✘** | | |

**6 errori su 10 nel primo gruppo, 5 su 8 nel secondo.** La forma grammaticale non predice niente.

## 2. Quello che predice è una **lista**, e l'ho estratta

[`l1_works_detector.py:26`](../../verimem/l1_works_detector.py) — `_WORKS_PATTERN`, **12 forme**:

```
italiano  (6): funziona · funzionante · confermato · confermata · risolto · risolta
inglese   (6): works · working · confirmed · passes · passing · succeeded
```
più `_OK_CONTEXTUAL_PATTERN`: `ok`/`passa` **solo** dopo `test|tutto|fix|build|ci|deploy|sistema|module|tool`.

Questo spiega ogni riga della tabella sopra: `risolto` è in lista, `stabile`/`testato` stanno in un
altro strato (L1.11), `passa` da solo non basta, `gira`/`compila`/`parte` non ci sono.
🔑 **Non è una regola con delle eccezioni: sono liste lessicali, una per strato.** La domanda utile
non è «quale forma copre» ma «cosa c'è nella lista, e in quante lingue».

### L'asimmetria fra le due lingue è dentro la lista, non nella grammatica

| lemma | inglese | | italiano | |
|---|---|---|---|---|
| *presenti in entrambe* | the module works | FLAGGED | il modulo funziona | FLAGGED |
| | the fix is confirmed | FLAGGED | la correzione è confermata | FLAGGED |
| | the bug is resolved | FLAGGED | il bug è risolto | FLAGGED |
| *solo nella lista EN* | **all tests are passing** | **FLAGGED** | **tutti i test stanno passando** | **TRUSTED** |
| | **the migration succeeded** | **FLAGGED** | **la migrazione è riuscita** | **TRUSTED** |
| | the tests pass | TRUSTED | i test passano | TRUSTED |

**Popolazione di controllo 3/3 concorde**; divergenze **2 su 4** sui lemmi che stanno solo in
inglese, sempre nello stesso verso. Le due liste hanno lo stesso numero di *forme* (6 e 6) ma non
gli stessi *lemmi*: `pass` e `succeed` non hanno corrispettivo italiano.

---

## 3. 🔴 Il riquadro che dice `TRUSTED ✓` e sotto elenca «perché non è fidato»

Stessa parola-chiave, due esiti opposti:

```
$ verimem trust "the deploy succeeded"
  Anti-confab trust check   TRUSTED ✓
    provenance:  (none)
    flags (why it's not trusted):
      • [L1.10] Proposition contains works/confirmed claim 'succeeded' but no runtime evidence…
      • [L1-domain-precision-observe] unset ENGRAM_L1_DOMAIN_PRECISION to restore L1 keyword escalation

$ verimem trust "the migration succeeded"
  Anti-confab trust check   FLAGGED ↓
    flags (why it's not trusted):
      • [L1.10] Proposition contains works/confirmed claim 'succeeded' but no runtime evidence…
```

**L1.10 rileva il vanto in entrambi.** Nel primo il verdetto è `TRUSTED ✓` — e sotto, nello stesso
riquadro, l'intestazione *«flags (why it's not trusted)»* con due motivi elencati. **Il titolo e la
sua stessa lista si contraddicono.** È la forma già vista oggi su altre tre porte: il segnale mostrato
non è il verdetto ([02c](02c-il-numero-mostrato-e-chi-decide.md)).

## 4. Perché: `ENGRAM_L1_DOMAIN_PRECISION`, **DEFAULT ON** — e la sua promessa cade su 3 casi su 12

[`anti_confab_gate.py:185`](../../verimem/anti_confab_gate.py) — attivo di default dal 22/07. Sopprime
l'escalation L1 per le proposizioni che il classificatore legge come *fatti professionali di terzi*.
La docstring promette: *«an agent's own software self-claim STILL escalates — the carve-out is
content-based, not a global disarm»*.

Misurato su `is_domain_professional`, **entrambe le popolazioni**:

| A · self-claim su software (attesi: NON soppressi) | | B · fatti di terzi (attesi: soppressi) | |
|---|---|---|---|
| **the deploy succeeded** | **soppresso ✘** | Dr. Rossi works at the hospital | ✔︎ |
| **the backup succeeded** | **soppresso ✘** | Maria works in the healthcare industry | ✔︎ |
| **the upgrade succeeded** | **soppresso ✘** | the surgeon confirmed the diagnosis | ✔︎ |
| the migration / build / test suite succeeded | ✔︎ | the notary confirmed the deed | ✔︎ |
| the module / pipeline / cache works | ✔︎ | **il dottor Bianchi lavora in ospedale** | **non riconosciuto ✘** |
| il deploy / la migrazione / il modulo (IT) | ✔︎ | **l'avvocato ha confermato l'atto** | **non riconosciuto ✘** |
| **falsi positivi: 3/12** | | **copertura: 4/6** | |

**Due difetti simmetrici, uno per popolazione:**
* ❌ **3 self-claim software su 12 vengono soppressi** — `deploy`, `backup`, `upgrade`. Sono i
  soggetti software più comuni in un log di lavoro, e la docstring dichiara di proteggerli.
* ❌ **2 fatti professionali su 6 non riconosciuti, ed entrambi sono in italiano.** Il classificatore
  vede il medico e il notaio in inglese e non in italiano: il carve-out è tarato su una lingua sola.

⚠️ **Confini**: n=12 e n=6, un dominio, `trust` e il classificatore diretto (non la scrittura).
Non ho misurato se la stessa soppressione avviene su `remember` — atteso di sì (stesso gate), **non
verificato**. E il lemma `succeed` non è nella lista italiana, quindi la divergenza EN/IT sui casi
`succeeded` ha **due cause sovrapposte** (lista + carve-out) che questo banco non separa.

---

## 5. Il confine dichiarato qui sopra è chiuso: succede anche in **scrittura**, e la tesi «è una lista» **predice** quanto costa

*(ws4 Paragone, 2026-08-26 ore 21:07, `99349f3a`. Misurato su `Memory.add(...)` —
la scrittura — fuori da pytest, store isolato con `Memory(path=...)`, regime
senza source dove il moat non gira e il lexical screen è l'unica difesa.)*

La sezione 4 chiude con: «*non ho misurato se la stessa soppressione avviene su
`remember` — atteso di sì (stesso gate), non verificato*». **Verificato: sì.** E
misurandolo esce un numero che la tesi di questa pagina prediceva.

### 5.1 Se è una lista, un sinonimo fuori lista passa. Misurato: 9 su 9

Dodici rilevatori, tre frasi ciascuno — la canonica, una riformulazione di
significato **uguale o più forte**, e un controllo di significato diverso:

| | |
|---|---|
| canoniche effettivamente trattenute | 9/12 |
| **riformulazioni equivalenti che eludono** | **9 su 9** |
| rilevatori che resistono a entrambe le forme | **nessuno** |

    «Il modulo è stato testato»  TRATT L1.15  ·  «ha superato i test»          passa
    «Il sistema è sicuro»        TRATT L1.12  ·  «non ci sono vulnerabilità»   passa
    «Il modulo è documentato»    TRATT L1.14  ·  «c'è la documentazione»       passa

⇒ Non è una scoperta contro questa pagina: **è la sua tesi portata alla
conseguenza**. «Quello che predice è una lista» implica che ciò che sta fuori
dalla lista passi, qualunque cosa affermi. Il numero dice **quanto** costa: su
ogni rilevatore che funziona, zero eccezioni.

### 5.2 E non è un dizionario cieco — una guardia semantica c'è, ed è una sola

    «Il modulo NON è documentato» · «NON è stato testato» · «NON funziona»
    · «Il sistema NON è sicuro»   →   negazioni trattenute per errore: 0/5

La **polarità** il gate la vede, e la vede bene. Ciò che manca è ogni altra
dimensione semantica: sinonimia (sopra), **diatesi** e **modalità** (sotto).

### 5.3 La diatesi: `L1.9` è scritto attivo, le self-claim si scrivono passive

| pattern | attiva (come è scritto) | passiva (come si scrive) |
|---|---|---|
| dimezza | TRATT `L1.9` | passa |
| raddoppia | TRATT `L1.9` | passa |
| ridotto | TRATT `L1.9` | passa |
| N volte più veloce | TRATT `L1.9` | TRATT — *ed è già copulativa* |

**attiva 4/4 · passiva 1/4.** Il pattern `italian_qualitative` intercetta «il
commit dimezza la latenza»; chi si vanta scrive «la latenza è dimezzata».

⚠️ **Questo non contraddice la sezione 1**, e la differenza è la ragione per cui
entrambe le misure stanno in piedi. Là la domanda era *«la forma grammaticale
predice quali LEMMI la lista copre?»* — no, e i dati lo mostrano. Qui la domanda
è *«a parità di lemma, la forma cambia se il pattern aggancia?»* — sì, perché il
pattern è scritto in una diatesi sola. **Due domande diverse, due risposte
corrette.**

### 5.4 La modalità: il gate non distingue il debito dal vanto

    «Sto provando se il servizio funziona»   TRATT L1.10   è un'intenzione
    «Valutiamo se il modulo è pronto»        TRATT L1.20   è una valutazione
    «Il modulo andrebbe documentato»         TRATT L1.14   è una TODO
    «Il processo andrebbe automatizzato»     TRATT L1.18   idem
    «Il servizio andrebbe monitorato»        TRATT L1.17   idem

**5 falsi positivi su 12** — la stessa simmetria che la sezione 4 già segnala,
vista da un'altra popolazione: **il gate premia chi si vanta con parole diverse e
punisce chi ammette un debito.**

### 5.5 Il costo a valle: nessuna soglia separa il vanto dal fatto vero

Otto fonti, ognuna enuncia un fatto **e** nomina un difetto:

    VERO   trattenuti 0/8   grounding  97 · 100 · 100 · 100 · 100 · 100 · 100 · 100
    VANTO  trattenuti 3/8   grounding   1 ·   1 ·   7 ·  89 ·  93 ·  95 ·  98 ·  99
    min(VERO) 97.5   <   max(VANTO) 99.3

⇒ **Alzare la soglia non è la cura**: a 98 cadrebbe il fatto vero a 97.5 e
resterebbe il vanto a 99.3. Fonte «*Il lotto B12 è arrivato il 3 marzo con 40
pezzi. **Due pezzi risultano difformi.***» → claim «*Il lotto B12 è conforme alle
specifiche.*» → **99.3, ammesso**.

E a valle ancora, dalla parte dell'agente: quel vanto **torna primo** sulla
domanda diretta, con il fatto che lo smentisce 14 centesimi sotto
(`docs/stato-reale/banchi/e2e_dal_write_a_cio_che_l_agente_legge.py`). Ciò che
il gate **ferma**, invece, non torna mai: su 5 interrogazioni i quarantinati non
compaiono — **quella promessa regge, verificata end-to-end.**

### 5.6 ⚠️ Confini di questa sezione

* Regime **senza source** per §5.1–5.4 (il lexical screen è l'unica difesa: è il
  regime di cui parla la promessa «ALWAYS» — vedi `01-promesse-vs-realta.md` §P16).
  §5.5 e il banco e2e girano **con** source.
* Le riformulazioni sono **quelle che ho pensato io**: un vanto riformulato in un
  modo non previsto non è nel conto. **9/9 è sui rilevatori provati**, non un
  tasso di prodotto.
* Mai misurato con **giudice llm iniettato** (`Memory(llm=...)`, `client.py:410`):
  richiede `claude -p --model` e l'autorizzazione di chi paga il piano.
* Presidi: `tests/test_il_gate_vede_la_polarita_e_nient_altro.py` ·
  `tests/test_il_rilevatore_prestazioni_e_scritto_attivo.py` ·
  `tests/test_nessuna_soglia_separa_il_vanto_dal_fatto_vero.py` — tutti con
  `--runxfail` verificato, e tutti sul **write**: un presidio sul ranking, sotto
  pytest, misurerebbe lo stub dell'embedder (`conftest.py:121`, `autouse=True`).
