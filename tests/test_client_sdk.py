"""engram.Memory — the turnkey add()/search() SDK with the anti-confab gate on by
default. Proves: (1) a benign fact round-trips add→search; (2) search surfaces the
provenance fields (status, grounding_score) that are Engram's differentiator;
(3) empty text is refused; (4) the lazy ``from engram import Memory`` export works.
"""
from __future__ import annotations

import pytest


def test_lazy_export_from_package():
    import engram

    assert engram.Memory is engram.Client  # alias
    from engram import Memory  # the documented one-liner import

    assert Memory is engram.Memory


def test_add_then_search_roundtrip(tmp_path):
    from engram import Memory

    mem = Memory(path=tmp_path / "sem" / "sem.db")
    res = mem.add("The deployment uses PostgreSQL 16 as its database.", topic="infra")
    assert res["stored"] is True and res["id"]

    hits = mem.search("which database does the deployment use?", k=5)
    assert any("PostgreSQL" in h["text"] for h in hits)


def test_search_surfaces_provenance(tmp_path):
    from engram import Memory

    mem = Memory(path=tmp_path / "sem" / "sem.db")
    mem.add("The API rate limit is 100 requests per minute.", topic="infra")
    hits = mem.search("rate limit", k=5)
    assert hits, "expected at least one hit"
    h = hits[0]
    # the differentiator: every hit carries its provenance, not just text+score
    for field in ("text", "score", "status", "grounding_score", "topic", "id"):
        assert field in h


def test_empty_text_is_refused(tmp_path):
    from engram import Memory

    mem = Memory(path=tmp_path / "sem" / "sem.db")
    res = mem.add("   ")
    assert res["stored"] is False and res["status"] == "empty"


def test_add_with_grounding_persists_and_surfaces_via_sdk(tmp_path, monkeypatch):
    """The headline claim: through the PUBLIC SDK, add(source=, grounding_llm) routes
    the write through the L4 source⊢fact gate, persists the computed grounding_score
    (schema v12), and search() surfaces it. Hermetic — stub grounding LLM, no claude -p."""
    import types

    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")

    class _StubGroundingLLM:
        def complete(self, system, messages, *, model=None, max_tokens=None):
            return types.SimpleNamespace(text="SCORE: 95")  # source strongly entails

    from engram import Memory

    mem = Memory(path=tmp_path / "sem" / "sem.db", grounding_llm=_StubGroundingLLM())
    res = mem.add(
        "The deployment uses PostgreSQL 16.", topic="infra", validate="fast",
        source="We migrated the deployment to PostgreSQL 16 last week, replacing MySQL.",
    )
    assert res["stored"] is True
    assert res["grounding_score"] == 95.0  # computed by the gate, not hand-set

    hits = mem.search("which database does the deployment use?", k=5)
    h = next(h for h in hits if "PostgreSQL" in h["text"])
    assert h["grounding_score"] == 95.0  # persisted (v12) + surfaced on read


def test_default_gate_downgrades_unsupported_claim(tmp_path):
    """The SDK's headline 'moat by default' is not decoration: with the cheap (no-LLM)
    fast gate, an unsupported works/verified claim is DOWNGRADED to quarantined, while a
    benign fact persists live. This is the L1 anti-confab screen acting on add()."""
    from engram import Memory

    mem = Memory(path=tmp_path / "sem" / "sem.db")
    bad = mem.add("I verified that all tests pass and the system works perfectly.", topic="t")
    assert bad["stored"] is True
    assert bad["status"] == "quarantined"  # downgraded, not silently stored as a fact
    assert bad["warnings"], "expected an L1 anti-confab warning"
    assert any("evidence" in (w.get("reason", "") + w.get("advice", "")).lower()
               for w in bad["warnings"])

    good = mem.add("The deployment uses PostgreSQL 16.", topic="t")
    assert good["status"] != "quarantined"  # benign fact is not gated down


def test_get_and_delete_roundtrip(tmp_path):
    from engram import Memory

    mem = Memory(path=tmp_path / "sem" / "sem.db")
    res = mem.add("The cache TTL is 300 seconds.", topic="infra")
    fid = res["id"]
    got = mem.get(fid)
    assert got is not None and "300 seconds" in got["text"] and got["id"] == fid
    assert mem.delete(fid) is True
    assert mem.get(fid) is None
    assert mem.delete(fid) is False  # already gone


def test_recall_is_search_alias(tmp_path):
    from engram import Memory

    mem = Memory(path=tmp_path / "sem" / "sem.db")
    mem.add("The region is eu-west-1.", topic="infra")
    assert any("eu-west-1" in h["text"] for h in mem.recall("which region", k=5))


def test_get_all_lists_facts(tmp_path):
    from engram import Memory

    mem = Memory(path=tmp_path / "sem" / "sem.db")
    mem.add("The primary region is eu-west-1.", topic="infra")
    mem.add("The backup region is us-east-1.", topic="infra")
    facts = mem.get_all(topic="infra", limit=50)
    assert len(facts) >= 2
    assert all({"id", "text", "status", "grounding_score"} <= set(f) for f in facts)


def test_update_supersedes_and_history(tmp_path):
    from engram import Memory

    mem = Memory(path=tmp_path / "sem" / "sem.db")
    r = mem.add("The server listens on port 8080.", topic="infra")
    old_id = r["id"]
    upd = mem.update(old_id, "The server listens on port 9090.", topic="infra")
    assert upd["updated"] is True and upd["supersedes"] == old_id and upd["id"]
    new_id = upd["id"]

    hist = mem.history(old_id)
    assert hist[0]["id"] == old_id  # chain starts at the old fact
    assert hist[0]["superseded_by"] == new_id  # old -> new link recorded
    assert any(h["id"] == new_id for h in hist)  # chain reaches the new version


@pytest.mark.parametrize("name", ["Memory", "Client"])
def test_missing_attr_raises(name):
    import engram

    getattr(engram, name)  # both exist
    with pytest.raises(AttributeError):
        engram.DefinitelyNotAThing  # noqa: B018
