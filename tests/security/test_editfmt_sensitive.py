"""CVE-011 — editfmt.apply_block deny-list contract.

Files / directories the agent must not silently rewrite via SEARCH/REPLACE:
  - VCS internals (.git, .hg, .svn)
  - IDE config (.vscode, .idea, .devcontainer)
  - CI / shell scripts (*.sh, *.bat, *.ps1, *.cmd)
  - Build manifests (Makefile, pyproject.toml, setup.py, package.json, ...)
  - Secrets (.pem, .key, .env)
  - Sensitive subpaths (.ssh, .aws, credentials.json, ...)

Override is opt-in via _EDITFMT_ALLOW_SENSITIVE=1.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.editfmt import EditBlock, _is_sensitive_target, apply_block

# ---------------------------------------------------------------------------
# _is_sensitive_target unit checks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rel,expected_block", [
    # blocked dirs
    (".git/config", True),
    (".vscode/settings.json", True),
    (".idea/workspace.xml", True),
    (".devcontainer/Dockerfile", True),
    (".github/workflows/ci.yml", True),
    # blocked names
    ("Makefile", True),
    ("pyproject.toml", True),
    ("setup.py", True),
    ("setup.cfg", True),
    ("package.json", True),
    (".env", True),
    # blocked extensions
    ("scripts/install.sh", True),
    ("scripts/build.bat", True),
    ("scripts/deploy.ps1", True),
    ("certs/server.pem", True),
    ("keys/private.key", True),
    # allowed
    ("src/main.py", False),
    ("docs/README.md", False),
    ("data/notes.txt", False),
    ("hippoagent/wake.py", False),
    ("tests/test_x.py", False),
])
def test_is_sensitive_target_classification(
    rel: str, expected_block: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("_EDITFMT_ALLOW_SENSITIVE", raising=False)
    blocked, reason = _is_sensitive_target(rel)
    assert blocked is expected_block, (
        f"{rel} expected blocked={expected_block}, got {blocked}, reason={reason}"
    )


def test_override_env_unblocks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Setting _EDITFMT_ALLOW_SENSITIVE=1 disables the deny-list."""
    monkeypatch.setenv("_EDITFMT_ALLOW_SENSITIVE", "1")
    blocked, _ = _is_sensitive_target("pyproject.toml")
    assert blocked is False
    blocked, _ = _is_sensitive_target(".git/config")
    assert blocked is False


# ---------------------------------------------------------------------------
# apply_block — full path through the dispatcher
# ---------------------------------------------------------------------------


def test_apply_block_refuses_pyproject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("_EDITFMT_ALLOW_SENSITIVE", raising=False)
    target = tmp_path / "pyproject.toml"
    target.write_text("[tool.test]\nx = 1\n", encoding="utf-8")
    block = EditBlock(path="pyproject.toml", search="x = 1", replace="x = 2")
    result = apply_block(block, root=tmp_path)
    assert result.ok is False
    assert "sensitive" in result.reason.lower()
    # File must remain unmodified
    assert "x = 1" in target.read_text(encoding="utf-8")


def test_apply_block_refuses_dot_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("_EDITFMT_ALLOW_SENSITIVE", raising=False)
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("[core]\n", encoding="utf-8")
    block = EditBlock(path=".git/config", search="[core]",
                      replace="[core]\n  pwned = true")
    result = apply_block(block, root=tmp_path)
    assert result.ok is False


def test_apply_block_refuses_shell_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("_EDITFMT_ALLOW_SENSITIVE", raising=False)
    target = tmp_path / "deploy.sh"
    target.write_text("#!/bin/sh\necho hi\n", encoding="utf-8")
    block = EditBlock(path="deploy.sh", search="echo hi",
                      replace="echo hi; rm -rf /")
    result = apply_block(block, root=tmp_path)
    assert result.ok is False


def test_apply_block_refuses_pem(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("_EDITFMT_ALLOW_SENSITIVE", raising=False)
    target = tmp_path / "server.pem"
    target.write_text("-----BEGIN CERT-----\n", encoding="utf-8")
    block = EditBlock(path="server.pem",
                      search="-----BEGIN CERT-----",
                      replace="bogus")
    result = apply_block(block, root=tmp_path)
    assert result.ok is False


def test_apply_block_allows_normal_python_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("_EDITFMT_ALLOW_SENSITIVE", raising=False)
    target = tmp_path / "src" / "main.py"
    target.parent.mkdir()
    target.write_text("def f(): pass\n", encoding="utf-8")
    block = EditBlock(path="src/main.py", search="def f(): pass",
                      replace="def f(): return 1")
    result = apply_block(block, root=tmp_path)
    assert result.ok is True


def test_override_allows_pyproject_edit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the operator opts in, the edit goes through."""
    monkeypatch.setenv("_EDITFMT_ALLOW_SENSITIVE", "1")
    target = tmp_path / "pyproject.toml"
    target.write_text("[tool]\nx = 1\n", encoding="utf-8")
    block = EditBlock(path="pyproject.toml", search="x = 1", replace="x = 2")
    result = apply_block(block, root=tmp_path)
    assert result.ok is True
    assert "x = 2" in target.read_text(encoding="utf-8")
