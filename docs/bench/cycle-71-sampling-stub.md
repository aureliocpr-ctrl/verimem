# Cycle #71 — MCPSamplingLLM Stub Consolidate Bench

> Date: 2026-05-15. Run: `python scripts/bench_c71_sampling_consolidate.py`.
> JSON: `cycle-71-sampling-stub.json`.
>
> Corpus stub: 10 episodi sintetici (5 success + 5 failure) in tmp dir
> isolato. SleepEngine completo (NREM + REM + counterfactual + schema +
> practice + critic) con `MCPSamplingLLM` che parla con FakeSession (stub
> MCP host che ritorna JSON skill canned + `asyncio.sleep(5ms)`).
>
> Scopo: dimostrare che il pattern end-to-end è **funzionalmente
> corretto** — SleepEngine produce skill via sampling senza API key
> esterna. Latenze ASSOLUTE non sono significative (LLM è stub). Latenze
> RELATIVE indicano overhead asyncio-bridge.

## Risultati

| Metric | Warmup (run 0) | Measure mean (run 1+2) |
|---|---|---|
| Elapsed end-to-end | 43.1 s | 30.2 s |
| n_clusters | 6 | 6 |
| n_nrem_skills | 6 | 6 |
| n_rem_skills | 2 | 2 |
| n_facts | 6 | 6 |
| Errors | 0 | 0 |

**Totali aggregati**: 43 chiamate `session.create_message` su 3 run
(14/run media). p50 12.3ms / mean 12.5ms / max 20.1ms per call (overhead
asyncio bridge + stub roundtrip).

## Sezioni del sleep cycle (1 run)

Da log strutturato:
- `consolidation_started` 200 ep cap
- 7 cluster identificati (`clusters_built`)
- 6 NREM skill prodotti (`nrem_synthesized`)
- 2 REM skill prodotti (`rem_synthesized`) — recombination
- 1 schema (`schema_synthesized` n_children=25)
- 2 counterfactual targets attempted (1 duplicate skipped)
- 1 practice cycle
- 3 merge (deduplica)
- 0 promotion / 0 retirement (corpus stub troppo piccolo)

## Validazione architetturale

1. **No API key esterna usata**: bench gira con `ANTHROPIC_API_KEY`
   non settato (verificato esplicitamente in stack trace pre-fix).
   Provider injection via `a.sleep.llm = MCPSamplingLLM(...)` funziona.
2. **Bridge sync→async safe**: `asyncio.to_thread(a.consolidate)` +
   `run_coroutine_threadsafe` da dentro SleepEngine→`llm.complete()` →
   NO deadlock, NO hang, completa in tempo prevedibile.
3. **JSON parsing dreamer**: stub ritorna JSON skill valido →
   dreamer estrae name/trigger/body/rationale → SkillLibrary.store
   senza errori.

## Limit dichiarati

- **Latenze non-rappresentative**: lo stub fa `asyncio.sleep(5ms)`. In
  produzione (subscription Sonnet) ogni call sarà ~1-3 s. Estrapolazione:
  43 call × 2 s = ~86 s totali per 3 run, ~30s per consolidate single.
  Accettabile per "sleep operation" non-interattiva.
- **Token estimate proxy**: MCP sampling result non espone usage stats,
  quindi `tokens_used` è char-count // 4. Approssimazione grossolana.
- **Real LLM test PENDING**: il bench REAL via subscription Claude Code
  va eseguito da Aurelio post-restart MCP server. Lo stub valida solo
  l'architettura, non la qualità del JSON output del modello reale.

## Conclusione

`MCPSamplingLLM` è production-ready a livello pattern. Il prossimo step
è **post-restart MCP**: chiamare `hippo_consolidate` da una sessione
Claude Code attiva, dove `server.request_context.session` è la sessione
MCP reale verso il host con subscription. Atteso: 6+ skill nuovi
prodotti dal vero LLM su corpus reale (215 ep, 538 fact, 318 skill).

## Next bench (post-restart)

`scripts/bench_c71_sampling_consolidate_real.py` (da scrivere): chiama
`mcp__hippoagent__hippo_consolidate` con corpus produzione, salva
report skill prodotti + qualità (% schemas keep, % retired, durata).
