---
description: Store one fact in HippoAgent semantic memory
argument-hint: <proposition>
---

Call the `hippo_remember` MCP tool with:
- `proposition="$ARGUMENTS"`
- `topic` — infer from the proposition content using these conventions:
  - User preferences → `preferences/<username>`
  - Technical decisions → `decisions/<domain>`
  - Lessons learned → `lessons/<topic>`
  - Project info → `project/<name>`
  - Math/algorithms results → `math/<topic>`
  - Pentesting findings → `nexus/<sub>` (see docs/usecases/pentesting_nexus.md)
- `confidence` — default 0.9; bump to 0.99 if the user said "definitely" or "verified".

Confirm to the user with the returned fact `id` so they can `/forget` it later if needed.
