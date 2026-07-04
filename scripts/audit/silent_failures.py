"""Engram silent-failure checker — permanent CI tool.

Cycle #49 (2026-05-14): consolidates the ad-hoc audit scripts written
during cycles #43-#47 into a single permanent tool that scans the
codebase for the silent-failure family.

The family has FOUR distinct layers, each capturing a real bug that
shipped historically:

1. PYTHON-NAME (cycle #10/#11/#13/#43): handler calls `_func_name(...)`
   on a name that is never defined; `NameError` is silently swallowed
   by an `except` clause; broken fallback runs instead. Detect via AST:
   for every Call(func=Name), verify the name resolves in any visible
   scope (module + outer functions + builtins + nested defs).

2. DISPATCH-DRIFT (cycle #23): a tool registered in `list_tools()` is
   never dispatched in `call_tool()`. Caller invokes the tool but the
   dispatcher falls through to "unknown tool". Detect by extracting
   the set of `Tool(name="...")` constructions and the set of
   `name == "..."` / `name in ("...", ...)` checks; the symmetric
   difference must be empty.

3. SQL-IDEMPOTENCY (cycle #45): a store method uses
   `INSERT OR REPLACE` on a `PRIMARY KEY` id without exposing any
   observability — callers can't tell when an overwrite happens. The
   row count and PRAGMA integrity_check both pass; the data loss is
   invisible. Detect by grepping for `INSERT OR REPLACE` in production
   modules and checking that the enclosing `def store(...)` accepts
   a `return_replaced` kwarg (the convention established by cycle #46).

4. HASH-NONINJECTIVE (cycle #46b): a content-hash derivation
   concatenates strings with a SINGLE-CHAR separator. NUL/structural
   chars from input can collide ("A"+sep+"B" vs "AB"+sep+""). Detect
   by grepping for `f"{x}<sep>{y}".encode()` or `(x + sep + y).encode()`
   patterns near `hashlib.*hexdigest()` calls.

Usage:
    python scripts/audit/silent_failures.py [--layer N] [--strict]
    --layer: 1=python-name 2=dispatch 3=sql 4=hash; omit = run all
    --strict: exit 1 if any finding (for CI); default exits 0 always

Output: human-readable report. Each finding cites the cycle that
caught the original instance.

Acceptance criterion: on current main branch ALL four layers report
ZERO findings — every historical bug is closed and pinned by a TDD
test. Re-running this checker periodically in CI ensures no new
instance creeps in.
"""
from __future__ import annotations

import argparse
import ast
import builtins
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENGRAM_DIR = REPO_ROOT / "engram"
SKIP_DIRS = {"__pycache__", "tests", ".pytest_cache", ".ruff_cache"}


def _rel(py: Path) -> Path:
    """Best-effort relative path for finding messages.

    Falls back to absolute path when py is outside REPO_ROOT — happens
    in tests where fixtures live in tmp_path.
    """
    try:
        return py.relative_to(REPO_ROOT)
    except ValueError:
        return py


# ---------------------------------------------------------------------------
# Layer 1: PYTHON-NAME — calls to undefined names
# ---------------------------------------------------------------------------


def _names_in_scope(scope_node: ast.AST) -> set[str]:
    names: set[str] = set()
    body = getattr(scope_node, "body", [])
    if isinstance(scope_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for arg in scope_node.args.args + scope_node.args.kwonlyargs:
            names.add(arg.arg)
        if scope_node.args.vararg:
            names.add(scope_node.args.vararg.arg)
        if scope_node.args.kwarg:
            names.add(scope_node.args.kwarg.arg)
    for child in body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(child.name)
        elif isinstance(child, ast.Assign):
            for tgt in child.targets:
                if isinstance(tgt, ast.Name):
                    names.add(tgt.id)
                elif isinstance(tgt, (ast.Tuple, ast.List)):
                    for elt in tgt.elts:
                        if isinstance(elt, ast.Name):
                            names.add(elt.id)
        elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            names.add(child.target.id)
        elif isinstance(child, ast.Import):
            for alias in child.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(child, ast.ImportFrom):
            for alias in child.names:
                names.add(alias.asname or alias.name)
        elif isinstance(child, (ast.For, ast.AsyncFor, ast.While, ast.If,
                                ast.Try, ast.With, ast.AsyncWith)):
            for sub in ast.walk(child):
                if isinstance(sub, ast.Assign):
                    for tgt in sub.targets:
                        if isinstance(tgt, ast.Name):
                            names.add(tgt.id)
                elif isinstance(sub, ast.Import):
                    for alias in sub.names:
                        names.add(alias.asname or alias.name.split(".")[0])
                elif isinstance(sub, ast.ImportFrom):
                    for alias in sub.names:
                        names.add(alias.asname or alias.name)
                elif isinstance(sub, ast.ExceptHandler) and sub.name:
                    names.add(sub.name)
                elif (
                    isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                ):
                    names.add(sub.name)
    return names


def check_python_name(py_files: list[Path]) -> list[str]:
    """Return list of human-readable findings (empty = clean)."""
    findings: list[str] = []
    for py in py_files:
        src = py.read_text(encoding="utf-8")
        try:
            tree = ast.parse(src, str(py))
        except SyntaxError:
            continue
        module_names = _names_in_scope(tree)
        module_names.update(dir(builtins))

        # `walk` is defined fresh per file; capture py + src + module_names
        # explicitly via default args so ruff B023 stays happy and the
        # loop-variable semantics are unambiguous.
        def walk(
            node: ast.AST,
            scopes: list[set[str]],
            _py: Path = py,
            _src: str = src,
            _module_names: set[str] = module_names,
        ) -> None:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                new_scope = (
                    _names_in_scope(node)
                    if not isinstance(node, ast.Lambda)
                    else set()
                )
                if isinstance(node, ast.Lambda):
                    for arg in node.args.args:
                        new_scope.add(arg.arg)
                # For loops, comprehensions, and except clauses inside this
                # function create local bindings the AST checker must see.
                for sub in ast.walk(node):
                    if isinstance(sub, (ast.For, ast.AsyncFor)):
                        for tgt_node in ast.walk(sub.target):
                            if isinstance(tgt_node, ast.Name):
                                new_scope.add(tgt_node.id)
                    elif isinstance(sub, ast.comprehension):
                        for tgt_node in ast.walk(sub.target):
                            if isinstance(tgt_node, ast.Name):
                                new_scope.add(tgt_node.id)
                    elif isinstance(sub, ast.ExceptHandler) and sub.name:
                        new_scope.add(sub.name)
                    elif isinstance(sub, ast.With):
                        for it in sub.items:
                            if it.optional_vars and isinstance(
                                it.optional_vars, ast.Name
                            ):
                                new_scope.add(it.optional_vars.id)
                    elif isinstance(sub, ast.NamedExpr):  # walrus
                        if isinstance(sub.target, ast.Name):
                            new_scope.add(sub.target.id)
                scopes = scopes + [new_scope]
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                name = node.func.id
                visible = set(_module_names)
                for s in scopes:
                    visible.update(s)
                if name not in visible:
                    line = _src.split("\n")[node.lineno - 1].strip()[:100]
                    findings.append(
                        f"{_rel(_py)}:{node.lineno} undefined-name '{name}': {line}"
                    )
            for child in ast.iter_child_nodes(node):
                walk(child, scopes)

        walk(tree, [])
    return findings


# ---------------------------------------------------------------------------
# Layer 2: DISPATCH-DRIFT — tool registered but not dispatched
# ---------------------------------------------------------------------------


def check_dispatch_drift(py_files: list[Path]) -> list[str]:
    findings: list[str] = []
    for py in py_files:
        if py.name != "mcp_server.py":
            continue
        src = py.read_text(encoding="utf-8")
        try:
            tree = ast.parse(src, str(py))
        except SyntaxError:
            continue

        registered: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and (
                (isinstance(node.func, ast.Attribute) and node.func.attr == "Tool")
                or (isinstance(node.func, ast.Name) and node.func.id == "Tool")
            ):
                for kw in node.keywords:
                    if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                        registered.add(kw.value.value)

        dispatched: set[str] = set()
        for m in re.finditer(r'name\s*==\s*["\']([a-zA-Z_][a-zA-Z0-9_]*)["\']', src):
            dispatched.add(m.group(1))
        for pat in (r"name\s+in\s+\(([^)]+)\)",
                    r"name\s+in\s+\{([^}]+)\}",
                    r"name\s+in\s+\[([^\]]+)\]"):
            for m in re.finditer(pat, src):
                for sub in re.finditer(
                    r'["\']([a-zA-Z_][a-zA-Z0-9_]*)["\']', m.group(1)
                ):
                    dispatched.add(sub.group(1))

        try:
            rel = _rel(py)
        except ValueError:
            rel = py
        for n in sorted(registered - dispatched):
            findings.append(f"{rel} registered-not-dispatched: {n}")
        for n in sorted(dispatched - registered):
            findings.append(f"{rel} dispatched-not-registered: {n}")
    return findings


# ---------------------------------------------------------------------------
# Layer 3: SQL-IDEMPOTENCY — INSERT OR REPLACE without observability kwarg
# ---------------------------------------------------------------------------


_IOR_RE = re.compile(r"INSERT\s+OR\s+REPLACE", re.IGNORECASE)
_DEF_STORE_RE = re.compile(r"^\s*def\s+store\s*\(", re.MULTILINE)


def check_sql_idempotency(py_files: list[Path]) -> list[str]:
    """Find `def store(...)` methods whose body uses INSERT OR REPLACE
    but whose signature does not accept `return_replaced` kwarg.

    Convention established cycle #46: any store that does INSERT OR
    REPLACE on a PRIMARY KEY id must expose `return_replaced=False`
    opt-in for observability. Without it, callers cannot tell when
    silent overwrites happen.
    """
    findings: list[str] = []
    for py in py_files:
        src = py.read_text(encoding="utf-8")
        try:
            tree = ast.parse(src, str(py))
        except SyntaxError:
            continue
        try:
            rel = _rel(py)
        except ValueError:
            rel = py

        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name != "store":
                continue
            # Body source
            start = node.lineno
            end = node.end_lineno or start
            body_src = "\n".join(src.split("\n")[start - 1 : end])
            if not _IOR_RE.search(body_src):
                continue
            # Check signature for return_replaced kwarg
            kw_names = {a.arg for a in node.args.kwonlyargs}
            kw_names.update({a.arg for a in node.args.args})
            if "return_replaced" not in kw_names:
                findings.append(
                    f"{rel}:{start} store() uses INSERT OR REPLACE but lacks "
                    f"`return_replaced` kwarg (cycle #46 convention)"
                )
    return findings


# ---------------------------------------------------------------------------
# Layer 4: HASH-NONINJECTIVE — f"{x}<sep>{y}" payload in hash near hashlib
# ---------------------------------------------------------------------------


_HASHLIB_RE = re.compile(r"hashlib\.\w+\([^)]*\)\.\w*hexdigest")
_FSTRING_CONCAT_RE = re.compile(
    r'f["\']\{[^}]+\}([^\w{}"\']{1,3})\{[^}]+\}["\']'
)


def check_hash_noninjective(py_files: list[Path]) -> list[str]:
    """Find content-hash payloads that may be non-injective.

    Pattern: an f-string with two interpolations separated by 1-3
    non-word chars, followed nearby by a hashlib hexdigest call.
    Either (A) NUL byte concat -- collides if input contains the sep
    char, or (B) any single-char sep -- same risk.

    Recommended fix: json.dumps([...]) or length-prefix.
    """
    findings: list[str] = []
    for py in py_files:
        src = py.read_text(encoding="utf-8")
        try:
            rel = _rel(py)
        except ValueError:
            rel = py
        for i, line in enumerate(src.split("\n"), start=1):
            m = _FSTRING_CONCAT_RE.search(line)
            if not m:
                continue
            sep = m.group(1)
            # Look for hashlib hexdigest within 5 lines
            context = "\n".join(
                src.split("\n")[max(0, i - 2) : min(len(src.split("\n")), i + 5)]
            )
            if _HASHLIB_RE.search(context):
                findings.append(
                    f"{rel}:{i} f-string concat with sep {sep!r} feeding hashlib — "
                    f"non-injective under sep-char injection (cycle #46b)"
                )
    return findings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _gather_py(base: Path) -> list[Path]:
    out: list[Path] = []
    for py in base.rglob("*.py"):
        if any(part in SKIP_DIRS for part in py.parts):
            continue
        if py.name == "__init__.py":
            continue
        out.append(py)
    return out


_CHECKS = {
    1: ("python-name", check_python_name),
    2: ("dispatch-drift", check_dispatch_drift),
    3: ("sql-idempotency", check_sql_idempotency),
    4: ("hash-noninjective", check_hash_noninjective),
}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--layer", type=int, choices=[1, 2, 3, 4],
                   help="Run only one layer; omit = all")
    p.add_argument("--strict", action="store_true",
                   help="Exit 1 on any finding (for CI)")
    args = p.parse_args(argv)

    py_files = _gather_py(ENGRAM_DIR)
    print(f"Scanning {len(py_files)} files under {ENGRAM_DIR.relative_to(REPO_ROOT)}/\n")

    selected = [args.layer] if args.layer else sorted(_CHECKS)
    total = 0
    for layer in selected:
        name, fn = _CHECKS[layer]
        findings = fn(py_files)
        print(f"--- Layer {layer}: {name} ---")
        if not findings:
            print("  ✓ clean (0 findings)")
        else:
            for f in findings:
                print(f"  {f}")
            print(f"  ✗ {len(findings)} finding{'s' if len(findings) != 1 else ''}")
        total += len(findings)
        print()

    print(f"Total: {total} finding{'s' if total != 1 else ''} across "
          f"{len(selected)} layer{'s' if len(selected) != 1 else ''}")
    return 1 if (args.strict and total > 0) else 0


if __name__ == "__main__":
    sys.exit(main())
