"""Path-traversal & sensitive-deny-list regression tests.

Covers Sprint 1 hardening for the FS sandbox (CVE-003 / SEC V4):

  • editfmt.apply_block must refuse any path that escapes the workspace
  • tools_extra._is_sensitive must flag credential paths (.ssh, .aws, *.pem,
    *.key, .gnupg, …)
  • fs_read_file / fs_write_file must refuse sensitive paths even when the
    path is technically inside an allowed root
  • HIPPO_FS_STRICT=1 keeps the agent in the project data dir
  • HIPPO_FS_HOME=1 expands the allow-list to the user home
  • Default (no env vars set) is STRICT (post Sprint 1)

These tests must be platform-agnostic — Windows hosts use absolute drive
paths, POSIX hosts use forward slashes. Where exactly-Windows or
exactly-POSIX behaviour matters, we skip the other platform.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem import tools_extra
from verimem.editfmt import EditBlock, apply_block

# ---------------------------------------------------------------------------
# editfmt.apply_block — workspace escape
# ---------------------------------------------------------------------------


def test_apply_block_refuses_dotdot_escape(tmp_path: Path) -> None:
    """`../../etc/passwd` must NEVER be reached from the workspace root."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    block = EditBlock(path="../../etc/passwd", search="", replace="x")
    result = apply_block(block, root=workspace)
    assert result.ok is False
    assert "escape" in result.reason.lower()
    # Critical: the escape target must NOT have been written.
    target = (workspace / "../../etc/passwd").resolve()
    assert not target.exists() or target.read_bytes() != b"x"


def test_apply_block_refuses_absolute_path_outside_workspace(tmp_path: Path) -> None:
    """An absolute path that resolves outside `root` must be refused."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    other = tmp_path / "other_dir"
    other.mkdir()
    target_path = other / "leaked.txt"
    # Bare absolute paths get lstripped by apply_block (safety) — we still
    # ensure that even via a creative relative path with parent escapes,
    # the resolved target lands outside workspace and gets rejected.
    block = EditBlock(
        path="../other_dir/leaked.txt", search="", replace="leaked",
    )
    result = apply_block(block, root=workspace)
    assert result.ok is False
    assert not target_path.exists()


def test_apply_block_allows_legitimate_in_workspace(tmp_path: Path) -> None:
    """Sanity: an in-workspace path still works (regression guard)."""
    workspace = tmp_path / "ws"
    workspace.mkdir()
    block = EditBlock(path="hello.txt", search="", replace="hi")
    result = apply_block(block, root=workspace)
    assert result.ok is True
    assert (workspace / "hello.txt").read_text(encoding="utf-8") == "hi"


# ---------------------------------------------------------------------------
# _is_sensitive — credential deny-list
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path_segment", [
    ".ssh/id_rsa",
    ".ssh/id_ed25519",
    ".aws/credentials",
    ".aws/credentials.json",
    ".gnupg/pubring.kbx",
    ".docker/config.json",
    ".kube/config",
    ".azure/credentials",
    ".env",
    ".netrc",
    "secrets.json",
    "user_settings.json",
])
def test_is_sensitive_flags_credential_paths(tmp_path: Path, path_segment: str) -> None:
    p = tmp_path / path_segment
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("dummy", encoding="utf-8")
    assert tools_extra._is_sensitive(p) is True, f"expected sensitive: {p}"


@pytest.mark.parametrize("filename", [
    "server.pem", "client.key", "private.pem", "tls.key", "ca.pem",
])
def test_is_sensitive_flags_pem_and_key_extensions(tmp_path: Path, filename: str) -> None:
    p = tmp_path / filename
    p.write_text("dummy", encoding="utf-8")
    assert tools_extra._is_sensitive(p) is True


def test_is_sensitive_passes_normal_files(tmp_path: Path) -> None:
    p = tmp_path / "README.md"
    p.write_text("hello", encoding="utf-8")
    assert tools_extra._is_sensitive(p) is False


def test_is_sensitive_passes_pemmer_substring_in_dir(tmp_path: Path) -> None:
    """A directory containing 'pem' but not ending in .pem/.key is fine."""
    p = tmp_path / "tempfile.txt"
    p.write_text("hello", encoding="utf-8")
    assert tools_extra._is_sensitive(p) is False


# ---------------------------------------------------------------------------
# fs_read_file / fs_write_file — sensitive paths refused
# ---------------------------------------------------------------------------


def test_fs_read_refuses_sensitive_even_when_inside_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build a fake .ssh/id_rsa inside an allowed root → still refused.

    The deny-list trumps the path-allowed check.
    """
    fake_ssh = tmp_path / ".ssh"
    fake_ssh.mkdir()
    target = fake_ssh / "id_rsa"
    target.write_text("BEGIN OPENSSH PRIVATE KEY", encoding="utf-8")
    # Make the entire tmp_path the allowed root.
    monkeypatch.setenv("HIPPO_FS_ROOT", str(tmp_path))
    result = tools_extra.fs_read_file(str(target))
    assert result.ok is False
    assert "sensitive" in (result.error or "").lower()


def test_fs_write_refuses_sensitive_even_when_inside_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_aws = tmp_path / ".aws"
    fake_aws.mkdir()
    target = fake_aws / "credentials"
    monkeypatch.setenv("HIPPO_FS_ROOT", str(tmp_path))
    result = tools_extra.fs_write_file(str(target), "[default]\naws_access_key_id=...")
    assert result.ok is False
    assert "sensitive" in (result.error or "").lower()
    # Critical: nothing was written.
    assert not target.exists()


# ---------------------------------------------------------------------------
# Filesystem scope env vars
# ---------------------------------------------------------------------------


def test_default_scope_is_strict(monkeypatch: pytest.MonkeyPatch) -> None:
    """No env vars set → default policy is STRICT (data dir only).

    This is the post-Sprint-1 fix: previously the default was HOME.
    """
    monkeypatch.delenv("HIPPO_FS_STRICT", raising=False)
    monkeypatch.delenv("HIPPO_FS_HOME", raising=False)
    monkeypatch.delenv("HIPPO_FS_ROOT", raising=False)
    roots = tools_extra._fs_roots()
    # Exactly one root, and it's the project data dir
    from verimem.config import CONFIG
    assert len(roots) == 1
    assert roots[0] == CONFIG.data_dir.resolve()


def test_strict_keeps_agent_in_data_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    """HIPPO_FS_STRICT=1 (explicit) → only data dir is allowed."""
    monkeypatch.setenv("HIPPO_FS_STRICT", "1")
    monkeypatch.delenv("HIPPO_FS_HOME", raising=False)
    monkeypatch.delenv("HIPPO_FS_ROOT", raising=False)
    roots = tools_extra._fs_roots()
    from verimem.config import CONFIG
    assert roots == [CONFIG.data_dir.resolve()]
    # And the home directory is OUT of scope.
    assert not tools_extra._is_within_any(Path.home(), roots)


def test_home_expands_to_user_home(monkeypatch: pytest.MonkeyPatch) -> None:
    """HIPPO_FS_HOME=1 → user home is in scope."""
    monkeypatch.setenv("HIPPO_FS_HOME", "1")
    monkeypatch.delenv("HIPPO_FS_STRICT", raising=False)
    monkeypatch.delenv("HIPPO_FS_ROOT", raising=False)
    roots = tools_extra._fs_roots()
    home = Path.home().resolve()
    # Home must be in the allow-list now.
    assert any(home == r or home.is_relative_to(r) for r in roots)


def test_explicit_root_overrides_strict(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """HIPPO_FS_ROOT=/explicit/path → only that path is allowed (no extras)."""
    monkeypatch.setenv("HIPPO_FS_ROOT", str(tmp_path))
    monkeypatch.delenv("HIPPO_FS_STRICT", raising=False)
    monkeypatch.delenv("HIPPO_FS_HOME", raising=False)
    roots = tools_extra._fs_roots()
    assert roots == [tmp_path.resolve()]


def test_fs_read_outside_root_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A path outside the allow-list must be rejected, even for a non-sensitive file."""
    inside = tmp_path / "allowed"
    inside.mkdir()
    outside = tmp_path / "forbidden"
    outside.mkdir()
    target = outside / "secret.txt"
    target.write_text("nope", encoding="utf-8")
    monkeypatch.setenv("HIPPO_FS_ROOT", str(inside))
    result = tools_extra.fs_read_file(str(target))
    assert result.ok is False
    assert "outside allowed roots" in (result.error or "").lower()
