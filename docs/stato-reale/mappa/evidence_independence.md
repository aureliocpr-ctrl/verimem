# `verimem/evidence_independence.py`

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) · **08/09**.

## Il claim del README

> `README:462` — «`verified_by` records WHERE the claim came from — it is shown
> on every read and **cannot be forged into a higher trust status** (**a
> self-cited receipt never becomes "verified"**; the gate's outcome + provenance
> are the trust signal, not a self-asserted badge).»

Letto e verificato: il modulo implementa esattamente quel «self-cited receipt
never becomes verified» — il suo docstring `:19-21` dice «**self-citation IS the
laundering move** (write the poison, then cite yourself)».

⚠️ **CORREZIONE DI UNA MIA ATTRIBUZIONE, fatta un'ora dopo averla pubblicata.**
Avevo scritto qui `README:292-296` («*Independence clustering collapses
copies/colluders of one feed to a single witness, so manufactured consensus
cannot self-confirm*»), e **non è di questo modulo**: quel clustering è
implementato in **`source_trust.py:47, 88, 186`** (`grep -rn "cluster"` su
`verimem/`), che non è nella mia parte. Il nome combaciava — «independence» — e
mi ero fermata lì.

🔑 **Per attribuire un claim non basta che il modulo sembri farlo: bisogna
verificare che nessun ALTRO lo faccia.** Un claim ha un solo implementatore, e
il candidato più ovvio non è sempre quello giusto. È la stessa forma del `grep`
che trova e non conclude, applicata all'attribuzione.

## La copertura di esecuzione

```
perimetro: 51 file di test che nominano i detector L1
copertura: 95.3%
statement non eseguiti: 94-95, 129, 139->141, 169
```

## La tabella

⚠️ Bozza generata con `scripts/mappa_bozza.py` (del lead) e **confermata
leggendo**: la colonna «chiamata da» viene da `git grep` per nome, e nel
progetto **589 funzioni su 2.973 (19,8%) condividono il nome** con
un'altra. Le righe con un omonimo plausibile sono segnate.

| # | funzione (`file:riga`) | cosa promette | chiamata da | test che la esercita | claim README | verdetto | prova |
|---|---|---|---|---|---|---|---|
| 1 | `verimem/evidence_independence.py:58` `LazyDocumentStore` | classe: A document store that opens only if the rule actually asks something. | `verimem/client.py:734`; `verimem/client.py:747`; `verimem/evidence_independence.py:46` (+4) | `tests/test_p0_independence_wiring.py` | - | NON MISURATO | - |
| 2 | `verimem/evidence_independence.py:70` `LazyDocumentStore.__init__` | funzione: (nessun docstring) | `verimem/_compat.py:27`; `verimem/client.py:355`; `verimem/document_index.py:255` (+11) | `tests/perf/seed_data.py`; `tests/security/test_pentest_validation.py`; `tests/test_abstention_hybrid.py` (+265) | - | NON MISURATO | - |
| 3 | `verimem/evidence_independence.py:75` `LazyDocumentStore._resolve` | funzione: (nessun docstring) | `verimem/content_pin.py:138`; `verimem/evidence_independence.py:89`; `verimem/grounding_gate.py:237` (+2) | `tests/test_il_riferimento_in_un_fatto_non_esce_dalla_radice.py`; `tests/test_mcp_contradiction.py` | - | NON MISURATO | - |
| 4 | `verimem/evidence_independence.py:88` `LazyDocumentStore.list_versions` | funzione: (nessun docstring) | `verimem/evidence_independence.py:93`; `verimem/evidence_independence.py:147`; `verimem/mcp_server.py:8527` (+1) | `tests/test_documents_tier.py`; `tests/test_evidence_independence.py`; `tests/test_gate_independence_observe.py` (+3) | - | NON MISURATO | - |
| 5 | `verimem/evidence_independence.py:98` `channel_of` | funzione: ``"gw:team-alpha"`` → ``"gw"``; ``None`` when there is no channel part. | `verimem/evidence_independence.py:48` | `tests/test_evidence_independence.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 6 | `verimem/evidence_independence.py:110` `is_trusted_channel` | funzione: True unless the identity is absent or explicitly unbound. | `verimem/evidence_independence.py:50`; `verimem/evidence_independence.py:212`; `verimem/evidence_independence.py:237` | `tests/test_evidence_independence.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 7 | `verimem/evidence_independence.py:124` `_source_id_of_ref` | funzione: ``doc:<source_id>`` / ``file:<path>[:<line>]`` → the source_id used at | `verimem/evidence_independence.py:159` | nessuno | - | **FUNZIONA COME PROMESSO** | eseguita, 1/13 statement del corpo scoperti (755 passed, EXIT=0) |
| 8 | `verimem/evidence_independence.py:145` `_stamps_for_source` | funzione: One entry per stored version: its ``indexed_by``, or None if unstamped. | `verimem/evidence_independence.py:163`; `verimem/evidence_independence.py:169` | nessuno | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |
| 9 | `verimem/evidence_independence.py:152` `author_principal_of_ref` | funzione: Who vouched for the document behind ``ref`` — or None. | `verimem/evidence_independence.py:47`; `verimem/evidence_independence.py:228` | `tests/test_evidence_independence.py` | - | **FUNZIONA COME PROMESSO** | eseguita, 1/17 statement del corpo scoperti (755 passed, EXIT=0) |
| 10 | `verimem/evidence_independence.py:182` `IndependenceVerdict` | classe: The AND rule's answer, with the reason it reached it. | `verimem/evidence_independence.py:45`; `verimem/evidence_independence.py:197`; `verimem/evidence_independence.py:207` (+7) | nessuno | - | NON MISURATO | - |
| 11 | `verimem/evidence_independence.py:190` `IndependenceVerdict.to_dict` | funzione: (nessun docstring) | `verimem/cli.py:2274`; `verimem/compilation.py:68`; `verimem/dashboard_routes/settings.py:338` (+9) | `tests/test_bayesian_gates.py`; `tests/test_compilation.py`; `tests/test_composer.py` (+14) | - | NON MISURATO | - |
| 12 | `verimem/evidence_independence.py:195` `independence_verdict` | funzione: Evaluate the AND rule over the refs a claim cites. | `verimem/anti_confab_gate.py:3258`; `verimem/anti_confab_gate.py:3259`; `verimem/evidence_independence.py:49` | `tests/test_evidence_independence.py` | - | **FUNZIONA COME PROMESSO** | eseguita: nessuno dei suoi statement è fra i non eseguiti dei 51 file (755 passed, EXIT=0) |

⚠️ **«FUNZIONA COME PROMESSO» qui vuol dire: eseguita dai test del
perimetro, e — per la funzione pubblica `detect_*` — provata nel
merito dal banco della famiglia.** Per le funzioni private il
verdetto poggia sull'esecuzione, non su un'asserzione sul loro
comportamento: chi vuole di più deve rompere la riga e guardare chi
si accende. **Non l'ho fatto per queste**, e lo scrivo.

