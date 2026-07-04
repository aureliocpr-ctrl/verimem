"""Massive stress test for HippoAgent pure-local modules.

Generates a large synthetic corpus (5k episodes, 1k skills, 2k facts)
and exercises ~25 pure-data modules, recording latency per call.
Pure-local, zero LLM.

Run: python scripts/stress_massive.py
"""
from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

random.seed(42)


@dataclass
class SynEpisode:
    id: str
    task_text: str
    outcome: str
    skills_used: list[str] = field(default_factory=list)
    tokens_used: int = 0
    created_at: float = 0.0
    final_answer: str = ""
    pinned: bool = False


@dataclass
class SynFact:
    id: str
    proposition: str
    topic: str
    confidence: float
    source_episodes: list[str] = field(default_factory=list)
    created_at: float = 0.0


def gen_corpus(n_eps: int = 5000, n_skills: int = 1000, n_facts: int = 2000):
    from engram.skill import Skill

    now = time.time()

    skills: list[Skill] = []
    skill_ids: list[str] = []
    for i in range(n_skills):
        sid = f"sk_{i:04d}"
        skill_ids.append(sid)
        parents: list[str] = []
        if i > 0 and random.random() < 0.5:
            n_par = random.randint(1, min(2, i))
            parents = random.sample(skill_ids[:i], k=n_par)
        status = random.choices(
            ["candidate", "promoted", "retired"],
            weights=[0.7, 0.2, 0.1],
        )[0]
        stage = random.choices(
            ["dream", "raw", "compiled", "schema"],
            weights=[0.1, 0.5, 0.3, 0.1],
        )[0]
        trials = random.randint(0, 50)
        successes = random.randint(0, trials) if trials > 0 else 0
        skills.append(Skill(
            id=sid,
            name=f"skill {i}",
            body=f"do task variant {i}",
            trigger=f"trigger {i % 50}",
            status=status,
            stage=stage,
            trials=trials,
            successes=successes,
            parent_skills=parents,
            created_at=now - random.uniform(0, 86400 * 90),
            last_used_at=now - random.uniform(0, 86400 * 30),
        ))

    eps: list[SynEpisode] = []
    for i in range(n_eps):
        outcome = random.choices(["success", "failure"], weights=[0.6, 0.4])[0]
        used = random.sample(skill_ids, k=random.randint(0, 3))
        eps.append(SynEpisode(
            id=f"ep_{i:05d}",
            task_text=f"task variant {i % 200}",
            outcome=outcome,
            skills_used=used,
            tokens_used=random.randint(0, 5000),
            created_at=now - random.uniform(0, 86400 * 60),
            final_answer=f"answer {i}",
        ))

    topics = [f"topic_{i}" for i in range(40)]
    facts: list[SynFact] = []
    for i in range(n_facts):
        facts.append(SynFact(
            id=f"f_{i:04d}",
            proposition=f"fact statement {i}",
            topic=random.choice(topics),
            confidence=random.uniform(0.1, 1.0),
            source_episodes=random.sample(
                [e.id for e in eps], k=random.randint(0, 3)
            ),
            created_at=now - random.uniform(0, 86400 * 60),
        ))

    return skills, eps, facts


def bench(name: str, fn) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        result = fn()
        ok = True
        err = ""
    except Exception as e:
        result = None
        ok = False
        err = f"{type(e).__name__}: {e}"
    elapsed_ms = (time.perf_counter() - t0) * 1000
    out_size = 0
    try:
        out_size = len(json.dumps(result, default=str)) if ok else 0
    except Exception:
        out_size = -1
    return {
        "name": name, "ok": ok, "ms": round(elapsed_ms, 2),
        "out_bytes": out_size, "err": err,
    }


def main():
    print("=== HippoAgent Massive Stress Test ===")
    print("Generating corpus (5000 ep / 1000 sk / 2000 facts)...")
    t0 = time.perf_counter()
    skills, eps, facts = gen_corpus()
    print(f"  generated in {(time.perf_counter()-t0)*1000:.0f}ms\n")

    results: list[dict[str, Any]] = []

    # --- skills modules (pure lists) ---
    from engram.skill_lineage_full import skill_lineage_full
    from engram.skill_recent import skills_recent
    from engram.skill_usage_decay import usage_decay
    from engram.skills_aggregate_stats import aggregate_stats
    from engram.skills_orphan import find_orphan_skills
    from engram.skills_search_by_predicate import skills_with_predicate
    from engram.skills_top_failing import top_failing_skills
    from engram.skills_top_used import top_used_skills
    from engram.skills_topology import skills_topology
    from engram.skills_untested import find_untested_skills

    results.append(bench("skills_topology", lambda: skills_topology(skills)))
    results.append(bench("find_orphan_skills", lambda: find_orphan_skills(skills)))
    results.append(bench("find_untested_skills", lambda: find_untested_skills(skills)))
    results.append(bench(
        "top_failing_skills",
        lambda: top_failing_skills(skills=skills, episodes=eps),
    ))
    results.append(bench("top_used_skills", lambda: top_used_skills(episodes=eps)))
    results.append(bench("skills_recent", lambda: skills_recent(skills)))
    results.append(bench("aggregate_stats", lambda: aggregate_stats(skills)))
    target = next((s for s in skills if s.parent_skills), skills[0])
    results.append(bench(
        f"skill_lineage_full[{target.id}]",
        lambda: skill_lineage_full(skill_id=target.id, all_skills=skills),
    ))
    results.append(bench("usage_decay", lambda: usage_decay(skills)))
    # add some preconditions for the predicate search
    for s in skills[:50]:
        s.preconditions = [f"pre_{random.randint(0,20)}"]
        s.postconditions = [f"post_{random.randint(0,20)}"]
    results.append(bench(
        "skills_with_predicate",
        lambda: skills_with_predicate(skills, predicate="pre_5"),
    ))

    # --- episodes modules (pure lists) ---
    from engram.episode_batch_get import episode_batch_get
    from engram.episode_classify import classify_episodes
    from engram.episode_recent_failures import recent_failures
    from engram.episode_summary import summarize_episodes
    from engram.episodes_with_skill import episodes_with_skill
    from engram.outcome_predict import predict_outcome

    results.append(bench("recent_failures", lambda: recent_failures(eps)))
    results.append(bench("classify_episodes[200]", lambda: classify_episodes(eps[:200])))
    results.append(bench(
        "summarize_episodes[1000]",
        lambda: summarize_episodes(eps[:1000]),
    ))
    ids_to_get = [e.id for e in random.sample(eps, k=50)]

    class _FakeMem:
        def __init__(self, lst):
            self._d = {e.id: e for e in lst}
        def get(self, eid):
            return self._d.get(eid)

    fake_mem = _FakeMem(eps)
    results.append(bench(
        "episode_batch_get",
        lambda: episode_batch_get(memory=fake_mem, episode_ids=ids_to_get),
    ))
    target_sk = random.choice(skills).id
    results.append(bench(
        "episodes_with_skill",
        lambda: episodes_with_skill(skill_id=target_sk, episodes=eps),
    ))
    results.append(bench(
        "predict_outcome",
        lambda: predict_outcome(task="task variant 5", episodes=eps),
    ))

    # --- facts modules (pure lists) ---
    from engram.facts_aggregate_overall import aggregate_facts_overall
    from engram.facts_by_confidence import facts_by_confidence
    from engram.facts_recent import facts_recent
    from engram.facts_topic_merge import merge_facts_by_topic

    results.append(bench("aggregate_facts_overall", lambda: aggregate_facts_overall(facts)))
    results.append(bench(
        "facts_by_confidence[0.7+]",
        lambda: facts_by_confidence(facts, min_conf=0.7),
    ))
    results.append(bench("facts_recent", lambda: facts_recent(facts)))
    results.append(bench(
        "merge_facts_by_topic",
        lambda: merge_facts_by_topic(facts, topic="topic_5"),
    ))

    # --- summary ---
    print(f"\n=== Results: {len(results)} benchmarks ===")
    print(f"{'name':<45} {'ok':<4} {'ms':>10} {'bytes':>10}  err")
    print("-" * 90)
    n_ok = 0
    total_ms = 0.0
    for r in results:
        flag = "+" if r["ok"] else "X"
        if r["ok"]:
            n_ok += 1
        total_ms += r["ms"]
        print(f"{r['name']:<45} {flag:<4} {r['ms']:>10.2f} {r['out_bytes']:>10}  {r['err'][:30]}")
    print("-" * 90)
    print(f"PASS: {n_ok}/{len(results)}  TOTAL: {total_ms:.0f}ms")

    Path("stress_report.json").write_text(json.dumps({
        "n_episodes": len(eps),
        "n_skills": len(skills),
        "n_facts": len(facts),
        "results": results,
        "summary": {
            "pass": n_ok, "total": len(results),
            "total_ms": round(total_ms, 2),
        },
    }, indent=2, default=str))
    print("\nReport saved -> stress_report.json")
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
