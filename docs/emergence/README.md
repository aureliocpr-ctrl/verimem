# Emergent skill discovery pipeline (cycle 213-244)

Quickstart for the LLM-free emergent skill discovery + adoption pipeline shipped in HippoAgent across the 2026-05-23 cycle 213-244 burst session.

## What it does

Detects communities of related facts in `semantic.db`, drafts candidate skills from them WITHOUT calling any LLM, persists everything to disk + DB, and exposes the whole pipeline through MCP tools + Auto-Dream auto-firings.

## Pipeline at a glance

```
detect (213)
  → normalize topic (214/215)
    → draft Markdown body (217)
      → persist disk (222)              ──→ ~/.engram/skill_drafts/<ts>/
      → register fact (229+237)         ──→ semantic.db topic=emerging_skill/*
      → wire in Auto-Dream (223/230)    ──→ every firing writes both
      → promote to candidate Skill (235) ──→ skills_index.db status=candidate
      → MCP exposure (218,227,232,236,239) ──→ 5 tools below
      → observability (238,239)          ──→ pipeline_status MCP + dashboard script
```

## Five MCP tools

| Tool | Purpose | Cycle |
|------|---------|-------|
| `hippo_emerging_skills_draft` | Run detect → draft, return in memory | 218 |
| `hippo_skill_drafts_list` | Read persisted draft batches from disk | 227 |
| `hippo_emerging_skills_register` | Force on-demand register as facts | 232 |
| `hippo_emerging_skill_promote` | Convert one fact → candidate Skill row | 236 |
| `hippo_emergence_pipeline_status` | Aggregate observability snapshot | 239 |

## Three helper scripts

- `python -m scripts.emergence_dashboard` — textual snapshot.
- `python -m scripts.emergence_threshold_sweep` — purity × cohesion grid.
- `python -m scripts.inspect_emerging_cluster <needle>` — deep-dive one cluster.
- `python -m scripts.pilot_snapshot` — H1 promotion-rate baseline + history.
- `python -m scripts.bench_emerging_pipeline` — latency probe on the live corpus.

## Four empirical singolarità found

- **#18** — SELF-APPLYING LOOP: Auto-Dream emergence discovery runs without any LLM token. Validated in cycle 230 (`new_items=2170` per firing on live corpus).
- **#19** — LINEAGE BACKWARD NAVIGATION: cycle 237 wires `lineage_to = first source fact_id`. `clp chain show <emerging_id>` walks back 23 hops to source cluster.
- **#20** — SHADOW ZONE DISCOVERIES: at purity ≥ 0.2 the matrix surfaces 4 candidates (vs 1 at default 0.4): `master-fact`, `antigravity-reverse`, `deep-clp`, `loop29-lineage`.
- **#21** — OBSERVER-SHIFTS-EMERGENCE: re-running the same threshold sweep 4 min after registering shadow candidates moved 3 of them BACK under the threshold. The session's own writes shift the Louvain partitioning (Heisenberg-like effect on emergence detection).

## Recommended defaults

- Detector: `min_community_size=4, min_topic_purity=0.4, min_cohesion=0.2`.
- (Empirically: cohesion is NOT the binding gate on the current corpus — purity dominates. See cycle 240 sweep.)
- Auto-Dream cooldown: 10 min (cycle 69 default).

## A4 honest caveats

- Registered facts have `status='model_claim'` (NOT verified). Cycle 184 anti-confab L1.8 gate skips them.
- Promoted Skills have `status='candidate', stage='manual'` (NOT promoted). Promotion to `status='promoted'` requires cycle 144 `promote_or_retire` trial loop.
- The H1 hypothesis (4-hook composition raises promotion rate from 4.3 % to >10 %) has a baseline scaffold (cycle 244 `pilot_snapshot.py`) but the multi-day pilot has NOT been executed yet.
- Singolarità #21 means empirical measurements are session-dependent. Controlled experiment design for observer drift is deferred.

## Source modules

| Module | Cycle |
|--------|-------|
| `engram/skill_emergence_detector.py` | 213 |
| `engram/topic_normalization.py` | 214/215 |
| `engram/skill_drafter.py` | 217/220 |
| `engram/skill_draft_persist.py` | 222 |
| `engram/auto_dream_worker.py` (4-hook + persist + register wiring) | 219/223/230/233 |
| `engram/dream_emergence_hook.py` | 219 |
| `engram/emerging_skill_register.py` | 229/237 |
| `engram/skill_promote_from_emerging.py` | 235 |
| `engram/parallel_drafter.py` (H8c falsified, value-as-boundary) | 228 |

## Cross-instance handoff

```
clp chain show 201d74c22422    # MASTER FACT FINAL cycle 215-244
clp chain show 6fac2b630c4a    # singolarità #21 observer-effect
python -m scripts.emergence_dashboard
python -m scripts.pilot_snapshot
```
