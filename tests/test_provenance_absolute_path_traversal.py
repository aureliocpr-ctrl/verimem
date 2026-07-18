"""Security regression (opus CodeQL triage 2026-07-18, alert [20]-[23]).

`_verify_file_ref` opened an ABSOLUTE path from a provenance ref without any
containment when ``repo_root is None`` — and the multi-tenant gateway builds
``Memory`` WITHOUT a repo_root. A hostile tenant could send
``verified_by=["file:/etc/passwd:1"]`` to (a) probe arbitrary server files
(existence + line-count oracle) and (b) FORGE ``status="verified"`` on a fact,
bypassing the grounding moat. The absolute branch must be refused exactly like
the relative one when there is no root to contain it.
"""
from pathlib import Path

from verimem.provenance_validator import _verify_file_ref


def test_absolute_ref_refused_without_repo_root(tmp_path: Path) -> None:
    # A real file OUTSIDE any repo root (stands in for /etc/passwd).
    secret = tmp_path / "outside_secret.txt"
    secret.write_text("l1\nl2\nl3\n", encoding="utf-8")
    ref = f"file:{secret}:1"
    # repo_root=None is the gateway's real config → an absolute ref must NOT be
    # opened. Pre-fix this returned True (file exists) = the vulnerability.
    assert _verify_file_ref(ref, repo_root=None) is False


def test_absolute_ref_outside_repo_root_refused(tmp_path: Path) -> None:
    # Even WITH a repo_root, an absolute path outside it stays refused.
    root = tmp_path / "repo"
    root.mkdir()
    secret = tmp_path / "outside.txt"
    secret.write_text("x\n", encoding="utf-8")
    assert _verify_file_ref(f"file:{secret}:1", repo_root=root) is False


def test_legit_ref_inside_repo_root_still_verifies(tmp_path: Path) -> None:
    # Counter-proof: a genuine in-root ref still works (no over-blocking).
    root = tmp_path / "repo"
    root.mkdir()
    f = root / "src.py"
    f.write_text("a\nb\nc\n", encoding="utf-8")
    assert _verify_file_ref(f"file:{f}:2", repo_root=root) is True
