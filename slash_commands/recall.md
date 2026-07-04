---
description: Semantic recall over past HippoAgent episodes
argument-hint: <query>
---

Call the `hippo_recall` MCP tool with `query="$ARGUMENTS"` and `k=5`.

Then summarise the returned episodes for the user, listing:
- `task` (truncated to 80 chars)
- `outcome` (success/failure)
- `similarity` (rounded to 2 decimals)
- `answer_preview` (first line)

If no episode has similarity >0.3, say "No relevant prior episodes found".
