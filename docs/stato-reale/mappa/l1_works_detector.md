# `verimem/l1_works_detector.py` — L1.10

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
(1) SCATTA su      «Il modulo funziona in produzione.»           senza evidenza → ✅ warning
(2) NON scatta su  «Il modulo riceve richieste dal gateway.»    → ✅ nessun warning
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
copertura: 97.0%
statement non eseguiti: 110
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/l1_works_detector.py:63` `_is_employment_use` | funzione: (nessun docstring) | `verimem/l1_works_detector.py:148` | nessuno | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 2 | `verimem/l1_works_detector.py:86` `WorksClaimWarning` | classe: Warning emitted when a 'works/confirmed' claim lacks runtime proof. | `verimem/l1_works_detector.py:131`; `verimem/l1_works_detector.py:140`; `verimem/l1_works_detector.py:157` (+1) | `tests/test_l1_works_detector.py` | - | NON MISURATO | - |
| 3 | `verimem/l1_works_detector.py:93` `_has_runtime_evidence` | funzione: Return True iff ``verified_by`` contains at least one runtime | `verimem/l1_works_detector.py:155` | `tests/test_l1_works_test_prefix_scan68.py` | - | **FUNZIONA COME PROMESSO** | eseguita, 1/13 statement del corpo scoperti (755 passed, EXIT=0) |
| 4 | `verimem/l1_works_detector.py:127` `detect_unsupported_works_claim` | funzione: Return a Warning if proposition contains 'works/confirmed' claim | `verimem/anti_confab_gate.py:136`; `verimem/anti_confab_gate.py:1504`; `verimem/l1_works_detector.py:172` | `tests/test_critic_findings_20260716.py`; `tests/test_l110_employment_fp.py`; `tests/test_l1_works_detector.py` (+1) | - | **FUNZIONA COME PROMESSO** | banco famiglia: scatta su «Il modulo funziona in produzione.…» senza evidenza, tace sulla prosa innocua; 755 passed, 6 xfailed, EXIT=0; modulo al 97.0% |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.

