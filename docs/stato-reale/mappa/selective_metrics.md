# `verimem/selective_metrics.py`

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
copertura: 90.8%
statement non eseguiti: 50, 71, 88, 138
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/selective_metrics.py:40` `_clean` | funzione: (nessun docstring) | `verimem/selective_metrics.py:48`; `verimem/selective_metrics.py:69`; `verimem/selective_metrics.py:86` (+4) | `tests/test_admission_gate_default_on.py`; `tests/test_interactive_judge.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 2 | `verimem/selective_metrics.py:44` `selective_risk_coverage` | funzione: (risk among answered, coverage) at ``threshold`` — strict ``>`` like | `verimem/selective_metrics.py:11`; `verimem/selective_metrics.py:34` | `tests/test_selective_metrics.py` | - | **FUNZIONA COME PROMESSO** | eseguita, 1/9 statement del corpo scoperti (755 passed, EXIT=0) |
| 3 | `verimem/selective_metrics.py:59` `aurc` | funzione: Area under the risk-coverage curve: rank by confidence (desc), take the | `verimem/selective_metrics.py:13`; `verimem/selective_metrics.py:34`; `verimem/selective_metrics.py:64` (+1) | `tests/test_selective_metrics.py`; `tests/test_stats.py` | - | **FUNZIONA COME PROMESSO** | eseguita, 1/11 statement del corpo scoperti (755 passed, EXIT=0) |
| 4 | `verimem/selective_metrics.py:82` `e_aurc` | funzione: Excess AURC over the ORACLE ranking (all correct first): 0 = the scores | `verimem/selective_metrics.py:13`; `verimem/selective_metrics.py:34` | `tests/test_selective_metrics.py` | - | **FUNZIONA COME PROMESSO** | eseguita, 1/6 statement del corpo scoperti (755 passed, EXIT=0) |
| 5 | `verimem/selective_metrics.py:94` `tce_at_lambda` | funzione: Calibration at the DECLARED operating point λ (threshold λ/(1+λ)): | `verimem/selective_metrics.py:17`; `verimem/selective_metrics.py:35` | `tests/test_selective_metrics.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 6 | `verimem/selective_metrics.py:132` `isotonic_fit` | funzione: Pure PAV (pool-adjacent-violators) isotonic regression of correctness on | `verimem/selective_metrics.py:21`; `verimem/selective_metrics.py:34` | `tests/test_selective_metrics.py` | - | **FUNZIONA COME PROMESSO** | eseguita, 1/17 statement del corpo scoperti (755 passed, EXIT=0) |
| 7 | `verimem/selective_metrics.py:153` `isotonic_fit.predict` | funzione: (nessun docstring) | `verimem/config.py:407`; `verimem/cross_encoder_rerank.py:17`; `verimem/outcome_predict.py:40` (+20) | `tests/conftest.py`; `tests/test_eval_records_read_path_regime.py`; `tests/test_forward_replay.py` (+10) | - | NON MISURATO | - |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.


---

## Il banco nel merito: la promessa «il numero non lusinga mai il negozio»

Il docstring di `aurc` dichiara:

> «**Tie-conservative**: within a confidence tie the WRONG answers rank first,
> so **the number never flatters the store**.»

È l'immunizzazione dichiarata contro la classe che questa squadra ha in memoria
dal 06/09 — *il righello che sbaglia a favore di chi lo usa*. Un modulo di
metriche che se ne dichiara immune va provato **proprio su quella**, perché è la
promessa che nessuno controlla: un numero che ci dà ragione non fa attrito.

```
── (1) la parità di confidenza non deve lusingare ──
AURC su 10 record TUTTI a confidenza 0.5 (5 giusti, 5 sbagliati)   0.8228
AURC sullo stesso insieme ordinato A FAVORE                        0.1772
la parità NON è più lusinghiera dell'ordine perfetto               True

── (3) il controllo che il numero non sia costante ──
perfetto 0.1772  ·  parità 0.8228  ·  pessimo 0.8228
e_aurc con l'ordine perfetto è ~0 (eccesso sull'oracolo)           True
```

⇒ **la promessa regge nel modo più forte possibile**: in caso di parità il
numero è **identico al caso pessimo** (0.8228). Il modulo non «attenua» la
parità: assume il peggio. E il controllo (3) prova che il numero si muove
davvero — senza, un `aurc` costante avrebbe passato la prima prova.

## Le quattro righe che nessun test esegue: i casi degeneri

```
selective_risk_coverage([]) → (None, 0.0)        [riga  50]   ✅
aurc([])                    → 0.0                [riga  71]   ✅
e_aurc([])                  → 0.0                [riga  88]   ✅
isotonic_fit([])            → prior neutro 0.5   [riga 138]   ✅
```

## Il punto operativo λ — e un mio controllo sbagliato, tenuto qui perché insegna

`tce_at_lambda([(0.1, True), (0.1, False)], lam=9.0)`: soglia 0.9, nessuna
risposta supera, **copertura 0.0**.

Il mio primo controllo cercava un campo `operable` e riceveva `None`. **Il campo
non esiste**: `.get()` su una chiave assente torna `None`, che *sembra* una
risposta ed è il silenzio di un dizionario. Letta la funzione, il modulo fa una
cosa migliore di un booleano:

```
sla_met        is None   ← «non valutabile», NON «bocciato»
observed_risk  is None
tce            is None
sla_target_risk = 0.1    ← ma il bersaglio dichiarato 1/(1+λ) resta scritto
```

⇒ **distingue «bocciato» (`False`) da «non valutabile» (`None`)**, che è
esattamente la distinzione «stato assente / stato ignoto» su cui @ws3 Ricerca
sta lavorando oggi. Il docstring lo dice con precisione: *«zero coverage →
observed/tce/sla_met are None: the operating point is INOPERABLE with these
scores — **declared, never scored as a pass**»*.

🔑 **La lezione è mia, non del modulo**: `dizionario.get("chiave_che_non_esiste")`
restituisce `None` senza distinguerlo da un `None` vero. In un banco, usare
`.get()` per un controllo significa non poter distinguere «il valore è sbagliato»
da «non ho letto l'API». La forma giusta è l'accesso diretto (`t["sla_met"]`),
che **solleva** invece di mentire.

Banco: `<scratchpad>/banco_selective_metrics.py`, 13 asserzioni, EXIT=0.
