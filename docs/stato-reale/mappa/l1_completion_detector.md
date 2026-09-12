# `verimem/l1_completion_detector.py` — L1.13

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
(1) SCATTA su      «La migrazione e' completata.»           senza evidenza → ✅ warning
(2) NON scatta su  «La migrazione tocca quattro tabelle.»    → ✅ nessun warning
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
copertura: 96.2%
statement non eseguiti: 135, 269-270
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/l1_completion_detector.py:109` `_e_il_sostantivo_fatto` | funzione: La parola trovata e' «fatto/fatti/fatta/fatte» usato come NOME? | `verimem/l1_completion_detector.py:229` | nessuno | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 2 | `verimem/l1_completion_detector.py:121` `CompletionClaimWarning` | classe: Warning emitted when 'complete/done/finished' claim lacks | `verimem/l1_completion_detector.py:211`; `verimem/l1_completion_detector.py:276`; `verimem/l1_completion_detector.py:289` | `tests/test_l1_completion_detector.py` | - | NON MISURATO | - |
| 3 | `verimem/l1_completion_detector.py:129` `_has_completion_evidence` | funzione: Return True iff verified_by contains closing criteria evidence. | `verimem/l1_completion_detector.py:235` | nessuno | - | **FUNZIONA COME PROMESSO** | eseguita, 1/24 statement del corpo scoperti (755 passed, EXIT=0) |
| 4 | `verimem/l1_completion_detector.py:180` `_il_participio_e_nella_fonte` | funzione: La fonte contiene lo STESSO participio che ha fatto scattare il match? | `verimem/l1_completion_detector.py:220`; `verimem/l1_completion_detector.py:250` | nessuno | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 5 | `verimem/l1_completion_detector.py:205` `detect_unsupported_completion_claim` | funzione: Return Warning if proposition contains completion claim AND | `verimem/anti_confab_gate.py:88`; `verimem/anti_confab_gate.py:1551`; `verimem/l1_completion_detector.py:290` | `tests/test_il_fatto_sostantivo_non_e_un_lavoro_finito.py`; `tests/test_il_perdono_non_si_compra_riscrivendo_il_claim_come_fonte.py`; `tests/test_l1_13_non_ferma_un_ricalco_della_fonte.py` (+2) | - | **FUNZIONA COME PROMESSO** | banco famiglia: scatta su «La migrazione e' completata.…» senza evidenza, tace sulla prosa innocua; 755 passed, 6 xfailed, EXIT=0; modulo al 96.2% |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.

