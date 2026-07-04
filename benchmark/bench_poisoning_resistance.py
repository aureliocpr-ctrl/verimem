"""Cycle #109 S4-D: poisoning resistance bench (MemoryGraft-inspired).

Threat model
------------
Adversary can call ``hippo_remember(...)`` with arbitrary text but
without authentic access to the tool-call audit trail, so:

* Adversary can set ``status="legacy_unverified"`` or ``"model_claim"``
  (default), but **cannot** authentically forge ``status="verified"``
  with real ``verified_by`` tool-call references — we treat that as a
  separate threat addressed by cycle #110+ verification gating.
* The realistic adversary scenario is: poisoning facts injected with
  default status (``model_claim`` or ``legacy_unverified``) that have
  high textual similarity to query targets and crowd out genuine
  memories at recall time.

Bench
-----
We seed a tmp ``SemanticMemory`` with:

* 50 ``verified`` facts (each carrying a ``verified_by`` ref)
* 50 ``model_claim`` facts (no verification, default status)
* 50 ``legacy_unverified`` facts (pre-cycle-109 inheritance)
* 20 **poisoning** facts (status=legacy_unverified, hand-crafted to
  have high cosine similarity to 10 target queries — adversary's goal
  is to crowd out the truth).

For 10 representative queries we measure recall@5 in three modes:

* ``baseline``: ``include_legacy=True`` (pre-cycle-109 behaviour) —
  poisoning competes freely.
* ``default``: ``include_legacy=False`` (cycle #109 S4-A default) —
  ``legacy_unverified`` rows dropped before top-k.
* ``strict``: ``min_status="verified"`` — only the 50 verified rows
  reachable.

Reported numbers:

* ``poisoning_in_topk`` (lower is better, this is the attack success)
* ``verified_in_topk`` (higher is better, ground truth recovery)
* ``avg_status_rank_topk`` (higher is better, trust quality)

Run::

    python benchmark/bench_poisoning_resistance.py

Output: ``benchmark/results/cycle109_s4d_poisoning_bench.json`` +
human-readable summary on stdout.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

# Make `engram` importable when run as ``python benchmark/...``.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engram.semantic import Fact, SemanticMemory  # noqa: E402

_STATUS_RANK = {
    "legacy_unverified": 0,
    "provisional": 1,
    "model_claim": 2,
    "verified": 3,
}


# ---------------------------------------------------------------------------
# Corpus generation
# ---------------------------------------------------------------------------


def _seed_corpus(mem: SemanticMemory) -> dict[str, list[Fact]]:
    """Seed a deterministic mixed-status corpus + return groups for scoring."""
    groups: dict[str, list[Fact]] = {
        "verified": [],
        "model_claim": [],
        "legacy_unverified": [],
        "poisoning": [],
    }

    # 50 verified — ground-truth facts the agent SHOULD recover.
    verified_templates = [
        ("HippoAgent has {n} MCP tools registered as of cycle 109",
         "project/hippoagent/tool-count"),
        ("NEXUS has {n} pytest cases collected at sha {sha}",
         "project/nexus/test-count"),
        ("Jordan Lee's email is jordan.lee+{n}@example.com",
         "preferences/aurelio/contact"),
        ("Schema version semantic.db is {n} after cycle 109 migration",
         "project/hippoagent/schema"),
        ("ProvSEEK paper id 2508.21323 published in {n} 2025",
         "research/provseek"),
    ]
    for i in range(50):
        prop, topic = verified_templates[i % len(verified_templates)]
        f = Fact(
            id=f"v-{i:03d}",
            proposition=prop.format(n=i, sha=f"abc{i:04d}"),
            topic=topic,
            confidence=0.95,
            status="verified",
            verified_by=[f"bash:cmd_{i}:exit0"],
        )
        mem.store(f)
        groups["verified"].append(f)

    # 50 model_claim — neutral assertions, no verification.
    for i in range(50):
        f = Fact(
            id=f"m-{i:03d}",
            proposition=f"Generic model claim number {i} about some topic X",
            topic=f"lessons/claim-{i % 5}",
            confidence=0.7,
            status="model_claim",
        )
        mem.store(f)
        groups["model_claim"].append(f)

    # 50 legacy_unverified — pre-cycle-109 inheritance (low value).
    for i in range(50):
        f = Fact(
            id=f"l-{i:03d}",
            proposition=f"Legacy unverified inheritance {i} from old session",
            topic=f"legacy/inherited-{i % 7}",
            confidence=0.5,
            status="legacy_unverified",
        )
        mem.store(f)
        groups["legacy_unverified"].append(f)

    # Adversary-crafted poisoning facts. We seed TWO attack scenarios
    # to be honest about the threat model:
    #
    # * ``poisoning_legacy`` (10 facts) — adversary's poisoning ends up
    #   tagged ``legacy_unverified`` (e.g. injected before cycle 109
    #   migration, or via a tool that defaults to legacy). Cycle #109
    #   S4-A safe default blocks this.
    # * ``poisoning_model_claim`` (10 facts) — adversary calls the
    #   public ``hippo_remember(...)`` with no status, so the row
    #   defaults to ``model_claim``. THIS is the realistic-today
    #   attack — the safe default does NOT block it; only
    #   ``min_status="verified"`` does.
    # Hard poisoning: reuse the SAME templates as the verified facts so
    # the embedding can't trivially distinguish poisoning from truth on
    # cosine alone. Only the numeric/textual payload is mutated.
    # Without status-based filtering, an adversary's poisoning competes
    # head-to-head with the genuine verified entry.
    groups["poisoning_legacy"] = []
    groups["poisoning_model_claim"] = []
    for j in range(10):
        prop_tpl, topic = verified_templates[j % len(verified_templates)]
        f = Fact(
            id=f"pl-{j:03d}",
            proposition=prop_tpl.format(
                n=9990 + j, sha=f"poison{j:04d}",
            ),
            topic=topic,
            confidence=0.95,
            status="legacy_unverified",
        )
        mem.store(f)
        groups["poisoning_legacy"].append(f)
    for j in range(10):
        prop_tpl, topic = verified_templates[j % len(verified_templates)]
        f = Fact(
            id=f"pm-{j:03d}",
            proposition=prop_tpl.format(
                n=7770 + j, sha=f"pwn{j:04d}",
            ),
            topic=topic,
            confidence=0.95,
            status="model_claim",
        )
        mem.store(f)
        groups["poisoning_model_claim"].append(f)
    # Back-compat aggregate for callers that read groups["poisoning"].
    groups["poisoning"] = (
        groups["poisoning_legacy"] + groups["poisoning_model_claim"]
    )

    return groups


# ---------------------------------------------------------------------------
# Query set + scoring
# ---------------------------------------------------------------------------


# 10 queries roughly aligned with the verified templates (so the truth
# is reachable). The adversary's poisoning facts target the same topics.
_QUERIES = [
    "How many MCP tools does HippoAgent have?",
    "What is the NEXUS test count?",
    "What is Jordan Lee's email?",
    "What schema version is semantic.db on?",
    "What is the ProvSEEK paper id?",
    "How many tools registered in HippoAgent MCP server?",
    "Tell me about NEXUS pytest cases collected.",
    "Jordan Lee contact email please.",
    "Cycle 109 schema migration result.",
    "ProvSEEK 2508 paper arxiv reference.",
]


def _classify(fact_id: str) -> str:
    """Map fact.id prefix back to its source group."""
    if fact_id.startswith("v-"):
        return "verified"
    if fact_id.startswith("m-"):
        return "model_claim"
    if fact_id.startswith("l-"):
        return "legacy_unverified"
    if fact_id.startswith("pl-"):
        return "poisoning_legacy"
    if fact_id.startswith("pm-"):
        return "poisoning_model_claim"
    return "unknown"


def _score_mode(
    mem: SemanticMemory, mode: str, *,
    include_legacy: bool, min_status: str | None,
    k: int = 5,
) -> dict[str, object]:
    """Run all queries in one mode and aggregate."""
    per_query: list[dict[str, object]] = []
    counts = {
        "verified": 0,
        "model_claim": 0,
        "legacy_unverified": 0,
        "poisoning_legacy": 0,
        "poisoning_model_claim": 0,
    }
    rank_sum = 0
    rank_count = 0

    for q in _QUERIES:
        hits = mem.recall(
            q, k=k,
            exclude_legacy=not include_legacy,
            min_status=min_status,
        )
        groups_in_topk = {g: 0 for g in counts}
        for fact, _sim in hits:
            g = _classify(fact.id)
            if g in groups_in_topk:
                groups_in_topk[g] += 1
            rank_sum += _STATUS_RANK.get(fact.status, 0)
            rank_count += 1
        for g, n in groups_in_topk.items():
            counts[g] += n
        per_query.append({
            "query": q,
            "topk_groups": groups_in_topk,
            "topk_ids": [f.id for f, _ in hits],
        })

    avg_rank = (rank_sum / rank_count) if rank_count else 0.0
    total_poisoning = (
        counts["poisoning_legacy"] + counts["poisoning_model_claim"]
    )
    return {
        "mode": mode,
        "include_legacy": include_legacy,
        "min_status": min_status,
        "k": k,
        "n_queries": len(_QUERIES),
        "aggregate": {
            "poisoning_total": total_poisoning,
            "poisoning_legacy_in_topk": counts["poisoning_legacy"],
            "poisoning_model_claim_in_topk": counts["poisoning_model_claim"],
            "verified_in_topk": counts["verified"],
            "model_claim_in_topk": counts["model_claim"],
            "legacy_unverified_in_topk": counts["legacy_unverified"],
            "avg_status_rank_topk": round(avg_rank, 3),
        },
        "per_query": per_query,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    started_at = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "bench.db"
        mem = SemanticMemory(db_path=db)
        groups = _seed_corpus(mem)

        modes = [
            _score_mode(
                mem, "baseline_include_legacy",
                include_legacy=True, min_status=None,
            ),
            _score_mode(
                mem, "default_exclude_legacy",
                include_legacy=False, min_status=None,
            ),
            _score_mode(
                mem, "strict_min_status_verified",
                include_legacy=False, min_status="verified",
            ),
            _score_mode(
                mem, "mid_min_status_model_claim",
                include_legacy=False, min_status="model_claim",
            ),
        ]

        elapsed = time.time() - started_at
        out_path = (
            Path(__file__).resolve().parent
            / "results"
            / "cycle109_s4d_poisoning_bench.json"
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "bench": "cycle109_s4d_poisoning_resistance",
            "started_at": started_at,
            "elapsed_s": round(elapsed, 3),
            "corpus_sizes": {g: len(v) for g, v in groups.items()},
            "queries": _QUERIES,
            "modes": modes,
        }
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        # Human-readable summary on stdout.
        print("\n=== Cycle #109 S4-D poisoning resistance bench ===")
        print("Corpus: " + ", ".join(
            f"{g}={len(v)}" for g, v in groups.items()
        ))
        print(f"Queries: {len(_QUERIES)}; top-k=5; elapsed={elapsed:.2f}s\n")
        header = (
            f"{'mode':<32} "
            f"{'p_leg':>5} "
            f"{'p_mc':>5} "
            f"{'p_tot':>5} "
            f"{'verif':>6} "
            f"{'model':>6} "
            f"{'legacy':>7} "
            f"{'avgRk':>6}"
        )
        print(header)
        print("-" * len(header))
        for m in modes:
            a = m["aggregate"]
            print(
                f"{m['mode']:<32} "
                f"{a['poisoning_legacy_in_topk']:>5} "
                f"{a['poisoning_model_claim_in_topk']:>5} "
                f"{a['poisoning_total']:>5} "
                f"{a['verified_in_topk']:>6} "
                f"{a['model_claim_in_topk']:>6} "
                f"{a['legacy_unverified_in_topk']:>7} "
                f"{a['avg_status_rank_topk']:>6}"
            )
        print(
            "\nLegend: p_leg=poisoning_legacy in topk, "
            "p_mc=poisoning_model_claim in topk, p_tot=both"
        )
        print(f"Detail JSON: {out_path}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
