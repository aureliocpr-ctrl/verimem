---
description: Show HippoAgent memory status — stats, recent episodes, recent facts
---

Call these MCP tools in parallel:
- `hippo_stats` (counts)
- `hippo_episode_list` with `limit=5` (recent episodes)
- `hippo_facts_recent` with `limit=5` (recent facts)
- `hippo_skill_top` with `top_k=5` (highest fitness skills)

Then render a markdown dashboard for the user:

```
## HippoAgent Memory

**Counts**: <eps> episodes (<succ>✓ / <fail>✗), <skills> skills (<promoted> promoted), <facts> facts

**Recent episodes**:
- [<outcome>] <task_text> (<ago>)

**Recent facts**:
- [<topic>] <proposition>

**Top skills by fitness**:
- <name> (fitness=<x>, trials=<y>)
```

Keep it under 20 lines total.
