# `verimem/bench_harness.py` — 732 righe, 22 funzioni, 3 classi

**Albero**: `7b9e8ca18afda05f386dd5ebf2b6fc2487ed017b` · **owner** ws1 QA (QA) ·
**08/09**.

## Che cosa promette, e chi lo usa

Docstring: fa girare **la stessa suite di task in tre condizioni** — `raw`
(LLM nudo), `hippo_cold` (agente nuovo per ogni task), `hippo_warm` (un agente
condiviso, con `consolidate()` ogni K task) — e raggruppa i risultati per
`(condizione, provider)` per quantificare l'*uplift* della memoria attiva.

**Chi lo consuma, in tutto il repo**:

```
grep -rn "bench_harness" --include='*.py' .   (esclusi tests/ e sé stesso)
  → scripts/bench_with_without_hippo.py:37
```

**Un solo consumatore.** Nessun claim del README passa da qui: i numeri
pubblicati vengono da `benchmark/` (`moat_multilingual_matrix.py`,
`epistemic_harness.py`), che è un'altra cosa. ⇒ questo modulo è
**infrastruttura di misura interna**, non la sorgente dei numeri in vetrina.

📌 **Un documento interno è disallineato**: `docs/F2_MODULE_INVENTORY.md:49` dà
`bench_harness.py` a **637 righe**; `wc -l` ne conta **732**. Segnalato a
@Release (owner dei 287 documenti), non corretto da me.

## Il perimetro

```
1 file di test  (tests/test_bench_harness.py)
26 passed in 35,83 s                                           EXIT=0
verimem\bench_harness.py   187 stmts   25 miss   36 branch   2 BrPart   86,1%
```

## La tabella

| # | funzione (file:riga) | cosa promette | chiamata da (LETTO) | esercitata? | verdetto | prova |
|---|---|---|---|---|---|---|
| 1 | `verimem/bench_harness.py:55` `TaskCase` | il caso: id, prompt, validatore, tag | tutte le suite | ESEGUITA | **FUNZIONA COME PROMESSO** | 26 passed |
| 2 | `verimem/bench_harness.py:67` `_val_contains` + `verimem/bench_harness.py:70` `_val_contains._v` | validatore «la risposta contiene X» | le suite | ESEGUITE | **FUNZIONA COME PROMESSO** | 26 passed |
| 3 | `verimem/bench_harness.py:77` `_val_equals_int` + `verimem/bench_harness.py:81` `_val_equals_int._v` | validatore «la risposta è l'intero N» | le suite | PARZIALE (87-88) | **NON MISURATO** sul ramo `ValueError` | il caso «intero non parsabile» non è esercitato |
| 4 | `verimem/bench_harness.py:92` `default_suite` | la suite di base | `run_full_bench`, script | ESEGUITA | **FUNZIONA COME PROMESSO** | 26 passed |
| 5 | `verimem/bench_harness.py:116` `hard_memory_recall_suite` | suite dura di richiamo | `scripts/bench_with_without_hippo.py:243` | ESEGUITA | **FUNZIONA COME PROMESSO** | 26 passed |
| 6 | `verimem/bench_harness.py:178` `memory_recall_suite` | suite di richiamo | script `:216` | ESEGUITA | **FUNZIONA COME PROMESSO** | 26 passed |
| 7 | `verimem/bench_harness.py:224` `compositional_suite` | suite composizionale (113 righe di casi) | script | ESEGUITA | **FUNZIONA COME PROMESSO** | 26 passed |
| 8 | `verimem/bench_harness.py:343` `skill_compounding_suite` | suite sull'accumulo di skill | script `:182, :197` | ESEGUITA | **FUNZIONA COME PROMESSO** | 26 passed |
| 9 | `verimem/bench_harness.py:389` `RunResult` | l'esito di un caso: condizione, provider, task, successo, latenza, errore | ovunque | ESEGUITA | **FUNZIONA COME PROMESSO** | 26 passed |
| 10 | `verimem/bench_harness.py:416` `run_case_raw` | un caso in condizione `raw` | `run_suite_raw` | PARZIALE (431-432) | **NON MISURATO** sull'`except` | — |
| 11 | `verimem/bench_harness.py:439` `run_case_hippo` | un caso con l'agente | `run_suite_hippo_{cold,warm}` | PARZIALE (460-462) | **NON MISURATO** sull'`except` | — |
| 12 | `verimem/bench_harness.py:475` `_factory_failure_results` | risultati fittizi quando la factory del provider fallisce | `run_suite_hippo_warm:525` | ESEGUITA | **FUNZIONA COME PROMESSO** | 26 passed |
| 13 | `verimem/bench_harness.py:484` `run_suite_raw` | l'intera suite in `raw` | `run_full_bench:576` | ESEGUITA | **FUNZIONA COME PROMESSO** | 26 passed |
| 14 | `verimem/bench_harness.py:497` `run_suite_hippo_cold` | agente nuovo per ogni caso | `run_full_bench:578` | PARZIALE (505-511) | **NON MISURATO**: il build che fallisce | — |
| 15 | `verimem/bench_harness.py:517` `run_suite_hippo_warm` | un agente condiviso + `consolidate()` ogni K | `run_full_bench:580` | PARZIALE (524-525, 534-537) | **NON MISURATO**: build fallito e `consolidate` fallito | — |
| 16 | `verimem/bench_harness.py:545` `ProviderSpec` | nome + factory di un provider | `run_full_bench` | ESEGUITA | **FUNZIONA COME PROMESSO** | 26 passed |
| 17 | `verimem/bench_harness.py:555` `run_full_bench` | orchestra provider × condizioni | `scripts/bench_with_without_hippo.py` | **PARZIALE — 14 righe** (577-592) | **NON MISURATO**: il dispatch delle condizioni e l'abort di un provider | — |
| 18 | `verimem/bench_harness.py:608` `aggregate` | il riepilogo per (condizione, provider) | script, consumatori | **ESEGUITA** | **FUNZIONA COME PROMESSO** | 26 passed |
| 19 | `verimem/bench_harness.py:643` `aggregate_by_task` | riepilogo per task | script | **ESEGUITA** | **FUNZIONA COME PROMESSO** | 26 passed |
| 20 | `verimem/bench_harness.py:669` `aggregate_by_iter` | riepilogo per iterazione | script | **ESEGUITA** | **FUNZIONA COME PROMESSO** | 26 passed |
| 21 | `verimem/bench_harness.py:698` `to_jsonable` / `verimem/bench_harness.py:703` `from_jsonable` | serializzazione dei risultati | script | ESEGUITE | **FUNZIONA COME PROMESSO** | 26 passed |
| 22 | `verimem/bench_harness.py:722` `merge_results` | unione di più liste di risultati | script | ESEGUITA | **FUNZIONA COME PROMESSO** | 26 passed |

## Il taglio netto: **le funzioni che producono i numeri sono tutte esercitate**

`aggregate`, `aggregate_by_task`, `aggregate_by_iter`, `to_jsonable`,
`from_jsonable`, `merge_results` — **ESEGUITE tutte e sei**. È la parte che
conta se qualcuno legge un numero uscito da qui.

Le **25 righe scoperte sono, senza eccezioni, percorsi di ERRORE**:
l'`except` di `run_case_raw`, quello di `run_case_hippo`, il build dell'agente
che fallisce (`hippo_cold` e `hippo_warm`), `agent.consolidate()` che fallisce,
l'abort di un provider dentro `run_full_bench`, e un intero non parsabile.

## Perché questo non è un dettaglio

Quei rami hanno un comportamento **che decide i numeri**: quando qualcosa
fallisce, il caso **entra lo stesso nei risultati** con `success=False`. Se
quella registrazione avesse un difetto — un caso perso invece che contato come
fallito — un bench con errori produrrebbe un tasso di successo **più alto del
vero, in silenzio**. Il denominatore si accorcerebbe senza che nessuno lo veda.

⇒ **verdetto NON MISURATO**, e lo scrivo come il secondo candidato dei miei
(dopo il roundtrip WebSocket di `ide.py`) per quando si passerà dai verdetti alle
cure. **Non lo curo adesso** (regola 2 del mandato).

## Che cosa NON ho misurato

- Il modulo chiama LLM veri attraverso le factory dei provider: **non ho
  eseguito nessun bench end-to-end**, solo i 26 test unitari. La tabella parla
  della *struttura*, non della bontà dei numeri che il modulo produrrebbe.
- `docs/F2_MODULE_INVENTORY.md` dice anche «1 classe, 26 funzioni» per questo
  file, mentre l'`ast` conta **22 funzioni e 3 classi**. Altra riga per
  @Release — e un promemoria: un inventario scritto a mano invecchia.
