# Corpus bonifica — manual health & re-clean (`scripts/engram_bonifica.py`)

Reproducible KEEP/QUARANTINE classifier for the live facts corpus.
**Manual tool by design** — it must NEVER become an auto-hook: bulk
status flips on the live corpus need a human looking at the dry-run
report first (auto-hooks did damage in the past; see the production
plan). Proven live 2026-06-01: 2452 kept / 7613 quarantined, fully
reversible.

## When to run it

- Recall feels polluted (machine exhaust, near-empty facts, duplicates
  surfacing in `hippo_facts_recall`).
- `clp doctor --full` / corpus-health metrics degrade.
- After a period of heavy automated writes (agentic loops, telemetry
  faucets) — check whether the gates held.

## The three modes

```bash
python scripts/engram_bonifica.py            # DRY-RUN: report only, read-only connection
python scripts/engram_bonifica.py --health   # one-line JSON health score (fast recheck)
python scripts/engram_bonifica.py --apply    # backup + quarantine + restore-map + re-measure
```

Always read the DRY-RUN report before `--apply`. The report includes a
**LEAK CHECK** section: curated-knowledge namespaces (`lessons`,
`decisions`, `preferences`, `master`, `handoff`, `skill`, `bench`) that
would be quarantined — the only acceptable reasons there are
`duplicate` and `near-empty`. Anything else = a rule regression; stop
and fix `classify()` (regression net: `tests/test_engram_bonifica_classify.py`).

## What `--apply` does, in order

1. `VACUUM INTO` full DB backup next to the live db
   (`semantic.db.bak-bonifica-<ts>`).
2. Writes a per-fact **restore-map** JSON
   (`~/Desktop/ProgettiAI/bonifica-restore-<ts>.json`: id, old_status,
   reason) — quarantine is a status flip, never a delete.
3. Flips `status='quarantined'` on the planned set, prints
   before/after active counts + health score.

## Rules in one paragraph

Near-empty propositions (<25 chars) and machine-exhaust namespaces
(`alloc/ replay/ tx/ lock/ nego/ metric/ test/ emerging_skill/ reflex/
sched/ proc/ watchdog/ heartbeat`) are quarantined; low-value history
(`archive`, `diary`, and `dialog/*` except curated `dialog/doc`) is
quarantined; dead/throwaway project subtopics go; curated namespaces
are kept; *unknown* namespaces are KEPT and flagged (prudence — never
hide what you don't recognise); exact-duplicate propositions keep the
best-status/newest copy only. Empty-topic facts: pre-compact auto-noise
goes, real knowledge stays.

## Reverting a bad run

Restore statuses from the restore-map (id → old_status), or in the
worst case swap the `VACUUM INTO` backup back in. Both artifacts are
created BEFORE any write — a crash mid-apply loses nothing.
