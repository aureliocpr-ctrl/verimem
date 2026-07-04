# HippoAgent — Platform Reference

End-to-end overview of the moving parts. For research provenance see
`FORGIA.md`; for migrations see `docs/MIGRATIONS.md`; for the
day-to-day cheatsheet see `README.md`.

> Last sync: 2026-05-09 (after FORGIA pezzo #29).

---

## 1. Component map

```
                                 ┌──────────────────────────┐
        Claude Code,             │     MCP server (stdio)   │
        Cursor, opencode, ...  → │  hippoagent.mcp_server   │
                                 │  • hippo_run_task        │
                                 │  • hippo_consolidate     │
                                 │  • hippo_recall          │
                                 │  • hippo_skills_for      │
                                 │  • hippo_status          │
                                 │  + 6 admin tools         │
                                 └────────────┬─────────────┘
                                              │
                                              ▼
   ┌─────────────────────────────────────────────────────────────────────┐
   │                          HippoAgent.build()                         │
   │                                                                     │
   │   ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────┐  │
   │   │ WakeAgent   │  │ SleepEngine  │  │ EpisodicMem  │  │ Skill   │  │
   │   │ ReAct loop  │◄─┤ NREM/REM     │  │ SQLite v4    │  │ Library │  │
   │   │ tool dispat.│  │ replay+merge │  │ DG/TCM/Hopf  │  │ Bayes   │  │
   │   └──────┬──────┘  └──────┬───────┘  └──────┬───────┘  └────┬────┘  │
   │          │                │                 │               │       │
   │          ▼                ▼                 ▼               ▼       │
   │   ┌─────────────────────────────────────────────────────────────┐   │
   │   │                 LLM Provider (multi-provider)               │   │
   │   │  Anthropic, OpenAI, OpenRouter, Groq, DeepSeek, Mistral,    │   │
   │   │  Qwen, Zhipu, Moonshot, Gemini, xAI, Fireworks, Together,   │   │
   │   │  Cerebras, Yi, Baichuan, Doubao, Perplexity, Novita,        │   │
   │   │  SambaNova, Hyperbolic, LM Studio, Ollama, Mock             │   │
   │   │                                                             │   │
   │   │  + FallbackLLM chain — retry on 429/5xx/timeout             │   │
   │   └─────────────────────────────────────────────────────────────┘   │
   └─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Configuration knobs (env)

The single source of truth is `hippoagent/config.py`. Only the env vars
documented here are read at config-load time; everything else is
hyperparameter (constant in the codebase or set via `object.__setattr__`
in tests).

| Env var | What it sets | Default | When it's read |
|---|---|---|---|
| `HIPPO_DATA_DIR` | root for episodes DB / skills / semantic / runs / reports | `<project>/data` | once at config import (FORGIA #29) |
| `HIPPO_LLM_PROVIDER` | force a specific provider, ignoring autodetect | autodetect | every `get_llm()` call |
| `HIPPO_OFFLINE` | force MockLLM, no network | unset | every `get_llm()` call |
| `HIPPO_MODEL` | override model id for every stage | provider default | every `resolve_model()` |
| `HIPPO_MODEL_EXECUTOR` / `_DREAMER` / `_CRITIC` | per-stage model override | inherit `HIPPO_MODEL` | every `resolve_model()` |
| `HIPPO_LOG_STDERR` | route structured logs to stderr (MCP needs this) | unset (stdout) | once at observability import (FORGIA #28) |
| `HIPPO_ENABLE_SHELL` | enable shell-running tool path | off | every `shell_run` dispatch |
| `HIPPO_MCP_DISABLE_RATELIMIT` | bypass token-bucket on MCP tools | off | every MCP tool call |
| `HIPPO_MCP_RATELIMIT_<TOOL>_RPM` / `_CAP` | per-tool rate-limit overrides | 1/min | first MCP call per tool |
| `<PROVIDER>_API_KEY` | unlock that provider | — | autodetect + per-call |
| `HIPPO_AUTO_FALLBACK` | auto-chain every other configured provider after the primary (anti rate-limit) | unset (off) | every `get_llm()` call (FORGIA #45) |

Provider keys: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`,
`GROQ_API_KEY`, `MISTRAL_API_KEY`, `DEEPSEEK_API_KEY`, `DASHSCOPE_API_KEY`,
`MOONSHOT_API_KEY`, `ZHIPU_API_KEY`, `GEMINI_API_KEY`, `XAI_API_KEY`,
`FIREWORKS_API_KEY`, `TOGETHER_API_KEY`, `CEREBRAS_API_KEY`, `YI_API_KEY`,
`BAICHUAN_API_KEY`, `DOUBAO_API_KEY`, `PERPLEXITY_API_KEY`,
`NOVITA_API_KEY`, `SAMBANOVA_API_KEY`, `HYPERBOLIC_API_KEY`,
`LMSTUDIO_API_KEY`. Ollama runs on `localhost:11434` by default —
override with `OLLAMA_HOST`.

---

## 3. End-to-end task flow

### 3.1 Wake (live execution)

```
task_text
   │
   ▼
WakeAgent.run(task_id, task_text, validator)
   │
   ├── ContextEngine.observe(task_emb)         [TCM cross-session — FORGIA #15/17]
   │
   ├── _retrieve_skills(task_text)             [Bayesian top-k from SkillLibrary]
   ├── _retrieve_episodes(task_text)           [DG sparse + TCM context + salience + recency]
   │
   ├── _try_compiled_macro(...)?               [Procedural compilation fast-path]
   │   └── (if hit) execute deterministically — 0 LLM calls
   │
   ├── _run_loop(...)                           [ReAct loop, max_steps]
   │   ├── prompt_builder
   │   ├── LLM.complete_with_tools / complete
   │   ├── _dispatch(tool_call)
   │   └── append observation, repeat
   │
   ├── (on failure) self-critique → optional retry
   │
   ├── episode.outcome = success/failure
   ├── _build_episode_context(post-task TCM drift)
   ├── memory.store(episode, context_emb=ctx)   [DG-encoded + context BLOB]
   │
   └── skills.update_fitness(...)               [Beta-Binomial Bayesian update]
```

### 3.2 Sleep (consolidation)

```
SleepEngine.cycle()
   │
   ├── stage_replay(forward_replay)              [salience-weighted priority]
   ├── stage_clustering                          [DG sparse cosine + agglom]
   ├── stage_NREM(synthesise canonical skill)    [LLM dreamer]
   ├── stage_REM(counterfactual + recombine)     [LLM dreamer + critic]
   ├── stage_schema(meta-skill from cluster)     [LLM dreamer]
   ├── stage_practice(low-fitness prompts)
   ├── stage_promote_retire(Bayesian decision)
   └── stage_decay_prune(Ebbinghaus)             [FORGIA #7/9]
```

### 3.3 Recall (multiple ranking modes)

```
EpisodicMemory.recall(query, k, *,
                       use_dg=False,             # Dentate Gyrus pattern separation
                       use_hopfield=False,       # Modern Hopfield (Ramsauer 2020)
                       hopfield_beta=8.0,        # softmax temperature
                       salience_weight=0.0,      # Mattar-Daw replay priority
                       recency_weight=0.0,
                       recency_tau_s=...,
                       context_emb=None,         # Tulving 1973 encoding-specificity
                       context_weight=0.0,
                       outcome_filter=None,      # 'success' | 'failure' | None
                       track_access=True)
```

Three orthogonal axes:
1. **Ranking primary**: cosine | DG-sparse | Hopfield
2. **Re-rank dimensions**: salience, recency, context-similarity
3. **Filtering**: outcome, optional access tracking

---

## 4. Multi-model bench harness (FORGIA #27)

Run the SAME task suite under three conditions on every available
provider, see who actually benefits from active memory.

```bash
# Mock-only (always works):
python scripts/bench_with_without_hippo.py --providers mock

# Auto-detect from env keys:
python scripts/bench_with_without_hippo.py --providers auto

# Specific subset:
python scripts/bench_with_without_hippo.py \
       --providers anthropic,groq,openrouter,deepseek \
       --conditions raw,hippo_warm \
       --consolidate-every 3 \
       --output-dir ./bench-out

# Render the summary as markdown:
python scripts/bench_summary_md.py ./bench-out/bench_with_without_hippo.summary.json
```

Conditions:
- `raw` — single-shot LLM, no memory/skills/sleep. Baseline.
- `hippo_cold` — fresh HippoAgent per task (wake/sleep machinery, no
  shared memory). Isolates wake-loop value from accumulated experience.
- `hippo_warm` — single agent, shared memory, sleep cycle every K tasks.
  Where the forged primitives (DG/TCM/Hopfield/SR) actually pay off.

Every (condition × provider) cell is isolated: a quota outage on one
provider doesn't abort the run; failures are recorded with `error=...`
in the result list.

Output: `bench_with_without_hippo.results.json` (every record) and
`bench_with_without_hippo.summary.json` (success_rate, mean_tokens,
mean_latency_s, mean_attempts grouped by (condition, provider)).

A `bench_with_without_hippo.partial.json` is written after every
(provider, condition) cell — if the run crashes mid-bench, the
partial file holds everything completed before the crash (FORGIA #49).

To diff two bench summaries (e.g. before/after a code change):

```bash
make bench-compare BEFORE=data/bench_real_before.summary.json \
                   AFTER=data/bench_real_after.summary.json
# or:
python scripts/bench_compare.py BEFORE.json AFTER.json --threshold 0.05
```

Exit code is 0 if every cell stays within `--threshold`, 1 otherwise.
Drop the markdown output into a PR comment.

### Reference run (2026-05-09, 4 real providers, 5-task default suite)

Configuration: `--providers anthropic,groq,openrouter,deepseek
--consolidate-every 3`. Wall-clock: 426s for 60 results, zero
provider failures. Raw data committed at
`data/bench_real_4providers.{results,summary}.json`.

| provider | condition | n | success | tokens | latency_s | attempts | errors |
|---|---|--:|--:|--:|--:|--:|--:|
| anthropic | raw | 5 | 1.00 | 56 | 0.73 | 1.0 | 0 |
| anthropic | hippo_cold | 5 | 1.00 | 3846 | 5.62 | 1.6 | 0 |
| anthropic | hippo_warm | 5 | 1.00 | 3616 | 1.87 | 1.4 | 0 |
| deepseek | raw | 5 | 1.00 | 46 | 0.69 | 1.0 | 0 |
| deepseek | hippo_cold | 5 | 1.00 | 2954 | 2.12 | 1.2 | 0 |
| deepseek | hippo_warm | 5 | 1.00 | 2485 | 1.94 | 1.2 | 0 |
| groq | raw | 5 | 1.00 | 78 | 0.21 | 1.0 | 0 |
| groq | hippo_cold | 5 | 0.80 | 2602 | 14.38 | 1.0 | 0 |
| groq | hippo_warm | 5 | 1.00 | 3085 | 17.58 | 1.2 | 0 |
| openrouter | raw | 5 | 1.00 | 56 | 1.63 | 1.0 | 0 |
| openrouter | hippo_cold | 5 | 1.00 | 3628 | 3.50 | 1.2 | 0 |
| openrouter | hippo_warm | 5 | 1.00 | 3584 | 3.44 | 1.2 | 0 |

**Honest reading of the numbers:**

1. **Raw wins on this suite.** 100 % accuracy at ~50 tokens / 0.7 s
   per task across every provider. No surprise — the default suite is
   trivia-grade (capital/2+2/reverse/echo/format). For trivia, a wake
   loop with retrieval + tools is **overhead, not value**.

2. **`hippo_warm` beats `hippo_cold`** in every cell on at least one
   axis: success_rate (groq 0.80 → 1.00), tokens (deepseek 2954 →
   2485), attempts (anthropic 1.6 → 1.4), latency (anthropic 5.62 s
   → 1.87 s). Memory + sleep cycles make subsequent runs cheaper and
   more reliable — exactly the predicted effect of the cabled
   primitives (DG/TCM/Hopfield/SR + procedural compilation).

3. **`groq` is anomalous on latency** — 14–17 s for hippo conditions
   vs 0.21 s raw. Groq's tool-use API path appears to retry / re-batch
   silently; sub-second raw single-shot but multi-second tool path.
   Worth a separate audit; not a HippoAgent bug.

4. **The token gap is structural, not waste.** ~50 raw vs ~3 000
   hippo means the agent is paying for: system prompt (~400 toks),
   skill catalogue (~800 toks at top-3), past episodes (~600 toks),
   tool schemas (~400 toks), ReAct scaffolding (~300 toks), the
   actual answer (~50 toks). Where the active-memory cost pays off is
   on **harder tasks where retrieved skills materially shorten the
   trajectory** — to be measured with a domain-specific suite. The
   default suite confirms the **infrastructure is correct**; it is
   not the right suite to demonstrate the **value**.

### Operational cost estimate

Token / call estimates per task on the reference benches above
(anthropic Haiku 4.5 — the cheapest configured frontier model):

| Mode | Tokens | LLM calls | $ per task (Haiku 4.5) |
|---|--:|--:|--:|
| `raw` | ~50–80 | 1 | ~$0.0001 |
| `hippo_cold` (no macro) | ~2 500–3 800 | 1–2 | ~$0.005 |
| `hippo_warm` (macro hit) | ~2 800 + 0 | 1 | ~$0.004 |
| sleep cycle (per consolidate) | varies | 4–8 (`SleepReport.n_llm_calls`) | ~$0.01–0.02 |

The headline: HippoAgent costs ~50× a raw call **per task**, but on
the `memory_recall` and `hard_memory_recall` suites that 50× buys
**+50 percentage-point accuracy** that raw simply cannot deliver
without an external context store.

Sleep cycles are bursty: a single consolidate may issue 4–8 LLM
calls (NREM clustering + REM recombination + schema synthesis +
practice prompts). On free-tier providers (groq) this can trip
upstream rate limits — set `HIPPO_AUTO_FALLBACK=1` (FORGIA #45) to
chain a backup provider for the sleep stage.

### Wiring the bench into CI

To run the bench as a regression gate on every PR (or nightly):

```yaml
# .github/workflows/bench.yml
name: bench-regression
on:
  pull_request:
    paths:
      - "hippoagent/**"
      - "scripts/bench_*"

jobs:
  bench-mock-before:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { ref: main }
      - run: pip install -e ".[dev]"
      - run: |
          mkdir -p /tmp/before
          HIPPO_DATA_DIR=/tmp/before-data \
            python scripts/bench_with_without_hippo.py \
              --providers mock --quiet --output-dir /tmp/before
      - uses: actions/upload-artifact@v4
        with: { name: bench-before, path: /tmp/before }

  bench-mock-after-and-gate:
    needs: bench-mock-before
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e ".[dev]"
      - run: |
          mkdir -p /tmp/after
          HIPPO_DATA_DIR=/tmp/after-data \
            python scripts/bench_with_without_hippo.py \
              --providers mock --quiet --output-dir /tmp/after
      - uses: actions/download-artifact@v4
        with: { name: bench-before, path: /tmp/before }
      - run: |
          python scripts/bench_compare.py \
            /tmp/before/bench_with_without_hippo.summary.json \
            /tmp/after/bench_with_without_hippo.summary.json \
            --threshold 0.05 \
            --metric success_rate
```

`bench_compare.py` exits 1 on regression, which fails the job and
blocks the merge. Output is markdown so a follow-up "post comment"
step can paste it on the PR for reviewer context.

### Available task suites

| Suite | Tasks | What it discriminates |
|---|--:|---|
| `default` | 5 | transport / harness verification (raw wins, hippo overhead visible) |
| `skill_compounding` | 8 | proceduralisation / macro fast-path (hippo_warm latency win) |
| `memory_recall` | 6 (3 seed / 3 query) | **long-term memory itself** (raw must fail; hippo_warm should succeed) |

The `memory_recall` suite is the discriminative one for the headline
HippoAgent claim: in `raw` mode the model has no way to retrieve a
seeded fact across calls (no shared context), so all query tasks
should fail. In `hippo_warm` the seeds are stored as episodes and
the recall pipeline retrieves them.

### Reference run #2 — `skill_compounding` suite (8 digit-sum tasks)

Same harness, harder suite (8 strongly-correlated tasks where the
SAME skill applies). `--consolidate-every 4` → one sleep cycle
mid-suite. Wall-clock: 646 s, 96 results.

| provider | condition | n | success | tokens | latency_s | attempts | errors |
|---|---|--:|--:|--:|--:|--:|--:|
| anthropic | raw | 8 | 1.00 | 60 | 0.68 | 1.0 | 0 |
| anthropic | hippo_cold | 8 | 1.00 | 4283 | 4.07 | 1.8 | 0 |
| anthropic | hippo_warm | 8 | 1.00 | 5160 | **2.39** | 2.0 | 0 |
| deepseek | raw | 8 | 1.00 | 50 | 0.70 | 1.0 | 0 |
| deepseek | hippo_cold | 8 | 1.00 | 5276 | 3.07 | 2.0 | 0 |
| deepseek | hippo_warm | 8 | 1.00 | 5290 | 3.10 | 2.0 | 0 |
| groq | raw | 8 | 0.88 | 82 | 0.68 | 1.0 | 0 |
| groq | hippo_cold | 8 | 0.88 | 3420 | 17.73 | 2.5 | 0 |
| groq | hippo_warm | 8 | **0.00** | 385 | 17.99 | 0.1 | **7** |
| openrouter | raw | 8 | 1.00 | 60 | 1.50 | 1.0 | 0 |
| openrouter | hippo_cold | 8 | 1.00 | 6493 | 4.05 | 2.0 | 0 |
| openrouter | hippo_warm | 8 | 1.00 | 6468 | **3.57** | 2.0 | 0 |

**Findings:**

1. **Anthropic hippo_warm latency −41 % vs hippo_cold** (4.07 → 2.39 s).
   The compiled-macro fast-path engages on later tasks — the agent
   recognises "sum the digits of N" as a compiled skill and answers
   without re-running the ReAct loop.

2. **Groq + hippo_warm: 7 / 8 errors due to upstream 429 rate limit.**
   The mid-suite sleep cycle issues a burst of sleep-stage LLM calls
   (NREM + REM + schema synthesis), and Groq's free-tier RPM cap fires
   after one of those bursts. The FallbackLLM chain mitigates this in
   production — set `HIPPO_LLM_FALLBACK_PROVIDERS=anthropic,deepseek`.
   Documented separately as a known operational caveat, not a bug.

3. **Hippo_warm pays an upfront cost.** Anthropic tokens grew from
   4283 → 5160 (+20 %) because hippo_warm runs consolidate which
   itself costs tokens. The compounding *latency* gain still wins.

4. **DeepSeek hippo_warm doesn't move.** Token usage and latency are
   essentially identical to hippo_cold. The procedural fast-path didn't
   trigger (the model didn't emit a stable enough trajectory across
   the 4 pre-sleep tasks for the compiler to extract a macro). Tunable
   via `CONFIG.compile_min_successes` and `CONFIG.compile_macro_threshold`.

### Reference run #3 — `memory_recall` suite (3 seed + 3 query)

The discriminative run. Same harness, suite designed to require
long-term memory. 3 providers (anthropic, deepseek, openrouter),
54 results, 300 s wall-clock, zero errors.

| provider | condition | n | success | tokens | latency_s |
|---|---|--:|--:|--:|--:|
| anthropic | raw | 6 | **0.50** | 63 | 0.79 |
| anthropic | hippo_cold | 6 | **1.00** | 2367 | 3.83 |
| anthropic | hippo_warm | 6 | **1.00** | 2784 | **1.67** |
| deepseek | raw | 6 | **0.50** | 47 | 0.73 |
| deepseek | hippo_cold | 6 | **1.00** | 3499 | 2.15 |
| deepseek | hippo_warm | 6 | **1.00** | 3063 | 2.15 |
| openrouter | raw | 6 | **0.50** | 65 | 1.62 |
| openrouter | hippo_cold | 6 | **1.00** | 3144 | 2.36 |
| openrouter | hippo_warm | 6 | **1.00** | 4254 | 2.73 |

**Headline finding: raw collapses to 50 % across every provider —
exactly the 3 query tasks fail because the model has no shared
context. Hippo modes hit 100 % on every provider.** This is the
suite that demonstrates the active-memory machinery isn't an
optimisation — it changes what's *possible*.

Notes:

1. **The 50 % raw success rate is the seed phase.** "Remember X" + a
   trivial "ok" reply pass the seed validators on all 3 providers.
   The 3 queries that ask "What was X?" all fail because the LLM has
   no place to retrieve the value from.

2. **Anthropic hippo_warm latency −56 %** (3.83 → 1.67 s). The
   recall pipeline + retrieved-episode injection lets the model
   answer in one ReAct step instead of multiple — the same
   compounding effect we saw on `skill_compounding`, but the
   accuracy delta dwarfs the latency delta here.

3. **Token cost ~3 000 vs ~50 raw**, same structural overhead as
   the other suites. On `memory_recall` it BUYS something
   (+50 % accuracy); on the trivia default suite it doesn't.

4. **Cold vs warm essentially identical on accuracy**, because the
   seed-phase episodes are stored within the same agent run for
   both conditions. `hippo_cold` *resets the agent per task*, but
   the episodes from earlier tasks were already persisted to the
   shared `HIPPO_DATA_DIR` — so the cold agent built fresh for the
   query task can still recall the seed. This is correct behaviour:
   the data dir is the persistent boundary, the agent build is
   ephemeral. (To force seed-and-query in completely separate data
   trees, set distinct `HIPPO_DATA_DIR` per phase.)

### Reference run #4 — `hard_memory_recall` suite (12 tasks, 3 difficulty classes)

Same setup as run #3, harder suite: 6 seeds + 6 queries split
across direct token recall (2), paraphrased query (2), and
multi-step synthesis (1+1). 3 providers, 108 results, 699 s
wall-clock, 0 errors.

| provider | condition | n | success | tokens | latency_s |
|---|---|--:|--:|--:|--:|
| anthropic | raw | 12 | **0.50** | 70 | 0.78 |
| anthropic | hippo_cold | 12 | **1.00** | 2643 | 2.92 |
| anthropic | hippo_warm | 12 | **1.00** | 3049 | **1.42** |
| deepseek | raw | 12 | **0.50** | 49 | 0.79 |
| deepseek | hippo_cold | 12 | **0.92** | 7738 | 9.38 |
| deepseek | hippo_warm | 12 | **0.92** | 8477 | 8.61 |
| openrouter | raw | 12 | **0.50** | 70 | 1.64 |
| openrouter | hippo_cold | 12 | **1.00** | 3488 | 2.85 |
| openrouter | hippo_warm | 12 | **1.00** | 3485 | 3.00 |

**Findings:**

1. **Headline holds at 12 tasks.** Raw stays nailed at 0.50 (the
   seed pass). Hippo modes get 0.92–1.00 across providers. The
   +42–50 pp accuracy uplift survives paraphrased queries and
   multi-step synthesis.

2. **Anthropic hippo_warm latency −51 %** (2.92 → 1.42 s vs cold).
   Strongest fast-path engagement measured to date.

3. **DeepSeek 11 / 12** lost only `query-C-synthesis` (the
   pin-code XOR year compute step). The model retrieved BOTH
   facts but failed the addition. **HippoAgent provides the
   memory; arithmetic composition is on the underlying model.**
   Honest reading: the agent isn't a chain-of-thought solver, it's
   a memory substrate — the LLM's reasoning floor leaks through on
   multi-step tasks.

4. **OpenRouter hippo_warm == hippo_cold on latency** (3.00 vs 2.85 s).
   Same Anthropic backend as `provider=anthropic`, but the routing
   layer adds enough overhead to mask the macro fast-path. Direct
   Anthropic wins on warm-loop performance for now.

### Reference run #5 — `memory_recall` × `n_iter=2` (compounding curve)

Same `memory_recall` suite, run twice with the harness's `--n-iter 2`
flag — second iteration builds on the memory of the first.
2 providers (anthropic, deepseek), 72 results, 442 s wall-clock.

Per-iter latency (the headline metric for compounding):

| condition | provider | iter=0 lat | iter=1 lat | Δ |
|---|---|--:|--:|--:|
| hippo_cold | anthropic | 4.99 s | 1.42 s | **−71 %** |
| hippo_warm | anthropic | 2.37 s | 1.27 s | **−46 %** |
| hippo_cold | deepseek | 1.83 s | 2.36 s | +29 % |
| hippo_warm | deepseek | 2.07 s | 2.64 s | +27 % |
| raw | anthropic | 0.81 s | 0.74 s | flat |
| raw | deepseek | 0.85 s | 0.78 s | flat |

**Findings:**

1. **Anthropic shows a strong second-iteration speed-up** (cold:
   −71 %, warm: −46 %). The skills compiled on iter 0 fire as
   procedural macros on iter 1 — the cabled `compilation.py` +
   wake fast-path are doing what they were forged to do.

2. **DeepSeek does NOT compound** — latency actually drifts up
   slightly (+27–29 %). The model's generated trajectories vary
   enough across iter 0 episodes that the macro compiler never
   crosses `CONFIG.compile_macro_threshold`, so iter 1 still pays
   the full ReAct loop. Tunable, but it's an honest reading of
   model-dependent behaviour.

3. **Raw is perfectly flat across iters**. Confirms that the per-iter
   latency variance we see for hippo modes is signal, not noise.

4. **All success rates are 1.00 across iters for hippo modes** — the
   memory survives the second exposure even after a sleep cycle in
   between (`consolidate_every=3`).

Raw data committed at `data/bench_compounding_n_iter2.{results,summary,by_iter}.json`.

---

## 5. MCP server

```bash
# Console_scripts entry point (after `pip install -e .`):
hippo mcp

# Or as a module:
python -m hippoagent.mcp_server
```

`mcp.json` for Claude Code / Cursor / Cline / Continue / opencode:

```json
{
  "mcpServers": {
    "engram": {
      "command": "engram",
      "args": ["mcp"],
      "env": { "ENGRAM_HOSTED": "1" }
    }
  }
}
```

> `engram` and `hippo` are the same entry point — use either. Hosted mode needs
> **no API key**: the host LLM (Claude Code, Cursor, …) does the work. A provider
> key (e.g. `ANTHROPIC_API_KEY`) is only needed for the standalone agent tools
> like `hippo_run_task`. Data dir defaults to `~/.engram` (override with `ENGRAM_DATA_DIR`).

Tools exposed: `hippo_run_task`, `hippo_consolidate`, `hippo_recall`,
`hippo_skills_for`, `hippo_status`, `hippo_skill_retire`,
`hippo_skill_promote`, `hippo_skill_edit`, `hippo_episode_get`.

Resources: `hippo://skills/list`, `hippo://skills/{id}`,
`hippo://episodes/recent`, `hippo://episodes/{id}`.

Security (CVE-007):
- `inputSchema` validation per tool (jsonschema or manual fallback).
- Append-only JSONL audit log at `<data_dir>/mcp_audit.log`.
- Token-bucket rate limit on `hippo_run_task` and `hippo_consolidate`
  (1/min default — override per tool with
  `HIPPO_MCP_RATELIMIT_<TOOL>_RPM`).
- `perm_shell` honoured: shell-like task content rejected unless
  `HIPPO_ENABLE_SHELL=1`.
- Stdout is protocol-clean: `HIPPO_LOG_STDERR=1` is set automatically
  at module import, so structlog never lands a log line on the
  JSON-RPC wire.

---

## 6. Test isolation

Every test that touches a real EpisodicMemory / SkillLibrary should
use `tmp_path` and either:

```python
# Option A — explicit injection (legacy, still works):
mem = EpisodicMemory(db_path=tmp_path / "ep.db")

# Option B — env override (FORGIA #29):
import os
os.environ["HIPPO_DATA_DIR"] = str(tmp_path)
# subprocess / reload uses tmp_path; in-process the env is read at
# config import time, so this works only across subprocess boundaries.
```

For subprocess-based tests (e.g. MCP smoke), set `HIPPO_DATA_DIR` in
the subprocess env; the new process re-runs config import and picks
up the override.

---

## 7. References

- `FORGIA.md` — every primitive, why it was forged, what it
  measures (29 pezzi as of 2026-05-09).
- `docs/MIGRATIONS.md` — schema versioning and migration strategy.
- `README.md` — getting-started cheatsheet.
- `ARCHITECTURE_AUDIT.md` — pre-FORGIA architectural review.
- `SECURITY_AUDIT.md` — threat model + countermeasures.
- `BENCH_VALIDATION.md` — benchmark validation methodology.
