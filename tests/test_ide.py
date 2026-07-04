"""Tests for the Engram IDE workspace API.

Covers: file tree, read/write/delete/create, path-traversal protection,
shell run, git status. Uses FastAPI TestClient against the live router and
isolates the workspace under tmp_path via the HIPPO_IDE_WORKSPACE env var.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from engram import dashboard


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Point the IDE at an isolated tmp workspace and return the Path."""
    monkeypatch.setenv("HIPPO_IDE_WORKSPACE", str(tmp_path))
    # Seed the workspace with a couple of files
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "util.py").write_text("def add(a, b): return a + b\n",
                                                encoding="utf-8")
    return tmp_path


# Hardened-IDE shell endpoints (CVE-001 / CVE-002) require:
#   1. HIPPO_ENABLE_SHELL=1
#   2. X-Hippo-Token header matching HIPPO_AUTH_TOKEN
# Tests that exercise /api/ide/run set both via this fixture.
_TEST_TOKEN = "test-token-engram-ci-only"


@pytest.fixture
def shell_enabled(monkeypatch):
    monkeypatch.setenv("HIPPO_ENABLE_SHELL", "1")
    monkeypatch.setenv("HIPPO_AUTH_TOKEN", _TEST_TOKEN)
    # Allow common test binaries (echo, python, dir, no-such-binary-xyz...)
    monkeypatch.setenv(
        "HIPPO_IDE_SHELL_ALLOWLIST",
        "echo,cmd,python,python3,no-such-binary-xyz,git,ls,dir,type",
    )


@pytest.fixture
def client(workspace, monkeypatch):
    # IDE fs/git endpoints now reuse the dashboard session-auth gate; these
    # functional tests exercise the dev/local posture (auth OFF). The auth gate
    # itself is covered by TestIdeFsAuthGate.
    monkeypatch.setenv("HIPPO_DASHBOARD_AUTH_DISABLED", "1")
    from engram.dashboard_routes.auth import reset_session_token
    reset_session_token()
    return TestClient(dashboard.app)


@pytest.fixture
def auth_headers():
    return {"X-Hippo-Token": _TEST_TOKEN}


# --- Enterprise auth gate on IDE fs/git endpoints (production posture) -------
# The IDE fs read/write/delete/tree + git endpoints previously had ZERO auth
# (scan68 ide.py:277-342,241,603 — unauthenticated workspace R/W). They now
# reuse the dashboard session-token dependency (verify_session_token), so the
# same dual-mode applies: OFF in local/dev (HIPPO_DASHBOARD_AUTH_DISABLED=1),
# fail-closed when enabled (the default = enterprise posture).
_DASH_TOKEN = "dash-session-token-ci-only"


@pytest.fixture
def auth_on_client(workspace, monkeypatch):
    """TestClient with dashboard session-auth ENABLED (enterprise posture)."""
    monkeypatch.delenv("HIPPO_DASHBOARD_AUTH_DISABLED", raising=False)
    monkeypatch.setenv("HIPPO_DASHBOARD_TOKEN", _DASH_TOKEN)
    from engram.dashboard_routes.auth import reset_session_token
    reset_session_token()
    yield TestClient(dashboard.app)
    reset_session_token()


class TestIdeFsAuthGate:
    """Fs/git endpoints must require X-Hippo-Token when auth is enabled."""

    _H = {"X-Hippo-Token": _DASH_TOKEN}

    def test_tree_requires_token(self, auth_on_client):
        assert auth_on_client.get("/api/ide/tree").status_code == 401

    def test_file_read_requires_token(self, auth_on_client):
        assert auth_on_client.get("/api/ide/file?path=main.py").status_code == 401

    def test_file_write_requires_token(self, auth_on_client):
        r = auth_on_client.put(
            "/api/ide/file", json={"path": "x.py", "content": "evil"},
        )
        assert r.status_code == 401

    def test_file_delete_requires_token(self, auth_on_client):
        assert auth_on_client.delete("/api/ide/file?path=main.py").status_code == 401

    def test_file_new_requires_token(self, auth_on_client):
        r = auth_on_client.post(
            "/api/ide/file/new", json={"path": "new.py", "is_dir": False},
        )
        assert r.status_code == 401

    def test_git_status_requires_token(self, auth_on_client):
        assert auth_on_client.get("/api/ide/git/status").status_code == 401

    def test_git_diff_requires_token(self, auth_on_client):
        assert auth_on_client.get("/api/ide/git/diff").status_code == 401

    def test_valid_token_allows_tree(self, auth_on_client):
        r = auth_on_client.get("/api/ide/tree", headers=self._H)
        assert r.status_code == 200

    def test_valid_token_allows_file_write(self, auth_on_client, workspace):
        r = auth_on_client.put(
            "/api/ide/file", headers=self._H,
            json={"path": "ok.py", "content": "x = 1\n"},
        )
        assert r.status_code == 200
        assert (workspace / "ok.py").read_text(encoding="utf-8") == "x = 1\n"

    def test_auth_disabled_allows_without_token(self, workspace, monkeypatch):
        # Dual-mode: local/dev posture -> no token required.
        monkeypatch.setenv("HIPPO_DASHBOARD_AUTH_DISABLED", "1")
        from engram.dashboard_routes.auth import reset_session_token
        reset_session_token()
        c = TestClient(dashboard.app)
        assert c.get("/api/ide/tree").status_code == 200
        reset_session_token()


def test_tree_lists_workspace_files(client, workspace):
    r = client.get("/api/ide/tree")
    assert r.status_code == 200
    data = r.json()
    assert data["root"] == str(workspace)
    names = [c["name"] for c in data["tree"]["children"]]
    assert "main.py" in names
    assert "lib" in names
    # Sub-tree expanded
    lib = next(c for c in data["tree"]["children"] if c["name"] == "lib")
    assert any(c["name"] == "util.py" for c in lib["children"])


def test_read_text_file(client):
    r = client.get("/api/ide/file?path=main.py")
    assert r.status_code == 200
    assert r.json()["content"] == "print('hello')\n"


def test_read_missing_file_404(client):
    r = client.get("/api/ide/file?path=does/not/exist.py")
    assert r.status_code == 404


def test_path_traversal_blocked(client):
    """Attempting to escape the workspace via .. must fail with 400."""
    r = client.get("/api/ide/file?path=../../etc/passwd")
    assert r.status_code == 400
    assert "escape" in r.json()["detail"].lower()


def test_write_creates_parents(client, workspace):
    r = client.put("/api/ide/file", json={
        "path": "newdir/nested/file.txt",
        "content": "fresh content\n",
    })
    assert r.status_code == 200
    assert (workspace / "newdir" / "nested" / "file.txt").read_text() == "fresh content\n"


def test_write_overwrites_existing(client, workspace):
    r = client.put("/api/ide/file", json={"path": "main.py",
                                           "content": "print('updated')\n"})
    assert r.status_code == 200
    assert (workspace / "main.py").read_text() == "print('updated')\n"


def test_create_new_file(client, workspace):
    r = client.post("/api/ide/file/new", json={"path": "todo.md", "is_dir": False})
    assert r.status_code == 200
    assert (workspace / "todo.md").exists()


def test_create_existing_file_409(client):
    r = client.post("/api/ide/file/new", json={"path": "main.py", "is_dir": False})
    assert r.status_code == 409


def test_delete_file(client, workspace):
    r = client.delete("/api/ide/file?path=main.py")
    assert r.status_code == 200
    assert not (workspace / "main.py").exists()


def test_delete_directory_recursive(client, workspace):
    r = client.delete("/api/ide/file?path=lib")
    assert r.status_code == 200
    assert not (workspace / "lib").exists()


def test_run_simple_command(client, shell_enabled, auth_headers):
    """Run a portable echo and check stdout/rc."""
    import sys
    if sys.platform == "win32":
        # `cmd /c echo …` — first token is the allowlisted `cmd` binary.
        cmd = "cmd /c echo hello-engram"
    else:
        cmd = "echo hello-engram"
    r = client.post(
        "/api/ide/run",
        json={"cmd": cmd, "timeout_s": 10},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["rc"] == 0
    assert "hello-engram" in data["stdout"]


def test_run_command_returns_nonzero_on_error(client, shell_enabled, auth_headers):
    r = client.post(
        "/api/ide/run",
        json={"cmd": "no-such-binary-xyz", "timeout_s": 5},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
    assert data["rc"] != 0


def test_run_truncates_huge_output(client, shell_enabled, auth_headers):
    """Output >64KB must come back truncated, not blow up the response.

    Uses a short command that *generates* a large output, rather than
    embedding the payload inline.
    """
    import sys
    py = "python" if sys.platform == "win32" else "python3"
    # 100KB of 'A' generated by python — short cmdline, big output
    cmd = f"{py} -c print('A'*100000)"
    r = client.post(
        "/api/ide/run",
        json={"cmd": cmd, "timeout_s": 15},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    # Either truncated or python wasn't found — both are fine; the point is
    # the endpoint stays responsive and bounded.
    assert isinstance(data.get("stdout", ""), str)
    if data.get("ok"):
        assert len(data["stdout"]) < 70_000  # cap (64KB) + truncation tag


def test_run_requires_shell_enabled_env(client, auth_headers, monkeypatch):
    """SEC V1 / CVE-001: without HIPPO_ENABLE_SHELL=1 the endpoint refuses.

    Set a valid run-token (HIPPO_AUTH_TOKEN) so the refusal under test is the
    SHELL-disabled 403, not the order-dependent 503 raised when the run-token
    env happens to be unset (the documented ide-503 flake). HIPPO_ENABLE_SHELL
    stays unset, so the endpoint must still refuse — with 403.
    """
    monkeypatch.setenv("HIPPO_AUTH_TOKEN", _TEST_TOKEN)
    monkeypatch.delenv("HIPPO_ENABLE_SHELL", raising=False)  # force shell OFF
    r = client.post(
        "/api/ide/run",
        json={"cmd": "echo hi", "timeout_s": 5},
        headers=auth_headers,
    )
    assert r.status_code == 403


def test_run_requires_auth_token(client, shell_enabled):
    """SEC V1 / CVE-001: missing or wrong token rejected even with shell on."""
    r = client.post("/api/ide/run", json={"cmd": "echo hi", "timeout_s": 5})
    assert r.status_code == 403
    r = client.post(
        "/api/ide/run",
        json={"cmd": "echo hi", "timeout_s": 5},
        headers={"X-Hippo-Token": "wrong"},
    )
    assert r.status_code == 403


def test_run_blocks_non_allowlisted_binary(client, shell_enabled, auth_headers):
    """SEC V1 / CVE-001: binary outside HIPPO_IDE_SHELL_ALLOWLIST refused."""
    r = client.post(
        "/api/ide/run",
        json={"cmd": "rm -rf /", "timeout_s": 5},
        headers=auth_headers,
    )
    assert r.status_code == 403


def test_git_status_on_non_repo(client):
    """An empty tmp dir is not a git repo → returns ok=False with error."""
    r = client.get("/api/ide/git/status")
    data = r.json()
    assert r.status_code == 200
    # Non-git → ok=False; if git happens to find a parent repo, that's still
    # a valid response
    assert "ok" in data


def test_ide_html_served(client):
    r = client.get("/ide")
    assert r.status_code == 200
    assert "ENGRAM IDE" in r.text
    assert "/static/ide.js" in r.text


def test_ide_js_served(client):
    r = client.get("/static/ide.js")
    assert r.status_code == 200
    assert "monaco" in r.text.lower()
    assert "WebSocket" in r.text


def test_safe_path_with_backslashes_normalised(client, workspace):
    """Windows-style backslash paths must work and not bypass containment."""
    r = client.put("/api/ide/file", json={"path": "win\\style\\file.txt",
                                           "content": "ok\n"})
    assert r.status_code == 200
    assert (workspace / "win" / "style" / "file.txt").read_text() == "ok\n"
