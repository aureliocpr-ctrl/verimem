# DESIGN — Memory ablation: an agent WITH vs WITHOUT verified memory

Owner question (Aurelio, 2026-07-20): *"quanto incide avere o non avere una
memoria? quanti token risparmi non analizzando tutto il progetto ogni volta?
quanto lavori meglio su un problema reale?"*

Status: **designed, not yet run** — scheduled AFTER the local-judge bench and
the certainty frontier work (mandated order). Nothing in here is a result.

## Why this benchmark matters

Every published memory-layer number today is retrieval-shaped (recall@k, QA
F1). Nobody in the category publishes the number buyers actually care about:
**how much faster / cheaper / better does an agent WORK when it has a
persistent verified memory** vs re-deriving context from scratch every
session. We have the perfect laboratory: a real codebase (`HippoAgent`, ~7.4k
tests), a real long-lived agent memory (6.4k+ verified facts, lineage chains,
episodes), and reproducible agent tooling (`claude -p`, subscription).

## Design (paired-task ablation, two arms)

For each task T in the task set, run the SAME agent twice:

* **ARM A — with memory**: the agent may call verimem recall/search/chain
  tools (read-only) before/while working.
* **ARM B — without memory**: same prompt, same tools EXCEPT memory; the
  agent must explore the repo/filesystem from scratch.

Both arms run headless (`claude -p`, same model, same effort), cold context,
N repetitions per task (variance), order randomized, in a worktree checkout
pinned to one commit so ground truth never moves.

### Task classes (12-20 tasks total)

1. **Factual recall about the project** ("which layer quarantines an
   unsourced performance claim, and in which file?") — ground truth =
   verified facts + code.
2. **Decision archaeology** ("why is the CE band threshold 40 and not
   99.64?") — ground truth in commit messages / memory lessons.
3. **Resume-a-task** ("continue task X: what was done, what's the next
   concrete step?") — ground truth = task ledger / lineage chain.
4. **Cross-session error avoidance** ("run the full suite the RIGHT way" —
   the memory knows the add