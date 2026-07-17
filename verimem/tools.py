"""Tools the wake-loop agent can invoke.

- PythonExecutor: runs Python in a fresh subprocess with timeout.
  Defense-in-depth: subprocess isolation + timeout + output cap.
- DockerPythonExecutor: optional ephemeral container backend.
- CodeAnalyzer: AST-based static checks (syntax, complexity, function presence).

All tools return a `ToolResult` so the loop can handle them uniformly.
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import CONFIG
from .observability import emit, get_log
from .trunc import smart_truncate

log = get_log()


@dataclass
class ToolResult:
    ok: bool
    output: str
    error: str = ""
    extra: dict[str, Any] | None = None

    def to_observation(self) -> str:
        if self.ok:
            tail = f"\n[extra: {json.dumps(self.extra)}]" if self.extra else ""
            return f"OK\n{self.output}{tail}"
        return f"ERROR\n{self.error}"


class PythonExecutor:
    """Run Python source in a subprocess with a hard timeout.

    Not a full security sandbox — assumes the model is non-adversarial.
    For research-grade isolation we'd add seccomp/Firejail/Docker; here
    we focus on correctness of the consolidation loop.
    """

    def __init__(self, timeout_s: float | None = None, max_chars: int | None = None) -> None:
        self.timeout_s = timeout_s or CONFIG.sandbox_timeout_s
        self.max_chars = max_chars or CONFIG.sandbox_max_output_chars

    def run(self, code: str, stdin: str = "") -> ToolResult:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "snippet.py"
            script.write_text(code, encoding="utf-8")
            from ._proc_quiet import quiet_popen_kwargs
            try:
                proc = subprocess.run(
                    [sys.executable, "-I", str(script)],
                    input=stdin,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_s,
                    cwd=tmp,
                    **quiet_popen_kwargs(),  # cycle #136: no win pop-up
                )
            except subprocess.TimeoutExpired:
                emit("python_exec_timeout", timeout_s=self.timeout_s)
                return ToolResult(ok=False, output="", error=f"Timeout after {self.timeout_s}s")
            # smart_truncate keeps both head AND tail of long output.
            # For Python execution this matters: tracebacks live at the
            # end of stderr, so head-only truncation can drop the very
            # error message we need.
            stdout = smart_truncate(proc.stdout or "", self.max_chars)
            stderr = smart_truncate(proc.stderr or "", self.max_chars,
                                     head_ratio=0.3)  # bias toward tail (traceback)
            ok = proc.returncode == 0
            emit("python_exec", ok=ok, returncode=proc.returncode, stdout_len=len(stdout))
            if ok:
                return ToolResult(ok=True, output=stdout, extra={"stderr": stderr} if stderr else None)
            return ToolResult(ok=False, output=stdout, error=stderr or f"exit={proc.returncode}")

    def run_with_tests(self, source_code: str, test_code: str) -> ToolResult:
        """Run candidate `source_code` then a test harness that calls into it."""
        full = source_code.rstrip() + "\n\n# ---- TEST HARNESS ----\n" + test_code
        return self.run(full)


class DockerPythonExecutor:
    """Run Python source inside an ephemeral Docker container.

    Stronger isolation than the subprocess executor:
      • --network=none      → no network egress (defeats SSRF/exfil)
      • --cap-drop=ALL      → no Linux capabilities
      • --read-only         → root FS is read-only; only the mounted /work is rw
      • --pids-limit=64     → defeats fork bombs
      • --memory=256m       → defeats memory bombs

    Falls back transparently to PythonExecutor if Docker isn't available
    or the container fails to start (caller decides via the factory).

    Image resolution:
      HIPPO_PYTHON_EXEC_IMAGE (env) → default 'python:3.12-slim'.
    """

    DEFAULT_IMAGE = "python:3.12-slim"

    def __init__(
        self,
        timeout_s: float | None = None,
        max_chars: int | None = None,
        image: str | None = None,
    ) -> None:
        self.timeout_s = timeout_s or CONFIG.sandbox_timeout_s
        self.max_chars = max_chars or CONFIG.sandbox_max_output_chars
        self.image = image or os.environ.get(
            "HIPPO_PYTHON_EXEC_IMAGE", self.DEFAULT_IMAGE,
        )
        # docker SDK is optional — only imported if backend explicitly chosen
        try:
            import docker  # type: ignore
            self._docker = docker
            self._client = docker.from_env()
            self._client.ping()
            self._available = True
        except Exception as exc:  # noqa: BLE001 — any failure means unavailable
            log.warning("docker_unavailable", error=str(exc))
            self._docker = None
            self._client = None
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def run(self, code: str, stdin: str = "") -> ToolResult:
        if not self._available:
            return ToolResult(
                ok=False, output="",
                error="docker backend unavailable (docker SDK or daemon missing)",
            )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            script = tmp_path / "snippet.py"
            script.write_text(code, encoding="utf-8")
            stdin_file: Path | None = None
            cmd = ["python", "-I", "/work/snippet.py"]
            if stdin:
                stdin_file = tmp_path / "stdin.txt"
                stdin_file.write_text(stdin, encoding="utf-8")
                cmd = ["sh", "-c",
                       "python -I /work/snippet.py < /work/stdin.txt"]
            try:
                container = self._client.containers.run(
                    image=self.image,
                    command=cmd,
                    network_mode="none",
                    cap_drop=["ALL"],
                    read_only=True,
                    mem_limit="256m",
                    pids_limit=64,
                    volumes={str(tmp_path.resolve()): {
                        "bind": "/work", "mode": "rw",
                    }},
                    working_dir="/work",
                    user="1000:1000",
                    detach=True,
                    stdout=True,
                    stderr=True,
                )
            except Exception as exc:  # noqa: BLE001
                emit("docker_exec_failed", error=str(exc))
                return ToolResult(ok=False, output="",
                                  error=f"docker run failed: {exc}")
            try:
                try:
                    res = container.wait(timeout=self.timeout_s)
                except Exception as exc:  # noqa: BLE001 — timeout
                    container.kill()
                    emit("docker_exec_timeout", timeout_s=self.timeout_s)
                    return ToolResult(
                        ok=False, output="",
                        error=f"Timeout after {self.timeout_s}s: {exc}",
                    )
                rc = res.get("StatusCode", 1) if isinstance(res, dict) else int(res)
                stdout = container.logs(stdout=True, stderr=False).decode(
                    "utf-8", errors="replace")[: self.max_chars]
                stderr = container.logs(stdout=False, stderr=True).decode(
                    "utf-8", errors="replace")[: self.max_chars]
            finally:
                try:
                    container.remove(force=True)
                except Exception:  # noqa: BLE001 — best-effort cleanup
                    pass
            ok = rc == 0
            emit("docker_exec", ok=ok, returncode=rc, stdout_len=len(stdout))
            if ok:
                return ToolResult(ok=True, output=stdout,
                                  extra={"stderr": stderr, "backend": "docker"} if stderr
                                  else {"backend": "docker"})
            return ToolResult(ok=False, output=stdout,
                              error=stderr or f"exit={rc}",
                              extra={"backend": "docker"})

    def run_with_tests(self, source_code: str, test_code: str) -> ToolResult:
        full = source_code.rstrip() + "\n\n# ---- TEST HARNESS ----\n" + test_code
        return self.run(full)


def make_python_executor(
    timeout_s: float | None = None, max_chars: int | None = None,
):
    """Factory: pick executor backend based on HIPPO_PYTHON_EXEC_BACKEND.

    backend ∈ {"subprocess" (default), "docker"}.

    If backend=docker but Docker is unavailable, transparently falls back
    to PythonExecutor and emits an observability warning. Tests covering
    this need to assert on the `extra.backend` field returned by `run()`.
    """
    backend = os.environ.get(
        "HIPPO_PYTHON_EXEC_BACKEND", "subprocess",
    ).strip().lower()
    if backend == "docker":
        ex = DockerPythonExecutor(timeout_s=timeout_s, max_chars=max_chars)
        if ex.available:
            emit("python_executor_backend", backend="docker",
                 image=ex.image)
            return ex
        emit("python_executor_backend_fallback",
             requested="docker", actual="subprocess")
    emit("python_executor_backend", backend="subprocess")
    return PythonExecutor(timeout_s=timeout_s, max_chars=max_chars)


class CodeAnalyzer:
    """Static checks via Python AST."""

    @staticmethod
    def syntax_check(code: str) -> ToolResult:
        try:
            tree = ast.parse(code)
            return ToolResult(ok=True, output="syntax ok", extra={"nodes": _ast_node_count(tree)})
        except SyntaxError as exc:
            return ToolResult(ok=False, output="", error=f"SyntaxError: {exc.msg} at line {exc.lineno}")

    @staticmethod
    def find_function(code: str, name: str) -> ToolResult:
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return ToolResult(ok=False, output="", error=f"SyntaxError: {exc}")
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                args = [a.arg for a in node.args.args]
                return ToolResult(
                    ok=True,
                    output=f"function `{name}` found",
                    extra={"args": args, "line": node.lineno},
                )
        return ToolResult(ok=False, output="", error=f"function `{name}` not found")

    @staticmethod
    def cyclomatic(code: str) -> ToolResult:
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return ToolResult(ok=False, output="", error=f"SyntaxError: {exc}")
        complexity = 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.And, ast.Or, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        return ToolResult(ok=True, output=f"complexity={complexity}", extra={"complexity": complexity})


def _ast_node_count(tree: ast.AST) -> int:
    return sum(1 for _ in ast.walk(tree))


# ---- Tool registry --------------------------------------------------------


@dataclass
class ToolSpec:
    name: str
    description: str
    schema: dict[str, Any]
    handler: Any  # callable


def default_tools() -> dict[str, ToolSpec]:
    py = make_python_executor()
    return {
        "submit_solution": ToolSpec(
            name="submit_solution",
            description=(
                "Submit your final answer / solution. Use this when you are confident "
                "the answer is correct. The orchestrator will run the validator."
            ),
            schema={
                "type": "object",
                "properties": {"answer": {"type": "string"}},
                "required": ["answer"],
            },
            handler=lambda answer: ToolResult(ok=True, output=textwrap.shorten(answer, 4000)),
        ),
        "run_python": ToolSpec(
            name="run_python",
            description=(
                "Execute Python code in a sandboxed subprocess. Returns stdout. "
                "Use to test your candidate solution before submitting."
            ),
            schema={
                "type": "object",
                "properties": {"code": {"type": "string"}, "stdin": {"type": "string"}},
                "required": ["code"],
            },
            handler=lambda code, stdin="": py.run(code, stdin),
        ),
        "syntax_check": ToolSpec(
            name="syntax_check",
            description="Parse Python code and report syntax errors without executing.",
            schema={
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
            },
            handler=lambda code: CodeAnalyzer.syntax_check(code),
        ),
        "find_function": ToolSpec(
            name="find_function",
            description="Check if a function with given name exists in the code.",
            schema={
                "type": "object",
                "properties": {"code": {"type": "string"}, "name": {"type": "string"}},
                "required": ["code", "name"],
            },
            handler=lambda code, name: CodeAnalyzer.find_function(code, name),
        ),
    }
