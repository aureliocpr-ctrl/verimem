---
name: hippoagent-memory
description: ANY mention of "memoria/memory/ricordi/ricordo/ricorda/ricordare/saved/stored" by the user MUST go to HippoAgent (hippo_* tools), NEVER to local file-system memory files (CLAUDE.md / MEMORY.md / .claude/projects/.../memory/*). Auto-fire flow - call hippo_health first to confirm reachable, then route the user's intent to the right tool. "salva/save X" → hippo_remember. "qual è il mio X / what's my X / cosa ricordi di X" → hippo_facts_search (instant keyword) then fall back to hippo_facts_recall (semantic). "cosa vedi nella memoria / what's in memory / dammi tutto" → hippo_facts_list + hippo_episode_list + hippo_stats. "abbiamo già fatto X / have we done X" → hippo_search (keyword on episodes) then hippo_recall (semantic). "dimentica X" → hippo_forget / hippo_fact_forget. AVOID hippo_run_task and hippo_consolidate inside Claude Code — they make EXTRA API calls to the configured Anthropic key (separate billing). The other 37 tools are FREE - they only read/write local SQLite, no API. Disable globally with env HIPPO_DISABLED=1.
---

# HippoAgent Persistent Memory — auto-recall skill (v5 — 75 tools)

This skill makes Claude Code automatically use HippoAgent's hippocampal
memory system across sessions. HippoAgent is a **plug-in MCP server**
that exposes 75 tools covering 3 memory tiers (episodes, facts, skills)
PLUS 3 reasoning tools (forward planning, STRIPS, structural analogy)
PLUS 26 introspection/curation tools (skill_health, recommend_actions,
predicate_graph_check, curate_pipeline, etc).

## ⚠️ CRITICAL: "memoria" = HippoAgent, NOT local files

When the user says any of these:
- "memoria", "memory"
- "ricordi", "ricordo", "ricorda", "ricordare"
- "saved", "stored", "salvato"
- "cosa sai di...", "what do you know about..."
- "cosa hai in memoria", "what's in memory"

→ **You MUST query HippoAgent (`hippo_*` tools)**.
→ **Do NOT read** `~/.claude/projects/*/memory/*.md` or `CLAUDE.md`
   files unless the user *explicitly* says "leggi il file CLAUDE.md"
   or "open the local memory file". Those local files are Claude Code's
   own auto-memory layer — separate, less rich, and not what the user
   is asking about when they say "memoria".

## ⚠️ Cost note: HOSTED MODE inside Claude Code

When running inside Claude Code (the default — `~/.mcp.json` sets
`HIPPO_HOSTED=1`), HippoAgent **never calls an external LLM API**.
Every cost stays on Claude Code's subscription tokens.

The 2 tools that would make extra API calls (`hippo_run_task`,
`hippo_consolidate`) are **disabled in hosted mode** and return an
error pointing to their free equivalents:

| Disabled (hosted) | Use instead | Why |
|---|---|---|
| `hippo_run_task` | `hippo_prepare_task` + your own ReAct + `hippo_record_episode` | The host (you, Claude Code) executes the task with your subscription tokens; HippoAgent only assembles the prompt and stores the result. **Free.** |
| `hippo_consolidate` | `hippo_consolidate_light` | Runs deduplication + promotion/retirement gate on fitness/trials only. Skips the dreamer + critic LLM stages. **Free.** |

The other 39 tools are read/write on local SQLite — **zero API cost**.

To run the **full** sleep cycle (with dreamer + critic, requires LLM)
ask the user explicitly. Only then unset `HIPPO_HOSTED` for that one
call, or run `hippo consolidate` from the CLI outside Claude Code.

## Activation flow

**Always**, at the start of every conversation:

1. Call `hippo_health` (deeper preflight, single call) to verify the
   memory layer is reachable. If it returns `status: degraded`, tell
   the user the layer is partially offline (the rest of Claude Code
   still works).

2. For each user message, decide which tool(s) to call based on the
   **routing table** below. **Always do the read BEFORE answering** so
   the response is grounded in the user's persistent memory.

3. After learning a new fact from the user, **store it via
   `hippo_remember`** (free, no API call, persistent across sessions).
   Do NOT call `hippo_run_task` to "record" the conversation — that
   spawns a separate agent + costs API calls.

4. **Do not auto-call `hippo_consolidate`**. The user will request it
   explicitly when they want a sleep cycle (e.g. "consolida adesso").

## Routing table — natural-language intent → tool

### "Save / store / remember this fact"

User says: `"salva che X"`, `"ricordati che X"`, `"my email is X"`,
`"il mio account è X"`, `"the API endpoint is X"`.

→ Call **`hippo_remember`** with `{proposition, topic?, confidence?}`.
   Writes directly to semantic memory (`semantic.db`), persistent
   across sessions, **no decay**. Confirm: "Saved. Fact id: X".

### "Recall / what do you know about X"

User says: `"qual è il mio account?"`, `"what's the API endpoint?"`,
`"ricordi qualcosa su X?"`.

→ First **`hippo_facts_search(query=X)`** — keyword LIKE on facts,
  instant (no embedding cold start). If 0 hits, fall back to
  **`hippo_facts_recall(query=X)`** — semantic cosine.

### "Have we done this task before?"

User says: `"abbiamo già fatto X?"`, `"have we built X before?"`,
new feature request that might overlap with prior work.

→ First **`hippo_search(query=X)`** — keyword LIKE on episode
  task_text, instant. If 0 hits, fall back to
  **`hippo_recall(query=X)`** — semantic cosine on episode embeddings.

### "Show / get the details of episode Y"

User says: `"dammi i dettagli dell'episodio Y"`, `"show me episode Y"`.

→ Call **`hippo_episode_get(episode_id=Y)`** — full ReAct trajectory.

### "Forget / delete / cancella X" (privacy / GDPR)

User says: `"dimentica che X"`, `"delete this"`, GDPR request.

→ For an episode: **`hippo_forget(episode_id=Y)`**.
→ For a fact:    **`hippo_fact_forget(fact_id=Z)`**.
→ For a skill:   **`hippo_skill_retire(skill_id=W)`**.

### "Pin / protect this episode forever"

User says: `"non dimenticare mai X"`, `"questo è importante"`.

→ Call **`hippo_episode_pin(episode_id=Y)`** so the episode is excluded
  from decay-pruning regardless of Ebbinghaus retention.
→ To release: `hippo_episode_unpin(episode_id=Y)`.

### "What skills do you have for X / cosa sai fare X"

→ First **`hippo_skills_search(query=X)`** — keyword on skill
  name+trigger+body. If 0 hits, **`hippo_skills_for(task=X, k=3)`**
  — semantic preview of which skills HippoAgent would inject.
→ For a 1-line summary: **`hippo_skill_describe(skill_id=W)`**.

### "Cosa vedi nella memoria? / What's in memory?"

User says: `"cosa vedi nella memoria"`, `"what do you have"`, `"dammi
tutto quello che sai"`, `"show me everything you remember"`.

→ Run **all three** in parallel and combine:
   - **`hippo_stats`** for counts (episodes / skills / facts / token usage).
   - **`hippo_facts_list(limit=20)`** for the latest declarative facts.
   - **`hippo_episode_list(limit=10)`** for the latest episodes.

Present the combined result. **Do NOT** read `CLAUDE.md` or
`~/.claude/projects/*/memory/MEMORY.md` — those are Claude Code's own
local memory, not HippoAgent's. The user almost certainly means
HippoAgent.

### "Esegui questo task / Run this task with memory" (HOSTED mode)

Inside Claude Code, **never call `hippo_run_task`** — it's disabled
when `HIPPO_HOSTED=1` (the default in `~/.mcp.json`). Instead, use
the free 2-step flow:

1. **`hippo_prepare_task(task=<the user's request>, k_skills=3, k_episodes=3)`**
   → returns `{skills, recall, rendered_prompt, llm_called: false}`.
   This is the relevant context from memory — past episodes that look
   similar, consolidated skills that might apply, an assembled prompt.
2. **You (Claude Code) execute the task** using your normal flow,
   informed by the context returned in step 1. Your subscription
   tokens pay the cost.
3. **`hippo_record_episode(task_text=..., final_answer=..., outcome=...,
   skills_used=[...], tokens_used=N)`** to persist the result so future
   sessions can recall it.

Same for sleep cycles: `hippo_consolidate` is disabled in hosted mode;
use **`hippo_consolidate_light`** instead — it does dedup + promote +
retire without any LLM call. The full dreamer/critic cycle stays
optional and explicit.

### Maintenance / dashboards / introspection

| Question | Tool |
|---|---|
| "Memoria reachable?" | `hippo_status` / `hippo_health` |
| "Quanti episodi/skill/facts?" | `hippo_stats` |
| "Token usati ultimi giorni?" | `hippo_metrics_history` |
| "Lista episodi recenti" | `hippo_episode_list` |
| "Lista facts" | `hippo_facts_list` |
| "Top skill per fitness" | `hippo_skill_top` |
| "Da che skill nasce questa?" | `hippo_skill_lineage` |
| "Perché questo episodio è stato richiamato?" | `hippo_recall_explain` |
| "Diff tra 2 skill" | `hippo_skill_compare` |
| "Skill duplicate?" | `hippo_skill_similar` |
| "Quali episodi hanno usato skill X?" | `hippo_episodes_by_skill` |
| "Esporta tutte le skill" | `hippo_skill_export` |
| "Importa un bundle skill" | `hippo_skill_import` |
| "Ultime invocazioni MCP (audit)" | `hippo_audit_tail` |
| "Cambia provider LLM" | `hippo_provider_switch` |
| "Bundle che co-occorrono" | `hippo_skill_bundles` |
| "Skill compound (parent ≥ 2)" | `hippo_compound_skills` |
| "Skill antagoniste" | `hippo_skill_antagonists` |
| "Merge manuale skill A → B" | `hippo_skill_merge` |
| "Test prompt skill su input" | `hippo_skill_test` |

### Reasoning on novel/composite tasks (Pezzo A+B+C)

When the task is **new** or **composite** (multi-step, doesn't match
any single skill semantically), don't just call `hippo_recall` and
hope. Combine the 3 reasoning tools:

| Tool | Question it answers | Foundation |
|---|---|---|
| `hippo_plan_forward(start_skill, depth, beam_width, goal_skill?)` | "Statistically, after using skill X, what's the most likely 3-step trajectory?" | Pfeiffer & Foster 2013 — hippocampal forward sweeps. Beam search on the empirical transition matrix from recent episodes. |
| `hippo_plan_strips(initial_state, goal_state, status?, max_depth)` | "What chain of skills makes the goal predicates true given the initial predicates?" | Anderson ACT-R / Fikes & Nilsson STRIPS — symbolic chaining via skill `preconditions` / `postconditions`. BFS shortest plan. |
| `hippo_find_analogues(target_skill_id, min_structural, max_semantic, top_k)` | "Are there skills with similar PROCEDURAL STRUCTURE but in a DIFFERENT semantic domain that might transfer?" | Gentner 1983 — structure-mapping. Jaccard on token signatures, filtered by low semantic cosine. |

**Composition pattern.** For an unfamiliar task:
1. `hippo_recall(task)` — semantic retrieval (existing).
2. If recall is thin, `hippo_find_analogues(top_skill_id)` — surface
   structurally-similar skills the semantic search missed.
3. If you have explicit pre/post for the goal, `hippo_plan_strips` —
   chain skills by symbolic preconditions.
4. If you have a starting skill but no explicit goal predicates,
   `hippo_plan_forward(start_skill, depth=3)` — see the most likely
   3-step trajectory and pick the branch that fits.

All three are **PURELY LOCAL** — no LLM call, ms-scale, free in
HOSTED mode. They give Claude Code 3 different "lenses" on the
skill library so the host LLM can pick its move with more
information than just "top-1 semantic match".

## Memory layout

| Memoria | DB path | Decay? | Keyword | Semantic | Write | Delete |
|---|---|---|---|---|---|---|
| Episodes | `~/.hippoagent/data/episodes/episodes.db` | sì (Ebbinghaus, pin escluso) | `hippo_search` | `hippo_recall` | `hippo_run_task` | `hippo_forget` |
| Facts | `~/.hippoagent/data/semantic.db` | **no** | `hippo_facts_search` | `hippo_facts_recall` | `hippo_remember` | `hippo_fact_forget` |
| Skills | `~/.hippoagent/data/skills/*.json` | per fitness threshold | `hippo_skills_search` | `hippo_skills_for` | sleep auto / `hippo_skill_edit` | `hippo_skill_retire` |

The 3 stores are independent SQLite/JSON; durable, atomic, no external
dependencies. Restarting Claude Code, rebooting the machine, moving to
a new project — none of those reset memory.

## Why this matters

Without this skill, every Claude conversation starts from zero. With it:

- The agent **remembers** facts you told it 5 sessions ago (your email,
  codebase conventions, prior bug fixes).
- The agent **reuses skills** it learned in prior sessions (compiled
  macros bypass the LLM entirely on recurring task families).
- The agent **scales compositively** — recombining 2 or 3 atomic skills
  on a new compound task.

## Empirical performance (committed bench data, real LLM calls)

- **Compositional generalization**: raw LLM 25-42%, HippoAgent **100%**
  on Anthropic / DeepSeek / OpenRouter (4-provider sweep, Lv1-Lv5).
- **Held-out practical tasks** (URL parsing, date format, capitalize,
  reverse, word count): 5/5 TRAIN + **5/5 HELD-OUT** on Anthropic Opus 4.7.
- **Learning curve**: token cost from 4225 (cold) → **0** at iter 3+
  (compiled-macro fast-path, 70% hit rate after consolidate).

## Disabling

To disable temporarily without uninstalling, set env var
**`HIPPO_DISABLED=1`** before launching Claude Code. The MCP server
exits immediately on startup; the rest of Claude Code is unaffected.

## Configuration tips

```bash
# Persistent data dir (default: ~/.hippoagent/data)
export HIPPO_DATA_DIR=~/.hippoagent/data

# Force a specific LLM provider
export HIPPO_LLM_PROVIDER=anthropic   # or openai|openrouter|groq|deepseek|ollama|xai

# Enable advanced neuroscientific mechanisms (default off — safe)
export HIPPO_BUNDLE_DISCOVERY_ENABLED=1
export HIPPO_NEGATIVE_BUNDLE_ENABLED=1
export HIPPO_SYNAPTIC_TAGGING_ENABLED=1
export HIPPO_CROSSOVER_ENABLED=1

# Auto-fallback across providers if rate-limited
export HIPPO_AUTO_FALLBACK=1
```

## Privacy

All memory lives in local SQLite/JSON files under `HIPPO_DATA_DIR`. **No
data is sent to remote servers** other than the LLM provider's standard
API. The skill library is plain JSON; user can inspect and edit at any
time. GDPR-symmetric: every memory tier has a forget tool.
