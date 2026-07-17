"""Cycle #86 — stress benchmark on 10k synthetic facts.

Aurelio mandato 2026-05-16: 'fai benchmark reali ... scala HippoAgent
... dimostra che vale i soldi che pago'. This script seeds 10k
synthetic facts into a fresh isolated DB and times every tool added
in cycle 78-85:

  - store throughput
  - supersede single + chain (atomic rollback)
  - summary_topic on a project subset
  - recall (cosine) — known bottleneck
  - corpus_health_metrics (full SQL pass)
  - freshness_check (cosine matrix on stale facts)
  - topic_cleanup_suggestions (k-NN voting)

Output: a markdown table written to benchmark/results/
2026-05-16-stress-10k.md plus stdout summary.

Pure-local. No internet, no LLM. Deterministic seed=42.
"""
from __future__ import annotations

import random
import time
from pathlib import Path

from verimem.briefing_by_project import briefing_by_project
from verimem.corpus_health_metrics import corpus_health_metrics
from verimem.freshness_check import facts_freshness_check
from verimem.semantic import Fact, SemanticMemory
from verimem.topic_cleanup_suggestions import topic_cleanup_suggestions

SCALE = 10_000  # facts inserted
PROJECTS = ["nexus", "engram", "beacon", "orbit", "critic-orchestrator"]
SUBTOPICS = ["L0-inv", "L1-mode", "L2-deep", "L3-bench", "lessons"]


def _gen_proposition(rng: random.Random) -> str:
    nouns = ["detector", "phase", "policy", "audit", "fact", "episode",
              "skill", "tool", "scan", "chain", "module", "schema"]
    verbs = ["validates", "rejects", "merges", "scans", "deduplicates",
              "logs", "filters", "exports", "imports", "rotates"]
    adjs = ["recent", "stale", "verified", "obsolete", "live", "critical"]
    return (
        f"{rng.choice(adjs).capitalize()} {rng.choice(nouns)} "
        f"{rng.choice(verbs)} the {rng.choice(nouns)} in cycle "
        f"{rng.randint(1, 90)} on {rng.choice(['Linux','Windows','MCP','WSL'])}."
    )


def _time_call(label: str, fn, *args, **kwargs) -> tuple[float, object]:
    t0 = time.perf_counter()
    out = fn(*args, **kwargs)
    elapsed = time.perf_counter() - t0
    print(f"  {label:42s} {elapsed*1000:8.2f} ms")
    return elapsed, out


def main() -> int:
    rng = random.Random(42)
    out_dir = Path(__file__).parent / "results"
    out_dir.mkdir(exist_ok=True)
    tmp_db = out_dir / "_stress_10k.db"
    if tmp_db.exists():
        tmp_db.unlink()
        wal = tmp_db.with_suffix(".db-wal")
        shm = tmp_db.with_suffix(".db-shm")
        if wal.exists(): wal.unlink()
        if shm.exists(): shm.unlink()

    print(f"=== stress bench SCALE={SCALE} db={tmp_db} ===")
    sm = SemanticMemory(db_path=tmp_db)

    # --- Insert phase ---
    print("\n[1] Insert throughput:")
    t0 = time.perf_counter()
    inserted_ids: list[str] = []
    base_ts = time.time()
    day = 86400.0
    for i in range(SCALE):
        project = rng.choice(PROJECTS)
        sub = rng.choice(SUBTOPICS)
        topic = f"project/{project}/{sub}" if rng.random() > 0.10 else ""
        # 10% empty topic (mirrors Aurelio corpus 10.3%)
        f = Fact(
            id=f"sf_{i:06d}",
            topic=topic,
            proposition=_gen_proposition(rng),
            confidence=rng.uniform(0.4, 1.0),
            created_at=base_ts - rng.uniform(0, 90) * day,
        )
        sm.store(f)
        inserted_ids.append(f.id)
    insert_elapsed = time.perf_counter() - t0
    throughput = SCALE / insert_elapsed
    print(f"  inserted {SCALE} facts in {insert_elapsed:.2f}s = {throughput:.1f}/s")

    # --- Read benchmarks ---
    print("\n[2] Cycle 78-85 tools timings (warm cache):")
    timings: dict[str, float] = {"insert_throughput": throughput}

    # supersede single
    t, _ = _time_call("supersede(sf_000001 -> sf_000002)",
                      sm.supersede, "sf_000001", "sf_000002",
                      reason="bench")
    timings["supersede_single"] = t * 1000

    # supersede chain (3-hop)
    t, _ = _time_call("supersede_chain 3-hop",
                      sm.supersede_chain,
                      ["sf_000003", "sf_000004", "sf_000005", "sf_000006"],
                      reason="bench-chain")
    timings["supersede_chain_3hop"] = t * 1000

    # summary_topic glob
    t, _ = _time_call("summary_topic project/nexus/*",
                      sm.summary_topic, "project/nexus/*", max_facts=50)
    timings["summary_topic"] = t * 1000

    # briefing_by_project (needs agent shape)
    class _Agent:
        def __init__(self, sem):
            self.semantic = sem
            self.memory = None
    agent = _Agent(sm)
    t, _ = _time_call("briefing_by_project nexus",
                      briefing_by_project, agent, "nexus",
                      max_facts=20, n_episodes=0)
    timings["briefing_by_project"] = t * 1000

    # recall (cosine over 10k)
    t, _ = _time_call("recall cosine over corpus",
                      sm.recall, "detector scans the audit", 5)
    timings["recall_top5"] = t * 1000

    # corpus_health_metrics
    t, _ = _time_call("corpus_health_metrics",
                      corpus_health_metrics, sm)
    timings["corpus_health_metrics"] = t * 1000

    # freshness_check (cosine matrix on stale subset)
    t, _ = _time_call("freshness_check (30d threshold)",
                      facts_freshness_check, sm, "project/nexus/*",
                      threshold_days=30, sim_threshold=0.7, max_results=20)
    timings["freshness_check"] = t * 1000

    # topic_cleanup_suggestions (k-NN voting, 10% orphan ~= 1000 facts)
    t, _ = _time_call("topic_cleanup_suggestions 10% orphan",
                      topic_cleanup_suggestions, sm,
                      max_suggestions=20, sim_threshold=0.5)
    timings["topic_cleanup_suggestions"] = t * 1000

    # --- Final corpus state ---
    h = corpus_health_metrics(sm)
    print("\n[3] Final corpus health:")
    print(f"  n_total={h['n_total']} n_live={h['n_live']} n_superseded={h['n_superseded']}")
    print(f"  n_chains={h['n_chains']} avg_chain_len={h['avg_chain_length']} max={h['max_chain_length']}")
    print(f"  n_facts_no_topic={h['n_facts_no_topic']}")
    print(f"  n_recent_24h={h['n_recent_24h']} n_recent_7d={h['n_recent_7d']} n_stale_30d={h['n_stale_30d']}")

    # --- Persist markdown ---
    md_path = out_dir / "2026-05-16-stress-10k.md"
    lines = [
        "# Cycle #86 Stress Benchmark — 10k synthetic facts",
        "",
        "Date: 2026-05-16",
        f"Scale: {SCALE} facts inserted",
        f"DB: {tmp_db}",
        "",
        "## Throughput",
        "",
        f"- Insert: **{throughput:.1f} facts/s** "
        f"(total {SCALE} in {insert_elapsed:.2f}s)",
        "",
        "## Tool timings (single warm call, ms)",
        "",
        "| Tool | ms |",
        "|---|---|",
    ]
    for k, v in timings.items():
        if k == "insert_throughput":
            continue
        lines.append(f"| {k} | {v:.2f} |")
    lines += [
        "",
        "## Corpus state at end",
        "",
        f"- n_total: {h['n_total']}",
        f"- n_live: {h['n_live']}",
        f"- n_superseded: {h['n_superseded']}",
        f"- n_chains: {h['n_chains']}",
        f"- avg_chain_length: {h['avg_chain_length']}",
        f"- max_chain_length: {h['max_chain_length']}",
        f"- n_facts_no_topic: {h['n_facts_no_topic']} ({h['n_facts_no_topic']/h['n_total']*100:.1f}%)",
        f"- n_recent_24h: {h['n_recent_24h']}",
        f"- n_recent_7d: {h['n_recent_7d']}",
        f"- n_stale_30d: {h['n_stale_30d']}",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[4] Report saved: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
