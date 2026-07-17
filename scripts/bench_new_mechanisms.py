"""A/B bench: do the FORGIA #158-#181 mechanisms actually move metrics?

Strategy: build a corpus with concrete failure/success patterns that
each mechanism is supposed to exploit, then run consolidate() twice
on identical inputs — once with all new flags OFF (baseline), once
with them ON. Compare report-level deltas.

This is *meccanical* impact, not LLM-quality impact. It answers:
  - Does enabling synaptic_tagging actually rescue episodes?
  - Does bundle_abstraction actually create compound skills?
  - Does crossover actually generate hybrids?
  - Does negative_bundle actually fire on failure pairs?
"""
from __future__ import annotations

import dataclasses
import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Force offline so no LLM calls happen.
os.environ["HIPPO_OFFLINE"] = "1"

# Make `hippoagent` importable when run from project root.
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

# ruff: noqa: E402 — env var must be set before module import.
from verimem import config as config_mod  # noqa: E402
from verimem.config import CONFIG  # noqa: E402
from verimem.episode import Episode, Trace  # noqa: E402
from verimem.memory import EpisodicMemory  # noqa: E402
from verimem.semantic import SemanticMemory  # noqa: E402
from verimem.skill import Skill, SkillLibrary  # noqa: E402
from verimem.sleep import SleepEngine  # noqa: E402


def _ep(eid, *, skills, outcome, ts) -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=f"task {eid}",
        outcome=outcome,  # type: ignore[arg-type]
        final_answer="x",
        traces=[Trace(step=1, thought="t", action="a",
                      action_input="", observation="o")],
        tokens_used=10, skills_used=list(skills),
        created_at=ts,
    )


def seed_corpus(eng: SleepEngine) -> None:
    """Plant a corpus designed to exercise every new mechanism."""
    now = time.time()

    # === Bundle abstraction (#163-#166) ===
    # A and B always co-occur on success → bundle (A,B) candidate.
    for i in range(6):
        eng.memory.store(_ep(f"ab{i}", skills=["A", "B"],
                              outcome="success", ts=now - 100 - i))

    # === Synaptic tagging (#174-#176) ===
    # C fails, then C succeeds within window → tag rescue on the failure.
    eng.memory.store(_ep("c_fail", skills=["C"], outcome="failure",
                          ts=now - 60))
    eng.memory.store(_ep("c_succ", skills=["C"], outcome="success",
                          ts=now - 30))

    # === Negative bundle / lateral inhibition (#169-#173) ===
    # X+Y always together → 4 failures, 0 successes → toxic pair.
    for i in range(4):
        eng.memory.store(_ep(f"xy{i}", skills=["X", "Y"],
                              outcome="failure", ts=now - 200 - i))

    # === Skills required by abstraction stage ===
    for sid, name in [("A", "alpha"), ("B", "beta"),
                      ("C", "gamma"), ("X", "xx"), ("Y", "yy")]:
        eng.skills.store(Skill(
            id=sid, name=name, trigger=f"trigger_{sid}",
            body=f"step1_{sid}\nstep2_{sid}\nstep3_{sid}",
            status="promoted", trials=10, successes=8,
        ))

    # Force salience on c_fail to a baseline lower than the boost target,
    # so the synaptic-tag boost is observable.
    eng.memory.update_salience("c_fail", 0.30)


def _build(tmp_path: Path) -> SleepEngine:
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    sem = SemanticMemory(db_path=tmp_path / "sem.db")
    return SleepEngine(memory=mem, skills=skills, semantic=sem, seed=42)


def _patch_cfg(**fields) -> object:
    """Returns a new frozen Config and re-binds modules that import CONFIG."""
    new = dataclasses.replace(CONFIG, **fields)
    config_mod.CONFIG = new
    from verimem import memory as memory_mod
    from verimem import sleep as sleep_mod
    sleep_mod.CONFIG = new
    memory_mod.CONFIG = new
    return new


def run_one(label: str, *, all_on: bool) -> dict:
    base = Path(tempfile.mkdtemp(prefix=f"hippo_bench_{label}_"))
    eng = _build(base)
    seed_corpus(eng)

    # Snapshot pre-cycle.
    pre_skills = list(eng.skills.all())
    pre_c_salience = eng.memory.get("c_fail").salience_score

    if all_on:
        _patch_cfg(
            bundle_discovery_enabled=True,
            bundle_discovery_min_count=3,
            bundle_discovery_min_overlap=0.5,
            negative_bundle_enabled=True,
            negative_bundle_min_count=3,
            negative_bundle_min_fail_ratio=0.7,
            synaptic_tagging_enabled=True,
            synaptic_tag_window_s=3600.0,
            synaptic_tag_salience_boost=0.25,
            crossover_enabled=True,
            crossover_n_pairs=2,
            crossover_top_k=4,
            sleep_min_episodes=2,  # otherwise tiny corpus skips cycle
        )
    else:
        _patch_cfg(sleep_min_episodes=2)

    t0 = time.time()
    report = eng.cycle()
    dur = time.time() - t0

    post_skills = list(eng.skills.all())
    post_c_salience_obj = eng.memory.get("c_fail")
    post_c_salience = (post_c_salience_obj.salience_score
                       if post_c_salience_obj else None)

    return {
        "label": label,
        "all_on": all_on,
        "duration_s": round(dur, 3),
        "n_skills_pre": len(pre_skills),
        "n_skills_post": len(post_skills),
        "n_skills_added": len(post_skills) - len(pre_skills),
        "compound_skills": sum(
            1 for s in post_skills if len(s.parent_skills) >= 2
        ),
        "crossover_skills": sum(
            1 for s in post_skills if "_x_" in s.name
        ),
        "report.n_bundles_proposed": report.n_bundles_proposed,
        "report.n_bundle_skills": report.n_bundle_skills,
        "report.n_antagonisms": report.n_antagonisms,
        "report.n_synaptic_tags": report.n_synaptic_tags,
        "report.n_crossovers": report.n_crossovers,
        "report.n_llm_calls": report.n_llm_calls,
        "c_fail.salience_pre": round(pre_c_salience, 3),
        "c_fail.salience_post": round(post_c_salience, 3)
        if post_c_salience is not None else None,
    }


def main() -> None:
    baseline = run_one("baseline_default_off", all_on=False)
    enabled = run_one("all_mechanisms_on", all_on=True)

    print("\n" + "=" * 72)
    print("FORGIA #158-#181 — MECHANICAL IMPACT BENCH")
    print("=" * 72)
    for k in baseline.keys():
        b = baseline[k]
        e = enabled[k]
        marker = " ← DELTA" if b != e else ""
        print(f"  {k:35s}  baseline={b!r:15s}  enabled={e!r:15s}{marker}")

    # Verdict.
    print("\n" + "-" * 72)
    print("VERDICT")
    print("-" * 72)
    deltas = []
    if enabled["report.n_bundle_skills"] > baseline["report.n_bundle_skills"]:
        deltas.append(
            f"  + {enabled['report.n_bundle_skills']} compound skills "
            f"synthesized from bundles"
        )
    if enabled["report.n_antagonisms"] > baseline["report.n_antagonisms"]:
        deltas.append(
            f"  + {enabled['report.n_antagonisms']} antagonist pairs detected"
        )
    if enabled["report.n_synaptic_tags"] > baseline["report.n_synaptic_tags"]:
        deltas.append(
            f"  + {enabled['report.n_synaptic_tags']} episodes salience-boosted "
            f"(c_fail: {baseline['c_fail.salience_post']} → "
            f"{enabled['c_fail.salience_post']})"
        )
    if enabled["report.n_crossovers"] > baseline["report.n_crossovers"]:
        deltas.append(
            f"  + {enabled['report.n_crossovers']} engram-crossover hybrids "
            f"generated"
        )
    if not deltas:
        print("  ⚠ No mechanism produced a measurable delta.")
        print("    The corpus may not exercise the patterns, or a wiring")
        print("    bug prevents activation.")
    else:
        print("  Mechanisms produced these concrete effects:")
        for d in deltas:
            print(d)

    out = Path(__file__).parent.parent / "data" / "bench_new_mechanisms.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "baseline": baseline, "enabled": enabled,
    }, indent=2))
    print(f"\nFull JSON: {out}")


if __name__ == "__main__":
    main()
