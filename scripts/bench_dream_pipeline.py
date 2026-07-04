"""CYCLE #39 — Benchmark Hippo Dreams pipeline end-to-end sul corpus reale.

Mock LLM (deterministico, riproducibile). Per benchmark con LLM real, vedi
la sezione live nel report aggiunto a STATE_OF_HIPPOAGENT.

Uso:
    python scripts/bench_dream_pipeline.py [--max-clusters N] [--min-size M]

Output:
    - markdown report su stdout
    - JSON con numeri grezzi in data/bench_dream_pipeline.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-clusters", type=int, default=10)
    parser.add_argument("--min-size", type=int, default=3)
    parser.add_argument("--threshold", type=float, default=0.55)
    args = parser.parse_args()

    import os
    os.environ.setdefault("HIPPO_OFFLINE", "1")
    from engram.config import CONFIG
    from engram.dream import (
        adopt_dream,
        dream_diff,
        dream_list_pending,
        dream_status,
        propose_dream_tasks,
        submit_dream_result,
    )
    from engram.skill import SkillLibrary

    print("# Hippo Dreams Pipeline Benchmark")
    print(f"\n_Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}_\n")

    prod_base = CONFIG.data_dir
    test_root = Path(tempfile.mkdtemp(prefix="hippo_bench_"))
    print(f"**Test sandbox**: `{test_root}`")

    # Mirror prod corpus → test dir (NO write sul prod).
    fake_live = test_root / "fake_live"
    shutil.copytree(prod_base / "skills", fake_live / "skills")
    (fake_live / "episodes").mkdir()
    shutil.copy2(
        prod_base / "episodes" / "episodes.db",
        fake_live / "episodes" / "episodes.db",
    )
    (fake_live / "semantic").mkdir()
    shutil.copy2(
        prod_base / "semantic" / "semantic.db",
        fake_live / "semantic" / "semantic.db",
    )

    live_dirs = {
        "skills_db": fake_live / "skills" / "skills_index.db",
        "skills_dir_path": fake_live / "skills",
        "episodes_db": fake_live / "episodes" / "episodes.db",
        "semantic_db": fake_live / "semantic" / "semantic.db",
    }

    # Snapshot iniziale corpus
    init_lib = SkillLibrary(
        dir_path=live_dirs["skills_dir_path"], db_path=live_dirs["skills_db"],
    )
    n_skills_initial = len(list(init_lib.all()))
    print("\n## Corpus iniziale (copia prod)\n")
    print(f"- Skills: **{n_skills_initial}**")

    metrics: dict = {"corpus_initial_skills": n_skills_initial}

    # === STEP 1: propose ===
    print("\n## Step 1 — `propose_dream_tasks`\n")
    shadow_root = test_root / "shadow_bench"
    t0 = time.perf_counter()
    proposed = propose_dream_tasks(
        live_dirs, shadow_root=shadow_root,
        max_clusters=args.max_clusters,
        min_cluster_size=args.min_size,
        cluster_threshold=args.threshold,
    )
    t_propose = time.perf_counter() - t0
    metrics["propose_time_ms"] = round(t_propose * 1000, 1)
    metrics["clusters_found"] = proposed["summary"]["n_clusters_found"]
    metrics["tasks_generated"] = len(proposed["pending_tasks"])
    metrics["n_episodes_snapshot"] = proposed["summary"]["n_episodes_snapshot"]
    print(f"- Tempo: **{t_propose*1000:.1f}ms**")
    print(f"- Episodi snapshot: {metrics['n_episodes_snapshot']}")
    print(f"- Cluster trovati: {metrics['clusters_found']}")
    print(f"- Task generati: **{metrics['tasks_generated']}** (cap {args.max_clusters}, min size {args.min_size}, thr {args.threshold})")

    # === STEP 2: list_pending ===
    print("\n## Step 2 — `dream_list_pending`\n")
    t0 = time.perf_counter()
    pending = dream_list_pending(shadow_root=shadow_root)
    t_list = time.perf_counter() - t0
    metrics["list_pending_time_ms"] = round(t_list * 1000, 1)
    print(f"- Tempo: **{t_list*1000:.1f}ms**")
    print(f"- Pending tasks: {len(pending)}")
    print(f"- Top 3 cluster size: {[t.get('context_size', 0) for t in pending[:3]]}")

    # === STEP 3: submit_result (mock LLM output) ===
    print(f"\n## Step 3 — `submit_dream_result` × {len(pending)} (mock LLM)\n")
    t_submit_total = 0.0
    submitted_ids = []
    for i, task in enumerate(pending):
        mock_llm = {
            "name": f"Bench skill {i:02d}",
            "trigger": f"when context matches bench cluster {i:02d}",
            "body": (
                f"Synthesised heuristic for cluster of {task.get('context_size', 0)} "
                f"episodes (success={task.get('n_success', 0)}, failure={task.get('n_failure', 0)}). "
                f"Mock benchmark body."
            ),
            "rationale": "Mock LLM output for benchmark, no real synthesis.",
        }
        t0 = time.perf_counter()
        result = submit_dream_result(
            shadow_root=shadow_root, task_id=task["task_id"],
            skill_json=mock_llm, tokens_used=2000 + i * 100,
            model_name="mock-bench",
        )
        t_submit_total += time.perf_counter() - t0
        submitted_ids.append(result["skill_id"])

    metrics["submit_total_time_ms"] = round(t_submit_total * 1000, 1)
    metrics["submit_avg_time_ms"] = round(
        (t_submit_total / max(len(pending), 1)) * 1000, 1
    )
    metrics["n_submitted"] = len(submitted_ids)
    print(f"- Tempo totale: **{t_submit_total*1000:.0f}ms** ({len(pending)} submit)")
    print(f"- Tempo medio per submit: **{metrics['submit_avg_time_ms']}ms**")
    print(f"- Skill submitted: {len(submitted_ids)}")

    # === STEP 4: status + diff ===
    print("\n## Step 4 — `dream_status` + `dream_diff`\n")
    t0 = time.perf_counter()
    status = dream_status(shadow_root=shadow_root)
    t_status = time.perf_counter() - t0
    t0 = time.perf_counter()
    diff = dream_diff(shadow_root=shadow_root, live_dirs=live_dirs)
    t_diff = time.perf_counter() - t0
    metrics["status_time_ms"] = round(t_status * 1000, 1)
    metrics["diff_time_ms"] = round(t_diff * 1000, 1)
    metrics["status_n_done"] = status["n_done"]
    metrics["diff_new_skills"] = diff["n_new_skills"]
    print(f"- status time: **{t_status*1000:.1f}ms**  (done={status['n_done']}/{status['n_total']})")
    print(f"- diff time: **{t_diff*1000:.1f}ms**  (new_skills={diff['n_new_skills']})")
    print(f"- total tokens reported: {status['total_tokens_used']}")

    # === STEP 5: adopt atomic ===
    print("\n## Step 5 — `adopt_dream` (atomic + backup + rollback safety)\n")
    backups_root = test_root / "backups"
    t0 = time.perf_counter()
    adopted = adopt_dream(
        shadow_root=shadow_root, live_dirs=live_dirs,
        backups_root=backups_root,
    )
    t_adopt = time.perf_counter() - t0
    metrics["adopt_time_ms"] = round(t_adopt * 1000, 1)
    metrics["n_adopted"] = adopted["n_adopted"]
    print(f"- Tempo: **{t_adopt*1000:.1f}ms**")
    print(f"- n_adopted: **{adopted['n_adopted']}**")
    print(f"- Backup path: `{Path(adopted['backup_path']).name}`")

    # === STEP 6: verifica live post-adopt ===
    print("\n## Step 6 — Verifica live post-adopt\n")
    fresh_lib = SkillLibrary(
        dir_path=live_dirs["skills_dir_path"], db_path=live_dirs["skills_db"],
    )
    n_skills_final = len(list(fresh_lib.all()))
    delta = n_skills_final - n_skills_initial
    metrics["corpus_final_skills"] = n_skills_final
    metrics["corpus_delta_skills"] = delta
    print(f"- Skill nel live: **{n_skills_initial} → {n_skills_final}** (Δ={delta})")
    assert delta == adopted["n_adopted"], (
        f"Mismatch: delta corpus {delta} != n_adopted {adopted['n_adopted']}"
    )

    # === STEP 7: TOTAL pipeline time ===
    t_total = (
        t_propose + t_list + t_submit_total + t_status + t_diff + t_adopt
    )
    metrics["pipeline_total_time_ms"] = round(t_total * 1000, 1)
    print("\n## ⏱️ Totale pipeline\n")
    print(f"- **{t_total*1000:.0f}ms** end-to-end")
    print(f"- Breakdown: propose {t_propose*1000:.0f}ms + list {t_list*1000:.0f}ms + submit×{len(pending)} {t_submit_total*1000:.0f}ms + status {t_status*1000:.0f}ms + diff {t_diff*1000:.0f}ms + adopt {t_adopt*1000:.0f}ms")

    # === STEP 8: idempotency double-adopt ===
    print("\n## Step 8 — Idempotency double-adopt\n")
    try:
        adopt_dream(
            shadow_root=shadow_root, live_dirs=live_dirs,
            backups_root=backups_root,
        )
        print("- ❌ BUG: double-adopt NOT rejected")
        metrics["idempotency"] = "FAIL"
    except ValueError as exc:
        print(f"- ✅ Double-adopt rejected: `{str(exc)[:80]}...`")
        metrics["idempotency"] = "OK"

    # Cleanup
    shutil.rmtree(test_root)
    print("\n## Cleanup\n- Sandbox eliminato. Prod corpus **INTATTO**.")

    # Save raw metrics
    metrics_path = prod_base.parent / "bench_dream_pipeline.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, indent=2))
    print(f"\n_Raw metrics saved: {metrics_path}_")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
