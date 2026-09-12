# `verimem/evidence_requirement.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) · **08/09**.

## Il claim del README

**NESSUNO.**

Cercato nel README con i termini del modulo (`grep -in`) e **nessuna
riga lo copre**. Il claim `README:704` è della famiglia dei detector
L1 e questo file non è uno di quelli: attribuirglielo sarebbe
inventare l'attribuzione — in un documento fatto per collegare i
claim al codice, l'errore peggiore.

⇒ come `ide.py` e `sandbox.py`: **superficie viva fuori dalla
vetrina**. Non è un difetto; è un dato per chi decide che cosa il
prodotto dichiara di essere.

## La copertura di esecuzione

```
perimetro: 51 file di test che nominano i detector L1
copertura: 100.0%
statement non eseguiti: —
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/evidence_requirement.py:34` `is_specific_claim` | funzione: True iff the text asserts a checkable specific — a quantity | `verimem/evidence_requirement.py:92`; `verimem/evidence_requirement.py:102`; `verimem/evidence_requirement.py:110` (+3) | `tests/test_evidence_requirement.py`; `tests/test_un_numero_non_misurabile_resta_una_affermazione_specifica.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 2 | `verimem/evidence_requirement.py:67` `evidence_requirement_enabled` | funzione: Opt-in via ``ENGRAM_EVIDENCE_REQUIREMENT`` (default OFF). | `verimem/evidence_requirement.py:98`; `verimem/evidence_requirement.py:111`; `verimem/sleep.py:391` (+3) | `tests/test_evidence_requirement.py`; `tests/test_sleep_tier2_triage.py`; `tests/test_un_numero_non_misurabile_resta_una_affermazione_specifica.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 3 | `verimem/evidence_requirement.py:74` `resolve_write_confidence` | funzione: Cap confidence for a SPECIFIC, UNSOURCED claim. | `verimem/evidence_requirement.py:112`; `verimem/mcp_server.py:13474`; `verimem/mcp_server.py:13475` | `tests/test_evidence_requirement.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.


---

## Il banco: 9 promesse su 9

```
── `is_specific_claim` ──
OK  quantità con unità («la latenza è 47 ms») → specifico
OK  anno («il rilascio è previsto nel 2027»)  → specifico
OK  claim GENERICO («il sistema è veloce»)    → NON specifico   ← controllo negativo
OK  testo vuoto                               → NON specifico

── `resolve_write_confidence`: cappa SOLO nei quattro casi ──
OK  specifico + SENZA evidenza + abilitato → cappato a 0.6
OK  CON evidenza    → passa intatto (0.9)     ← il guard che MORDE
OK  generico        → passa intatto (0.9)
OK  DISABILITATO    → passa intatto (0.9)
OK  già sotto il tetto (0.3) → NON viene alzato — la regola solo TOGLIE fiducia

9 casi · il banco regge                                               EXIT=0
```

I quattro casi «passa intatto» sono ciò che rende leggibile il primo: spegnendo
**un criterio alla volta** si vede che il cap dipende da tutti e quattro insieme,
non da uno solo.

## 🔴 La misura che il docstring aspetta — **fatta**

Il modulo è **opt-in, default OFF**, e il docstring dice perché:

> «Opt-in (default OFF) **so the corpus-wide impact can be measured before
> flipping it on** — same discipline as the admission gate.»

Il presidio è quindi fermo **in attesa di una misura**. Non l'ho trovata da
nessuna parte, quindi l'ho fatta — con le funzioni stesse del modulo, sullo store
vivo, in sola lettura (`sqlite3 mode=ro`, 7,9 s):

```
flag ENGRAM_EVIDENCE_REQUIREMENT              SPENTO (default)

fatti vivi                                    15680
senza `verified_by`                           15092   (96,2%)
«specifici» (quantità o anno)                 12572   (80,2%)
⇒ CAPPATI a 0.6 se il flag venisse acceso      3762   (24,0%)
```

⚠️ **PREDIZIONE MIA, depositata prima: «oltre il 50%». SMENTITA** — è il 24,0%.
E la ragione è istruttiva: avevo moltiplicato le due percentuali alte (96,2% ×
80,2% ≈ 77%) **dimenticando il terzo criterio**, `confidence > 0.6`. Il grosso
del corpus è **già scritto sotto il tetto**, quindi il cap non lo tocca.

🔑 Quel «già sotto il tetto» è il dato che nessuna delle tre percentuali dice da
sola: **su quattro fatti specifici e senza fonte, tre stanno già a fiducia bassa
e uno no**. Accendere la regola cambierebbe il ranking di **un fatto vivo su
quattro**.

## Come si legge questo numero, senza forzarlo

**Non dico se accendere.** Dico che la decisione ora ha il suo numero, che il
docstring lo chiedeva come condizione, e che il numero è **grande ma non
travolgente**: 3762 fatti scenderebbero a 0.6 e ranklerebbero sotto quelli con
fonte.

Quello che il mio conto **non** dice, e va scritto:
- **quanti di quei 3762 sono veri.** Il cap non li dichiara falsi, toglie
  fiducia — ma se la gran parte fosse vera, si starebbe declassando il corpus
  onesto. **NON MISURATO.**
- **l'effetto sul recall**: la fiducia entra nel ranking, quindi cambia *che cosa
  torna* a chi interroga. Va misurato prima, non dopo. **NON MISURATO.**
- il numero è di **oggi**: cresce col corpus, e va rifatto prima di decidere
  (`<scratchpad>/banco_evidence_requirement.py`, 8 secondi).

⇒ **FUNZIONA COME PROMESSO** sulle funzioni; **il presidio è SPENTO**, e la
condizione che il modulo stesso poneva per accenderlo — misurare l'impatto — da
oggi è soddisfatta per la prima metà (quanti), non per la seconda (quali).
