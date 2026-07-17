"""IDE mutating endpoints must refuse to target the workspace ROOT (scan #310).

`_safe_path` blocks `..`/drive/UNC traversal, but an empty/`"/"`/`"."`
path normalises to the workspace root itself and passes containment.
`ide_file_delete` then runs `shutil.rmtree(root)` — a single
`DELETE /api/ide/file?path=/` wipes the entire workspace (the second,
still-open half of the "zero-auth + DELETE path=/ -> rmtree" finding;
auth was added by a later audit, the root-delete was not).

Contract: delete/write/new resolving to the root are rejected (400),
the workspace survives, and a normal child delete still works.
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
    c.headers.update({"X-Hippo-Token": get_session_token()})
    return c


@pytest.mark.parametrize("root_path", ["/", "", ".", "\\", "/."])
def test_delete_root_is_refused(client, workspace, root_path):
    # Seed a real file so the workspace is non-empty and the rmtree would
    # actually destroy data if it went through.
    (workspace / "keepme.txt").write_text("precious", encoding="utf-8")
    r = client.request("DELETE", "/api/ide/file", params={"path": root_path})
    assert r.status_code == 400, (
        f"DELETE path={root_path!r} must be refused, got {r.status_code}"
    )
    assert workspace.exists(), "workspace root must survive a root-delete attempt"
    assert (workspace / "keepme.txt").exists(), "child files must be untouched"


def test_delete_child_still_works(client, workspace):
    (workspace / "trash.txt").write_text("x", encoding="utf-8")
    r = client.request("DELETE", "/api/ide/file", params={"path": "trash.txt"})
    assert r.status_code == 200, r.text
    assert not (workspace / "trash.txt").exists(), "normal delete must still work"


def test_write_to_root_is_refused(client, workspace):
    r = client.put("/api/ide/file", json={"path": "/", "content": "x"})
    assert r.status_code == 400
    assert workspace.is_dir()
