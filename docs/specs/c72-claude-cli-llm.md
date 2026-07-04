# Cycle #72 — ClaudeCLILLM (subscription via `claude -p` subprocess)

> Data: 2026-05-15. Build on cycle #71 BIS (commit 18b8224).
> Vincolo NON NEGOZIABILE: NESSUNA API key esterna. SOLO subscription
> Claude Code Pro/Max.

## Problema

Cycle #71 (commit 1f36176 + 489e507 + 18b8224) implementa MCP sampling
provider per `hippo_consolidate` in HOSTED MODE. Pattern architetturalmente
corretto, ma **Claude Code come MCP host NON espone**
`sampling/createMessage` — `McpError: Method not found`. Risultato:
hippo_consolidate full bloccato → `hippo_consolidate_light` resta
l'unica opzione operativa (no dreamer, no critic, no REM).

Aurelio: "ci stiamo girando intorno da 24 ore — impegnati seriamente".

## Soluzione

Bypassare lo MCP sampling. Usare `claude -p` (Claude Code CLI in
`--print` non-interactive mode) come subprocess. La CLI autentica
automaticamente via OAuth/keychain locale (la stessa subscription
attiva di Aurelio) — ZERO API key, ZERO MCP sampling.

### Sanity check già eseguito

```bash
$ echo "Output strict JSON only: {...}" | claude -p --output-format json
# duration 8.6s, is_error: false, result: '{"name": "test", ...}'
# auth: subscription OAuth (no --bare)
# model: claude-opus-4-7[1m] (dal modelUsage), 1M context
```

Funziona. Subprocess Python → CLI Claude → subscription → JSON in stdout.

## Architettura

### `engram/llm.py::ClaudeCLILLM`

Drop-in replacement per `AnthropicLLM`/`MCPSamplingLLM`. Implementa la
stessa interfaccia `complete(system, messages, ...) → LLMResponse` SYNC.

```python
class ClaudeCLILLM:
    def __init__(self, *, claude_bin: str = "claude",
                 timeout_s: float = 180.0,
                 extra_args: list[str] | None = None) -> None:
        self.claude_bin = claude_bin
        self.timeout_s = timeout_s
        self.extra_args = extra_args or []

    def complete(self, system, messages, *, model=None,
                 temperature=0.0, max_tokens=None,
                 stop_sequences=None) -> LLMResponse:
        # 1. Concatena system + messages in un unico prompt text
        # 2. Esegue: claude -p --output-format json <flag>
        # 3. Parsa stdout JSON {result: "<text>", is_error, ...}
        # 4. Ritorna LLMResponse con .text = result["result"]
        ...

    def supports_tools(self) -> bool:
        return False  # P0 text-only
```

### Costruzione prompt

`claude -p` accetta prompt via stdin O argv. Per evitare quoting hell su
Windows, passo via stdin:

```python
full_prompt = f"{system}\n\n{user_content}"
result = subprocess.run(
    [self.claude_bin, "-p", "--output-format", "json"]
    + self.extra_args,
    input=full_prompt, capture_output=True, text=True,
    timeout=self.timeout_s, encoding="utf-8",
)
data = json.loads(result.stdout)
text = data["result"]
```

### Provider registration

```python
# engram/llm.py::_build
if p == "claude_cli":
    return ClaudeCLILLM()
```

### Refactor handler `hippo_consolidate`

In HOSTED MODE, prova FALLBACK chain:
1. **MCP sampling** se `session.check_client_capability(SamplingCapability)`
2. **ClaudeCLILLM** se `shutil.which("claude")` esiste
3. **fail-fast** con error chiaro

```python
if _is_hosted():
    if check_client_capability(SamplingCapability):
        llm = MCPSamplingLLM(loop, session)
    elif shutil.which("claude"):
        llm = ClaudeCLILLM()
    else:
        return _err("...")
    a.sleep.llm = llm
    ...
```

## Test plan (4 RED)

1. **RED**: `ClaudeCLILLM.complete()` con `subprocess.run` mocked
   ritorna stdout JSON valido → LLMResponse(text="...", model="...").
2. **RED**: timeout / non-zero exit → LLMError raised.
3. **RED**: `supports_tools()` → False.
4. **RED**: handler `hippo_consolidate` in hosted mode + sampling
   capability missing + `shutil.which("claude")` mock → usa ClaudeCLILLM
   (verifica via mock subprocess che è stato chiamato).

## Limit dichiarati P0

- **Latenza**: 1 call = ~8s subprocess startup + LLM. 14 call consolidate
  = ~2 min totali. Accettabile per "sleep" non-interattiva.
- **No tool-use**: `--bare` mode disabilitato (servono OAuth), ma per
  consolidate prompt-only va bene. Tool-use viene in cycle #73 se serve.
- **Subprocess spawn overhead**: 3.7s TTFT su test. Mitigabile con
  `--continue` o session reuse in cycle #73 se serve.
- **Cost USD reported**: `total_cost_usd: 0.3125` nel JSON output è
  metadata informativo, assorbito dalla subscription (non è addebito
  separato). HippoAgent NON usa quel field.

## Bench plan

Run reale `hippo_consolidate` post-implement: misurare
duration_s + n_nrem_skills + n_rem_skills + 0 errori. Confronto con
stub bench (29s, 6+2 skill) → reale atteso ~2-3 min, skill simile.

## Critic gate plan

Round v0.3.0 su:
- Claim: "ClaudeCLILLM via subprocess sblocca consolidate full in
  HOSTED MODE senza API key esterna, usando subscription OAuth."
- Falsification stash: pre-fix vs post-fix test transition.
- Caller verification: chain handler→sleep.cycle→ClaudeCLILLM.complete.

## Non-goals (cycle #72)

- NON tool-use via CLI (richiede --bare + permission setup complex).
- NON streaming (cycle #73 se serve).
- NON model selection (host decide via subscription default).
- NON refactor SleepEngine ad async.
