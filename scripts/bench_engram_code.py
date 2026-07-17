"""Engram Code benchmark — hard validation across diverse tasks.

For each task we:
  1. seed an isolated workspace with input files;
  2. run a real LLM session via EngramCode.submit();
  3. apply emitted SEARCH/REPLACE blocks (Confirm auto-yes);
  4. validate HARD — file hash changed, syntax compiles, tests pass, etc.

We run with a free provider by default (Groq Llama-3.3-70B). Override
via env vars:
    HIPPO_LLM_PROVIDER=groq HIPPO_MODEL_EXECUTOR=llama-3.3-70b-versatile

Output: a single Markdown table at the end + a JSON summary file.
"""
from __future__ import annotations

import hashlib
import json
import os
import runpy
import subprocess
import sys
import tempfile
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import patch

from verimem.agent import HippoAgent
from verimem.code import EngramCode
from verimem.tools_extra import all_tools

# ---------------------------------------------------------------- Validators


def hash_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.exists() else "MISSING"


def py_compile_ok(p: Path) -> tuple[bool, str]:
    if not p.exists():
        return False, "file does not exist"
    try:
        compile(p.read_text(encoding="utf-8"), str(p), "exec")
        return True, ""
    except SyntaxError as err:
        return False, f"SyntaxError: {err}"


def import_module(p: Path) -> dict:
    """Load a Python file and return its global namespace via runpy."""
    return runpy.run_path(str(p))


def run_pytest(workspace: Path, target: str = "") -> tuple[bool, str]:
    cmd = [sys.executable, "-m", "pytest", "-q", "--tb=short"]
    if target:
        cmd.append(target)
    try:
        r = subprocess.run(cmd, cwd=str(workspace), capture_output=True,
                            timeout=60)
    except subprocess.TimeoutExpired:
        return False, "pytest timed out"
    out = (r.stdout + r.stderr).decode("utf-8", errors="replace")
    return r.returncode == 0, out[-400:]


# ---------------------------------------------------------------- Task spec


@dataclass
class TaskSpec:
    name: str
    seed: dict[str, str]
    prompt: str
    validate: Callable[[Path], tuple[bool, str]]


@dataclass
class TaskResult:
    name: str
    ok: bool
    reason: str
    elapsed_s: float
    steps: int
    tokens: int
    files_changed: list[str] = field(default_factory=list)


# ---------------------------------------------------------------- Validators per-task


def _v_calculator(ws: Path) -> tuple[bool, str]:
    p = ws / "calculator.py"
    if not p.exists(): return False, "calculator.py missing"
    txt = p.read_text(encoding="utf-8")
    if "return a - b" in txt: return False, "buggy line still present"
    if "return a + b" not in txt: return False, "fixed line absent"
    ok, why = py_compile_ok(p)
    if not ok: return False, why
    return True, "ok"


def _v_factorial(ws: Path) -> tuple[bool, str]:
    p = ws / "math_utils.py"
    if not p.exists(): return False, "math_utils.py missing"
    ok, why = py_compile_ok(p)
    if not ok: return False, why
    try:
        ns = import_module(p)
    except Exception as err:
        return False, f"import failed: {err}"
    fac = ns.get("factorial")
    if fac is None: return False, "factorial() not defined"
    try:
        if fac(0) != 1: return False, f"factorial(0) = {fac(0)}, expected 1"
        if fac(5) != 120: return False, f"factorial(5) = {fac(5)}, expected 120"
        if fac(1) != 1: return False, f"factorial(1) = {fac(1)}, expected 1"
    except Exception as err:
        return False, f"factorial raised: {err}"
    return True, "ok"


def _v_new_module(ws: Path) -> tuple[bool, str]:
    p = ws / "stringutils.py"
    if not p.exists(): return False, "stringutils.py was not created"
    ok, why = py_compile_ok(p)
    if not ok: return False, why
    try:
        ns = import_module(p)
    except Exception as err:
        return False, f"import failed: {err}"
    rev = ns.get("reverse_words")
    if rev is None: return False, "reverse_words() not defined"
    try:
        if rev("hello world") != "world hello":
            return False, f"reverse_words('hello world') = {rev('hello world')!r}"
        if rev("a") != "a":
            return False, f"reverse_words('a') = {rev('a')!r}"
        if rev("") != "":
            return False, f"reverse_words('') = {rev('')!r}"
    except Exception as err:
        return False, f"reverse_words raised: {err}"
    return True, "ok"


def _v_pytest_pass(ws: Path) -> tuple[bool, str]:
    test_file = ws / "test_priority.py"
    if not test_file.exists():
        return False, "test_priority.py was not created"
    ok, out = run_pytest(ws, "test_priority.py")
    return ok, out


def _v_refactor(ws: Path) -> tuple[bool, str]:
    a = (ws / "module_a.py").read_text(encoding="utf-8") if (ws / "module_a.py").exists() else ""
    b = (ws / "module_b.py").read_text(encoding="utf-8") if (ws / "module_b.py").exists() else ""
    t = (ws / "test_refactor.py").read_text(encoding="utf-8") if (ws / "test_refactor.py").exists() else ""
    if "def foo" in a:
        return False, "module_a.py still defines foo()"
    if "def bar" not in a:
        return False, "module_a.py does not define bar()"
    if "foo(" in b or "foo(" in t:
        return False, "callers still use foo()"
    if "bar(" not in b or "bar(" not in t:
        return False, "callers don't call bar()"
    return run_pytest(ws, "test_refactor.py")


# ---------------------------------------------------------------- The tasks


TASKS: list[TaskSpec] = [
    TaskSpec(
        name="1-bugfix",
        seed={"calculator.py":
              '"""Toy calc."""\n\n'
              'def add(a, b):\n'
              '    return a - b   # bug: should be +\n'
              '\n'
              'def multiply(a, b):\n'
              '    return a * b\n'},
        prompt=(
            "There is a bug in calculator.py — the add() function returns "
            "a - b instead of a + b. Fix it using a SEARCH/REPLACE block. "
            "Don't run anything; just emit the edit."
        ),
        validate=_v_calculator,
    ),
    TaskSpec(
        name="2-add-feature",
        seed={"math_utils.py":
              '"""Math helpers."""\n\n'
              'def square(x):\n'
              '    return x * x\n'},
        prompt=(
            "Add a function `factorial(n)` to math_utils.py that returns n! "
            "with factorial(0) == 1 and factorial(1) == 1. Implementation can "
            "be iterative or recursive. Use a SEARCH/REPLACE block. Don't run "
            "the file. Don't add tests. Just add the function."
        ),
        validate=_v_factorial,
    ),
    TaskSpec(
        name="3-new-module",
        seed={"README.md": "# project\n\nstringutils module is missing.\n"},
        prompt=(
            "Create a new file `stringutils.py` containing a function "
            "`reverse_words(s: str) -> str` that returns the words of s in "
            "reverse order, separated by single spaces. "
            "reverse_words('hello world') must return 'world hello'. "
            "reverse_words('') must return ''. "
            "Use a SEARCH/REPLACE block with empty SEARCH to create the new file."
        ),
        validate=_v_new_module,
    ),
    TaskSpec(
        name="4-write-tests",
        seed={"priority.py":
              '"""A simple priority queue."""\n'
              'import heapq\n\n'
              'class PriorityQueue:\n'
              '    def __init__(self):\n'
              '        self._h = []\n'
              '    def push(self, item, priority):\n'
              '        heapq.heappush(self._h, (priority, item))\n'
              '    def pop(self):\n'
              '        if not self._h:\n'
              '            raise IndexError("empty")\n'
              '        return heapq.heappop(self._h)[1]\n'
              '    def __len__(self):\n'
              '        return len(self._h)\n'},
        prompt=(
            "Write a pytest test file `test_priority.py` for the PriorityQueue "
            "class in priority.py. Cover: push+pop, ordering by priority, "
            "len(), empty pop raises IndexError. Use a SEARCH/REPLACE block "
            "with empty SEARCH to create the file. Use plain pytest, no fixtures."
        ),
        validate=_v_pytest_pass,
    ),
    TaskSpec(
        name="5-multi-file-refactor",
        seed={
            "module_a.py":
                'def foo(x):\n    return x * 2\n',
            "module_b.py":
                'from module_a import foo\n\n'
                'def double(x):\n    return foo(x)\n',
            "test_refactor.py":
                'from module_a import foo\nfrom module_b import double\n\n'
                'def test_foo(): assert foo(3) == 6\n'
                'def test_double(): assert double(4) == 8\n',
        },
        prompt=(
            "Rename the function `foo` to `bar` across the workspace. "
            "Update module_a.py (definition), module_b.py (import + call), "
            "and test_refactor.py (import + tests). After the rename, "
            "`pytest test_refactor.py` must still pass. Emit one SEARCH/REPLACE "
            "block per file."
        ),
        validate=_v_refactor,
    ),
]


# ---------------------------------------------------------------- Runner


def _run_task(spec: TaskSpec, agent: HippoAgent) -> TaskResult:
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        for rel, content in spec.seed.items():
            target = ws / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        before_hashes = {rel: hash_file(ws / rel) for rel in spec.seed}

        session = EngramCode(workspace=ws, agent=agent)

        t0 = time.perf_counter()
        try:
            with patch("verimem.code.Confirm.ask", return_value=True):
                session.submit(spec.prompt)
            elapsed = time.perf_counter() - t0
        except Exception as err:
            elapsed = time.perf_counter() - t0
            return TaskResult(
                name=spec.name, ok=False,
                reason=f"submit raised: {err}",
                elapsed_s=elapsed, steps=0, tokens=0,
            )
        finally:
            os.chdir(Path(__file__).parent.parent)

        # Compute changed files (seed paths + any new top-level files)
        changed: list[str] = []
        all_paths: set[str] = set(spec.seed)
        for p in ws.glob("*"):
            if p.is_file():
                all_paths.add(p.name)
        for rel in all_paths:
            after = hash_file(ws / rel)
            before = before_hashes.get(rel, "MISSING")
            if before != after:
                changed.append(rel)

        try:
            ok, reason = spec.validate(ws)
        except Exception as err:
            ok, reason = False, f"validator crashed: {err}\n{traceback.format_exc()[-300:]}"

        eps = agent.memory.all(limit=1)
        steps = eps[0].num_steps if eps else 0
        tokens = eps[0].tokens_used if eps else 0

        return TaskResult(
            name=spec.name, ok=ok, reason=reason,
            elapsed_s=elapsed, steps=steps, tokens=tokens,
            files_changed=changed,
        )


def main() -> int:
    print("=" * 76)
    print(f"  Engram Code BENCH"
          f"  · provider={os.environ.get('HIPPO_LLM_PROVIDER', '(auto)')}"
          f"  · model={os.environ.get('HIPPO_MODEL_EXECUTOR', '(default)')}")
    print("=" * 76)

    agent = HippoAgent.build(tools=all_tools())

    results: list[TaskResult] = []
    for spec in TASKS:
        print(f"\n┌─ TASK: {spec.name}")
        r = _run_task(spec, agent)
        results.append(r)
        status = "✅" if r.ok else "❌"
        print(f"└─ {status} {r.name}  · {r.elapsed_s:.1f}s · "
               f"{r.steps} step · {r.tokens} tok · "
               f"changed={r.files_changed} · reason: {r.reason[:120]}")

    print()
    print("=" * 76)
    print("  RESULTS")
    print("=" * 76)
    print(f"{'task':<22} {'ok':<4} {'time':>6} {'step':>5} {'tok':>7}  reason")
    print("-" * 76)
    for r in results:
        print(f"{r.name:<22} {('✅' if r.ok else '❌'):<4} {r.elapsed_s:>6.1f} "
              f"{r.steps:>5} {r.tokens:>7}  {r.reason[:40]}")
    n_ok = sum(1 for r in results if r.ok)
    print("-" * 76)
    print(f"  {n_ok}/{len(results)} passed  · "
           f"total {sum(r.elapsed_s for r in results):.1f}s · "
           f"{sum(r.tokens for r in results)} tokens")
    print("=" * 76)

    out = Path("data/reports") / "bench_engram_code.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([r.__dict__ for r in results], indent=2),
                    encoding="utf-8")
    print(f"  summary saved to {out}")

    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
