# `verimem/l1_security_detector.py` — L1.12

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
(1) SCATTA su      «L'endpoint e' sicuro contro SQL injection.»           senza evidenza → ✅ warning
(2) NON scatta su  «L'endpoint accetta richieste POST.»    → ✅ nessun warning
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
copertura: 95.1%
statement non eseguiti: 104, 108->102
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/l1_security_detector.py:77` `_is_acquisition_use` | funzione: 'secured <acquisition object>' = obtained, not hardened. | `verimem/l1_security_detector.py:128` | nessuno | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 2 | `verimem/l1_security_detector.py:85` `SecurityClaimWarning` | classe: Warning emitted when 'secure/hardened' claim lacks audit evidence. | `verimem/l1_security_detector.py:120`; `verimem/l1_security_detector.py:134`; `verimem/l1_security_detector.py:148` | `tests/test_l1_security_detector.py` | - | NON MISURATO | - |
| 3 | `verimem/l1_security_detector.py:92` `_has_security_evidence` | funzione: Return True iff verified_by contains security validation evidence. | `verimem/l1_security_detector.py:132` | nessuno | - | **FUNZIONA COME PROMESSO** | eseguita, 1/14 statement del corpo scoperti (755 passed, EXIT=0) |
| 4 | `verimem/l1_security_detector.py:116` `detect_unsupported_security_claim` | funzione: Return Warning if proposition contains 'secure/hardened' claim | `verimem/anti_confab_gate.py:125`; `verimem/anti_confab_gate.py:1535`; `verimem/l1_security_detector.py:149` | `tests/test_critic_findings_20260716.py`; `tests/test_l1_bare_prefix_hardening_audit3.py`; `tests/test_l1_security_detector.py` | - | **FUNZIONA COME PROMESSO** | banco famiglia: scatta su «L'endpoint e' sicuro contro SQL in…» senza evidenza, tace sulla prosa innocua; 755 passed, 6 xfailed, EXIT=0; modulo al 95.1% |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.

