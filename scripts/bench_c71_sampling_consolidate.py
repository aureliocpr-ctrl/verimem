"""Cycle #71 bench — MCPSamplingLLM end-to-end stub consolidate.

Misura latenza + correttezza di `SleepEngine.cycle()` quando l'LLM è
sostituito da `MCPSamplingLLM` che parla con un FakeSession (stub MCP
host). Non chiama LLM reali — il test "reale" via subscription va fatto
manualmente da Aurelio dentro una sessione Claude Code post-restart.

Output: JSON in docs/bench/cycle-71-sampling-stub.json + md.
"""
from __future__ import annotations

import asyncio
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------- FakeSession returning valid JSON --------------------------

class _FakeContent:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeResult:
    def __init__(self, text: str) -> None:
        self.role = "assistant"
        self.content = _FakeContent(text)
        self.model = "claude-stub-bench"
        self.stopReason = "endTurn"


class _StubMCPSession:
    """Async fake. Returns canned skill JSON for any prompt — enough
    for SleepEngine.cycle() to produce skills without real LLM."""

    def __init__(self) -> None:
        self.n_calls = 0
        self.latencies_s: list[float] = []

    async def create_message(self, **kwargs) -> _FakeResult:
        t0 = time.time()
        self.n_calls += 1
        # Simulate small think-time
        await asyncio.sleep(0.005)
        # Return a generic skill JSON the dreamer can parse
        text = json.dumps({
            "name": f"stub_skill_{self.n_calls}",
            "trigger": "when task involves stub",
            "body": "do_stub_action()",
            "rationale": "Stub rationale for bench",
        })
        self.latencies_s.append(time.time() - t0)
        return _FakeResult(text)


# ---------- Bench --------------------------------------------------------


def _build_agent_with_corpus(tmp_dir: Path):
    """Build a real agent with a small corpus (~10 episodes).

    Uses ENGRAM_DATA_DIR env var (read by EpisodicMemory at construct
    time) instead of mutating frozen CONFIG.
    """
    import os
    os.environ["ENGRAM_DATA_DIR"] = str(tmp_dir)

    from engram.agent import HippoAgent
    from engram.llm import MockLLM
    # Pass a Mock so build() doesn't need ANTHROPIC_API_KEY. We swap
    # a.sleep.llm later with the MCPSamplingLLM stub.
    a = HippoAgent.build(llm=MockLLM())

    # Seed 10 episodes
    from engram.episode import Episode
    for i in range(10):
        ep = Episode(
            id=f"ep-bench-{i}",
            task_text=f"Bench task #{i}: process payload {i}",
            outcome="success" if i % 2 == 0 else "failure",
            final_answer=f"answer {i}",
            salience_score=0.5 + i * 0.05,
        )
        a.memory.store(ep)
    return a


async def _run_bench() -> dict[str, Any]:
    import tempfile

    from engram.llm import MCPSamplingLLM

    tmp_dir = Path(tempfile.mkdtemp(prefix="hippo_c71_bench_"))
    a = _build_agent_with_corpus(tmp_dir)

    loop = asyncio.get_running_loop()
    sess = _StubMCPSession()
    sampling_llm = MCPSamplingLLM(loop=loop, session=sess)
    # Swap
    a.sleep.llm = sampling_llm

    # 3 runs: warmup + 2 measure
    runs: list[dict[str, Any]] = []
    for i in range(3):
        t0 = time.time()
        try:
            report = await asyncio.to_thread(a.consolidate)
            err = None
        except Exception as exc:  # noqa: BLE001
            err = str(exc)
            report = None
        elapsed = time.time() - t0
        runs.append({
            "run": i,
            "elapsed_s": round(elapsed, 3),
            "n_clusters": (
                getattr(report, "n_clusters", 0) if report else 0
            ),
            "n_nrem_skills": (
                getattr(report, "n_nrem_skills", 0) if report else 0
            ),
            "n_rem_skills": (
                getattr(report, "n_rem_skills", 0) if report else 0
            ),
            "n_facts": (
                getattr(report, "n_facts", 0) if report else 0
            ),
            "error": err,
        })

    # MCP call stats
    measure_runs = runs[1:]  # skip warmup
    mcp_latencies_ms = [
        lat * 1000 for lat in sess.latencies_s
    ]

    return {
        "runs": runs,
        "warmup_elapsed_s": runs[0]["elapsed_s"],
        "measure_mean_elapsed_s": statistics.mean(
            r["elapsed_s"] for r in measure_runs
        ),
        "n_mcp_calls_total": sess.n_calls,
        "mcp_call_latency_ms": {
            "p50": (
                statistics.median(mcp_latencies_ms)
                if mcp_latencies_ms else 0.0
            ),
            "mean": (
                statistics.mean(mcp_latencies_ms)
                if mcp_latencies_ms else 0.0
            ),
            "max": max(mcp_latencies_ms) if mcp_latencies_ms else 0.0,
        },
        "tmp_dir": str(tmp_dir),
    }


def main() -> int:
    print("Cycle #71 bench — MCPSamplingLLM stub end-to-end")
    print("=" * 60)
    result = asyncio.run(_run_bench())

    print(f"\nTmp dir: {result['tmp_dir']}")
    print(f"MCP calls total: {result['n_mcp_calls_total']}")
    print(f"MCP call latency: p50={result['mcp_call_latency_ms']['p50']:.1f}ms "
          f"mean={result['mcp_call_latency_ms']['mean']:.1f}ms "
          f"max={result['mcp_call_latency_ms']['max']:.1f}ms")
    print(f"\nWarmup elapsed: {result['warmup_elapsed_s']}s")
    print(f"Mean measure elapsed: {result['measure_mean_elapsed_s']:.3f}s")
    print("\nPer-run breakdown:")
    for r in result["runs"]:
        marker = "warmup" if r["run"] == 0 else "measure"
        err = f" err={r['error']!r}" if r["error"] else ""
        print(
            f"  [{marker}] run={r['run']} elapsed={r['elapsed_s']}s "
            f"clusters={r['n_clusters']} nrem={r['n_nrem_skills']} "
            f"rem={r['n_rem_skills']} facts={r['n_facts']}{err}"
        )

    # Save
    out_json = ROOT / "docs" / "bench" / "cycle-71-sampling-stub.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nSaved: {out_json.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
