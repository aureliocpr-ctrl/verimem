# `verimem/l1_extended_detector.py` — L1.x fix

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
(1) SCATTA su      «The bug is FIXED.»           senza evidenza → ✅ warning
(2) NON scatta su  «The bug is in the cache layer.»    → ✅ nessun warning
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
copertura: 92.6%
statement non eseguiti: 105, 135
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/l1_extended_detector.py:80` `FixClaimWarning` | classe: Warning emitted when a FIX-family claim lacks evidence. | `verimem/l1_extended_detector.py:11`; `verimem/l1_extended_detector.py:120`; `verimem/l1_extended_detector.py:130` (+2) | `tests/test_anti_confab_gate_l18_wire.py`; `tests/test_l1_extended_detector.py` | - | NON MISURATO | - |
| 2 | `verimem/l1_extended_detector.py:92` `_has_evidence_ref` | funzione: Return True iff ``verified_by`` contains at least one accepted | `verimem/l1_extended_detector.py:140` | nessuno | - | **FUNZIONA COME PROMESSO** | eseguita, 1/13 statement del corpo scoperti (755 passed, EXIT=0) |
| 3 | `verimem/l1_extended_detector.py:116` `detect_unsupported_fix_claim` | funzione: Return a Warning if the proposition contains a FIX_KEYWORDS entry | `verimem/anti_confab_gate.py:98`; `verimem/anti_confab_gate.py:1433`; `verimem/anti_confab_gate.py:1472` (+1) | `tests/test_anti_confab_gate_l18_wire.py`; `tests/test_l1_extended_detector.py`; `tests/test_unresolved_non_e_resolved.py` | - | **FUNZIONA COME PROMESSO** | banco famiglia: scatta su «The bug is FIXED.…» senza evidenza, tace sulla prosa innocua; 755 passed, 6 xfailed, EXIT=0; modulo al 92.6% |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.

