"""End-to-end demo of Engram Code's edit-apply pipeline.

Runs without API keys: a MockAgent simulates the LLM emitting a
SEARCH/REPLACE block; the demo verifies that the diff preview is shown
and the file is modified on disk after confirmation.
"""
from __future__ import annotations

import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from engram.code import EngramCode
from engram.episode import Episode, Trace


@dataclass
class _FakeWakeResult:
    episode: Episode
    success: bool
    message: str
    skills_retrieved: list


class _MockAgent:
    """Minimal HippoAgent stand-in for the demo flow."""
    class _Memory:
        def count(self): return 7
    class _Skills:
        def count(self, status=None): return 3
        def all(self): return []
    def __init__(self, scripted_answer: str) -> None:
        self.memory = self._Memory()
        self.skills = self._Skills()
        self.semantic = None
        self.wake = None
        self.sleep = None
        self._answer = scripted_answer

    def run_task(self, *, task_id, task_text, validator):
        ep = Episode(task_id=task_id, task_text=task_text,
                     outcome="success", final_answer=self._answer,
                     skills_used=[], tokens_used=420)
        ep.traces.append(Trace(
            step=1, thought="t",
            action="submit_solution",
            action_input='{"answer": "<edit blocks>"}',
            observation="ok",
        ))
        return _FakeWakeResult(episode=ep, success=True,
                               message="non-empty",
                               skills_retrieved=[])

    def consolidate(self):  # /sleep
        from engram.sleep import SleepReport
        return SleepReport()

    def reset(self): pass


def main() -> int:
    print("=" * 64)
    print("  Engram Code — end-to-end edit demo (mock LLM, no API key)")
    print("=" * 64)

    import os
    original_cwd = os.getcwd()
    try:
        return _run_demo()
    finally:
        os.chdir(original_cwd)


def _run_demo() -> int:
    import os
    with tempfile.TemporaryDirectory() as td:
        workspace = Path(td)
        # Seed workspace with a buggy file
        buggy = workspace / "calc.py"
        buggy.write_text(
            'def add(a, b):\n'
            '    return a - b   # ← bug: should be +\n'
            '\n'
            'if __name__ == "__main__":\n'
            '    print(add(2, 3))\n',
            encoding="utf-8",
        )
        print(f"\nWorkspace: {workspace}")
        print(f"Initial calc.py:\n{buggy.read_text()}")

        # Scripted agent answer with a SEARCH/REPLACE block
        scripted = """\
The function `add` returns `a - b` instead of `a + b`. Fixing:

calc.py
<<<<<<< SEARCH
    return a - b   # ← bug: should be +
=======
    return a + b   # fixed
>>>>>>> REPLACE

That's the minimal change."""

        # Auto-confirm the edit prompt
        with patch("engram.code.Confirm.ask", return_value=True):
            session = EngramCode(workspace=workspace, agent=_MockAgent(scripted))
            print("\n--- session.submit('fix the bug in calc.py') ---")
            session.submit("fix the bug in calc.py")

        print("\nFinal calc.py on disk:")
        print(buggy.read_text())

        # Verify
        new = buggy.read_text()
        assert "return a + b" in new, "edit was not applied"
        assert "return a - b" not in new, "old buggy line still present"
        print("\n✓ edit applied correctly. file modified on disk.")
        # On Windows we must release the cwd before tempdir cleanup
        os.chdir(Path(__file__).parent.parent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
