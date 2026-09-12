# `verimem/self_provenance.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) · **08/09**.

## Il claim del README

> `README:232` — «**Provenance on every read** — answers cite where each fact came from (conversation, document offset, tool call).»

⚠️ **Parziale**: la riga promette la provenienza *in lettura*, mentre questo modulo firma le **impronte delle scritture del motore** (`P85 actor/self-provenance`). Sono due metà della stessa catena, e la riga del README **non nomina la firma**. Attribuzione da confermare con chi tiene i claim (@ws7 Product Owner).

## La copertura di esecuzione

```
perimetro: 51 file di test che nominano i detector L1
copertura: 90.2%
statement non eseguiti: 65-66, 70-71
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/self_provenance.py:36` `is_self_ref` | funzione: True iff ``ref`` is an engine-signed footprint (``actor:...``). | `verimem/active_probe.py:38`; `verimem/active_probe.py:84`; `verimem/provenance_signing.py:41` (+7) | `tests/test_self_provenance.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 2 | `verimem/self_provenance.py:42` `actor_of` | funzione: ``actor:composer:run42`` -> ``composer``; None for non-actor refs. | `verimem/self_provenance.py:31`; `verimem/source_trust.py:147`; `verimem/source_trust.py:151` | `tests/test_self_provenance.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 3 | `verimem/self_provenance.py:50` `_threshold` | funzione: (nessun docstring) | `verimem/self_provenance.py:76` | `tests/test_verimem_env_thresholds.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 4 | `verimem/self_provenance.py:55` `self_write_check` | funzione: Fraction of engine-written facts among the ``window`` most recent ones, | `verimem/compose_daemon.py:33`; `verimem/compose_daemon.py:45`; `verimem/compose_daemon.py:56` (+1) | `tests/test_self_provenance.py` | - | **FUNZIONA COME PROMESSO** | eseguita, 2/15 statement del corpo scoperti (755 passed, EXIT=0) |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.

