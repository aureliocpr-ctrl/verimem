"""Manual demo: see the divergence block in a real prompt.

Run:
    python scripts/demo_trace_alignment.py

What it does:
  1. Builds an in-memory pair of episodes — one successful, one failed —
     that used the same skill on a similar task.
  2. Calls the trace_alignment module exactly as wake.py does.
  3. Prints the divergence block that would be injected into the prompt.

This is intentionally minimal: no LLM, no SQLite, no agent loop. It exists
only to let me read with my own eyes what the model would see, instead of
trusting that 'it should work'.
"""
from __future__ import annotations

from engram.episode import Episode, Trace
from engram.trace_alignment import (
    align_traces,
    find_divergence_point,
    format_divergence,
)


def _trace(step: int, action: str, action_input: str, observation: str) -> Trace:
    return Trace(
        step=step, thought=f"step {step}",
        action=action, action_input=action_input,
        observation=observation,
    )


SUCCESS = Episode(
    id="ep_success",
    task_id="bugfix-add",
    task_text="Fix calculator.py: the add function returns a - b but should return a + b.",
    outcome="success",
    final_answer="patched calc.py: changed return a - b -> return a + b",
    skills_used=["sk_bugfix_arith"],
    traces=[
        _trace(1, "fs_read_file", "calc.py",
               "def add(a, b):\n    return a - b   # bug: should be plus"),
        _trace(2, "apply_edit",
               'SEARCH: return a - b\nREPLACE: return a + b',
               "edit applied successfully (1 hunk)"),
        _trace(3, "run_python", "from calc import add; print(add(2,3))",
               "5"),
        _trace(4, "submit_solution", "fixed",
               "submitted: changed sign in add()"),
    ],
)


FAILURE = Episode(
    id="ep_failure",
    task_id="bugfix-add",
    task_text="Fix calculator.py: add returns a - b instead of a + b.",
    outcome="failure",
    critique="rewrote the whole file blindly instead of patching the one line",
    skills_used=["sk_bugfix_arith"],
    traces=[
        _trace(1, "fs_read_file", "calc.py",
               "def add(a, b):\n    return a - b   # bug: should be plus"),
        # divergence: failure overwrote the file instead of editing the line
        _trace(2, "fs_write_file",
               'calc.py | def add(a, b):\\n    return a + b',
               "edit applied successfully (file rewritten)"),
        _trace(3, "run_python", "from calc import add; print(add(2,3))",
               "ImportError: cannot import name 'add' from 'calc' (file truncated)"),
        _trace(4, "submit_solution", "tried",
               "submitted: rewrote calc.py"),
    ],
)


def main() -> None:
    a = align_traces(FAILURE, SUCCESS)

    print("=" * 70)
    print("ALIGNMENT (failure vs success):")
    print("=" * 70)
    for i, p in enumerate(a.pairs, start=1):
        f_str = (
            f"step {p.fail.step:>2} action={p.fail.action!r}" if p.fail
            else "                 (skip)"
        )
        s_str = (
            f"step {p.success.step:>2} action={p.success.action!r}" if p.success
            else "                 (skip)"
        )
        marker = "  =" if p.action_match else "  X"
        sim = "      "
        if p.obs_similarity > float("-inf"):
            sim = f"{p.obs_similarity:+.2f}"
        print(f"{i:>2} | {sim} {marker} | F: {f_str:<48} | S: {s_str}")

    print()
    print("=" * 70)
    print("DIVERGENCE POINT")
    print("=" * 70)
    div = find_divergence_point(a)
    if div is None:
        print("(no actionable divergence)")
    else:
        print(div.rationale)
        print()
        print("WHAT WAKE.PY WOULD INJECT INTO THE PROMPT:")
        print("-" * 70)
        print(format_divergence(div, a))


if __name__ == "__main__":
    main()
