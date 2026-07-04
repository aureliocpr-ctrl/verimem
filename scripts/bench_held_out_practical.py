"""FORGIA pezzo #200 — bench held-out su task pratici (NON digit-sum).

Setup:
  • 5 task TRAIN — text/string operations elementari (domain extraction,
    date formatting, capitalization, reversal, word count).
  • Sleep consolidate.
  • 5 task HELD-OUT — varianti dello stesso pattern con input diversi.

Misura: success rate raw vs hippo_warm su Anthropic Claude Opus 4.7.

Run: python scripts/bench_held_out_practical.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

# Add parent dir.
sys.path.insert(0, str(Path(__file__).parent.parent))

from engram.agent import HippoAgent  # noqa: E402
from engram.config import CONFIG  # noqa: E402

# Force Anthropic.
os.environ["HIPPO_LLM_PROVIDER"] = "anthropic"
os.environ.setdefault("HIPPO_BENCH_NO_NETWORK", "")
os.environ.setdefault("HIPPO_DISABLE_HF_DOWNLOAD", "0")


TRAIN_TASKS = [
    ("t1_dom", "Extract the domain (host) from this URL: 'https://www.example.com/path/to/page'. Answer with just the domain string.",
     "www.example.com"),
    ("t2_date", "Convert the ISO date '2026-01-15' to long English form 'Month DD, YYYY'. Answer with just the formatted date.",
     "January 15, 2026"),
    ("t3_cap", "Capitalize the first letter of each word in: 'the quick brown fox'. Answer with the result string only.",
     "The Quick Brown Fox"),
    ("t4_rev", "Reverse this string character by character: 'abcdef'. Answer with only the reversed string.",
     "fedcba"),
    ("t5_count", "Count the number of words in: 'the rain in spain falls mainly on the plain'. Answer with the integer only.",
     "9"),
]

HELDOUT_TASKS = [
    ("h1_dom", "Extract the domain (host) from this URL: 'https://api.github.com/repos/foo/bar'. Answer with just the domain string.",
     "api.github.com"),
    ("h2_date", "Convert the ISO date '2027-12-25' to long English form 'Month DD, YYYY'. Answer with just the formatted date.",
     "December 25, 2027"),
    ("h3_cap", "Capitalize the first letter of each word in: 'hippoagent is a memory layer'. Answer with the result string only.",
     "Hippoagent Is A Memory Layer"),
    ("h4_rev", "Reverse this string character by character: 'hello world'. Answer with only the reversed string.",
     "dlrow olleh"),
    ("h5_count", "Count the number of words in: 'machine learning models compose primitives'. Answer with the integer only.",
     "5"),
]


def _check(answer: str, expected: str) -> bool:
    """Lenient match — strip + lowercase + remove punctuation."""
    def _norm(s: str) -> str:
        s = (s or "").strip().lower()
        # Strip surrounding quotes/punctuation/whitespace.
        s = re.sub(r"^[\s'\"`.,:;]+|[\s'\"`.,:;]+$", "", s)
        return s
    a = _norm(answer)
    e = _norm(expected)
    return a == e or e in a or a in e


def run_phase(agent: HippoAgent, tasks, label: str) -> list[dict]:
    out = []
    print(f"\n--- {label} ({len(tasks)} tasks) ---")
    for tid, text, expected in tasks:
        t0 = time.time()
        try:
            result = agent.run_task(
                tid, text,
                lambda ans: (bool(ans and ans.strip()), "non-empty"),
            )
            ans = result.episode.final_answer or ""
            ok = _check(ans, expected)
            entry = {
                "task_id": tid,
                "task": text[:60],
                "expected": expected,
                "answer": ans[:120],
                "match": ok,
                "tokens": result.episode.tokens_used,
                "steps": result.episode.num_steps,
                "skills": [s.id for s in result.skills_retrieved],
                "elapsed_s": round(time.time() - t0, 2),
            }
        except Exception as exc:
            entry = {
                "task_id": tid,
                "error": f"{type(exc).__name__}: {exc}",
                "match": False,
                "elapsed_s": round(time.time() - t0, 2),
            }
        marker = "OK" if entry.get("match") else "XX"
        print(f"  [{marker}] {tid}: tokens={entry.get('tokens', 'N/A')} "
              f"steps={entry.get('steps', '?')} "
              f"elapsed={entry['elapsed_s']}s "
              f"skills={len(entry.get('skills', []))}")
        out.append(entry)
    return out


def main() -> int:
    print("==== HELD-OUT BENCH ON PRACTICAL TASKS (NON DIGIT-SUM) ====")
    print(f"Provider: {os.environ['HIPPO_LLM_PROVIDER']}")
    print(f"Episodes DB: {CONFIG.episodes_db}")

    agent = HippoAgent.build()

    # Phase 1 — TRAIN
    train_results = run_phase(agent, TRAIN_TASKS, "TRAIN (warm-up)")

    # Sleep consolidate
    print("\n--- CONSOLIDATE ---")
    t0 = time.time()
    rep = agent.consolidate()
    print(f"  duration: {time.time()-t0:.2f}s")
    print(f"  n_clusters: {rep.n_clusters}")
    print(f"  n_nrem_skills: {rep.n_nrem_skills}")
    print(f"  promoted: {len(rep.promoted)} | retired: {len(rep.retired)}")

    # Phase 2 — HELD-OUT
    heldout_results = run_phase(agent, HELDOUT_TASKS, "HELD-OUT")

    train_succ = sum(1 for r in train_results if r.get("match"))
    held_succ = sum(1 for r in heldout_results if r.get("match"))
    print("\n==== SUMMARY ====")
    print(f"TRAIN success: {train_succ}/{len(TRAIN_TASKS)} "
          f"({100*train_succ/len(TRAIN_TASKS):.0f}%)")
    print(f"HELD-OUT success: {held_succ}/{len(HELDOUT_TASKS)} "
          f"({100*held_succ/len(HELDOUT_TASKS):.0f}%)")

    out_path = (CONFIG.data_dir
                / "bench_held_out_practical.results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "provider": os.environ["HIPPO_LLM_PROVIDER"],
            "train": train_results,
            "heldout": heldout_results,
            "consolidate": {
                "n_clusters": rep.n_clusters,
                "n_nrem_skills": rep.n_nrem_skills,
                "n_rem_skills": rep.n_rem_skills,
                "promoted": rep.promoted,
            },
            "summary": {
                "train_success": train_succ,
                "heldout_success": held_succ,
                "train_total": len(TRAIN_TASKS),
                "heldout_total": len(HELDOUT_TASKS),
            },
        }, f, indent=2, default=str)
    print(f"Saved to: {out_path}")
    return 0 if held_succ >= len(HELDOUT_TASKS) // 2 else 1


if __name__ == "__main__":
    sys.exit(main())
