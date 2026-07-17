# Engram MCP Server — 5-minute integration guide

This is the practical onboarding for plugging **Engram** (formerly
HippoAgent) into any MCP-aware client: Claude Code, Cursor, opencode,
Cline, Continue, Zed, anything that speaks the
[Model Context Protocol](https://modelcontextprotocol.io/).

For the architectural overview see [`PLATFORM.md`](./PLATFORM.md).
For the bigger picture (status, roadmap, what's prototype) see
[`../STATE.md`](../STATE.md).

> **TL;DR**: Engram gives your AI agent a **persistent memory layer**
> — episodes from previous sessions, semantic facts you've told it,
> and consolidated skills it has learned. **175 MCP tools** exposed
> over stdio JSON-RPC. Zero extra LLM cost when run subscription-first
> (the host's Pro/Max plan does the work).

---

## 1. Install

```bash
pip install -e .
# Or just the MCP server stack (no dashboard/TUI):
pip install -e ".[mcp-only]"
```

After install, `verimem` is the canonical command; `engram` and `hippo`
remain as compatibility aliases (same entry point). The MCP server
entry point is `verimem mcp`.

## 2. Set at least one provider key (optional in hosted mode)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# or any of: OPENAI_API_KEY, OPENROUTER_API_KEY, GROQ_API_KEY,
# DEEPSEEK_API_KEY, MISTRAL_API_KEY, GEMINI_API_KEY, XAI_API_KEY,
# MOONSHOT_API_KEY, ZHIPU_API_KEY, FIREWORKS_API_KEY, TOGETHER_API_KEY,
# CEREBRAS_API_KEY, YI_API_KEY, PERPLEXITY_API_KEY, DASHSCOPE_API_KEY
# (Ollama: just have ollama running on localhost:11434)
```

**Subscription-first mode** (recommended for Claude Code Pro/Max users):
set `VERIMEM_HOSTED=1`. The server then refuses to run any internal
LLM loop — every tool that would have made an LLM call returns a
structured payload the host can act on. Zero extra API spend.

Backward-compat: the legacy `ENGRAM_*` and `HIPPO_*` env names are still
accepted (auto-mirrored at import time). For new configs prefer the
canonical `VERIMEM_*` names.

## 3. Test the server stand-alone

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}' | python -m verimem.mcp_server
```

You should see a JSON-RPC reply with `serverInfo.name == "verimem"`.

## 4. Wire into your client

### Claude Code

`~/.claude/.mcp.json` (or project-local `.mcp.json`):

```json
{
  "mcpServers": {
    "verimem": {
      "command": "verimem",
      "args": ["mcp"],
      "env": {
        "VERIMEM_HOSTED": "1",
        "VERIMEM_DATA_DIR": "${HOME}/.verimem"
      }
    }
  }
}
```

(Existing installs with data in `~/.engram` need no change: with
`VERIMEM_DATA_DIR` unset, an existing `~/.engram` is found and used
automatically — nothing is migrated or moved.)

Restart Claude Code. The 175 `hippo_*` tools become callable
immediately. `hippo_recall`, `hippo_remember`, `hippo_record_episode`,
etc. all dispatch under the aliases `verimem_*` and `engram_*` as well
(backward-compat).

### Cursor

`.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global) —
same JSON shape as above.

### opencode

`opencode.toml`:

```toml
[mcp.verimem]
command = "verimem"
args = ["mcp"]
[mcp.verimem.env]
VERIMEM_HOSTED = "1"
VERIMEM_DATA_DIR = "${HOME}/.verimem"
```

### Continue / Cline / Zed

All speak the same `mcpServers` JSON config; copy the Claude Code block.

---

## 5. What Engram gives the host: 228 tools, 12 categories

The host LLM sees the full list via `list_tools()` at session start
(20.8k tokens of JSON schemas, ~10% of a 200k context window, ~2%
of a 1M window). Below is a categorized tour of the most-used tools;
for the full canonical list call `verimem health` or
`python -c "import asyncio; from verimem.mcp_server import list_tools; print('\n'.join(t.name for t in asyncio.run(list_tools())))"`.

### A. Recall — bring past episodes into context (3 tools)

| Tool | What it does |
|---|---|
| `hippo_recall` | semantic recall top-k episodes by query (cosine on embeddings) |
| `hippo_recall_chain` | recall + follow citation/skill chains for transitive context |
| `hippo_recall_explain` | recall + return *why* each episode matched (score breakdown) |

**When the host calls it**: at the start of every non-trivial task —
"did we solve something similar before?". Returns 5 episodes with
their final answers in ~2-5k tokens.

### B. Remember / Forget — write to semantic memory (3 tools)

| Tool | What it does |
|---|---|
| `hippo_remember` | store one declarative fact (proposition + topic + confidence) |
| `hippo_forget` | delete a stored fact by id |
| `hippo_fact_forget` | alias for `hippo_forget` (kept for naming consistency) |

**When the host calls it**: when the user states a preference,
configuration, decision, or constant ("my email is X", "we use Y for Z").
Zero LLM call, pure SQLite write.

### C. Episodes — the raw experience log (15 tools)

| Tool | What it does |
|---|---|
| `hippo_record_episode` | persist a task + final answer + outcome (success/failure) |
| `hippo_record_episodes_batch` | bulk-record N episodes in one call |
| `hippo_episode_get` / `hippo_episode_batch_get` | fetch episode(s) in full |
| `hippo_episode_list` | filter by topic/agent/outcome/date |
| `hippo_episode_pin` / `hippo_episode_unpin` | protect from decay |
| `hippo_episode_summary` | LLM-free summarization (extractive) |
| `hippo_episode_diff` | structural diff between two episodes |
| `hippo_episode_replay` | re-execute an episode trajectory step-by-step |
| `hippo_episode_classify` | route by topic/outcome heuristics |
| `hippo_episode_clusters` | DBSCAN clusters of similar tasks |
| `hippo_episode_recent_failures` | last N failed episodes, for retrospection |
| `hippo_episodes_by_skill` / `hippo_episodes_with_skill` | reverse lookup |
| `hippo_episodes_find_duplicates` / `hippo_episodes_dedup` | hygiene |

### D. Facts / Semantic memory (15 tools)

| Tool | What it does |
|---|---|
| `hippo_facts_search` | literal substring search over fact propositions |
| `hippo_facts_recall` | semantic (embedding cosine) recall |
| `hippo_facts_list` | list all, paginated |
| `hippo_facts_recent` | last N facts written |
| `hippo_facts_by_agent` / `hippo_facts_by_confidence` | filtered views |
| `hippo_facts_topics` / `hippo_facts_cluster_by_topic` | discover topics |
| `hippo_facts_disagreement` | flag facts with conflicting propositions |
| `hippo_facts_aggregate_overall` | corpus-level stats |
| `hippo_facts_export_all` | bulk export JSON |
| `hippo_facts_find_duplicates` / `hippo_facts_merge` / `hippo_facts_topic_merge` | hygiene |
| `hippo_fact_priority` | retrieval-order weight on a single fact |

### E. Skills — the consolidated procedural knowledge (50 tools)

Most populous category. Skills are persistent, fitness-tracked,
inspectable artifacts (`<data_dir>/skills/<id>.json` + index in SQLite).

**Discovery & lookup**:
- `hippo_skill_top` — top-N by fitness
- `hippo_skills_for` — preview which skills *would* be retrieved for a task
- `hippo_skills_search` — substring search
- `hippo_skills_search_by_predicate` — STRIPS-style pre/post search
- `hippo_skills_recent` — last N created
- `hippo_skills_top_used` / `hippo_skills_top_failing` — usage stats
- `hippo_skill_similar` — semantic neighbors of a given skill
- `hippo_skill_describe` / `hippo_skill_inspect` — full record

**Lifecycle**:
- `hippo_skill_promote` / `hippo_skill_retire` — manual gate
- `hippo_skill_promote_by_threshold` — automated by fitness band
- `hippo_skill_retire_invisible` — admin: drop unused
- `hippo_skill_archive` / `hippo_skill_recover` — soft-delete + undo
- `hippo_skill_edit` — rewrite body/trigger/rationale

**Composition / analysis**:
- `hippo_skill_lineage` / `hippo_skill_lineage_full` / `hippo_skill_lineage_metrics` — derive-from graph
- `hippo_skill_provenance` — which episodes spawned a skill
- `hippo_skill_cooccurrence_graph` — A and B applied together
- `hippo_skill_bundles` / `hippo_skills_recommend_actions` — combos
- `hippo_skill_compile_macro` — skill → AST → exec deterministic bypass (95% latency cut)
- `hippo_skills_topology` / `hippo_skills_dot` — visualize graph
- `hippo_skill_merge` / `hippo_skill_merge_pair` — fuse duplicates
- `hippo_skills_find_duplicates` / `hippo_skills_orphan` — hygiene

**Health**:
- `hippo_skill_health` — single skill diagnostic
- `hippo_skill_failure_audit` / `hippo_skill_exposure_audit` — investigate regressions
- `hippo_skill_bottlenecks` / `hippo_skill_antagonists` — root-cause
- `hippo_skill_usage_decay` — temporal weight
- `hippo_skill_test` — synthetic verification
- `hippo_skill_derive_predicates` / `hippo_skills_derive_predicates_batch` — auto-extract STRIPS

**Import/export**:
- `hippo_skill_export` / `hippo_skill_import` / `hippo_skills_export_all`
- `hippo_skill_clone` — deep copy with new id
- `hippo_skill_diff_render` — visualize two skill versions

### F. Hippo Dreams — subscription-first consolidation pipeline (7 tools, cycle #34-#40)

The headline feature of v0.2.0. Immutable shadow → review → adopt
with atomic rollback. Zero internal LLM call (host LLM does the work).

| Tool | What it does |
|---|---|
| `hippo_dream_create_shadow` | snapshot live SQLite via sqlite3 backup API → isolated shadow root |
| `hippo_dream_propose` | cluster episodes (no LLM), emit pending tasks with `system_prompt`+`user_prompt` for each — host LLM consumes these |
| `hippo_dream_submit_result` | persist a skill the host's LLM synthesized; lenient validation; reject on double-submit |
| `hippo_dream_status` | counts: total / done / pending / tokens used |
| `hippo_dream_list_pending` | tasks still needing host-LLM synthesis |
| `hippo_dream_diff` | new skills on shadow not yet in live |
| `hippo_dream_adopt` | atomic apply with backup + rollback on failure |

**Typical flow** (from real session):
```
hippo_dream_create_shadow → hippo_dream_propose →
[host LLM iterates: list_pending → submit_result per task] →
hippo_dream_diff → hippo_dream_adopt
```
End-to-end measured: 20.8s on a 318-skill / 170-episode corpus.

### G. Reasoning chains & planning (~12 tools)

| Tool | What it does |
|---|---|
| `hippo_reason` | apply a chain of skills to a task |
| `hippo_chain_validate` / `hippo_chain_facts` / `hippo_chain_render` | validate + render |
| `hippo_chain_complexity` | depth metric |
| `hippo_recall_chain` | recall transitively along a chain |
| `hippo_forward_chain` | forward inference from facts |
| `hippo_plan_forward` / `hippo_plan_strips` | STRIPS-style planning |
| `hippo_compose_macro` / `hippo_compose_plan` | combine multiple skills |
| `hippo_compound_skills` | discover composable pairs |
| `hippo_promote_chain` | promote a reasoning chain to skill |
| `hippo_render_chain` | visualize a chain |

### H. Lineage / causal mining (~8 tools)

| Tool | What it does |
|---|---|
| `hippo_causal_extract` | extract cause-effect from episode pair |
| `hippo_causal_skill_mine` | mine recurring causal rules |
| `hippo_skill_lineage_*` | derive-from / merged-from graph |
| `hippo_export_graph` / `hippo_export_dot` | graphviz dump |
| `hippo_find_analogues` | structural analogy across domains |
| `hippo_find_cross_domain_schemas` | cross-corpus pattern mining |

### I. Audit / metrics (~7 tools)

| Tool | What it does |
|---|---|
| `hippo_audit_tail` / `hippo_audit_summary` | append-only JSONL of every tool call |
| `hippo_metrics_export` / `hippo_metrics_history` / `hippo_metrics_one_liner` | dashboards |
| `hippo_stats` / `hippo_stats_velocity` | corpus growth rate |

### J. Health / status / introspection (~8 tools)

| Tool | What it does |
|---|---|
| `hippo_health` / `hippo_health_report` | server up + components OK |
| `hippo_status` | counts + active provider |
| `hippo_dashboard_overview` | aggregate view |
| `hippo_introspect_state` | dump engine internals |
| `hippo_session_recap` | human-readable summary |
| `hippo_corpus_size` / `hippo_corpus_health_score` / `hippo_corpus_diff` | corpus-level |

### K. Analytics / prediction (~12 tools)

| Tool | What it does |
|---|---|
| `hippo_outcome_patterns` / `hippo_outcome_predict` / `hippo_outcome_timeseries` | forecasting |
| `hippo_outcomes_by_skill` | per-skill success rate |
| `hippo_predict_warmup_skills` | which skills will need recall for upcoming task |
| `hippo_detect_anomalies` / `hippo_detect_skill_drift` | regression alarms |
| `hippo_diagnose_failure` | RCA on failed episode |
| `hippo_assess_confidence` / `hippo_assess_fact_freshness` | quality scoring |
| `hippo_rank_facts_trust` / `hippo_rank_skills_roi` | priority lists |
| `hippo_emerging_patterns` | trend detection |

### L. Misc (rollup, prune, cross-agent, provider, etc.)

Tools that don't fit cleanly elsewhere — namespace, time-windowed rollups,
multi-tenant cross-agent consensus, provider switching, briefings,
session management. List via `verimem health --tools`.

---

## 6. Resources (read-only context the host LLM can `read_resource()`)

| Resource URI | What it is |
|---|---|
| `hippo://skills/list` | JSON list of all consolidated skills |
| `hippo://skills/{id}` | one skill with body + lineage |
| `hippo://episodes/recent` | last N episodes |
| `hippo://episodes/{id}` | one episode with full trajectory |
| `hippo://facts/recent` | last N facts |
| `hippo://audit/tail` | recent tool calls (read-only audit) |

---

## 7. Typical session example (Claude Code, real workflow)

**You** (user, in Claude Code chat):
> "Help me refactor `auth.py` to use bcrypt."

**Claude Code** internally calls (your CLAUDE.md tells it to use
Engram automatically):
1. `hippo_recall("refactor auth bcrypt")` → finds 3 past episodes
   where you migrated from sha256→bcrypt last month. Pulls their
   final answers as context (~3k tokens).
2. Reads `auth.py`.
3. `hippo_skills_for("refactor authentication library swap")` → finds
   a consolidated skill from the previous migrations ("audit usage
   sites → introduce shim → flip default → remove old").
4. Applies the skill, edits the file.
5. After it lands tests: `hippo_record_episode(task_text="...",
   final_answer="...", outcome="success", skills_used=["auth_lib_swap_v3"])`
6. Optionally `hippo_remember(proposition="auth.py now uses bcrypt
   with cost=12", topic="project/X/auth")`.

Next month when you say "rotate the bcrypt cost factor", the recall
finds today's session and primes the answer immediately.

---

## 8. Operational knobs

| Env var (canonical) | Legacy aliases | Purpose | Default |
|---|---|---|---|
| `VERIMEM_DATA_DIR` | `ENGRAM_DATA_DIR` / `HIPPO_DATA_DIR` | where episodes/skills/etc. live | `~/.verimem` (existing `~/.engram` / `~/.hippoagent` auto-detected, never migrated) |
| `VERIMEM_HOSTED` | `ENGRAM_HOSTED` / `HIPPO_HOSTED` | host LLM mode — no internal LLM | unset |
| `VERIMEM_LLM_PROVIDER` | `ENGRAM_*` / `HIPPO_*` | force a specific provider | autodetect |
| `VERIMEM_MODEL` / `_EXECUTOR` / `_DREAMER` / `_CRITIC` | `ENGRAM_*` / `HIPPO_*` | per-stage model | provider default (Opus 4.7) |
| `VERIMEM_LOG_STDERR` | `ENGRAM_*` / `HIPPO_*` | route logs to stderr (auto-set by `verimem mcp`) | unset |
| `VERIMEM_ENABLE_SHELL` | `ENGRAM_*` / `HIPPO_*` | unblock shell-running tools | off |
| `VERIMEM_MCP_DISABLE_RATELIMIT` | `ENGRAM_*` / `HIPPO_*` | bypass token-bucket | off |
| `VERIMEM_MCP_RATELIMIT_<TOOL>_RPM` | `ENGRAM_*` / `HIPPO_*` | per-tool override | 1/min |
| `VERIMEM_AUTO_FALLBACK` | `ENGRAM_*` / `HIPPO_*` | chain backup providers on rate-limit | unset |

> All three prefixes are mirrored to each other at package import
> (`verimem._compat.init_env_aliases`) — `VERIMEM_X`, `ENGRAM_X` and
> `HIPPO_X` all work, explicit values are never overridden. **New configs
> should use `VERIMEM_*`** (canonical since the 0.6.0 total rename).

## 9. Security defaults (already on)

- **Schema validation** on every tool call (`inputSchema` enforced).
- **Token-bucket rate limit** on `hippo_run_task`, `hippo_consolidate`,
  `hippo_dream_*` heavy ops (1/min default).
- **`perm_shell` gate**: shell-like task content rejected unless
  `VERIMEM_ENABLE_SHELL=1`.
- **Append-only JSONL audit log** at `<data_dir>/mcp_audit.log`.
- **Stdout is JSON-RPC only**: structlog goes to stderr in MCP mode.
- **No built-in auth** on MCP server (stdio-only by design — isolate
  via OS process boundaries / sandboxing).

## 10. Troubleshooting

**Server hangs on initialize.** Verify your client speaks MCP protocol
`2024-11-05`. Send `initialized` notification after the initialize
handshake (it's in the spec).

**`hippo_run_task` returns the same answer ignoring memory.** Check
`hippo_status` — `n_episodes` should be > 0 after a few runs. If it
stays at 0, your `VERIMEM_DATA_DIR` may be ephemeral (per-shell tmp).
Pin it to a stable path.

**Stdout pollution.** If your MCP client logs `Failed to parse JSONRPC
message`, check that `VERIMEM_LOG_STDERR=1` is in the spawn env. The
`verimem mcp` entry point sets it automatically.

**Multi-tenant isolation.** Set `VERIMEM_DATA_DIR` per tenant. Every
data path (episodes, skills, semantic, runs, reports) re-roots
automatically.

**Tool count saturating context.** 228 tools = ~27k tokens of schemas
at session start. On 200k contexts that's ~13%. On 1M it's ~3%.
You can mute the dashboard tool subset by setting
`VERIMEM_DISABLE_DASHBOARD_TOOLS=1` (cuts ~15 tools, saves ~2k tokens)
— but the cost is generally worth paying for the recall capability
you get back.

**Old `hippo_*` / `engram_*` tool names still work in CLAUDE.md /
config?** Yes, indefinitely for now. The dispatcher normalizes
`verimem_X` and `engram_X` → `hippo_X` (the internal wire name) at
call time; `verimem_*` is the canonical public spelling since the
0.6.0 total rename.

---

_See also: [`PLATFORM.md`](./PLATFORM.md) (architecture deep-dive),
[`MEMORY_PROTOCOL.md`](./MEMORY_PROTOCOL.md) (auto-write CLAUDE.md
setup), [`../STATE.md`](../STATE.md) (current state + roadmap)._
