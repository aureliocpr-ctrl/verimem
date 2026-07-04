# HippoAgent Memory Protocol

How to make HippoAgent **automatic** for Claude Code (or any LLM agent).

Most users want HippoAgent to behave like a real hippocampus: write when
something matters, read when context is needed — without typing commands.

This document shows the **two-line setup** that achieves that.

---

## TL;DR

Add this block to your `~/.claude/CLAUDE.md` (or project-level `CLAUDE.md`):

```markdown
## HippoAgent Memory Protocol (NON NEGOTIABLE)

### READ (recall context)
1. **Non-trivial task start** → call `hippo_recall` with task-related query.
   If similar episodes exist (similarity >0.5), cite them before starting.
2. **Factual user question** ("what is X?", "remember Y?") → call
   `hippo_facts_search` BEFORE answering from internal memory.
3. **Architectural decision** → call `hippo_recall` to check past decisions.

### WRITE (auto-persist)
4. **End of significant task** (≥3 steps, deliverable, bug fix, feature,
   decision) → call `hippo_record_episode` with `task_text`, `final_answer`,
   `outcome` (success/failure).
5. **New fact learned** (user preference, decision, configuration, important
   result) → call `hippo_remember` with `proposition`, `topic`, `confidence`.
6. **Recurring pattern identified** → consider `hippo_record_episode` as seed
   for a future skill (the consolidation cycle will promote it).

### DO NOT save
- Casual chats, greetings, short confirmations
- Output identical to existing memory
- PII when not necessary (emails, passwords)

### Topic conventions
Use hierarchical namespaces:
`project/<name>`, `preferences/<user>`, `decisions/architecture`,
`lessons/debugging`, `nexus/target/<ip>`, `math/<topic>`.
```

That's it. Open a new Claude Code session and HippoAgent will start
recording episodes and facts automatically.

---

## Verifying it works

After a few interactions, run from any session:

```
What have we worked on recently?
```

Claude should call `hippo_recall` and `hippo_stats` and produce a real
summary instead of saying "I don't have memory between sessions".

Or directly via MCP tools:

```
hippo_stats()        → counts of episodes, skills, facts
hippo_episode_list() → most recent episodes
hippo_facts_recent() → most recent facts
```

---

## When NOT to use the auto-protocol

For some workflows the auto-write rule is too noisy:

- **Pair-programming throwaway sessions** — quick prototyping you don't
  want indexed forever.
- **Confidential single-session work** — keep memory scoped per project
  using project-level `CLAUDE.md` instead of global.
- **Multi-user team chats** — explicit `/remember` is clearer ownership.

In those cases drop the protocol from global config and use explicit
slash commands (`/recall`, `/remember`) per turn.

---

## Slash commands (optional, for explicit control)

If you prefer manual control over auto-protocol, install the slash commands
from `slash_commands/` in this repo into `~/.claude/commands/`:

- `/recall <query>` — search episodes
- `/remember <fact>` — store one fact
- `/memory` — show full status (counts + recent)

See [`slash_commands/README.md`](../slash_commands/README.md) for details.

---

## How it fits with HippoAgent's consolidation cycle

The Memory Protocol governs **write rate**. HippoAgent's consolidation
loop (FORGIA #156 — "sleep cycle") then:

1. Clusters similar episodes → emerging **skill candidates**
2. Promotes high-fitness candidates → **compiled macros**
3. Retires stale / failed skills → keeps the library clean
4. Generates abstract **facts** from repeated outcomes

So the user types in plain English → episodes get recorded → after enough
data the system distills **deterministic procedures** that no longer need
the LLM. This is the Voyager / SkillSet pattern, adapted for MCP.

See `docs/PLATFORM.md` for the full architecture.
