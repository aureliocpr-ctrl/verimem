---
description: Delete a fact from HippoAgent semantic memory by id
argument-hint: <fact_id>
---

Call `hippo_fact_forget` with `fact_id="$ARGUMENTS"`.

If the tool returns `{ok: true}`, confirm "Fact <id> forgotten."
If it returns an error, show the error and suggest checking the id with `/memory`.
