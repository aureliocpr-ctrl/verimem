"""Document indexing had no path confinement (audit MEDIUM).

`hippo_document_index_file` took `path` from the caller and handed it straight
to DocumentIndex().index_file(). An agent steered by poisoned content could
index ~/.aws/credentials, .env or an SSH key — and the contents then come back
through document_semantic_search and can be promoted into facts. That is worse
than a file read: the secret takes up residence INSIDE the memory corpus, which
is the one place this product promises you can trust.

Two guards, because a root jail alone is not enough: the realistic case is a
`.env` sitting in the project root, i.e. INSIDE any sensible jail. So the roots
say WHERE we may read, and the sensitive-name denylist says WHAT we never read
even there.
"""
from __future__ import annotations

import json
from typing import Any

import pytest

from verimem import mcp_server


async def _invoke(name: str, arguments: dict[str, Any]):
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(method="tools/call",
                          params=CallToolRequestParams(name=name,
                                                       arguments=arguments))
    res = await handler(req)
    payload = res.root if hasattr(res, "root") else res
    return json.loads([c.text for c in payload.content if hasattr(c, "text")][0])


def test_path_outside_the_roots_is_refused(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    secret = outside / "notes.md"
    secret.write_text("hello", encoding="utf-8")
    monkeypatch.setenv("ENGRAM_DOC_ROOTS", str(root))
    ok, why = mcp_server._doc_path_allowed(str(secret))
    assert not ok and ("root" in why.lower() or "outside" in why.lower()), why


@pytest.mark.parametrize("name", [
    ".env", ".env.local", "id_rsa", "server.pem", "private.key",
    "credentials", "keys.env", "cert.pfx",
])
def test_sensitive_names_refused_even_inside_the_roots(name, tmp_path, monkeypatch):
    """The realistic case: the secret lives IN the project."""
    root = tmp_path / "project"
    root.mkdir()
    f = root / name
    f.write_text("SECRET=1", encoding="utf-8")
    monkeypatch.setenv("ENGRAM_DOC_ROOTS", str(root))
    ok, why = mcp_server._doc_path_allowed(str(f))
    assert not ok, f"{name} would have been indexed into the corpus"
    assert "sensitive" in why.lower() or "secret" in why.lower(), why


def test_ordinary_document_inside_the_roots_is_allowed(tmp_path, monkeypatch):
    """Narrowness: normal documents must still index."""
    root = tmp_path / "project"
    root.mkdir()
    doc = root / "handbook.md"
    doc.write_text("# Handbook\nThe tank holds 500 liters.", encoding="utf-8")
    monkeypatch.setenv("ENGRAM_DOC_ROOTS", str(root))
    ok, why = mcp_server._doc_path_allowed(str(doc))
    assert ok, why


def test_roots_default_to_the_process_cwd_when_unset(monkeypatch):
    """Secure by default: unconfigured must not mean unrestricted."""
    monkeypatch.delenv("ENGRAM_DOC_ROOTS", raising=False)
    ok, _why = mcp_server._doc_path_allowed(str(__file__))
    assert isinstance(ok, bool)          # resolves without exploding
    ok2, why2 = mcp_server._doc_path_allowed("C:/Windows/System32/drivers/etc/hosts")
    assert not ok2, f"unconfigured jail let an out-of-tree path through: {why2}"


@pytest.mark.asyncio
async def test_tool_refuses_a_sensitive_file_end_to_end(tmp_path, monkeypatch):
    root = tmp_path / "project"
    root.mkdir()
    env = root / ".env"
    env.write_text("MOONSHOT_API_KEY=sk-should-never-be-indexed", encoding="utf-8")
    monkeypatch.setenv("ENGRAM_DOC_ROOTS", str(root))
    payload = await _invoke("hippo_document_index_file", {"path": str(env)})
    blob = json.dumps(payload).lower()
    assert "error" in blob, payload
    assert "sk-should-never-be-indexed" not in blob, "the guard echoed the secret"
