"""Procedural compilation — distil successful skill traces into deterministic macros.

The cognitive analogue: declarative-to-procedural transition (Anderson 1982,
Logan 1988 instance theory). When a motor pattern is repeated enough times
with success, it migrates from "deliberate reasoning" to "automatic execution".

Concretely: when a skill has been applied successfully many times, we ask the
DREAMER (during sleep) to extract a parameterised macro from those traces.
The macro is a list of tool-call templates with task-derived placeholders.

At wake time, when a task strongly matches a compiled skill, we EXECUTE the
macro directly — bypassing the LLM reasoning loop. This is:
  • Faster:    no model latency between steps.
  • Cheaper:   zero tokens for the execution.
  • Stronger:  the more a skill is used, the more it converges to a stable
               procedure rather than degrading.

Failure modes are handled by fallback: if any step in the macro errors, we
abort the macro and let the regular LLM ReAct loop take over — the failure
also counts against the skill's fitness so a broken macro will eventually be
revised or retired.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .config import CONFIG
from .episode import Episode
from .observability import emit, get_log

log = get_log()


# --- Data structures -------------------------------------------------------


@dataclass
class MacroStep:
    """One tool call in a compiled macro.

    Args dict may contain placeholder strings of the form `{{TASK}}` or
    `{{LAST_OBSERVATION}}`; these are substituted at execution time.
    """
    tool: str
    args: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"tool": self.tool, "args": self.args}

    @classmethod
    def from_dict(cls, d: dict) -> MacroStep:
        return cls(tool=str(d.get("tool", "")), args=dict(d.get("args") or {}))


@dataclass
class CompiledMacro:
    """A skill's distilled execution pattern."""
    skill_id: str
    steps: list[MacroStep] = field(default_factory=list)
    derived_from_episodes: list[str] = field(default_factory=list)
    confidence: float = 0.0  # how likely the macro generalises

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "steps": [s.to_dict() for s in self.steps],
            "derived_from_episodes": list(self.derived_from_episodes),
            "confidence": float(self.confidence),
        }

    @classmethod
    def from_dict(cls, d: dict) -> CompiledMacro:
        return cls(
            skill_id=str(d.get("skill_id", "")),
            steps=[MacroStep.from_dict(s) for s in (d.get("steps") or [])],
            derived_from_episodes=list(d.get("derived_from_episodes") or []),
            confidence=float(d.get("confidence", 0.0)),
        )


# --- Macro extraction (LLM-driven, runs during sleep) ----------------------


COMPILER_SYSTEM = """You are HippoAgent's COMPILER — a procedural distillation expert.

You receive several SUCCESSFUL trajectories that all applied the same skill.
Your job: extract a single PARAMETERISED MACRO — a deterministic sequence of
tool calls that implements the skill, with placeholders for the parts that
depend on the specific task.

Placeholders you may use INSIDE string arguments:
  • {{TASK}}              — the full task text
  • {{LAST_OBSERVATION}}  — the previous step's observation (string)

Output strict JSON only, no markdown fences:
{
  "steps": [
    {"tool": "<tool_name>", "args": {"<arg_name>": "<value or placeholder>"}},
    ...
  ],
  "confidence": 0.0..1.0,
  "rationale": "<one sentence on what generalises>"
}

Rules:
  • The macro must end with `submit_solution`.
  • Be conservative: if the trajectories diverge, lower confidence.
  • Prefer fewer steps. Do NOT include exploration/dead-end steps."""


COMPILER_USER_TEMPLATE = """## SKILL
Name: {name}
Trigger: {trigger}
Body: {body}

## SUCCESSFUL TRAJECTORIES (n={n})
{trajectories}

Distil ONE parameterised macro that captures what is invariant across them."""


def _extract_json(text: str) -> dict | None:
    """Extract a JSON OBJECT from a possibly-wrapped LLM response.

    Thin alias for the shared `jsonutil.extract_json_object` helper —
    kept here for backward-compat with existing imports. New callers
    should import from `engram.jsonutil` directly.
    """
    from .jsonutil import extract_json_object
    return extract_json_object(text)


def trajectories_to_prompt(episodes: list[Episode], cap: int = 5) -> str:
    """Render ≤cap successful episodes as compact trajectories for the compiler."""
    blocks: list[str] = []
    for i, ep in enumerate(episodes[:cap]):
        steps_str: list[str] = []
        for t in ep.traces:
            args_excerpt = t.action_input[:200].replace("\n", " ")
            steps_str.append(f"  {t.step}. {t.action}({args_excerpt})")
        blocks.append(
            f"### Trajectory {i+1}\n"
            f"TASK: {ep.task_text[:200]}\n"
            f"STEPS:\n" + "\n".join(steps_str) + "\n"
            f"FINAL_ANSWER: {ep.final_answer[:200]}"
        )
    return "\n\n".join(blocks)


def compile_macro(
    skill: Any,  # Skill — circular import; duck-typed
    successful_episodes: list[Episode],
    llm: Any,
) -> CompiledMacro | None:
    """Ask the LLM to distil a parameterised macro from successful trajectories.

    Returns None if extraction fails or the LLM output is invalid.
    """
    if len(successful_episodes) < CONFIG.compile_min_successes:
        return None
    from .llm import resolve_model  # local import — avoid cycle at import time

    prompt = COMPILER_USER_TEMPLATE.format(
        name=skill.name,
        trigger=skill.trigger,
        body=skill.body,
        n=len(successful_episodes),
        trajectories=trajectories_to_prompt(successful_episodes),
    )
    try:
        resp = llm.complete(
            system=COMPILER_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            model=resolve_model("dreamer"),
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("compile_llm_failed", skill_id=skill.id, error=str(exc))
        return None

    data = _extract_json(resp.text)
    if not data or not isinstance(data.get("steps"), list):
        log.warning("compile_invalid_json", skill_id=skill.id, raw=resp.text[:200])
        return None

    raw_steps = data["steps"]
    if not raw_steps:
        return None

    # The macro must terminate with submit_solution; otherwise it can never
    # close the wake loop.
    last = raw_steps[-1] if raw_steps else {}
    if str(last.get("tool", "")) != "submit_solution":
        log.warning("compile_no_terminator", skill_id=skill.id)
        return None

    macro = CompiledMacro(
        skill_id=skill.id,
        steps=[MacroStep.from_dict(s) for s in raw_steps],
        derived_from_episodes=[ep.id for ep in successful_episodes],
        confidence=float(data.get("confidence", 0.5)),
    )
    emit("macro_compiled", skill_id=skill.id, n_steps=len(macro.steps),
         confidence=macro.confidence)
    return macro


# --- Macro execution (zero-LLM, runs at wake time) -------------------------


_PLACEHOLDER_RE = re.compile(r"\{\{\s*([A-Z_]+)\s*\}\}")


def _substitute(value: Any, ctx: dict[str, str]) -> Any:
    """Recursively substitute placeholders in str / dict / list values."""
    if isinstance(value, str):
        def repl(m: re.Match) -> str:
            return ctx.get(m.group(1), m.group(0))
        return _PLACEHOLDER_RE.sub(repl, value)
    if isinstance(value, dict):
        return {k: _substitute(v, ctx) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute(v, ctx) for v in value]
    return value


@dataclass
class MacroRunResult:
    ok: bool
    final_answer: str = ""
    traces: list[dict[str, Any]] = field(default_factory=list)
    aborted_at_step: int | None = None
    reason: str = ""


def execute_macro(
    macro: CompiledMacro,
    task_text: str,
    tools: dict[str, Any],
) -> MacroRunResult:
    """Execute a compiled macro deterministically — no LLM calls.

    The placeholder context is built progressively: TASK is fixed, LAST_OBSERVATION
    is updated after each successful step.
    """
    ctx: dict[str, str] = {"TASK": task_text, "LAST_OBSERVATION": ""}
    traces: list[dict[str, Any]] = []
    final_answer = ""

    for i, step in enumerate(macro.steps, start=1):
        spec = tools.get(step.tool)
        if spec is None:
            return MacroRunResult(
                ok=False, traces=traces, aborted_at_step=i,
                reason=f"unknown tool: {step.tool}",
            )
        args = _substitute(step.args, ctx)
        if not isinstance(args, dict):
            return MacroRunResult(
                ok=False, traces=traces, aborted_at_step=i,
                reason="args did not resolve to a dict",
            )
        try:
            result = spec.handler(**args)
        except TypeError as exc:
            return MacroRunResult(
                ok=False, traces=traces, aborted_at_step=i,
                reason=f"bad args for {step.tool}: {exc}",
            )
        except Exception as exc:  # noqa: BLE001
            return MacroRunResult(
                ok=False, traces=traces, aborted_at_step=i,
                reason=f"tool error in {step.tool}: {exc}",
            )

        # ToolResult-like ducktyping
        ok_attr = getattr(result, "ok", True)
        out_attr = getattr(result, "output", str(result))
        observation = getattr(result, "to_observation", lambda out=out_attr: str(out))()

        traces.append({
            "step": i,
            "tool": step.tool,
            "args": args,
            "observation": observation,
            "ok": bool(ok_attr),
        })

        if not ok_attr:
            return MacroRunResult(
                ok=False, traces=traces, aborted_at_step=i,
                reason=f"step {i} ({step.tool}) returned not-ok",
            )

        # smart_truncate preserves tail too — handy when an observation
        # ends with a result the next step depends on (final number,
        # filename, error code).
        from .trunc import smart_truncate
        ctx["LAST_OBSERVATION"] = smart_truncate(str(observation), 2000)

        if step.tool == "submit_solution":
            final_answer = str(args.get("answer", out_attr))
            return MacroRunResult(ok=True, final_answer=final_answer, traces=traces)

    # Macro ended without submit_solution — should have been caught at compile time
    return MacroRunResult(
        ok=False, traces=traces,
        reason="macro completed without submit_solution",
    )
