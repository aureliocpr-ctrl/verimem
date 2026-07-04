"""Cycle #49 — TDD tests for scripts/audit/silent_failures.py.

Each test plants a known-buggy fixture and verifies that the relevant
detector layer catches it. Also tests that clean fixtures don't trip
false positives.

The 4 layers correspond to the 4 silent-failure patterns identified
in cycles #43, #23, #45, #46b respectively.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "audit"))

import silent_failures as sf  # noqa: E402

# ---------------------------------------------------------------------------
# Layer 1: PYTHON-NAME
# ---------------------------------------------------------------------------


def test_layer1_clean_module(tmp_path: Path) -> None:
    f = tmp_path / "clean.py"
    f.write_text("def foo():\n    return bar()\ndef bar():\n    return 1\n")
    assert sf.check_python_name([f]) == []


def test_layer1_catches_undefined_call(tmp_path: Path) -> None:
    f = tmp_path / "buggy.py"
    f.write_text("def foo():\n    return _undefined_func()\n")
    findings = sf.check_python_name([f])
    assert len(findings) == 1
    assert "_undefined_func" in findings[0]


def test_layer1_closure_is_not_false_positive(tmp_path: Path) -> None:
    """A nested-def closure should be visible to its caller."""
    f = tmp_path / "closure.py"
    f.write_text(
        "def outer():\n"
        "    def inner():\n"
        "        return 1\n"
        "    return inner()\n"
    )
    assert sf.check_python_name([f]) == []


def test_layer1_for_loop_var_is_not_false_positive(tmp_path: Path) -> None:
    """`for fn in subs: fn(x)` must not flag `fn` as undefined."""
    f = tmp_path / "forloop.py"
    f.write_text(
        "def emit(subs, evt):\n"
        "    for fn in subs:\n"
        "        fn(evt)\n"
    )
    assert sf.check_python_name([f]) == []


def test_layer1_except_var_is_not_false_positive(tmp_path: Path) -> None:
    """`except Exception as e: log(e)` must not flag `e` as undefined."""
    f = tmp_path / "exc.py"
    f.write_text(
        "def log(msg): return msg\n"
        "def safe():\n"
        "    try:\n"
        "        1/0\n"
        "    except Exception as e:\n"
        "        log(e)\n"
    )
    assert sf.check_python_name([f]) == []


# ---------------------------------------------------------------------------
# Layer 2: DISPATCH-DRIFT
# ---------------------------------------------------------------------------


def test_layer2_clean_dispatch(tmp_path: Path) -> None:
    f = tmp_path / "mcp_server.py"
    f.write_text(
        'def list_tools():\n'
        '    return [Tool(name="foo"), Tool(name="bar")]\n'
        'def call_tool(name, arguments):\n'
        '    if name == "foo":\n'
        '        return 1\n'
        '    if name == "bar":\n'
        '        return 2\n'
    )
    assert sf.check_dispatch_drift([f]) == []


def test_layer2_catches_registered_not_dispatched(tmp_path: Path) -> None:
    f = tmp_path / "mcp_server.py"
    f.write_text(
        'def list_tools():\n'
        '    return [Tool(name="foo"), Tool(name="orphan_tool")]\n'
        'def call_tool(name, arguments):\n'
        '    if name == "foo":\n'
        '        return 1\n'
    )
    findings = sf.check_dispatch_drift([f])
    assert any(
        "orphan_tool" in s and "registered-not-dispatched" in s
        for s in findings
    )


def test_layer2_in_tuple_dispatch_recognised(tmp_path: Path) -> None:
    """`if name in ("a", "b"):` should count both as dispatched."""
    f = tmp_path / "mcp_server.py"
    f.write_text(
        'def list_tools():\n'
        '    return [Tool(name="a"), Tool(name="b")]\n'
        'def call_tool(name, arguments):\n'
        '    if name in ("a", "b"):\n'
        '        return 1\n'
    )
    assert sf.check_dispatch_drift([f]) == []


# ---------------------------------------------------------------------------
# Layer 3: SQL-IDEMPOTENCY
# ---------------------------------------------------------------------------


def test_layer3_clean_store_with_kwarg(tmp_path: Path) -> None:
    f = tmp_path / "store.py"
    f.write_text(
        "class Store:\n"
        "    def store(self, x, *, return_replaced: bool = False):\n"
        '        conn.execute("INSERT OR REPLACE INTO t VALUES (?)", (x,))\n'
        "        return None\n"
    )
    assert sf.check_sql_idempotency([f]) == []


def test_layer3_catches_store_missing_kwarg(tmp_path: Path) -> None:
    f = tmp_path / "store.py"
    f.write_text(
        "class Store:\n"
        "    def store(self, x):\n"
        '        conn.execute("INSERT OR REPLACE INTO t VALUES (?)", (x,))\n'
    )
    findings = sf.check_sql_idempotency([f])
    assert any("return_replaced" in s for s in findings)


def test_layer3_ignores_store_without_ior(tmp_path: Path) -> None:
    """A store() that does plain INSERT (no OR REPLACE) is fine."""
    f = tmp_path / "store.py"
    f.write_text(
        "class Store:\n"
        "    def store(self, x):\n"
        '        conn.execute("INSERT INTO t VALUES (?)", (x,))\n'
    )
    assert sf.check_sql_idempotency([f]) == []


# ---------------------------------------------------------------------------
# Layer 4: HASH-NONINJECTIVE
# ---------------------------------------------------------------------------


def test_layer4_clean_json_dumps(tmp_path: Path) -> None:
    f = tmp_path / "hash.py"
    f.write_text(
        "import hashlib, json\n"
        "def good_id(a, b):\n"
        "    payload = json.dumps([a, b]).encode()\n"
        '    return hashlib.sha256(payload).hexdigest()[:12]\n'
    )
    assert sf.check_hash_noninjective([f]) == []


def test_layer4_catches_fstring_separator(tmp_path: Path) -> None:
    f = tmp_path / "hash.py"
    f.write_text(
        "import hashlib\n"
        "def bad_id(a, b):\n"
        "    payload = f\"{a}|{b}\".encode()\n"
        '    return hashlib.sha256(payload).hexdigest()[:12]\n'
    )
    findings = sf.check_hash_noninjective([f])
    assert len(findings) >= 1


# ---------------------------------------------------------------------------
# Real-corpus smoke test
# ---------------------------------------------------------------------------


def test_full_corpus_is_clean() -> None:
    """The CURRENT engram/ codebase must have zero findings.

    If this test fails, a new instance of the silent-failure family
    just crept in — investigate and either fix the code or update the
    detector if it's a legitimate pattern this layer should permit.
    """
    engram = ROOT / "engram"
    py_files = sf._gather_py(engram)
    for layer, (name, fn) in sf._CHECKS.items():
        findings = fn(py_files)
        assert findings == [], (
            f"Layer {layer} ({name}) reported findings on main:\n"
            + "\n".join(f"  - {f}" for f in findings)
        )
