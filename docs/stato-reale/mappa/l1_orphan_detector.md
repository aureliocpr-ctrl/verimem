# `verimem/l1_orphan_detector.py` — L1.x orphan

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

## La copertura di esecuzione

```
perimetro: 51 file di test che nominano i detector L1
copertura: 92.2%
statement non eseguiti: 57, 122-123
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/l1_orphan_detector.py:47` `_has_commit_ref` | funzione: Return True iff the ``verified_by`` blob contains any prefix in | `verimem/anti_confabulation.py:216`; `verimem/l1_orphan_detector.py:100`; `verimem/l1_orphan_detector.py:127` | `tests/test_anti_confab_pr_merged_r3.py` | - | **FUNZIONA COME PROMESSO** | eseguita, 1/4 statement del corpo scoperti (755 passed, EXIT=0) |
| 2 | `verimem/l1_orphan_detector.py:62` `detect_l1_orphan_candidates` | funzione: Return fact_ids that are L1-orphan candidates. | `verimem/l1_orphan_detector.py:1`; `verimem/l1_orphan_detector.py:135` | `tests/test_l1_orphan_detector.py` | - | **FUNZIONA COME PROMESSO** | eseguita, 1/25 statement del corpo scoperti (755 passed, EXIT=0) |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.

