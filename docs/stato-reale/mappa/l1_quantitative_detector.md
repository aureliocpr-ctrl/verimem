# `verimem/l1_quantitative_detector.py` — L1.19

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
(1) SCATTA su      «La latenza e' 40 ms.»           senza evidenza → ✅ warning
(2) NON scatta su  «Il sistema ha quattro componenti.»    → ✅ nessun warning
(3) sulla frase NEGATA: ✅ non scatta (guardia interna)
```

**(2) è la colonna che rende leggibile (1)**: senza, un detector che
quarantena tutto passerebbe la prima prova a pieni voti.

## La copertura di esecuzione

```
perimetro: 51 file di test che nominano i detector L1
copertura: 89.1%
statement non eseguiti: 127, 131, 140
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/l1_quantitative_detector.py:116` `QuantitativeClaimWarning` | classe: (nessun docstring) | `verimem/l1_quantitative_detector.py:138`; `verimem/l1_quantitative_detector.py:153`; `verimem/l1_quantitative_detector.py:167` | `tests/test_l1_quantitative_detector.py` | - | NON MISURATO | - |
| 2 | `verimem/l1_quantitative_detector.py:122` `_has_quant_evidence` | funzione: (nessun docstring) | `verimem/l1_quantitative_detector.py:151` | nessuno | - | **FUNZIONA COME PROMESSO** | eseguita, 2/9 statement del corpo scoperti (755 passed, EXIT=0) |
| 3 | `verimem/l1_quantitative_detector.py:134` `detect_unsupported_quant_claim` | funzione: (nessun docstring) | `verimem/anti_confab_gate.py:119`; `verimem/anti_confab_gate.py:1648`; `verimem/l1_quantitative_detector.py:167` | `tests/test_l1_quantitative_detector.py`; `tests/test_la_copula_con_apostrofo_aggira_il_layer_metrico.py` | - | **FUNZIONA COME PROMESSO** | banco famiglia: scatta su «La latenza e' 40 ms.…» senza evidenza, tace sulla prosa innocua; 755 passed, 6 xfailed, EXIT=0; modulo al 89.1% |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.

