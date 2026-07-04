"""Round 4 demo — Multi-agent memory namespacing.

Simulate 3 specialised agents (pentester, reviewer, architect) all
writing into the same HippoAgent. Each agent's recall scopes to its
own memories + optionally to a shared pool.

Run: python scripts/agent_scope_demo.py
"""
from __future__ import annotations

from dataclasses import dataclass

from engram.agent_scope import (
    count_by_agent,
    filter_facts_by_agent,
    tag_for_agent,
)


@dataclass
class Fact:
    id: str
    proposition: str
    topic: str
    confidence: float = 0.9


def main():
    print("=" * 70)
    print("Round 4 demo — Multi-agent shared memory")
    print("=" * 70)

    # Each agent writes facts using tag_for_agent
    facts = [
        # pentester
        Fact("1", "WordPress CF7 5.7.3 → CVE-2023-6449",
             tag_for_agent("vuln/wp/cf7", agent_id="pentester")),
        Fact("2", "Cloudflare WAF blocks UNION-based SQLi",
             tag_for_agent("waf/cloudflare", agent_id="pentester")),
        Fact("3", "nmap -A triggers cloud WAFs",
             tag_for_agent("lessons/recon", agent_id="pentester")),
        # reviewer
        Fact("4", "TS 5.x strict mode catches null returns",
             tag_for_agent("typescript/strict", agent_id="reviewer")),
        Fact("5", "ESLint no-explicit-any prevents drift",
             tag_for_agent("lint", agent_id="reviewer")),
        # architect
        Fact("6", "Hexagonal architecture splits domain from infra",
             tag_for_agent("patterns/hexagonal", agent_id="architect")),
        Fact("7", "Event sourcing requires snapshotting at scale",
             tag_for_agent("patterns/eventsourcing", agent_id="architect")),
        # shared (no agent prefix)
        Fact("8", "OWASP Top 10 categories never go out of style", "shared/owasp"),
        Fact("9", "RTT > 50ms requires caching layer", "shared/performance"),
    ]

    print(f"\n{len(facts)} total facts written across 3 agents + shared")

    # Counts by agent
    counts = count_by_agent(facts)
    print("\n>> Distribution by agent:")
    for agent, n in counts.items():
        print(f"   {agent:12s}: {n} facts")

    # Each agent recalls its own scope
    print("\n>> Per-agent scoped recall:")
    for agent_id in ["pentester", "reviewer", "architect"]:
        own = filter_facts_by_agent(facts, agent_id=agent_id)
        with_shared = filter_facts_by_agent(
            facts, agent_id=agent_id, include_shared=True
        )
        print(f"\n   {agent_id}:")
        print(f"     own only      ({len(own)}): "
              + ", ".join(f.id for f in own))
        print(f"     +shared       ({len(with_shared)}): "
              + ", ".join(f.id for f in with_shared))

    # Legacy mode — no agent_id → only un-prefixed
    print("\n>> Legacy mode (agent_id=None, no-prefix only):")
    legacy = filter_facts_by_agent(facts, agent_id=None)
    print(f"   {len(legacy)} facts (the 2 shared ones)")
    for f in legacy:
        print(f"     {f.id}: [{f.topic}] {f.proposition}")

    print("\n" + "=" * 70)
    print("KEY INSIGHT")
    print("=" * 70)
    print("Single HippoAgent instance now supports a TEAM of agents:")
    print("  - pentester writes its findings under agent:pentester/...")
    print("  - reviewer writes code lessons under agent:reviewer/...")
    print("  - architect writes design patterns under agent:architect/...")
    print("  - everyone reads shared/... for cross-cutting knowledge")
    print()
    print("Zero schema change. Convention-only. Backwards compatible.")
    print("Foundation for federated multi-agent learning.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
