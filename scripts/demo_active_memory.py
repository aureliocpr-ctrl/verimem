"""End-to-end demo of the six active-memory mechanisms.

No real LLM calls — uses a scripted mock so the demo is reproducible
and runnable without API keys. Output is a narrative print stream that
shows each mechanism firing, along with the resulting library state.

Run:   python scripts/demo_active_memory.py
"""
from __future__ import annotations

import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engram.config import CONFIG
from engram.episode import Episode, Trace
from engram.llm import LLMResponse
from engram.memory import EpisodicMemory
from engram.semantic import SemanticMemory
from engram.skill import Skill, SkillLibrary
from engram.sleep import SleepEngine
from engram.tools import ToolResult, ToolSpec, default_tools
from engram.wake import WakeAgent, WakeConfig, trivial_validator


def banner(title: str) -> None:
    print()
    print("─" * 70)
    print(f"  {title}")
    print("─" * 70)


# --- Mock LLM that scripts a different reply per stage ----------------------


@dataclass
class _ScriptedLLM:
    """LLM mock with per-system-prompt-fingerprint responses.

    The `complete()` method returns the right JSON for whatever sleep
    stage is calling it, so a single object can drive the whole cycle.
    """
    calls: int = 0

    NREM = """{
  "name": "Save text to file",
  "trigger": "when asked to save or write a piece of text to a file on disk",
  "body": "1. Build the path. 2. Call fs_write_file. 3. Submit confirmation.",
  "rationale": "Across the cluster the agent always wrote to disk then submitted."
}"""
    REM = """{
  "name": "Save and verify",
  "trigger": "save a piece of content and read it back to verify",
  "body": "Write the file, then read it back, then submit.",
  "rationale": "Combines persistence with verification."
}"""
    CURATOR = """{
  "name": "Save text to file",
  "trigger": "when asked to write text content to a file on disk",
  "body": "Use fs_write_file then submit_solution.",
  "rationale": "Merged from two near-duplicate persistence skills."
}"""
    MACRO = """{
  "steps": [
    {"tool": "fs_write_file", "args": {"path": "/tmp/out.txt", "content": "{{TASK}}"}},
    {"tool": "submit_solution", "args": {"answer": "saved"}}
  ],
  "confidence": 0.9,
  "rationale": "two-step pattern across all successes"
}"""
    COUNTERFACTUAL = """{
  "name": "Verify before submit",
  "trigger": "when previous attempts failed to confirm output",
  "body": "Always read back the result before submitting.",
  "rationale": "Failure mode: agent submitted unverified output."
}"""
    SCHEMA = """{
  "name": "Filesystem operations",
  "trigger": "any task that reads, writes, or persists data on disk",
  "body": "Pick: 'Save text to file' for writes; 'Verify before submit' for paranoid writes.",
  "rationale": "Both children operate on local files."
}"""
    PRACTICE = """{
  "prompts": [
    "Save the text 'demo content' to a file named demo.txt",
    "Create a backup of /tmp/notes.md to /tmp/notes.bak.md"
  ]
}"""

    def supports_tools(self) -> bool:
        return False

    def complete(self, system: str, messages, **_) -> LLMResponse:
        self.calls += 1
        if "COMPILER" in system:
            text = self.MACRO
        elif "COUNTERFACTUAL" in system:
            text = self.COUNTERFACTUAL
        elif "SCHEMA" in system:
            text = self.SCHEMA
        elif "TUTOR" in system:
            text = self.PRACTICE
        elif "REM" in system:
            text = self.REM
        elif "CURATOR" in system:
            text = self.CURATOR
        else:
            text = self.NREM
        return LLMResponse(text=text, input_tokens=200, output_tokens=80,
                            model="scripted", latency_s=0.0)


def _success_episode(skill_id: str, task: str, n: int = 2) -> Episode:
    ep = Episode(task_id="t", task_text=task, outcome="success",
                  final_answer="saved", skills_used=[skill_id])
    for i in range(1, n + 1):
        ep.traces.append(Trace(step=i, thought="t",
                                action="fs_write_file" if i == 1 else "submit_solution",
                                action_input='{"path":"/tmp/out.txt","content":"x"}'
                                              if i == 1 else '{"answer":"saved"}',
                                observation="ok"))
    return ep


def _failure_episode(skill_id: str) -> Episode:
    ep = Episode(task_id="t", task_text="task that fails", outcome="failure",
                  final_answer="", skills_used=[skill_id],
                  critique="agent submitted without verifying")
    ep.traces.append(Trace(step=1, thought="t", action="submit_solution",
                            action_input='{"answer":"???"}',
                            observation="validator rejected"))
    return ep


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        lib = SkillLibrary(tmp / "skills", tmp / "skills" / "idx.db")
        mem = EpisodicMemory(tmp / "ep.db")
        sem = SemanticMemory(tmp / "sem.db")
        llm = _ScriptedLLM()

        # === 1. Seed the library with skills + episodes ====================
        banner("Seeding the library — six skills + episodes")

        # A: high fitness, used many times → compilation candidate
        skill_a = Skill(name="Save text to file",
                         trigger="save a piece of text to a file on disk",
                         body="just write it", trials=10, successes=10,
                         status="promoted")
        # B: filesystem buddy for clustering
        skill_b = Skill(name="Read file",
                         trigger="read a file from disk to retrieve its contents",
                         body="x", trials=4, successes=3, status="promoted")
        # C: filesystem buddy
        skill_c = Skill(name="Open file",
                         trigger="open a file from disk to inspect its contents",
                         body="y", trials=3, successes=2, status="candidate")
        # D: failing skill → counterfactual target
        skill_d = Skill(name="Submit unverified",
                         trigger="when ready to submit without verification",
                         body="just submit", trials=4, successes=0)
        # E: uncertain middle (fitness ≈ 0.5) → practice target
        skill_e = Skill(name="Reformat output",
                         trigger="when reformatting an output is required",
                         body="reformat the text", trials=4, successes=2)
        # F: another fs cluster member
        skill_f = Skill(name="Append to file",
                         trigger="append a line to a file on disk",
                         body="x", trials=3, successes=2, status="promoted")

        for s in (skill_a, skill_b, skill_c, skill_d, skill_e, skill_f):
            lib.store(s)

        for i in range(6):
            mem.store(_success_episode(skill_a.id, f"save the phrase iteration {i}"))
        for _ in range(2):
            mem.store(_failure_episode(skill_d.id))

        print(f"  skills      : {lib.count()}")
        print(f"  episodes    : {mem.count()}  (4 success, 2 failure)")

        # === 2. Run a full sleep cycle =====================================
        banner("Sleep cycle — six mechanisms fire in one pass")
        # Lower the schema cluster threshold for the demo so the fs cluster
        # forms reliably under all-MiniLM-L6-v2 without HF_TOKEN tuning.
        original_thr = CONFIG.schema_cluster_threshold
        object.__setattr__(CONFIG, "schema_cluster_threshold", 0.40)
        try:
            engine = SleepEngine(memory=mem, skills=lib, semantic=sem, llm=llm)
            t0 = time.time()
            report = engine.cycle()
            dt = time.time() - t0
        finally:
            object.__setattr__(CONFIG, "schema_cluster_threshold", original_thr)

        print(f"  duration    : {dt:.2f}s  ({llm.calls} LLM calls, "
               f"{report.tokens_used} tokens)")
        print(f"  NREM skills : {report.n_nrem_skills}")
        print(f"  REM hybrids : {report.n_rem_skills}")
        print(f"  merges      : {len(report.merged)}")
        print(f"  🔧 macros   : {report.n_macros_compiled}")
        print(f"  🌀 cf       : {report.n_counterfactuals}")
        print(f"  🌳 schemas  : {report.n_schemas}")
        print(f"  📚 practice : {report.n_practice_prompts} prompts written")
        print(f"  promoted    : {len(report.promoted)}")
        print(f"  retired     : {len(report.retired)}")

        # === 3. Inspect the resulting active-memory state ==================
        banner("Active-memory state — the library has adapted")
        compiled = [s for s in lib.all() if s.compiled_macro]
        cfs = [s for s in lib.all() if s.is_counterfactual]
        schemas = [s for s in lib.all() if s.stage == "schema"]
        practice = [s for s in lib.all() if s.practice_prompts]

        print(f"  🔧 compiled         : {len(compiled)}")
        for s in compiled:
            n_steps = len(s.compiled_macro.get("steps") or [])
            conf = s.compiled_macro.get("confidence", 0.0)
            print(f"     • {s.name!r}  (steps={n_steps}, conf={conf:.2f})")
        print(f"  🌀 counterfactuals  : {len(cfs)}")
        for s in cfs:
            parent = s.parent_skills[0][:8] if s.parent_skills else "—"
            print(f"     • {s.name!r}  ← parent {parent}")
        print(f"  🌳 schemas          : {len(schemas)}")
        for s in schemas:
            print(f"     • {s.name!r}")
        print(f"  📚 practice prompts : {len(practice)} skill(s) ready to practise")
        for s in practice[:3]:
            print(f"     • {s.name!r} ({len(s.practice_prompts)} prompts)")

        # === 4. Wake fast-path: macro bypasses the LLM =====================
        banner("Wake — re-running a similar task uses the macro fast-path")
        captured: dict[str, Any] = {}

        def write_handler(*, path: str, content: str) -> ToolResult:
            captured["path"] = path
            captured["content"] = content
            return ToolResult(ok=True, output=f"wrote {len(content)} bytes")

        def submit_handler(*, answer: str) -> ToolResult:
            captured["answer"] = answer
            return ToolResult(ok=True, output=answer)

        tools = dict(default_tools())
        tools["fs_write_file"] = ToolSpec(
            name="fs_write_file", description="write content",
            schema={"type": "object",
                    "properties": {"path": {"type": "string"},
                                    "content": {"type": "string"}},
                    "required": ["path", "content"]},
            handler=write_handler,
        )
        tools["submit_solution"] = ToolSpec(
            name="submit_solution", description="finalise",
            schema={"type": "object",
                    "properties": {"answer": {"type": "string"}},
                    "required": ["answer"]},
            handler=submit_handler,
        )

        class _BoomLLM:
            calls = 0
            tools_calls = 0
            def supports_tools(self): return False
            def complete(self, *a, **kw):
                _BoomLLM.calls += 1
                raise AssertionError("LLM should NOT be called — macro should fire")
            def complete_with_tools(self, *a, **kw):
                _BoomLLM.tools_calls += 1
                raise AssertionError("LLM should NOT be called — macro should fire")

        agent = WakeAgent(memory=mem, skills=lib, tools=tools,
                          llm=_BoomLLM(), config=WakeConfig())
        result = agent.run(
            task_id="demo-fast",
            task_text="save a piece of text to a file on disk",
            validator=trivial_validator,
        )
        print("  task        : 'save a piece of text to a file on disk'")
        print(f"  success     : {result.success}")
        print(f"  steps       : {result.episode.num_steps}")
        print(f"  tokens used : {result.episode.tokens_used}")
        print("  llm calls   : 0  (macro fired, no model invoked)")
        print(f"  written     : path={captured.get('path')!r}  "
               f"content={captured.get('content')!r}")
        print(f"  answer      : {captured.get('answer')!r}")

        # === 5. Summary ====================================================
        banner("Summary — six mechanisms, one library")
        print("  The library now embodies six forms of active learning:")
        print("    1. Procedural compilation  → the macro you just saw fire")
        print("    2. Forward replay          → injected as PREDICTED PATH")
        print("       (silent here because we triggered the macro fast-path)")
        print("    3. Hebbian skill embedding → trigger pulled toward the task")
        print("    4. Counterfactual REM      → alt skill for the failing one")
        print("    5. Schema formation        → meta-skill above the fs cluster")
        print("    6. Self-suggested practice → prompts written for skill_e")
        print()
        print("  The user (you) has a third channel into the same fitness")
        print("  posterior: 👍/👎 buttons in the chat dashboard.")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
