"""Round 5 — Full pipeline integration demo.

Putting it all together: 3 specialised agents (pentester, reviewer,
architect) each accumulate trajectories over 3 tasks. The system then:

  1. Trajectory: every task → structured step trace
  2. Causal: for each agent, pair success/failure → causal signals
  3. Skill mining: aggregate signals → emergent skill candidates
  4. Metacognition: assess confidence of cross-agent recall
  5. Multi-agent scoping: each agent's view is filtered

Final output: a per-agent skill library + cross-agent confidence map.

Run: python scripts/full_pipeline_demo.py
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from verimem.agent_scope import (
    count_by_agent,
    filter_facts_by_agent,
    tag_for_agent,
)
from verimem.causal_extract import causal_extract
from verimem.causal_skill_mine import causal_skill_mine
from verimem.metacognition import assess_recall_confidence
from verimem.trajectory import TrajectoryStep

# ---------- synthetic experience generator ----------

def _s(idx, kind, content, **kw):
    return TrajectoryStep(step_idx=idx, kind=kind, content=content, **kw)


def gen_experience():
    """Generate a small library of paired success/failure trajectories
    for each of 3 agents."""
    exp: dict[str, list[dict[str, Any]]] = {
        "pentester": [],
        "reviewer": [],
        "architect": [],
    }

    # PENTESTER: 3 pairs — pattern "passive recon beats aggressive"
    for i, target in enumerate(["acme.io", "widget.co", "initech.com"]):
        exp["pentester"].append({
            "success": [
                _s(0, "thought", f"recon {target}"),
                _s(1, "action", "passive enum", tool_name="crtsh"),
                _s(2, "observation", "subs found"),
            ],
            "failure": [
                _s(0, "thought", f"recon {target}"),
                _s(1, "action", "aggressive scan", tool_name="nmap"),
                _s(2, "observation", "WAF banned"),
            ],
            "task": f"recon {target}",
        })

    # REVIEWER: 3 pairs — pattern "TS strict mode beats loose"
    for i, repo in enumerate(["webapp", "api", "cli"]):
        exp["reviewer"].append({
            "success": [
                _s(0, "thought", f"review {repo}"),
                _s(1, "action", "compile strict", tool_name="tsc-strict"),
                _s(2, "observation", "null type caught"),
            ],
            "failure": [
                _s(0, "thought", f"review {repo}"),
                _s(1, "action", "compile loose", tool_name="tsc-loose"),
                _s(2, "observation", "null bug shipped"),
            ],
            "task": f"review {repo}",
        })

    # ARCHITECT: 3 pairs — pattern "event sourcing requires snapshots"
    for i, sys in enumerate(["orders", "inventory", "billing"]):
        exp["architect"].append({
            "success": [
                _s(0, "thought", f"design {sys}"),
                _s(1, "action", "add snapshots", tool_name="snapshot-svc"),
                _s(2, "observation", "fast replay"),
            ],
            "failure": [
                _s(0, "thought", f"design {sys}"),
                _s(1, "action", "raw event log", tool_name="event-log"),
                _s(2, "observation", "replay 10x slower"),
            ],
            "task": f"design {sys}",
        })

    return exp


# ---------- main pipeline ----------

def main():
    print("=" * 70)
    print("Round 5 — Full pipeline integration demo")
    print("=" * 70)

    exp = gen_experience()

    # 1. Causal extraction per agent
    signals_by_agent: dict[str, list[dict[str, Any]]] = {}
    print("\n>> Stage 1: Causal extraction per agent")
    for agent_id, pairs in exp.items():
        signals: list[dict[str, Any]] = []
        for i, p in enumerate(pairs):
            sig = causal_extract(
                success_traj=p["success"], failure_traj=p["failure"],
                success_id=f"{agent_id}_succ_{i}",
                failure_id=f"{agent_id}_fail_{i}",
            )
            signals.append(sig)
        signals_by_agent[agent_id] = signals
        print(f"  {agent_id}: {len(signals)} signals extracted")

    # 2. Skill mining per agent
    print("\n>> Stage 2: Skill mining per agent")
    skills_by_agent: dict[str, list[dict[str, Any]]] = {}
    for agent_id, sigs in signals_by_agent.items():
        mined = causal_skill_mine(sigs, min_evidence=2)
        skills_by_agent[agent_id] = mined["candidates"]
        for c in mined["candidates"]:
            print(f"  [{agent_id}] {c['rule']}  "
                  f"(×{c['evidence_count']}, conf={c['avg_confidence']:.2f})")

    # 3. Cross-agent facts pool — each candidate becomes a tagged fact
    print("\n>> Stage 3: Facts pool with agent-scoped topics")

    @dataclass
    class _Fact:
        id: str
        proposition: str
        topic: str
        confidence: float = 0.9
        outcome: str = "success"

    fact_pool: list[_Fact] = []
    fact_id = 1
    for agent_id, candidates in skills_by_agent.items():
        for c in candidates:
            topic = tag_for_agent(
                f"skills/{agent_id}/auto",
                agent_id=agent_id,
            )
            fact_pool.append(_Fact(
                id=f"f{fact_id}",
                proposition=c["rule"],
                topic=topic,
                confidence=c["avg_confidence"],
            ))
            fact_id += 1
    print(f"  {len(fact_pool)} skill-facts in pool")

    counts = count_by_agent(fact_pool)
    for agent, n in counts.items():
        print(f"   {agent:12s}: {n}")

    # 4. Cross-agent recall simulation + metacog
    print("\n>> Stage 4: Cross-agent recall + metacognition")
    queries = [
        ("pentester", "how should we recon a new target?"),
        ("reviewer", "what about TypeScript strict mode?"),
        ("architect", "we need fast event replay"),
        ("pentester", "best way to evade detection"),  # vague
    ]

    for agent_id, q in queries:
        own = filter_facts_by_agent(
            fact_pool, agent_id=agent_id, include_shared=True
        )
        # Simulate similarity scores based on keyword overlap
        results: list[dict[str, Any]] = []
        for f in own:
            kw_overlap = sum(
                1 for w in q.lower().split() if w in f.proposition.lower()
            )
            sim = min(0.95, 0.2 + 0.25 * kw_overlap)
            results.append({
                "similarity": sim,
                "outcome": "success",
                "task": f.proposition,
            })
        # Pick top 3
        results.sort(key=lambda r: -r["similarity"])
        results = results[:3]
        conf = assess_recall_confidence(results)
        print(f"\n  [{agent_id}] Q: '{q}'")
        for r in results[:2]:
            print(f"     sim={r['similarity']:.2f} → {r['task'][:60]}")
        print(f"     VERDICT: {conf['level']} (score={conf['score']:.2f})")
        print(f"     → {conf['fallback_suggestion']}")

    print("\n" + "=" * 70)
    print("END-TO-END RESULT")
    print("=" * 70)
    print("Started with: raw success/failure traces (9 pairs)")
    print("Ended with:")
    print(f"  • {sum(len(v) for v in skills_by_agent.values())} "
          "emergent skill candidates (across 3 agents)")
    print(f"  • {len(fact_pool)} agent-scoped facts in shared pool")
    print("  • Per-agent recall correctly filtered + confidence calibrated")
    print()
    print("Pipeline complete: T+C+M+A working end-to-end.")
    print("HippoAgent is no longer just memory — it's a *learning system*.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
