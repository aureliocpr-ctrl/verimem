"""Cycle #143 (2026-05-18 sera) — codebase pattern ingest.

Aurelio direttiva: HippoAgent deve essere infallibile su qualsiasi task,
inclusi coding/learning/anti-confabulazione. Cycle 142 ha aperto la
copertura coding sul lato failure (capture + recall). Cycle 143 chiude
il lato learning: scansiona un repo Python human-written, estrae
pattern via AST, persiste come fact con verified_by 'file:<path>:<line>'
così future task recall possa proporre pattern già provati.

Phase 1 scope (this PR): AST extraction of
    • try/except handlers          → pattern/<repo>/error-handling
    • def with docstring           → pattern/<repo>/api
    • class with docstring         → pattern/<repo>/types

Out of scope Phase 1 (cycle 143b o successivi):
    • cross-file dataflow / call graph
    • type inference
    • test pattern extraction
    • non-Python sources

API contract:
    extract_patterns_from_file(path) -> list[dict]
        Each dict: {proposition, topic, verified_by, category, line}.

    ingest_codebase(repo_root, *, sm, max_files=1000, skip_dirs=(...),
                    dry_run=False) -> dict
        Returns {files_parsed, patterns_extracted, patterns_persisted,
                 errors_skipped, duration_ms}.

TDD strict RED→GREEN: this file must fail on import (ModuleNotFoundError)
because engram/codebase_ingest.py does not yet exist.
"""
from __future__ import annotations

from pathlib import Path

import pytest

# RED MARKER: this import is the failure pin.
from verimem.codebase_ingest import (
    extract_patterns_from_file,
    ingest_codebase,
)
from verimem.semantic import SemanticMemory


# ---- Fixture helpers --------------------------------------------------
def _write(repo: Path, rel: str, content: str) -> Path:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture
def mini_repo(tmp_path: Path) -> Path:
    """A tiny fake repo with one file containing all phase-1 pattern kinds."""
    repo = tmp_path / "fakerepo"
    repo.mkdir()
    _write(repo, "src/sample.py", '''"""sample module."""

def parse_int(s):
    """Convert string to int with graceful fallback."""
    try:
        return int(s)
    except ValueError:
        return None


class Calculator:
    """Stateless arithmetic helper for integer ops."""

    def add(self, a, b):
        return a + b
''')
    return repo


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sem.db")


# ---- TestExtractPatterns ---------------------------------------------
class TestExtractPatterns:
    """extract_patterns_from_file pulls the right categories."""

    def test_extract_try_except_pattern(self, mini_repo: Path) -> None:
        patterns = extract_patterns_from_file(mini_repo / "src/sample.py")
        excs = [p for p in patterns if p["category"] == "error-handling"]
        assert excs, (
            f"cycle 143: must detect try/except pattern, got {patterns!r}"
        )
        # The handler catches ValueError — proposition should surface it.
        assert any("ValueError" in p["proposition"] for p in excs), (
            f"cycle 143: error-handling fact must name the caught exception. "
            f"Got: {[p['proposition'] for p in excs]!r}"
        )

    def test_extract_function_docstring(self, mini_repo: Path) -> None:
        patterns = extract_patterns_from_file(mini_repo / "src/sample.py")
        apis = [p for p in patterns if p["category"] == "api"]
        assert apis, "cycle 143: function with docstring must produce api fact"
        assert any("parse_int" in p["proposition"] for p in apis), (
            f"cycle 143: function name must appear in proposition. "
            f"Got: {[p['proposition'] for p in apis]!r}"
        )

    def test_extract_class_docstring(self, mini_repo: Path) -> None:
        patterns = extract_patterns_from_file(mini_repo / "src/sample.py")
        types = [p for p in patterns if p["category"] == "types"]
        assert types, "cycle 143: class with docstring must produce types fact"
        assert any("Calculator" in p["proposition"] for p in types)

    def test_verified_by_includes_file_and_line(
        self, mini_repo: Path,
    ) -> None:
        patterns = extract_patterns_from_file(mini_repo / "src/sample.py")
        assert patterns, "cycle 143: must extract at least one pattern"
        for p in patterns:
            assert "verified_by" in p and p["verified_by"], (
                f"cycle 143: every pattern must carry a verified_by ref. "
                f"Missing on {p!r}"
            )
            ref = p["verified_by"][0]
            assert ref.startswith("file:"), (
                f"cycle 143: verified_by must use 'file:<path>:<line>' "
                f"shape, got {ref!r}"
            )
            assert "sample.py" in ref, (
                f"cycle 143: verified_by must point at the right source. "
                f"Got {ref!r}"
            )

    def test_syntax_error_returns_empty_not_raises(
        self, tmp_path: Path,
    ) -> None:
        bad = tmp_path / "broken.py"
        bad.write_text("def f(:\n    pass\n", encoding="utf-8")
        # Must NOT raise — broken files are skipped silently (logged).
        out = extract_patterns_from_file(bad)
        assert out == [], (
            f"cycle 143: syntax error file must yield empty list, got {out!r}"
        )


# ---- TestIngestCodebase ----------------------------------------------
class TestIngestCodebase:
    """ingest_codebase walks the repo + persists to SemanticMemory."""

    def test_returns_summary_with_expected_keys(
        self, mini_repo: Path, sm: SemanticMemory,
    ) -> None:
        out = ingest_codebase(mini_repo, sm=sm)
        for key in (
            "files_parsed", "patterns_extracted", "patterns_persisted",
            "errors_skipped", "duration_ms",
        ):
            assert key in out, (
                f"cycle 143: summary missing key {key!r}. Got {out.keys()!r}"
            )

    def test_dry_run_extracts_but_does_not_persist(
        self, mini_repo: Path, sm: SemanticMemory,
    ) -> None:
        out = ingest_codebase(mini_repo, sm=sm, dry_run=True)
        assert out["patterns_extracted"] > 0, (
            f"cycle 143: dry_run must still extract, got "
            f"extracted={out['patterns_extracted']!r}"
        )
        assert out["patterns_persisted"] == 0, (
            f"cycle 143: dry_run must NOT persist, got "
            f"persisted={out['patterns_persisted']!r}"
        )

    def test_skip_pycache_dir(
        self, mini_repo: Path, sm: SemanticMemory,
    ) -> None:
        # Plant a tainted file under __pycache__/
        _write(mini_repo, "src/__pycache__/cached.py",
               "class Should_Never_Parse:\n    \"\"\"BAD.\"\"\"\n    pass\n")
        out = ingest_codebase(mini_repo, sm=sm)
        # The class name 'Should_Never_Parse' must NOT appear in any persisted fact.
        from verimem.semantic import SemanticMemory as _SM  # noqa: F401
        with sm._connect() as conn:  # noqa: SLF001 — test inspection
            rows = conn.execute(
                "SELECT proposition FROM facts WHERE proposition LIKE ?",
                ("%Should_Never_Parse%",),
            ).fetchall()
        assert not rows, (
            f"cycle 143: __pycache__ must be skipped, "
            f"found leaked facts {rows!r}"
        )

    def test_max_files_cap_enforced(
        self, tmp_path: Path, sm: SemanticMemory,
    ) -> None:
        repo = tmp_path / "biggerrepo"
        repo.mkdir()
        for i in range(5):
            _write(repo, f"m{i}.py",
                   f'"""mod {i}."""\n\ndef f{i}():\n    """fn {i}."""\n    pass\n')
        out = ingest_codebase(repo, sm=sm, max_files=2)
        assert out["files_parsed"] <= 2, (
            f"cycle 143: max_files=2 must cap, got "
            f"files_parsed={out['files_parsed']!r}"
        )

    def test_idempotent_no_duplicates_on_rerun(
        self, mini_repo: Path, sm: SemanticMemory,
    ) -> None:
        first = ingest_codebase(mini_repo, sm=sm)
        second = ingest_codebase(mini_repo, sm=sm)
        assert second["patterns_persisted"] == 0, (
            f"cycle 143: second run must persist 0 new facts (idempotent), "
            f"got {second['patterns_persisted']!r} new on second run after "
            f"{first['patterns_persisted']!r} on first"
        )
