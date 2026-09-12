# `verimem/l1_automated_detector.py` — L1.18

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
(1) SCATTA su      «Il backup e' automatizzato.»           senza evidenza → ✅ warning
(2) NON scatta su  «Il backup copia la cartella dei dati.»    → ✅ nessun warning
(3) sulla frase NEGATA: ⚠️ SCATTA (il detector non conosce la negazione)
```

**(2) è la colonna che rende leggibile (1)**: senza, un detector che
quarantena tutto passerebbe la prima prova a pieni voti.

📌 **Sul punto (3)**: non è un difetto del prodotto. La guardia
della negazione sta **a valle**, dove il gate raccoglie i warning
(`negation_scope.py`, importato da `anti_confab_gate.py:140-141`),
e stare in un punto solo è un pregio dichiarato. **Ma la funzione
`detect_unsupported_*` è pubblica**: chi la importa direttamente
riceve un warning su una frase onesta («…**non** funziona»), cioè
il difetto curato il 2026-08-04. Limite noto della superficie
pubblica, misurato l'08/09; nessuna cura (regola 2).

## La copertura di esecuzione

```
perimetro: 51 file di test che nominano i detector L1
copertura: 94.4%
statement non eseguiti: 99, 157
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/l1_automated_detector.py:89` `AutomationClaimWarning` | classe: (nessun docstring) | `verimem/l1_automated_detector.py:155`; `verimem/l1_automated_detector.py:171`; `verimem/l1_automated_detector.py:183` | `tests/test_l1_automated_detector.py` | - | NON MISURATO | - |
| 2 | `verimem/l1_automated_detector.py:94` `_has_automated_evidence` | funzione: (nessun docstring) | `verimem/l1_automated_detector.py:158` | nessuno | - | **FUNZIONA COME PROMESSO** | eseguita, 1/11 statement del corpo scoperti (755 passed, EXIT=0) |
| 3 | `verimem/l1_automated_detector.py:111` `_is_descriptive_occurrence` | funzione: True iff THIS specific automation keyword is a descriptive recurring | `verimem/l1_automated_detector.py:165` | nessuno | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 4 | `verimem/l1_automated_detector.py:151` `detect_unsupported_automated_claim` | funzione: (nessun docstring) | `verimem/anti_confab_gate.py:81`; `verimem/anti_confab_gate.py:1630`; `verimem/l1_automated_detector.py:183` | `tests/test_l1_automated_detector.py`; `tests/test_l1_bare_prefix_hardening_audit3.py`; `tests/test_l1_fp_reduction.py` (+1) | - | **FUNZIONA COME PROMESSO** | banco famiglia: scatta su «Il backup e' automatizzato.…» senza evidenza, tace sulla prosa innocua; 755 passed, 6 xfailed, EXIT=0; modulo al 94.4% |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.

