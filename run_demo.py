#!/usr/bin/env python
"""End-to-end demo of the HippoAgent learning loop.

Pipeline:
1. Reset state.
2. BASELINE: run held-out tasks WITHOUT skill library → record pass rate.
3. WAKE: run wake-set tasks (records episodes; uses skills as they emerge).
4. SLEEP: run consolidation cycle.
5. HIPPO: run held-out tasks WITH consolidated skill library.
6. Compare BASELINE vs HIPPO with statistical test, save report.

This is the scientific test: does sleep consolidation produce measurable
improvement on novel tasks (zero-shot transfer)?
"""
from __future__ import annotations

import argparse
import json
import time

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from benchmark.evaluator import (
    BenchmarkReport,
    EvalResult,
    Evaluator,
    two_proportion_z,
    wilson_interval,
)
from benchmark.tasks import heldout_split, wake_split
from engram.agent import HippoAgent
from engram.config import CONFIG
from engram.tools import PythonExecutor
from engram.wake import WakeConfig

console = Console()


def progress(label: str, i: int, er: EvalResult) -> None:
    mark = "[green]✓[/]" if er.success else "[red]✗[/]"
    console.print(
        f"  {mark} [{i:02d}] {er.task_id:24s}  "
        f"steps={er.steps:2d} tokens={er.tokens:5d}  "
        f"skills={len(er.skills_used)}  ({er.message[:40]})"
    )


def run_phase(
    label: str,
    tasks,
    use_skills: bool,
    wake_max_steps: int = CONFIG.wake_max_steps,
) -> BenchmarkReport:
    cfg = WakeConfig(
        use_skills=use_skills,
        use_past_episodes=use_skills,
        max_steps=wake_max_steps,
    )
    agent = HippoAgent.build(wake_config=cfg)
    evaluator = Evaluator(agent, executor=PythonExecutor())
    console.rule(f"[bold cyan]Phase: {label} ({len(tasks)} tasks)[/]")
    return evaluator.run(tasks, label=label, on_each=lambda i, er: progress(label, i, er))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-wake", type=int, default=0, help="cap wake tasks (0 = all)")
    ap.add_argument("--n-heldout", type=int, default=0, help="cap heldout tasks (0 = all)")
    ap.add_argument("--seed", type=int, default=CONFIG.seed)
    ap.add_argument("--skip-baseline", action="store_true",
                    help="skip the no-skill baseline (faster but no comparison)")
    args = ap.parse_args()

    t_start = time.time()

    # 1. Reset
    console.rule("[bold red]Phase 0: reset[/]")
    HippoAgent.build().reset()

    wake_tasks = wake_split(seed=args.seed)
    heldout_tasks = heldout_split(seed=args.seed)
    if args.n_wake:
        wake_tasks = wake_tasks[: args.n_wake]
    if args.n_heldout:
        heldout_tasks = heldout_tasks[: args.n_heldout]

    # 2. Baseline (no skills, no past episodes)
    baseline = None
    if not args.skip_baseline:
        baseline = run_phase("baseline", heldout_tasks, use_skills=False)
        # Wipe any episodes the baseline created — we don't want them in wake memory
        HippoAgent.build().memory.clear()

    # 3. Wake
    wake_report = run_phase("wake", wake_tasks, use_skills=True)

    # 4. Sleep
    console.rule("[bold magenta]Phase: sleep[/]")
    sleep_report = HippoAgent.build().consolidate()
    console.print(Panel.fit(
        f"replayed={sleep_report.n_episodes_replayed}  "
        f"clusters={sleep_report.n_clusters}\n"
        f"NREM_skills={sleep_report.n_nrem_skills}  "
        f"REM_skills={sleep_report.n_rem_skills}  facts={sleep_report.n_facts}\n"
        f"promoted={len(sleep_report.promoted)}  "
        f"retired={len(sleep_report.retired)}  "
        f"merged={len(sleep_report.merged)}\n"
        f"duration={sleep_report.duration_s:.1f}s  tokens={sleep_report.tokens_used}",
        title="Sleep Report", border_style="magenta",
    ))

    # 5. HippoAgent (with consolidated skills)
    hippo = run_phase("hippo", heldout_tasks, use_skills=True)

    # 6. Comparison + report
    console.rule("[bold green]Final Report[/]")
    table = Table(title="Held-out comparison")
    table.add_column("metric"); table.add_column("baseline"); table.add_column("hippo")
    table.add_column("Δ")
    if baseline:
        b_pass = baseline.pass_rate
        h_pass = hippo.pass_rate
        b_lo, b_hi = wilson_interval(
            sum(1 for r in baseline.results if r.success), len(baseline.results))
        h_lo, h_hi = wilson_interval(
            sum(1 for r in hippo.results if r.success), len(hippo.results))
        z, pval = two_proportion_z(
            sum(1 for r in hippo.results if r.success), len(hippo.results),
            sum(1 for r in baseline.results if r.success), len(baseline.results),
        )
        table.add_row(
            "pass_rate",
            f"{b_pass:.1%} CI95[{b_lo:.0%},{b_hi:.0%}]",
            f"{h_pass:.1%} CI95[{h_lo:.0%},{h_hi:.0%}]",
            f"{(h_pass - b_pass) * 100:+.1f}pp (z={z:.2f}, p={pval:.3f})",
        )
        table.add_row("avg_steps", f"{baseline.avg_steps:.1f}", f"{hippo.avg_steps:.1f}",
                      f"{hippo.avg_steps - baseline.avg_steps:+.1f}")
        table.add_row("avg_tokens", f"{baseline.avg_tokens:.0f}", f"{hippo.avg_tokens:.0f}",
                      f"{hippo.avg_tokens - baseline.avg_tokens:+.0f}")
        table.add_row("skill_reuse_rate", "0%",
                      f"{hippo.skill_reuse_rate:.1%}",
                      f"+{hippo.skill_reuse_rate * 100:.1f}pp")
    else:
        table.add_row("pass_rate", "—", f"{hippo.pass_rate:.1%}", "—")
    console.print(table)

    # Save
    out = CONFIG.reports_dir / f"demo_{int(time.time())}.json"
    payload = {
        "wake": wake_report.summary_dict(),
        "hippo_heldout": hippo.summary_dict(),
        "sleep": {
            "n_episodes_replayed": sleep_report.n_episodes_replayed,
            "n_clusters": sleep_report.n_clusters,
            "n_nrem_skills": sleep_report.n_nrem_skills,
            "n_rem_skills": sleep_report.n_rem_skills,
            "n_facts": sleep_report.n_facts,
            "promoted": sleep_report.promoted,
            "retired": sleep_report.retired,
            "merged": sleep_report.merged,
            "duration_s": sleep_report.duration_s,
            "tokens_used": sleep_report.tokens_used,
        },
        "duration_total_s": time.time() - t_start,
    }
    if baseline:
        payload["baseline_heldout"] = baseline.summary_dict()
        payload["statistical"] = {"z": z, "p_value": pval, "delta_pp": (h_pass - b_pass) * 100}
    out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    console.print(f"[dim]→ report saved at {out}[/dim]")
    console.print(f"[dim]→ total runtime: {time.time() - t_start:.1f}s[/dim]")


if __name__ == "__main__":
    main()
