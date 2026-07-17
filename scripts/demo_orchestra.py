"""Active-memory orchestra — see all five new mechanisms in one run.

Run:
    python scripts/demo_orchestra.py

What it does, in one breath:
  Builds a small but realistic SkillLibrary + EpisodicMemory state, then
  walks through the five new mechanisms in order. For each it prints
  what was BEFORE the mechanism fired and what is AFTER, so you can
  read the effect with your own eyes.

This is intentionally minimal: no LLM (we use a stub MagicMock for the
Dreamer when needed), no SQLite-dependent magic. The point is to read
what the system actually does, not to hit a benchmark number.
"""
from __future__ import annotations

import shutil
import tempfile
import time
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

from verimem import embedding
from verimem import skill as skill_mod
from verimem import sleep as sleep_mod
from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory
from verimem.semantic import SemanticMemory
from verimem.skill import Skill, SkillLibrary
from verimem.sleep import SleepEngine, compute_skill_avg_steps, replay_priority
from verimem.trace_alignment import (
    align_traces,
    find_divergence_point,
)
from verimem.trunc import smart_truncate

# ---------------------------------------------------------------------------
# Pretty printing helpers — keep main() readable.
# ---------------------------------------------------------------------------


def section(title: str) -> None:
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


def kv(k: str, v: object, *, indent: int = 2) -> None:
    print(" " * indent + f"{k:<28} {v}")


def cosine_norm(u: np.ndarray, v: np.ndarray) -> float:
    nu = float(np.linalg.norm(u))
    nv = float(np.linalg.norm(v))
    if nu == 0 or nv == 0:
        return 0.0
    return float(np.dot(u, v) / (nu * nv))


# ---------------------------------------------------------------------------
# Scenario factory.
# ---------------------------------------------------------------------------


def make_state(tmpdir: Path):
    """Realistic-but-tiny state: 1 winner, 1 rival, 1 stale skill,
    a couple of successes, a couple of failures, an anomalous run.
    """
    skills = SkillLibrary(
        dir_path=tmpdir / "skills",
        db_path=tmpdir / "skills_index.db",
    )
    memory = EpisodicMemory(db_path=tmpdir / "ep.db")
    semantic = SemanticMemory(db_path=tmpdir / "semantic.db")

    base_emb = embedding.encode("fix arithmetic bug in calculator").tolist()
    winner = Skill(
        name="bugfix_arith", trigger="fix arithmetic bug",
        body="patch return statement",
        status="promoted", trials=10, successes=8,
        learned_embedding=base_emb,
        last_used_at=time.time(),
    )
    rival = Skill(
        name="rewrite_arith", trigger="rewrite arithmetic module",
        body="overwrite the file",
        status="candidate", trials=2, successes=1,
        learned_embedding=base_emb,  # cosine 1.0 with winner — perfect rival
    )
    stale = Skill(
        name="legacy_helper", trigger="legacy task pattern",
        body="invoke legacy helper",
        status="promoted", trials=20, successes=18,
        learned_embedding=embedding.encode("legacy task pattern").tolist(),
        last_used_at=time.time() - 30 * 24 * 3600.0,
    )
    skills.store(winner)
    skills.store(rival)
    skills.store(stale)

    # Two successes for the winner
    for i in range(2):
        memory.store(Episode(
            id=f"ok_{i}", task_id="bf",
            task_text=f"fix calculator add returns wrong sign #{i}",
            outcome="success",
            skills_used=[winner.id],
            traces=[
                Trace(step=1, thought="", action="fs_read_file",
                      action_input="calc.py",
                      observation="def add(a, b):\n    return a - b"),
                Trace(step=2, thought="", action="apply_edit",
                      action_input="patch", observation="edit applied"),
                Trace(step=3, thought="", action="submit_solution",
                      action_input="ok", observation="done"),
            ],
        ))

    # Two failures both diverging at step 2 (different wrong action each)
    for i, wrong_action in enumerate(["fs_write_file", "rewrite_file"]):
        memory.store(Episode(
            id=f"fail_{i}", task_id="bf",
            task_text=f"failed bugfix attempt #{i}",
            outcome="failure",
            critique="overwrote whole file instead of patching the line",
            skills_used=[winner.id],
            traces=[
                Trace(step=1, thought="", action="fs_read_file",
                      action_input="calc.py",
                      observation="def add(a, b):\n    return a - b"),
                Trace(step=2, thought="", action=wrong_action,
                      action_input="patch", observation="edit applied"),
                Trace(step=3, thought="", action="submit_solution",
                      action_input="tried", observation="failed"),
            ],
        ))

    # Anomalous episode — 10 steps where typical is 3
    memory.store(Episode(
        id="anom", task_id="bf",
        task_text="anomalous bug fix that took forever",
        outcome="success",
        skills_used=[winner.id],
        traces=[
            Trace(step=i, thought="", action=f"step{i}",
                  action_input="x", observation="y")
            for i in range(1, 11)
        ],
    ))
    return skills, memory, semantic, winner, rival, stale


# ---------------------------------------------------------------------------
# Each mechanism has its own little movement.
# ---------------------------------------------------------------------------


def show_trace_alignment(memory):
    section("1) TRACE ALIGNMENT — divergenza tra fail e success-twin")
    success = memory.get("ok_0")
    failure = memory.get("fail_0")
    a = align_traces(failure, success)
    print()
    print("  Step-by-step alignment (F=failure, S=success):")
    for p in a.pairs:
        f_str = f"step{p.fail.step:>2} {p.fail.action!r:<18}" if p.fail else "      (skip)        "
        s_str = f"step{p.success.step:>2} {p.success.action!r:<18}" if p.success else "      (skip)        "
        marker = "==" if p.action_match else "!="
        sim = f"{p.obs_similarity:+.2f}" if p.obs_similarity > float("-inf") else "  -- "
        print(f"    obs={sim} {marker}  F: {f_str}  S: {s_str}")
    div = find_divergence_point(a)
    print()
    if div:
        print("  Detected divergence:")
        print("  " + div.rationale)


def show_lateral_inhibition(skills, winner, rival):
    section("2) LATERAL INHIBITION — il rival si differenzia dal winner")
    task = "fix calculator add function returns wrong sign"
    task_vec = embedding.encode(task)

    # Cosine before
    rb = np.asarray(rival.learned_embedding, dtype=np.float32)
    cos_rival_task_before = cosine_norm(rb, task_vec)
    cos_rival_winner_before = cosine_norm(
        rb, np.asarray(winner.learned_embedding, dtype=np.float32),
    )

    # Flip the flag for this section only.
    original = skill_mod.CONFIG
    skill_mod.CONFIG = replace(
        original,
        lateral_inhibition_enabled=True,
        lateral_inhibition_alpha=0.10,
        lateral_inhibition_min_similarity=0.80,
        lateral_inhibition_top_k=5,
    )
    try:
        skills.update_fitness(winner.id, success=True, tokens=10, task_text=task)
    finally:
        skill_mod.CONFIG = original

    # Cosine after
    rival_after = skills.get(rival.id)
    ra = np.asarray(rival_after.learned_embedding, dtype=np.float32)
    cos_rival_task_after = cosine_norm(ra, task_vec)
    winner_after = skills.get(winner.id)
    cos_rival_winner_after = cosine_norm(
        ra, np.asarray(winner_after.learned_embedding, dtype=np.float32),
    )

    print()
    print("  cosine(rival, task)   before:", f"{cos_rival_task_before:+.4f}",
          " -> after:", f"{cos_rival_task_after:+.4f}",
          " delta:", f"{cos_rival_task_after - cos_rival_task_before:+.4f}")
    print("  cosine(rival, winner) before:", f"{cos_rival_winner_before:+.4f}",
          " -> after:", f"{cos_rival_winner_after:+.4f}",
          " delta:", f"{cos_rival_winner_after - cos_rival_winner_before:+.4f}")
    print("  Negative deltas = differentiation working (rival moved away).")


def show_spontaneous_reactivation(skills, semantic, memory, stale):
    section("3) SPONTANEOUS REACTIVATION — la skill stale viene rispolverata")
    print()
    kv("stale.last_used_at  (before)",
       f"{stale.last_used_at:.0f} ({(time.time() - stale.last_used_at) / 86400:.1f} days ago)")

    original = sleep_mod.CONFIG
    sleep_mod.CONFIG = replace(
        original,
        spontaneous_reactivation_enabled=True,
        spontaneous_reactivation_n=3,
        spontaneous_reactivation_min_age_s=24 * 3600.0,
    )
    try:
        engine = SleepEngine(memory=memory, skills=skills, semantic=semantic,
                             llm=MagicMock(), seed=42)
        n = engine._stage_spontaneous_reactivation(sleep_mod.SleepReport())
    finally:
        sleep_mod.CONFIG = original

    stale_after = skills.get(stale.id)
    kv("skills reactivated", n)
    kv("stale.last_used_at  (after)",
       f"{stale_after.last_used_at:.0f} ({(time.time() - stale_after.last_used_at) / 86400:.1f} days ago)")
    print("  The reactivation pushed last_used_at forward by half the decay")
    print("  cutoff so decay_idle_embeddings won't snap it next cycle.")


def show_replay_surprise(memory):
    section("4) REPLAY PRIORITY by SURPRISE — episodi anomali salgono in priorità")
    skill_ids = {sid for ep in memory.all() for sid in ep.skills_used}
    avg = compute_skill_avg_steps(memory, skill_ids)
    now = time.time()
    max_age = max((now - ep.created_at for ep in memory.all()), default=1.0)
    print()
    print(f"  average num_steps for the bugfix skill: {list(avg.values())[0]:.1f}")
    print()
    print("  episode             num_steps   priority(no surprise)   priority(w/ surprise=0.4)")
    original = sleep_mod.CONFIG
    for ep in memory.all():
        sleep_mod.CONFIG = replace(original, sleep_replay_priority_surprise=0.0)
        p_no = replay_priority(ep, now, max_age, avg)
        sleep_mod.CONFIG = replace(original, sleep_replay_priority_surprise=0.4)
        p_yes = replay_priority(ep, now, max_age, avg)
        print(f"  {ep.id:<18}  {ep.num_steps:>9}    "
              f"{p_no:>+18.4f}    {p_yes:>+18.4f}")
    sleep_mod.CONFIG = original
    print("  The 'anom' episode (10 steps when typical is 3) gets a clear")
    print("  boost when the surprise weight is on.")


def show_recall_floor(memory):
    section("5) RECALL FLOOR — episodi irrilevanti scompaiono dal prompt")
    novel_query = "compose a haiku about autumn leaves"  # nothing similar exists
    print()
    print(f"  query: {novel_query!r}")
    print()
    no_floor = memory.recall(novel_query, k=5, min_similarity=0.0)
    with_floor = memory.recall(novel_query, k=5, min_similarity=0.30)
    print(f"  recall(min_sim=0.00): returned {len(no_floor)} episodes")
    for ep, sim in no_floor:
        print(f"    {sim:+.2f}  {ep.task_text[:54]}")
    print()
    print(f"  recall(min_sim=0.30): returned {len(with_floor)} episodes")
    for ep, sim in with_floor:
        print(f"    {sim:+.2f}  {ep.task_text[:54]}")
    print("  Without the floor the prompt would inject 5 unrelated 'few-shot'")
    print("  examples and bias the model toward bugfix templates for a haiku.")


def show_smart_truncate():
    section("6) SMART_TRUNCATE — head+tail preserved on long output")
    fake_stderr = (
        "Loading dataset...\n"
        "Epoch 1/100 loss=2.34\n"
        + "\n".join(f"Epoch {i}/100 loss={2.34 - i*0.02:.2f}" for i in range(2, 95))
        + "\nTraceback (most recent call last):\n"
          "  File 'train.py', line 42, in <module>\n"
          "    model.fit(x, y)\n"
          "RuntimeError: out of memory at batch 73\n"
    )
    print()
    print(f"  fake stderr length: {len(fake_stderr)} chars")
    truncated = smart_truncate(fake_stderr, max_chars=400, head_ratio=0.3)
    print("  smart_truncate to 400 chars (head_ratio=0.3 — bias toward tail):")
    print(f"  {'-'*50}")
    for line in truncated.split("\n"):
        print(f"  {line}")
    print(f"  {'-'*50}")
    print("  The traceback at the END survived the truncation. Naive head-cut")
    print("  would have shown 100 lines of training noise and dropped the error.")


# ---------------------------------------------------------------------------


def main() -> None:
    tmpdir = Path(tempfile.mkdtemp(prefix="orchestra_"))
    try:
        skills, memory, semantic, winner, rival, stale = make_state(tmpdir)

        print()
        print("Active-memory orchestra — five new zero-LLM mechanisms,")
        print("exercised on a tiny but realistic state.")

        show_trace_alignment(memory)
        show_lateral_inhibition(skills, winner, rival)
        show_spontaneous_reactivation(skills, semantic, memory, stale)
        show_replay_surprise(memory)
        show_recall_floor(memory)
        show_smart_truncate()

        print()
        print("Done. All operations above ran without a single LLM call.")
        print()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
