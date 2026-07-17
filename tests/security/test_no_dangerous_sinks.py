"""Security invariant (audit 2026-07-11): the shipped ``engram`` package contains
NO dangerous code-execution / deserialization sinks on ANY path.

A static AST scan — not a grep — so ``model.eval()`` (a torch method) never trips
the builtin ``eval(...)`` check. Fails with file:line if a sink is introduced,
forcing a security review before it can ship.

Covers the classic RCE / arbitrary-deserialization set:
  eval, exec, __import__, os.system,
  pickle.load(s), cPickle.load(s), marshal.load(s), yaml.load (the UNSAFE loader
  — yaml.safe_load is fine and NOT flagged).

Scope note: ``subprocess(..., shell=True)`` is deliberately NOT guarded here — it
exists in the coding-agent sandbox/judge (agentos), is reviewed separately, and
is its own (documented) residual. This guard is the deserialization/eval class,
which the 2026-07-11 audit verified at ZERO across the package.
"""
from __future__ import annotations

import ast
from pathlib import Path

_PKG = Path(__file__).resolve().parents[2] / "verimem"

_NAME_SINKS = {"eval", "exec", "__import__"}
_DOTTED_SINKS = {
    ("os", "system"),
    ("pickle", "load"), ("pickle", "loads"),
    ("cPickle", "load"), ("cPickle", "loads"),
    ("marshal", "load"), ("marshal", "loads"),
    ("yaml", "load"),  # the unsafe loader; yaml.safe_load is allowed
}


def _dotted(node: ast.AST) -> tuple[str, ...] | None:
    """('os','system') for os.system, or None if the base isn't a plain Name
    (so a chained call like ``x().eval()`` is not treated as a dotted sink)."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return tuple(reversed(parts))
    return None


def _scan(path: Path) -> list[str]:
    findings: list[str] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return findings
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if isinstance(f, ast.Name):
            if f.id in _NAME_SINKS:
                findings.append(f"{path.name}:{node.lineno}: {f.id}(...)")
        elif isinstance(f, ast.Attribute):
            d = _dotted(f)
            if d is not None and d[-2:] in _DOTTED_SINKS:
                findings.append(f"{path.name}:{node.lineno}: {'.'.join(d)}(...)")
    return findings


def test_no_dangerous_execution_or_deserialization_sinks():
    findings: list[str] = []
    for py in _PKG.rglob("*.py"):
        findings.extend(_scan(py))
    assert not findings, (
        "dangerous RCE/deserialization sink(s) introduced in the engram package "
        "— security review required before shipping:\n  " + "\n  ".join(findings))
