"""Cycle #55 — End-to-end live integration test across cycle #51..#54.

Verifies the full chain on the REAL corpus at ~/.engram:
  1. Create test episode E1 with key_facts F1+F2 + related_episode_id (#51)
  2. Verify F1, F2 have source_episodes=[E1.id]
  3. Verify causal_edges has (E1.id → related, 'narrative_link')
  4. Walker trace(E1.id, episode, both, 2) → finds E1, F1, F2, related (#52)
  5. Walker trace(F1.id, fact, backward) → reaches E1 (#52)
  6. Briefing get_briefing(task_text=F1.proposition) → F1 in proactive_hits (#53)
  7. Cleanup: forget F1+F2 + delete E1 + remove test causal_edges
  8. Stats: read briefing.jsonl tail and report (#54)

This test EXERCISES the code paths the running MCP server does NOT
yet have loaded (it was spawned before cycle #51 changes). It bypasses
MCP and goes straight through the engram package. If green, the
restart-MCP-server step at next session will activate live the same
code we just exercised.

NOT a unit test — requires real ~/.engram corpus. Don't run in CI.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

os.environ.setdefault("HIPPO_OFFLINE", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HIPPO_EAGER_PRELOAD", "0")
os.environ.setdefault("HIPPO_DATA_DIR", str(Path.home() / ".engram"))
os.environ.setdefault("ENGRAM_DATA_DIR", str(Path.home() / ".engram"))


def main() -> int:
    # SCAN-68 [46] 2026-06-02 (NONNA): questo e2e MUTA il corpus REALE ~/.engram
    # (insert+delete di episodi/fatti, cleanup non crash-safe). Per design gira
    # sul corpus vero, ma un run ACCIDENTALE o un crash a meta inquina la
    # produzione. Richiedi opt-in ESPLICITO: senza HIPPO_ALLOW_REAL_E2E=1 non
    # costruisce nulla e non tocca il DB (no-op sicuro, exit 0).
    if os.environ.get("HIPPO_ALLOW_REAL_E2E") != "1":
        print("SKIP: e2e su corpus REALE disabilitato. Esegui con "
              "HIPPO_ALLOW_REAL_E2E=1 per acconsentire alla mutazione del corpus.")
        return 0
    from verimem.briefing import get_briefing
    from verimem.lineage_trace import trace
    from verimem.mcp_server import _build_episode, _build_fact
    from verimem.memory import EpisodicMemory
    from verimem.semantic import SemanticMemory
    from verimem.skill import SkillLibrary

    report: dict = {"steps": [], "ok": True}

    # --- Setup live agent ----------------------------------------------
    memory = EpisodicMemory()
    semantic = SemanticMemory()
    skills = SkillLibrary()

    class _Ag:
        pass
    a = _Ag()
    a.memory = memory
    a.semantic = semantic
    a.skills = skills

    # Pick an existing episode for related_episode_ids
    all_eps = memory.all()
    if not all_eps:
        report["ok"] = False
        report["error"] = "no episodes in corpus, cannot run E2E"
        print(json.dumps(report, indent=2))
        return 1
    related_ep = all_eps[0]
    related_id = related_ep.id

    # --- Step 1: create test episode with key_facts + related ----------
    test_marker = f"E2E-CYCLE51-{int(time.time())}"
    test_task = f"E2E test {test_marker}"
    test_final_answer = (
        f"Narrative for E2E test {test_marker}. This episode is used "
        "to verify cycle #51 write-side + cycle #52 lineage walker + "
        "cycle #53 briefing semantic recall.\n\n"
        "It will be deleted at the end of the test."
    )
    e1 = _build_episode(
        task_id=f"e2e-{int(time.time())}",
        task_text=test_task,
        final_answer=test_final_answer,
        outcome="success",
        skills_used=[], tokens_used=0, num_steps=1,
    )
    memory.store(e1)

    fact1_prop = (
        f"E2E key fact 1 for {test_marker}: cycle 51 write-side "
        f"populates source_episodes."
    )
    fact2_prop = (
        f"E2E key fact 2 for {test_marker}: cycle 52 walker reads "
        f"the graph end-to-end."
    )
    f1 = _build_fact(
        proposition=fact1_prop, topic="test/e2e-cycle51-55",
        confidence=0.9, source_episodes=[e1.id],
    )
    f2 = _build_fact(
        proposition=fact2_prop, topic="test/e2e-cycle51-55",
        confidence=0.9, source_episodes=[e1.id],
    )
    semantic.store(f1)
    semantic.store(f2)
    memory.add_causal_edge(
        src_id=e1.id, dst_id=related_id,
        via_skill_id="narrative_link", weight=1.0,
    )
    report["steps"].append({
        "step": "1_write",
        "episode_id": e1.id,
        "fact_ids": [f1.id, f2.id],
        "related_id": related_id,
    })

    # --- Step 2: verify source_episodes populated ----------------------
    f1_check = semantic.get(f1.id)
    f2_check = semantic.get(f2.id)
    s2_ok = (
        f1_check is not None and e1.id in f1_check.source_episodes
        and f2_check is not None and e1.id in f2_check.source_episodes
    )
    report["steps"].append({
        "step": "2_facts_source_episodes",
        "f1_source_episodes": (
            f1_check.source_episodes if f1_check else None
        ),
        "f2_source_episodes": (
            f2_check.source_episodes if f2_check else None
        ),
        "ok": s2_ok,
    })
    if not s2_ok:
        report["ok"] = False

    # --- Step 3: verify causal_edge created ----------------------------
    with sqlite3.connect(str(memory.db_path)) as conn:
        edge_rows = conn.execute(
            "SELECT * FROM causal_edges WHERE src_episode_id = ? "
            "AND dst_episode_id = ?", (e1.id, related_id),
        ).fetchall()
    s3_ok = len(edge_rows) == 1
    report["steps"].append({
        "step": "3_causal_edge",
        "n_edges": len(edge_rows),
        "ok": s3_ok,
    })
    if not s3_ok:
        report["ok"] = False

    # --- Step 4: walker from E1 reaches F1, F2, related ----------------
    walk = trace(e1.id, "episode", a,
                 direction="both", max_depth=2, max_nodes=200)
    node_ids = {(n["id"], n["kind"]) for n in walk["nodes"]}
    expected = {
        (e1.id, "episode"),
        (f1.id, "fact"),
        (f2.id, "fact"),
        (related_id, "episode"),
    }
    missing = expected - node_ids
    s4_ok = walk["ok"] and not missing
    report["steps"].append({
        "step": "4_walker_from_episode",
        "n_nodes": len(walk["nodes"]),
        "n_edges": len(walk["edges"]),
        "depth_reached": walk["depth_reached"],
        "missing_expected": [list(t) for t in missing],
        "ok": s4_ok,
    })
    if not s4_ok:
        report["ok"] = False

    # --- Step 5: walker from F1 reaches E1 (backward) ------------------
    walk_f1 = trace(f1.id, "fact", a,
                    direction="backward", max_depth=2, max_nodes=50)
    f1_node_ids = {(n["id"], n["kind"]) for n in walk_f1["nodes"]}
    s5_ok = (e1.id, "episode") in f1_node_ids
    report["steps"].append({
        "step": "5_walker_from_fact_backward",
        "n_nodes": len(walk_f1["nodes"]),
        "reached_E1": s5_ok,
        "ok": s5_ok,
    })
    if not s5_ok:
        report["ok"] = False

    # --- Step 6: briefing semantic recall surfaces F1 ------------------
    # Query is intentionally close to F1 prop.
    query = "cycle 51 write-side populates source_episodes"
    brief = get_briefing(
        agent=a, n_facts=0, n_pinned=0, n_recent_episodes=0,
        n_top_skills=0,
        task_text=query, top_k_proactive=5,
        threshold_proactive=0.40,  # lower threshold for E2E robustness
    )
    proactive_ids = [h["id"] for h in brief.get("proactive_hits", [])]
    s6_ok = f1.id in proactive_ids
    report["steps"].append({
        "step": "6_briefing_proactive_recall",
        "query": query,
        "n_hits": len(proactive_ids),
        "hits": [
            {"id": h["id"], "sim": h["similarity"],
             "prop": h["proposition"][:60]}
            for h in brief.get("proactive_hits", [])
        ],
        "f1_surfaced": s6_ok,
        "ok": s6_ok,
    })
    if not s6_ok:
        report["ok"] = False

    # --- Step 7: cleanup ----------------------------------------------
    try:
        with sqlite3.connect(str(semantic.db_path)) as conn:
            conn.execute("DELETE FROM facts WHERE id = ?", (f1.id,))
            conn.execute("DELETE FROM facts WHERE id = ?", (f2.id,))
        with sqlite3.connect(str(memory.db_path)) as conn:
            conn.execute(
                "DELETE FROM causal_edges WHERE src_episode_id = ?",
                (e1.id,),
            )
            conn.execute(
                "DELETE FROM episodes WHERE id = ?", (e1.id,),
            )
        report["steps"].append({"step": "7_cleanup", "ok": True})
    except Exception as exc:
        report["steps"].append({
            "step": "7_cleanup", "ok": False,
            "error": str(exc),
        })
        report["ok"] = False

    # --- Step 8: briefing stats from real telemetry --------------------
    try:
        from verimem.briefing_stats import compute_stats
        jsonl_path = (
            Path(os.environ.get("ENGRAM_DATA_DIR",
                                str(Path.home() / ".engram")))
            / "audit" / "briefing.jsonl"
        )
        stats = compute_stats(jsonl_path)
        report["steps"].append({
            "step": "8_briefing_stats",
            "n_firings": stats.get("n_firings"),
            "hit_rate": stats.get("hit_rate"),
            "p50_ms": stats.get("p50_latency_ms"),
            "p95_ms": stats.get("p95_latency_ms"),
            "suggested_min_matched": stats.get("suggested_min_matched"),
            "suggested_rationale": stats.get("suggested_rationale"),
            "ok": True,
        })
    except Exception as exc:
        report["steps"].append({
            "step": "8_briefing_stats",
            "ok": False, "error": str(exc),
        })

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
