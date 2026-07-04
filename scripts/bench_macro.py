"""Benchmark: procedural-compilation speed-up vs ReAct loop.

Compares wall-clock time and token cost for the same task:
  • Cold path  — no compiled macro, agent runs full ReAct loop with N LLM calls.
  • Hot path   — compiled macro fires, zero LLM calls.

LLM is simulated with a configurable latency (env BENCH_LLM_LATENCY_S, default
0.6s) so the benchmark approximates a real model call without needing keys.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engram.compilation import CompiledMacro, MacroStep
from engram.llm import LLMResponse, LLMToolResponse, ToolCall
from engram.memory import EpisodicMemory
from engram.skill import Skill, SkillLibrary
from engram.tools import ToolResult, ToolSpec, default_tools
from engram.wake import WakeAgent, WakeConfig, trivial_validator


def _mk_tools(captured: dict[str, Any]) -> dict[str, ToolSpec]:
    """Tools that record what they were called with — sandbox-free."""
    def write_handler(*, path: str, content: str) -> ToolResult:
        captured["path"] = path
        captured["content"] = content
        return ToolResult(ok=True, output=f"wrote {len(content)} bytes")

    def submit_handler(*, answer: str) -> ToolResult:
        captured["answer"] = answer
        return ToolResult(ok=True, output=answer)

    tools = dict(default_tools())
    tools["fs_write_file"] = ToolSpec(
        name="fs_write_file",
        description="write content to path",
        schema={
            "type": "object",
            "properties": {"path": {"type": "string"},
                            "content": {"type": "string"}},
            "required": ["path", "content"],
        },
        handler=write_handler,
    )
    tools["submit_solution"] = ToolSpec(
        name="submit_solution",
        description="finalise answer",
        schema={
            "type": "object",
            "properties": {"answer": {"type": "string"}},
            "required": ["answer"],
        },
        handler=submit_handler,
    )
    return tools


@dataclass
class _SimLLM:
    """LLM mock with configurable per-call latency.

    For ReAct mode: emits a sequence of tool-use replies that solve the task,
    one per call. Tracks call count + total simulated latency.
    """
    latency_s: float = 0.6
    calls: int = 0
    sleep_total_s: float = 0.0
    plan: list[dict[str, Any]] | None = None
    plan_idx: int = 0

    def supports_tools(self) -> bool:
        return True

    def complete(self, *a, **kw) -> LLMResponse:  # noqa: D401
        time.sleep(self.latency_s)
        self.sleep_total_s += self.latency_s
        self.calls += 1
        return LLMResponse(
            text="(text-only)", input_tokens=200, output_tokens=80,
            model="sim", latency_s=self.latency_s,
        )

    def complete_with_tools(self, *a, **kw) -> LLMToolResponse:
        time.sleep(self.latency_s)
        self.sleep_total_s += self.latency_s
        self.calls += 1
        idx = min(self.plan_idx, len(self.plan or []) - 1) if self.plan else 0
        self.plan_idx += 1
        if not self.plan:
            tc = ToolCall(id=f"t{self.calls}", name="submit_solution",
                          input={"answer": "done"})
            return LLMToolResponse(
                text="", tool_calls=[tc],
                input_tokens=200, output_tokens=80,
                model="sim", latency_s=self.latency_s, raw_content=[],
            )
        step = self.plan[idx]
        tc = ToolCall(id=f"t{self.calls}", name=step["tool"], input=step["args"])
        return LLMToolResponse(
            text="", tool_calls=[tc],
            input_tokens=200, output_tokens=80,
            model="sim", latency_s=self.latency_s, raw_content=[],
        )


def _bench_run(
    skill: Skill,
    plan: list[dict[str, Any]],
    task: str,
    latency_s: float,
    tmpdir: Path,
    tag: str,
) -> dict[str, Any]:
    """Run one task with a fresh agent state, return metrics."""
    captured: dict[str, Any] = {}
    lib = SkillLibrary(tmpdir / f"{tag}_skills",
                        tmpdir / f"{tag}_skills" / "idx.db")
    mem = EpisodicMemory(tmpdir / f"{tag}_ep.db")
    lib.store(skill)

    sim = _SimLLM(latency_s=latency_s, plan=plan)
    agent = WakeAgent(
        memory=mem, skills=lib, tools=_mk_tools(captured),
        llm=sim, config=WakeConfig(),
    )
    t0 = time.perf_counter()
    result = agent.run(task_id=tag, task_text=task, validator=trivial_validator)
    dt = time.perf_counter() - t0

    return {
        "tag": tag,
        "ok": result.success,
        "wall_s": dt,
        "llm_calls": sim.calls,
        "tokens": result.episode.tokens_used,
        "answer": captured.get("answer", ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3,
                         help="Repeat each path N times for median")
    parser.add_argument("--latency", type=float,
                         default=float(os.environ.get("BENCH_LLM_LATENCY_S", "0.6")),
                         help="Simulated per-LLM-call latency in seconds")
    args = parser.parse_args()

    task = "echo this phrase back"

    # Plan that the simulated ReAct LLM will follow on COLD path:
    #   step 1 — write a scratch file (simulates an extra step)
    #   step 2 — submit the answer
    cold_plan = [
        {"tool": "fs_write_file",
         "args": {"path": "/tmp/scratch.txt", "content": "echoing"}},
        {"tool": "submit_solution",
         "args": {"answer": "echoed: echo this phrase back"}},
    ]

    # Macro that the HOT path uses (deterministic, single-step):
    macro_steps = [
        MacroStep(tool="submit_solution",
                   args={"answer": "echoed: {{TASK}}"}),
    ]

    cold_runs: list[dict[str, Any]] = []
    hot_runs: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        for i in range(args.repeats):
            # COLD: skill exists but has no compiled macro → ReAct loop runs
            cold_skill = Skill(
                name="echo phrase back", trigger="when asked to echo a phrase",
                body="just echo the input", trials=10, successes=10, status="promoted",
            )
            cold_runs.append(_bench_run(
                cold_skill, cold_plan, task, args.latency, tmp, f"cold_{i}",
            ))

        for i in range(args.repeats):
            # HOT: skill has compiled macro → wake fast-path bypasses LLM
            hot_skill = Skill(
                name="echo phrase back", trigger="when asked to echo a phrase",
                body="just echo the input", trials=10, successes=10, status="promoted",
            )
            macro = CompiledMacro(skill_id=hot_skill.id, steps=macro_steps,
                                   confidence=0.95)
            hot_skill.compiled_macro = macro.to_dict()
            hot_runs.append(_bench_run(
                hot_skill, cold_plan, task, args.latency, tmp, f"hot_{i}",
            ))

    cold_med = statistics.median(r["wall_s"] for r in cold_runs)
    hot_med = statistics.median(r["wall_s"] for r in hot_runs)
    cold_calls = statistics.median(r["llm_calls"] for r in cold_runs)
    hot_calls = statistics.median(r["llm_calls"] for r in hot_runs)
    cold_tokens = statistics.median(r["tokens"] for r in cold_runs)
    hot_tokens = statistics.median(r["tokens"] for r in hot_runs)

    speedup = cold_med / hot_med if hot_med > 0 else float("inf")
    saved = cold_med - hot_med

    print()
    print("=" * 64)
    print("  HippoAgent — procedural-compilation benchmark")
    print("=" * 64)
    print(f"  task            : {task!r}")
    print(f"  repeats         : {args.repeats} per path")
    print(f"  sim LLM latency : {args.latency:.2f} s/call")
    print()
    print(f"  COLD (ReAct)    median  wall={cold_med:.3f}s  "
           f"llm_calls={cold_calls}  tokens={cold_tokens}")
    print(f"  HOT  (macro)    median  wall={hot_med:.3f}s  "
           f"llm_calls={hot_calls}   tokens={hot_tokens}")
    print()
    print(f"  → speed-up      : {speedup:6.2f}x")
    print(f"  → time saved    : {saved*1000:6.1f} ms per task")
    print(f"  → token saved   : {(cold_tokens - hot_tokens):6.0f}")
    print(f"  → both ok       : "
           f"{all(r['ok'] for r in cold_runs + hot_runs)}")
    print(f"  → answers match : "
           f"{all(r['answer'] == cold_runs[0]['answer'] for r in cold_runs)} (cold), "
           f"{all(r['answer'] == hot_runs[0]['answer'] for r in hot_runs)} (hot)")
    print("=" * 64)

    # Persist a JSON summary for downstream tooling
    out_path = Path("data/reports") / "bench_macro.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "task": task,
        "repeats": args.repeats,
        "latency_s": args.latency,
        "cold": {"median_wall_s": cold_med, "median_calls": cold_calls,
                  "median_tokens": cold_tokens, "runs": cold_runs},
        "hot":  {"median_wall_s": hot_med, "median_calls": hot_calls,
                  "median_tokens": hot_tokens, "runs": hot_runs},
        "speedup": speedup,
        "saved_ms_per_task": saved * 1000,
    }
    out_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"  summary written : {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
