# `verimem/l1_tested_detector.py` — L1.x tested

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) · **08/09**.

## Il claim del README

> `README:704` — «Write-path gate (**unsupported "it works" claims
> quarantined** — stored, not served)»
>
> `README:218-224` — «each row also says **WHICH screen stopped it**
> and what would let it through, recomputed on the spot»

⚠️ Le righe **100-160**, che l'indice indicava per questa famiglia,
parlano del **grounding moat (L4)** e della banda a due soglie: sono
un'altra superficie. Verificato leggendole tutte e sessanta.

## La prova: il banco della famiglia, tre domande

```
(1) SCATTA su      «Il parser e' testato.»           senza evidenza → ✅ warning
(2) NON scatta su  «Il parser legge file JSON.»    → ✅ nessun warning
(3) sulla frase NEGATA: ✅ non scatta (guardia interna)
```

**(2) è la colonna che rende leggibile (1)**: senza, un detector che
quarantena tutto passerebbe la prima prova a pieni voti.

## La copertura di esecuzione

```
perimetro: 51 file di test che nominano i detector L1
copertura: 91.6%
statement non eseguiti: 157, 164, 176, 192
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/l1_tested_detector.py:73` `_e_sintassi` | funzione: La parola e' un pezzo di codice citato, non un'asserzione? | `verimem/l1_tested_detector.py:199` | `tests/test_la_regex_quadratica_riceve_quaranta_caratteri.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 2 | `verimem/l1_tested_detector.py:139` `VerificationClaimWarning` | classe: (nessun docstring) | `verimem/l1_tested_detector.py:190`; `verimem/l1_tested_detector.py:207`; `verimem/l1_tested_detector.py:218` | `tests/test_l1_tested_detector.py` | - | NON MISURATO | - |
| 3 | `verimem/l1_tested_detector.py:144` `_has_tested_evidence` | funzione: True solo se ``verified_by`` contiene un ref di test VERIFICABILE. | `verimem/l1_extended_detector.py:66`; `verimem/l1_tested_detector.py:205`; `verimem/proof_evidence.py:6` (+2) | `tests/test_l1_tested_test_prefix_bypass.py`; `tests/test_la_prova_eseguita_da_un_altro_prefisso.py`; `tests/test_unresolved_non_e_resolved.py` | - | **FUNZIONA COME PROMESSO** | eseguita, 3/25 statement del corpo scoperti (755 passed, EXIT=0) |
| 4 | `verimem/l1_tested_detector.py:186` `detect_unsupported_tested_claim` | funzione: (nessun docstring) | `verimem/anti_confab_gate.py:130`; `verimem/anti_confab_gate.py:1583`; `verimem/l1_tested_detector.py:218` | `tests/test_l1_tested_detector.py`; `tests/test_l1_tested_test_prefix_bypass.py`; `tests/test_non_testato_non_e_un_claim_di_test.py` | - | **FUNZIONA COME PROMESSO** | banco famiglia: scatta su «Il parser e' testato.…» senza evidenza, tace sulla prosa innocua; 755 passed, 6 xfailed, EXIT=0; modulo al 91.6% |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.

