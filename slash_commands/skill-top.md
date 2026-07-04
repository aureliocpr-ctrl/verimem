---
description: Show the top-fitness HippoAgent skills
argument-hint: [top_k=10]
---

Call `hippo_skill_top` with `top_k=$ARGUMENTS` (default 10 if empty).

Render a table:

| Skill | Stage | Status | Trials | Successes | Fitness |
|---|---|---|---:|---:|---:|

One row per skill, highest fitness first.
