"""Cycle #143 (2026-05-18 sera) — codebase pattern ingest.

Aurelio direttiva (vision expansion): HippoAgent deve essere infallibile
su qualsiasi task. Cycle 142 ha aperto la copertura coding lato failure
(capture/recall errori). Cycle 143 chiude il lato learning: scansiona un
repo Python human-written, estrae pattern via AST, persiste come Fact
con verified_by 'file:<path>:<line>' così future task recall possa
proporre pattern già provati.

Phase 1 categories:
    • error-handling — try/except handlers (which exception, what action)
    • api            — function with docstring
    • types          — class with docstring

API:
    extract_patterns_from_file(path) -> list[dict]
        Each dict: {proposition, topic, verified_by, category, line}.

    ingest_codebase(repo_root, *, sm, max_files=1000, skip_dirs=(...),
                    dry_run=False) -> dict
        Returns {files_parsed, patterns_extracted, patterns_persisted,
                 errors_skipped, duration_ms}.

Idempotency:
    Re-ingesting the same repo persists 0 new facts. The dedup key is
    ``(topic, verified_by)`` — same source file:line for the same
    category produces the same key. A naive string equality on the
    proposition would mis-merge two patterns that happen to share text;
    the file:line ref is the authoritative anchor.
"""
from __future__ import annotations

import ast
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .semantic import SemanticMemory

# Default ignore set — common Python project chaff. Operators can extend
# via the ``skip_dirs`` kwarg of ``ingest_codebase``.
_DEFAULT_SKIP_DIRS: tuple[str, ...] = (
    ".git", "__pycache__", ".venv", "venv", "env",
    "node_modules", ".tox", ".mypy_cache", ".pytest_cache",
    "build", "dist", ".eggs",
)


# ======================================================================
# AST extraction
# ======================================================================
def _extract_try_except(
    tree: ast.AST, repo_name: str, file_ref: str,
) -> list[dict]:
    """Each ``except XxxError`` handler becomes one fact."""
    out: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        for handler in node.handlers:
            # Resolve the exception name(s) caught.
            exc_name = "Exception"
            if handler.type is not None:
                exc_name = ast.unparse(handler.type)
            # Tiny description of what the handler does (first stmt).
            first = handler.body[0] if handler.body else None
            action = (
                "pass" if isinstance(first, ast.Pass)
                else "return" if isinstance(first, ast.Return)
                else "raise" if isinstance(first, ast.Raise)
                else "log+continue" if first is not None
                else "skip"
            )
            proposition = (
                f"This codebase handles {exc_name} by {action} "
                f"at the call site."
            )
            out.append({
                "proposition": proposition,
                "topic": f"pattern/{repo_name}/error-handling",
                "verified_by": [f"{file_ref}:{handler.lineno}"],
                "category": "error-handling",
                "line": handler.lineno,
            })
    return out


def _extract_function_docstrings(
    tree: ast.AST, repo_name: str, file_ref: str,
) -> list[dict]:
    """Functions with docstrings become api facts."""
    out: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        doc = ast.get_docstring(node)
        if not doc:
            continue
        # Trim multi-line docs to the first line for the fact body.
        first_line = doc.strip().splitlines()[0][:200]
        proposition = f"Function {node.name}(...) — {first_line}"
        out.append({
            "proposition": proposition,
            "topic": f"pattern/{repo_name}/api",
            "verified_by": [f"{file_ref}:{node.lineno}"],
            "category": "api",
            "line": node.lineno,
        })
    return out


def _extract_class_docstrings(
    tree: ast.AST, repo_name: str, file_ref: str,
) -> list[dict]:
    """Classes with docstrings become types facts."""
    out: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        doc = ast.get_docstring(node)
        if not doc:
            continue
        first_line = doc.strip().splitlines()[0][:200]
        proposition = f"Class {node.name} — {first_line}"
        out.append({
            "proposition": proposition,
            "topic": f"pattern/{repo_name}/types",
            "verified_by": [f"{file_ref}:{node.lineno}"],
            "category": "types",
            "line": node.lineno,
        })
    return out


def extract_patterns_from_file(
    path: Path, *, repo_name: str = "", file_ref: str = "",
) -> list[dict]:
    """Parse one Python file and return a list of pattern fact dicts.

    Returns ``[]`` on syntax error / decode error rather than raising —
    a malformed source must not crash the ingest of a large repo.
    """
    try:
        src = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        tree = ast.parse(src, filename=str(path))
    except SyntaxError:
        return []

    name = repo_name or path.parent.name or "repo"
    ref = file_ref or f"file:{path.as_posix()}"
    patterns: list[dict] = []
    patterns.extend(_extract_try_except(tree, name, ref))
    patterns.extend(_extract_function_docstrings(tree, name, ref))
    patterns.extend(_extract_class_docstrings(tree, name, ref))
    return patterns


# ======================================================================
# Walk + persist
# ======================================================================
def _iter_python_files(
    repo_root: Path, *,
    skip_dirs: tuple[str, ...],
    max_files: int,
) -> list[Path]:
    """Walk ``repo_root`` and return up to ``max_files`` .py files,
    skipping any path with a segment in ``skip_dirs``.
    """
    skip_set = set(skip_dirs)
    found: list[Path] = []
    for p in repo_root.rglob("*.py"):
        if any(part in skip_set for part in p.parts):
            continue
        found.append(p)
        if len(found) >= max_files:
            break
    return found


def _verified_by_key(verified_by: list[str]) -> str:
    """Single canonical string for the (topic, verified_by) dedup probe."""
    return ",".join(sorted(verified_by))


def _already_persisted(
    sm: SemanticMemory, topic: str, vb_key: str,
) -> bool:
    """Check whether a fact with this topic + verified_by ref already lives
    in semantic memory. Used as the idempotency probe.
    """
    with sm._connect() as conn:  # noqa: SLF001 — internal probe
        rows = conn.execute(
            "SELECT verified_by FROM facts "
            "WHERE topic = ? AND superseded_by IS NULL",
            (topic,),
        ).fetchall()
    for r in rows:
        raw = r["verified_by"] if hasattr(r, "keys") else r[0]
        if not raw:
            continue
        # ``verified_by`` is stored as a JSON list string. Compare
        # canonicalised forms.
        try:
            import json as _json
            existing = _json.loads(raw)
            if isinstance(existing, list):
                if _verified_by_key([str(x) for x in existing]) == vb_key:
                    return True
        except Exception:  # noqa: BLE001 — corrupt row, just keep going
            continue
    return False


def ingest_codebase(
    repo_root: Path,
    *,
    sm: SemanticMemory,
    max_files: int = 1000,
    skip_dirs: tuple[str, ...] = _DEFAULT_SKIP_DIRS,
    dry_run: bool = False,
) -> dict:
    """Walk ``repo_root``, AST-parse every .py up to ``max_files``,
    persist non-duplicate pattern facts to ``sm``.

    Returns a summary dict with:
      • files_parsed (int)
      • patterns_extracted (int)
      • patterns_persisted (int) — always 0 when ``dry_run=True``
      • errors_skipped (int) — files that failed parse / decode
      • duration_ms (float)
    """
    from .semantic import Fact  # local — avoids circular import at import time

    t0 = time.perf_counter()
    repo_name = repo_root.name or "repo"
    files = _iter_python_files(
        repo_root, skip_dirs=skip_dirs, max_files=max_files,
    )

    files_parsed = 0
    patterns_extracted = 0
    patterns_persisted = 0
    errors_skipped = 0

    for path in files:
        rel = path.relative_to(repo_root).as_posix()
        file_ref = f"file:{rel}"
        try:
            patterns = extract_patterns_from_file(
                path, repo_name=repo_name, file_ref=file_ref,
            )
        except Exception:  # noqa: BLE001 — defensive: never crash on one file
            errors_skipped += 1
            continue
        files_parsed += 1
        patterns_extracted += len(patterns)
        if dry_run:
            continue
        for p in patterns:
            vb_key = _verified_by_key(p["verified_by"])
            if _already_persisted(sm, p["topic"], vb_key):
                continue
            fact = Fact(
                proposition=p["proposition"],
                topic=p["topic"],
                confidence=0.7,  # mid-trust: AST-derived, not verified by run.
                verified_by=list(p["verified_by"]),
                status="model_claim",
            )
            sm.store(fact)
            patterns_persisted += 1

    return {
        "files_parsed": files_parsed,
        "patterns_extracted": patterns_extracted,
        "patterns_persisted": patterns_persisted,
        "errors_skipped": errors_skipped,
        "duration_ms": (time.perf_counter() - t0) * 1000.0,
    }
