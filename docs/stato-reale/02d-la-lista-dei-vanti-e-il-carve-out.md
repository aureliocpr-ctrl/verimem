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
