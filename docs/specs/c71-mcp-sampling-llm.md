# Cycle #71 — MCPSamplingLLM (full consolidate via subscription)

> Stato: paper-first. Build on cycle #70 P3-bis (commit 93a156b).
> Vincolo NON NEGOZIABILE: **NESSUNA API key esterna**. Solo subscription
> Claude del host (Claude Code Pro/Max).
>
> **AGGIORNAMENTO 2026-05-15 (cycle #71 BIS, commit 489e507+)**:
> Architettura validata in produzione (commit 1f36176) MA Claude Code
> come MCP host **NON espone `sampling/createMessage`** (ritorna
> `McpError: Method not found`). Pre-check capability aggiunto:
> `hippo_consolidate` in HOSTED MODE ora ritorna esplicitamente error
> chiaro "host MCP client does NOT support sampling/createMessage"
> invece di 0-skill silent failure dopo 40s. Funzionerà con host che
> espongono sampling (Claude Desktop con sampling enabled, MCP client
> custom). Per Claude Code: attendere supporto MCP sampling lato host.

## Problema

`hippo_consolidate` (full sleep cycle = dreamer NREM + dreamer REM +
critic) usa `engram/sleep.py::SleepEngine.cycle()` che fa 6+ chiamate
`self.llm.complete(...)` per cluster di episodi. Provider attuali
(`AnthropicLLM`, `OpenAILLM`, `OpenAICompatLLM`, `OllamaLLM`) leggono
una **API key esterna** e chiamano HTTP al cloud del provider → addebito.

Conseguenza: in HOSTED MODE (`HIPPO_HOSTED=1`, dentro Claude Code),
`hippo_consolidate` è **hard-refused** in `mcp_server.py:4649`. Light
consolidate (no LLM) è l'unica opzione → no dreamer, no critic, niente
skill distillation, niente REM ricombinante.

## Soluzione

Aggiungere un provider **`mcp_sampling`** che, invece di chiamare HTTP
al cloud, manda una `sampling/createMessage` request al **client MCP**
(Claude Code). Il client risponde usando la sua subscription. **Zero
costo extra** per HippoAgent.

### MCP Sampling — pattern Python SDK

```python
from mcp.server.session import ServerSession
from mcp.types import SamplingMessage, TextContent

# Dentro tool handler async:
session: ServerSession = server.request_context.session
result = await session.create_message(
    messages=[SamplingMessage(role="user",
              content=TextContent(type="text", text=prompt))],
    max_tokens=1024,
    system_prompt="You are HippoAgent dreamer.",
    temperature=0.0,
)
text: str = result.content.text  # TextContent
```

Verificato: `ServerSession.create_message(...)` esiste in `mcp` 1.x
(installato), ritorna `CreateMessageResult` con `.content` (TextContent
o ImageContent o AudioContent) e `.model`, `.stopReason`.

## Architettura

### `engram/llm.py::MCPSamplingLLM`

Interface identica a `AnthropicLLM` (drop-in replacement per `SleepEngine`):

```python
class MCPSamplingLLM:
    def __init__(self, *, loop: asyncio.AbstractEventLoop,
                 session: ServerSession):
        self._loop = loop
        self._session = session

    def complete(
        self, system: str, messages: list[dict[str, str]],
        *, model: str | None = None, temperature: float = 0.0,
        max_tokens: int | None = None,
        stop_sequences: list[str] | None = None,
    ) -> LLMResponse:
        """SYNC façade. Internally bridges to async create_message via
        run_coroutine_threadsafe → safe to call from asyncio.to_thread
        (used by hippo_consolidate handler)."""
        future = asyncio.run_coroutine_threadsafe(
            self._async_complete(system, messages, temperature,
                                 max_tokens, stop_sequences),
            self._loop,
        )
        return future.result(timeout=120.0)

    async def _async_complete(...) -> LLMResponse:
        # Build SamplingMessage list from {role, content} dicts
        sampling_msgs = [
            SamplingMessage(role=m["role"],
                            content=TextContent(type="text",
                                                text=m["content"]))
            for m in messages
        ]
        result = await self._session.create_message(
            messages=sampling_msgs,
            max_tokens=max_tokens or 1024,
            system_prompt=system,
            temperature=temperature,
            stop_sequences=stop_sequences,
        )
        text = result.content.text if hasattr(result.content, "text") else ""
        # Token counts not available in MCP sampling result — use
        # rough estimate len(text) // 4 as char→token proxy
        return LLMResponse(
            text=text, input_tokens=0, output_tokens=len(text) // 4,
            model=result.model, latency_s=0.0,
        )

    def supports_tools(self) -> bool:
        return False  # P0: text-only sampling, no tools
```

### Provider registration in `engram/llm.py::_build()`

```python
if p == "mcp_sampling":
    raise LLMError(
        "mcp_sampling provider requires explicit session injection — "
        "use MCPSamplingLLM(loop=..., session=...) constructor "
        "directly in mcp_server.py handler.",
    )
```

NOTA: `mcp_sampling` non può essere costruito da env solo (serve la
session). È OK: il provider è "injected" dal `hippo_consolidate`
handler quando rileva HOSTED mode + sampling-capable client.

### Refactor `hippo_consolidate` handler in `mcp_server.py`

```python
if name == "hippo_consolidate":
    if _is_hosted():
        # CYCLE #71: in hosted mode, route LLM via MCP sampling
        try:
            loop = asyncio.get_running_loop()
            session = server.request_context.session
            sampling_llm = MCPSamplingLLM(loop=loop, session=session)
        except (LookupError, AttributeError) as exc:
            # No request context / no session — fall back to refused
            return _err(f"sampling unavailable: {exc}")
        old_llm = a.sleep.llm
        a.sleep.llm = sampling_llm
        try:
            report = await asyncio.to_thread(a.consolidate)
        finally:
            a.sleep.llm = old_llm
    else:
        # Non-hosted: existing path with configured provider
        report = await asyncio.to_thread(a.consolidate)
    return _ok({...})
```

## Test plan (4 RED minimi)

1. RED — `MCPSamplingLLM.complete(...)` con FAKE async session che ritorna
   `CreateMessageResult(content=TextContent(text="hello"), model="claude-x")`
   → `.complete()` ritorna `LLMResponse(text="hello", model="claude-x")`.
2. RED — `MCPSamplingLLM.complete()` chiamato da thread separato
   (simula `asyncio.to_thread`) → `run_coroutine_threadsafe` bridge
   funziona, no deadlock, ritorna result entro timeout.
3. RED — `hippo_consolidate` in HOSTED MODE con session fake che ritorna
   JSON skill valido → NON refuse, `a.consolidate()` gira, ritorna
   `{n_clusters, n_nrem_skills, ...}` non-zero.
4. RED — `MCPSamplingLLM.supports_tools()` → False (P0 no tools).

## Non-goals (cycle #71)

- NON implementa `complete_with_tools` (P1 cycle #72 se necessario).
- NON cambia `light_consolidate` (resta fallback se sampling fail).
- NON aggiunge model selection (host decide quale modello usare via
  `modelPreferences` — sempre None per ora).
- NON modifica provider chain `FallbackLLM` (mcp_sampling è
  injected punto-a-punto, non in chain).

## Bench plan

`scripts/bench_c71_sampling_consolidate.py`:
- Setup: agent reale con corpus produzione (215 ep, 538 fact).
- Trigger: `hippo_consolidate` 3 run (warmup + 2 measure).
- Metriche: duration_s, n_clusters, n_nrem_skills, n_rem_skills,
  promoted, retired, output_tokens (proxy).
- Goal: dimostrare che il full consolidate funziona via subscription
  con qualità non-zero (vs light=0).

## Critic gate plan

Round critic v0.3.0 debiased su:
- Claim: "MCPSamplingLLM funziona drop-in con SleepEngine, e
  hippo_consolidate in hosted mode produce skill non-zero."
- Counterexample attesi: (a) deadlock se asyncio.to_thread re-entra
  nel main loop; (b) timeout su corpus grande; (c) malformed JSON
  da sampling. Hardening su a/b/c se trovato.

## Performance baseline

Sampling latenza dipende dal modello del host (Sonnet ~1s, Opus ~3-5s).
Full consolidate su 5 cluster × 2 chiamate = 10 LLM call. Atteso:
20-50s end-to-end. Accettabile per operazione "sleep" non-interattiva.
