"""Evaluator: run a list of tasks against an agent and compute metrics.

Metrics:
- pass_rate (overall + per-family + per-difficulty)
- avg_steps, avg_tokens
- skill_reuse_count (how many tasks invoked ≥1 skill)
- learning curve (per-task index → cumulative pass rate)

Statistical comparison: Wilson score interval for pass rates of two groups.
"""
from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from verimem.agent import HippoAgent
from verimem.tools import PythonExecutor
from verimem.wake import WakeResult

from .tasks import BenchmarkTask


@dataclass
class EvalResult:
    task_id: str
    family: str
    difficulty: int
    success: bool
    steps: int
    tokens: int
    skills_used: list[str]
    duration_s: float
    message: str


@dataclass
class BenchmarkReport:
    label: str
    results: list[EvalResult] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    ended_at: float = 0.0

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.success) / len(self.results)

    @property
    def avg_steps(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.steps for r in self.results) / len(self.results)

    @property
    def avg_tokens(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.tokens for r in self.results) / len(self.results)

    @property
    def skill_reuse_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.skills_used) / len(self.results)

    def by_family(self) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        fams = {r.family for r in self.results}
        for f in fams:
            sub = [r for r in self.results if r.family == f]
            if not sub:
                continue
            out[f] = {
                "n": len(sub),
                "pass_rate": sum(1 for r in sub if r.success) / len(sub),
                "avg_steps": sum(r.steps for r in sub) / len(sub),
                "avg_tokens": sum(r.tokens for r in sub) / len(sub),
            }
        return out

    def learning_curve(self) -> list[tuple[int, float]]:
        """Cumulative pass-rate after each task in order."""
        curve = []
        cum = 0
        for i, r in enumerate(self.results, 1):
            cum += int(r.success)
            curve.append((i, cum / i))
        return curve

    def summary_dict(self) -> dict:
        return {
            "label": self.label,
            "n": len(self.results),
            "pass_rate": self.pass_rate,
            "avg_steps": self.avg_steps,
            "avg_tokens": self.avg_tokens,
            "skill_reuse_rate": self.skill_reuse_rate,
            "by_family": self.by_family(),
            "duration_s": self.ended_at - self.started_at,
        }


def wilson_interval(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score CI for binomial proportion."""
    if trials == 0:
        return (0.0, 0.0)
    p = successes / trials
    denom = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denom
    half = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def two_proportion_z(s1: int, n1: int, s2: int, n2: int) -> tuple[float, float]:
    """Two-proportion z test. Returns (z, two-sided p)."""
    if n1 == 0 or n2 == 0:
        return (0.0, 1.0)
    p1, p2 = s1 / n1, s2 / n2
    p = (s1 + s2) / (n1 + n2)
    if p in (0.0, 1.0):
        return (0.0, 1.0)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return (0.0, 1.0)
    z = (p1 - p2) / se
    # two-sided p-value via standard normal CDF
    from math import erf, sqrt
    p_value = 2 * (1 - 0.5 * (1 + erf(abs(z) / sqrt(2))))
    return (z, p_value)


class Evaluator:
    def __init__(self, agent: HippoAgent, executor: PythonExecutor | None = None) -> None:
        self.agent = agent
        self.executor = executor or PythonExecutor()

    def run(
        self,
        tasks: list[BenchmarkTask],
        label: str,
        on_each: Callable[[int, EvalResult], None] | None = None,
    ) -> BenchmarkReport:
        report = BenchmarkReport(label=label)
        for i, task in enumerate(tasks, 1):
            t0 = time.time()
            try:
                result: WakeResult = self.agent.run_task(
                    task_id=task.id,
                    task_text=task.prompt,
                    validator=task.validator_for(self.executor),
                )
                er = EvalResult(
                    task_id=task.id,
                    family=task.family,
                    difficulty=task.difficulty,
                    success=result.success,
                    steps=result.episode.num_steps,
                    tokens=result.episode.tokens_used,
                    skills_used=[s.id for s in result.skills_retrieved],
                    duration_s=time.time() - t0,
                    message=result.message,
                )
            except Exception as exc:  # noqa: BLE001
                er = EvalResult(
                    task_id=task.id, family=task.family, difficulty=task.difficulty,
                    success=False, steps=0, tokens=0, skills_used=[],
                    duration_s=time.time() - t0,
                    message=f"crash: {exc!r}",
                )
            report.results.append(er)
            if on_each:
                on_each(i, er)
        report.ended_at = time.time()
        return report
