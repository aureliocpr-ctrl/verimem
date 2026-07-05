# Verimem SDK — quickstart (5 verbs)

> Install: `pip install verimem` *(PyPI name not yet reserved — for now:
> `pip install -e .` from this repo)*. Local SQLite, no external API key.

```python
from engram import Memory

mem = Memory("my.db")                     # or Memory("my.db", llm=your_llm)

# 1) add — everything enters through the anti-confabulation gate.
mem.add("Client Rossi's budget is 500k", asserted_at=1741000000)  # event time
# add a whole conversation (atomic extraction + consolidation; needs llm=):
# mem.add([{"role": "user", "content": "..."}], conversation_id="chat-42")

# 2) search — with the switches no one else has:
mem.search("Rossi budget")                        # default view
mem.search("Rossi budget", deep=True)             # archaeology: dormant memories too
mem.search("Rossi budget", as_of=1735000000)      # time travel: what was true THEN
mem.search("Rossi budget", with_history=True)     # each hit carries its transitions

# 3) update — never destroys: stores the new fact and supersedes the old
r = mem.add("Client Rossi's budget is 550k")      # then: mem.update(old_id, ...)

# 4) history — the supersession chain of one fact (audit trail)
mem.history(r["id"])

# 5) explain — the evidence dossier ("how do you know?"):
mem.explain("Rossi budget")   # provenance, status, two clocks, replaced values,
                              # DECLARED conflicts, relevance — or an explicit
                              # abstention with its reason. Judge-grade.
```

**Why this instead of mem0/Zep** — measured on HaluMem (n=188, judge=Claude,
caveats in `docs/TRUST_MAINTENANCE.md`): never fabricates on unanswerable
questions (0.976–1.0 abstention), conflict questions 0.15 → 0.80 with
reconciliation + dated history, overall QA 0.739 vs MemOS's self-reported
0.672. The write path refuses to launder claims into truth; the read path can
answer *"what changed, when — and how do you know?"*.

MCP server (`hippo_*` tools) exposes the same surfaces for Claude/agents —
memory that integrates with today's AIs (MCP) and tomorrow's (plain SQLite).
