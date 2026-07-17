"""verimem.Memory — the turnkey add()/search() SDK with the anti-confab gate on by
default. Proves: (1) a benign fact round-trips add→search; (2) search surfaces the
provenance fields (status, grounding_score) that are Engram's differentiator;
(3) empty text is refused; (4) the lazy ``from verimem import Memory`` export works.
"""
from __future__ import annotations

import pytest


def test_lazy_export_from_package():
    import verimem

    assert verimem.Memory is verimem.Client  # alias
    from verimem import Memory  # the documented one-liner import

    assert Memory is verimem.Memory


def test_add_then_search_roundtrip(tmp_path):
    from verimem import Memory

    mem = Memory(path=tmp_path / "sem" / "sem.db")
    res = mem.add("The deployment uses PostgreSQL 16 as its database.", topic="infra")
    assert res["stored"] is True and res["id"]

    hits = mem.search("which database does the deployment use?", k=5)
    assert any("PostgreSQL" in h["text"] for h in hits)


def test_search_surfaces_provenance(tmp_path):
    from verimem import Memory

    mem = Memory(path=tmp_path / "sem" / "sem.db")
    mem.add("The API rate limit is 100 requests per minute.", topic="infra")
    hits = mem.search("rate limit", k=5)
    assert hits, "expected at least one hit"
    h = hits[0]
    # the differentiator: every hit carries its provenance, not just text+score
    for field in ("text", "score", "status", "grounding_score", "topic", "id"):
        assert field in h


def test_empty_text_is_refused(tmp_path):
    from verimem import Memory

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

    from verimem import Memory

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
    from verimem import Memory

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
    from verimem import Memory

    mem = Memory(path=tmp_path / "sem" / "sem.db")
    res = mem.add("The cache TTL is 300 seconds.", topic="infra")
    fid = res["id"]
    got = mem.get(fid)
    assert got is not None and "300 seconds" in got["text"] and got["id"] == fid
    assert mem.delete(fid) is True
    assert mem.get(fid) is None
    assert mem.delete(fid) is False  # already gone


def test_recall_is_search_alias(tmp_path):
    from verimem import Memory

    mem = Memory(path=tmp_path / "sem" / "sem.db")
    mem.add("The region is eu-west-1.", topic="infra")
    assert any("eu-west-1" in h["text"] for h in mem.recall("which region", k=5))


def test_get_all_lists_facts(tmp_path):
    from verimem import Memory

    mem = Memory(path=tmp_path / "sem" / "sem.db")
    mem.add("The primary region is eu-west-1.", topic="infra")
    mem.add("The backup region is us-east-1.", topic="infra")
    facts = mem.get_all(topic="infra", limit=50)
    assert len(facts) >= 2
    assert all({"id", "text", "status", "grounding_score"} <= set(f) for f in facts)


def test_update_supersedes_and_history(tmp_path):
    from verimem import Memory

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
    import verimem

    getattr(verimem, name)  # both exist
    with pytest.raises(AttributeError):
        verimem.DefinitelyNotAThing  # noqa: B018


# ---- iter 50 (2026-07-06): the 24h capabilities land on the SDK -------------

class _StubLLM:
    def __init__(self, text):
        self._text = text
        self.calls = []

    def complete(self, system, messages, **kw):
        self.calls.append({"system": system})

        class R:
            text = self._text
        return R()


def test_add_messages_ingests_conversation_with_event_time(tmp_path):
    """add(list[messages]) routes through the gated conversation ingestion
    (atomic extraction + consolidation) and stamps the EVENT time (v13)."""
    from verimem.client import Memory
    mem = Memory(tmp_path / "m.db", llm=_StubLLM("Rossi's budget is 500k"))
    ts = 1_750_000_000.0
    res = mem.add([{"role": "user", "content": "il budget di Rossi è 500k"}],
                  asserted_at=ts, conversation_id="c1")
    assert res["stored"] == 1
    hit = mem.search("Rossi budget", k=3)[0]
    f = mem.semantic.get(hit["id"])
    assert abs(float(f.asserted_at) - ts) < 1.0


def test_add_messages_forwards_user_name_identity_fix(tmp_path):
    """0.4.0 identity fix on the SDK verb: add(list, user_name=...) forwards the
    app-provided name to the extraction prompt (facts become retrieval-ready:
    'Alice ...' instead of 'The user ...')."""
    from verimem.client import Memory
    llm = _StubLLM("Alice moved to Berlin in March")
    mem = Memory(tmp_path / "m.db", llm=llm)
    mem.add([{"role": "user", "content": "I moved to Berlin in March."}],
            user_name="Alice", conversation_id="c2")
    assert any("Alice" in c["system"] for c in llm.calls), \
        "user_name must reach the extraction prompt"


def test_add_messages_without_llm_raises_clear_error(tmp_path):
    from verimem.client import Memory
    mem = Memory(tmp_path / "m.db")
    try:
        mem.add([{"role": "user", "content": "ciao"}])
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "llm" in str(exc).lower()


def test_add_text_accepts_asserted_at(tmp_path):
    from verimem.client import Memory
    mem = Memory(tmp_path / "m.db")
    ts = 1_750_000_000.0
    res = mem.add("Rossi's budget is 500k", asserted_at=ts)
    f = mem.semantic.get(res["id"])
    assert abs(float(f.asserted_at) - ts) < 1.0


def test_search_deep_finds_dormant(tmp_path):
    import time

    from verimem.client import Memory
    from verimem.semantic import Fact
    mem = Memory(tmp_path / "m.db")
    old = time.time() - 90 * 86400.0
    mem.semantic.store(Fact(id="dorm", proposition="Rossi budget set at 500k",
                            topic="t", created_at=old, last_verified_at=old),
                       embed="sync")
    assert all(h["id"] != "dorm" for h in mem.search("Rossi budget", k=5))
    got = mem.search("Rossi budget", k=5, deep=True)
    assert any(h["id"] == "dorm" for h in got), "deep surfaces the dormant fact"


def test_search_as_of_time_travels(tmp_path):
    import time

    from verimem.client import Memory
    from verimem.semantic import Fact
    mem = Memory(tmp_path / "m.db")
    now = time.time()
    D = 86400.0
    mem.semantic.store(Fact(id="o", proposition="income is 3500", topic="t",
                            asserted_at=now - 120 * D), embed="sync")
    mem.semantic.store(Fact(id="n", proposition="income is 5000", topic="t",
                            asserted_at=now - 30 * D), embed="sync")
    mem.semantic.supersede("o", "n", reason="update")
    april = mem.search("income", k=3, as_of=now - 60 * D)
    assert [h["id"] for h in april] == ["o"], "the past view serves the OLD truth"


def test_search_with_history_carries_transition(tmp_path):
    import time

    from verimem.client import Memory
    from verimem.semantic import Fact
    mem = Memory(tmp_path / "m.db")
    now = time.time()
    mem.semantic.store(Fact(id="o2", proposition="income is 3500", topic="t",
                            asserted_at=now - 120 * 86400.0), embed="sync")
    mem.semantic.store(Fact(id="n2", proposition="income is 5000", topic="t",
                            asserted_at=now - 30 * 86400.0), embed="sync")
    mem.semantic.supersede("o2", "n2", reason="update")
    hits = mem.search("income", k=3, with_history=True)
    top = next(h for h in hits if h["id"] == "n2")
    assert top["history"] and "3500" in top["history"][0]["text"], \
        "the transition story rides on the hit"


def test_explain_returns_trust_report(tmp_path):
    from verimem.client import Memory
    mem = Memory(tmp_path / "m.db")
    mem.add("Rossi's budget is 500k")
    rep = mem.explain("Rossi budget")
    assert rep["abstained"] is False and rep["n_facts"] >= 1
    # GLASS contract (known limit, open item for the critic): recall has no
    # relevance floor, so on a non-empty store an off-domain query still
    # returns top-k — the dossier DECLARES the weak relevance score instead
    # of hiding it (abstained=True only on zero hits, e.g. empty store).
    rep2 = mem.explain("marziani viola")
    assert rep2["facts"][0]["relevance"] is not None, "relevance declared"


def test_delete_purge_history_kills_the_whole_chain(tmp_path):
    """GDPR contract (iter 64, probe-confirmed defect): delete() alone removes
    ONE row — the superseded predecessors carrying the SAME sensitive datum
    survive and resurface via deep recall and as_of (time travel). For a
    judge-grade memory, "forget my salary" must forget the WHOLE chain:
    delete(fact_id, purge_history=True) removes predecessors, successors and
    their unresolved-dispute ledger entries. Default False = behaviour
    unchanged."""
    import time as _t

    from verimem.client import Memory
    from verimem.semantic import Fact
    from verimem.temporal_context import recall_as_of

    mem = Memory(tmp_path / "g.db")
    now = _t.time()
    D = 86400.0
    for fid, val, age in (("a", 3000, 120), ("b", 4000, 60), ("c", 5000, 10)):
        mem.semantic.store(Fact(id=fid, topic="t",
                                proposition=f"Rossi salary is {val} (SENSITIVE)",
                                asserted_at=now - age * D), embed="sync")
    mem.semantic.supersede("a", "b", reason="update")
    mem.semantic.supersede("b", "c", reason="update")

    assert mem.delete("c", purge_history=True) is True
    for fid in ("a", "b", "c"):
        assert mem.semantic.get(fid) is None, f"{fid} must be gone"
    deep = mem.semantic.recall("Rossi salary", k=5, deep=True,
                               include_superseded=True)
    assert not any("SENSITIVE" in getattr(f, "proposition", "")
                   for f, *_ in deep), "no resurrection via deep"
    past = recall_as_of(mem.semantic, "Rossi salary", when=now - 90 * D, k=5)
    assert past == [], "no resurrection via time travel"


def test_delete_default_still_single_row(tmp_path):
    from verimem.client import Memory
    from verimem.semantic import Fact
    mem = Memory(tmp_path / "g2.db")
    mem.semantic.store(Fact(id="x", proposition="old note", topic="t"), embed="sync")
    mem.semantic.store(Fact(id="y", proposition="new note", topic="t"), embed="sync")
    mem.semantic.supersede("x", "y", reason="u")
    assert mem.delete("y") is True
    assert mem.semantic.get("x") is not None, "default delete stays single-row"


def _seed_sensitive_chain(mem):
    import time as _t

    from verimem.semantic import Fact
    now = _t.time()
    D = 86400.0
    for fid, val, age in (("a", 3000, 120), ("b", 4000, 60), ("c", 5000, 10)):
        mem.semantic.store(Fact(id=fid, topic="t",
                                proposition=f"Rossi salary is {val} (SENSITIVE)",
                                asserted_at=now - age * D), embed="sync")
    mem.semantic.supersede("a", "b", reason="update")
    mem.semantic.supersede("b", "c", reason="update")
    return now


def test_purge_history_closes_over_a_prior_plain_delete(tmp_path):
    """Review 5-lenti C4: A->B->C same sensitive datum; a plain delete(B) —
    the DEFAULT of the same API, so any pre-existing DB has such holes — left
    A.superseded_by dangling. The later GDPR purge then stopped at the hole:
    purge(A) never reached C (still LIVE), purge(C) never reached A
    (resurrectable via as_of). The plain delete now re-links pointers through
    the deleted row, so the chain stays walkable in both directions."""
    from verimem.client import Memory

    # forward: purge(A) must reach C through the hole left by delete(B)
    mem = Memory(tmp_path / "fw.db")
    _seed_sensitive_chain(mem)
    assert mem.delete("b") is True                     # plain delete digs the hole
    assert mem.delete("a", purge_history=True) is True
    assert mem.semantic.get("c") is None, "forward closure must cross the hole"

    # backward: purge(C) must reach A through the same hole (fresh db)
    mem2 = Memory(tmp_path / "bw.db")
    now = _seed_sensitive_chain(mem2)
    assert mem2.delete("b") is True
    assert mem2.delete("c", purge_history=True) is True
    assert mem2.semantic.get("a") is None, "backward closure must cross the hole"
    from verimem.temporal_context import recall_as_of
    past = recall_as_of(mem2.semantic, "Rossi salary", when=now - 90 * 86400.0, k=5)
    assert past == [], "no resurrection via time travel after the purge"
