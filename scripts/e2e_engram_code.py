"""LIVE end-to-end test of Engram Code with a real LLM.

Run with:
  HIPPO_MODEL_EXECUTOR=claude-opus-4-7 HIPPO_LLM_PROVIDER=anthropic \\
    python scripts/e2e_engram_code.py

The script:
  1. creates a temp workspace with a buggy Python file
  2. instantiates EngramCode with a real HippoAgent
  3. asks the agent (in plain English) to find and fix the bug
  4. auto-confirms the edit prompt and verifies the file on disk

No mocks. Counts as a passing run only if the buggy line is actually fixed.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from verimem.agent import HippoAgent
from verimem.code import EngramCode
from verimem.tools_extra import all_tools

BUGGY_FILE_NAME = "calculator.py"
BUGGY_CODE = '''"""Toy calculator with one bug for the agent to find."""

def add(a, b):
    return a - b   # bug: this should be a + b

def multiply(a, b):
    return a * b

if __name__ == "__main__":
    print("2 + 3 =", add(2, 3))
    print("4 * 5 =", multiply(4, 5))
'''


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


def main() -> int:
    if not os.environ.get("ANTHROPIC_API_KEY") and \
       os.environ.get("HIPPO_LLM_PROVIDER", "").lower() == "anthropic":
        print("ANTHROPIC_API_KEY not set — aborting (or remove the provider override)")
        return 2

    original_cwd = os.getcwd()
    try:
        return _run()
    finally:
        os.chdir(original_cwd)


def _run() -> int:
    with tempfile.TemporaryDirectory() as td:
        workspace = Path(td)
        target = workspace / BUGGY_FILE_NAME
        target.write_text(BUGGY_CODE, encoding="utf-8")

        banner("Engram Code — LIVE E2E (real LLM)")
        print(f"  workspace : {workspace}")
        print(f"  model     : {os.environ.get('HIPPO_MODEL_EXECUTOR', '(default)')}")
        print(f"  provider  : {os.environ.get('HIPPO_LLM_PROVIDER', '(auto)')}")
        print(f"\n  Initial {BUGGY_FILE_NAME}:")
        print("  " + "-" * 50)
        for line in BUGGY_CODE.splitlines():
            print("    " + line)

        banner("Instantiating EngramCode")
        agent = HippoAgent.build(tools=all_tools())
        session = EngramCode(workspace=workspace, agent=agent)

        task = (
            f"There's a bug in {BUGGY_FILE_NAME}. The `add` function returns "
            "the wrong value. Find the bug and fix it using a SEARCH/REPLACE "
            "edit block. Don't run the code — just emit the edit."
        )
        banner(f"Submitting task: {task[:60]}…")
        t0 = time.perf_counter()
        with patch("verimem.code.Confirm.ask", return_value=True):
            session.submit(task)
        elapsed = time.perf_counter() - t0

        banner("Verification")
        new = target.read_text(encoding="utf-8")
        ok_added = "return a + b" in new
        ok_removed = "return a - b" not in new
        print(f"  '+ b' present : {ok_added}")
        print(f"  '- b' removed : {ok_removed}")
        print(f"  elapsed       : {elapsed:.1f}s")
        if not (ok_added and ok_removed):
            print(f"\n  Final file content:\n{new}")
            return 1
        print("\n  ✓ Engram Code fixed the bug autonomously with a real LLM.")
        os.chdir(Path(__file__).parent.parent)
        return 0


if __name__ == "__main__":
    sys.exit(main())
