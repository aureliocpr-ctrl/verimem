"""Tests for sandboxed tools."""
from __future__ import annotations

from verimem.tools import CodeAnalyzer, PythonExecutor


def test_python_exec_ok():
    py = PythonExecutor()
    res = py.run("print(2+2)")
    assert res.ok
    assert res.output.strip() == "4"


def test_python_exec_runtime_error():
    py = PythonExecutor()
    res = py.run("raise ValueError('boom')")
    assert not res.ok
    assert "ValueError" in res.error or "ValueError" in res.output


def test_python_exec_timeout():
    py = PythonExecutor(timeout_s=0.5)
    res = py.run("import time; time.sleep(5)")
    assert not res.ok
    assert "Timeout" in res.error


def test_syntax_check():
    res = CodeAnalyzer.syntax_check("def f(x): return x*2")
    assert res.ok
    bad = CodeAnalyzer.syntax_check("def f(x: return")
    assert not bad.ok


def test_find_function():
    code = "def add(a, b):\n    return a+b\n"
    res = CodeAnalyzer.find_function(code, "add")
    assert res.ok
    assert res.extra and res.extra["args"] == ["a", "b"]
    miss = CodeAnalyzer.find_function(code, "subtract")
    assert not miss.ok


def test_run_with_tests():
    py = PythonExecutor()
    src = "def square(x): return x*x"
    tests = "assert square(3) == 9\nassert square(0) == 0\nprint('PASS')\n"
    res = py.run_with_tests(src, tests)
    assert res.ok
    assert "PASS" in res.output
