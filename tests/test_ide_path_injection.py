"""FORGIA pezzo #183 — defense-in-depth path injection guard.

Issue: CodeQL flagged `hippoagent/ide.py:312` as `py/path-injection`
because `body.path` (user-provided) flows into `Path.mkdir()` /
`Path.touch()`. The existing `_safe_path` sanitizer uses
`Path.resolve() + relative_to(root)` for containment, which is
correct on Linux/macOS but CodeQL doesn't recognize this idiom
and the `..` segments are never *explicitly* rejected before
resolution.

This test suite asserts explicit rejection of common path-traversal
attack vectors BEFORE resolve happens. Defense in depth: even if
the OS/filesystem behaves unexpectedly (case-insensitive FS,
junction points on Windows), the static refusal makes the
sanitizer auditable.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from verimem import dashboard


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_IDE_WORKSPACE", str(tmp_path))
    return tmp_path


@pytest.fixture
def client(workspace):
    from verimem.dashboard_routes.auth import get_session_token
    c = TestClient(dashboard.app)
    # The state-changing /api/ide/* endpoints are gated by the X-Hippo-Token
    # session header (dashboard auth hardening). Authenticate so these tests
    # actually reach the path-traversal validation instead of bouncing on 401.
    c.headers.update({"X-Hippo-Token": get_session_token()})
    return c


# --- Path-traversal vectors -----------------------------------------------


def test_reject_dotdot_segment(client):
    r = client.put("/api/ide/file",
                   json={"path": "../outside.txt", "content": "x"})
    assert r.status_code == 400
    assert "escape" in r.json()["detail"].lower() or \
           "traversal" in r.json()["detail"].lower()


def test_reject_dotdot_in_middle(client):
    r = client.put("/api/ide/file",
                   json={"path": "ok/../../escape.txt", "content": "x"})
    assert r.status_code == 400


def test_reject_drive_letter_absolute_windows(client):
    r = client.put("/api/ide/file",
                   json={"path": "C:/Windows/System32/foo.txt",
                         "content": "x"})
    assert r.status_code == 400


def test_reject_unc_path_windows(client):
    r = client.put("/api/ide/file",
                   json={"path": "//server/share/foo.txt", "content": "x"})
    assert r.status_code == 400


def test_reject_tilde_home_expansion(client):
    r = client.put("/api/ide/file",
                   json={"path": "~/secrets.txt", "content": "x"})
    assert r.status_code == 400


def test_reject_null_byte(client):
    r = client.put("/api/ide/file",
                   json={"path": "ok.txt\x00../escape", "content": "x"})
    assert r.status_code == 400


def test_reject_dotdot_in_new_endpoint(client):
    """The /file/new endpoint (CodeQL alert source) must also reject."""
    r = client.post("/api/ide/file/new",
                    json={"path": "../outside_dir", "is_dir": True})
    assert r.status_code == 400


def test_legitimate_nested_path_still_works(client, workspace):
    """Defense-in-depth must NOT block legitimate nested paths."""
    r = client.put("/api/ide/file",
                   json={"path": "valid/nested/file.txt", "content": "ok"})
    assert r.status_code == 200
    assert (workspace / "valid" / "nested" / "file.txt").read_text() == "ok"
