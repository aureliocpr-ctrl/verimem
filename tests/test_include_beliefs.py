"""``include_beliefs`` — the read-side opt-in for ``user_belief`` (Giro 2).

The write side ships (``af22b04`` status+hiding, ``0e670e1`` ingest tagging); this
locks the retrieval half: beliefs are OUT of the default view everywhere, and come
back ONLY on an explicit ``include_beliefs=True`` — on every recall branch, because
the branch asymmetries are exactly where past leaks lived (cycle-138 quarantined
back-door via search_facts; hunt-#3 cold-encode fallback dropping the orphan opt-in).

Covered branches, mirroring the ``include_orphaned`` architecture:
  * warm cache hot-path  -> ``include_beliefs=True`` must BYPASS the cache (the cache
    is the default view only) and the next default query must still hide beliefs
    (no cache poisoning in either direction);
  * legacy SQL path      -> conditional status clause;
  * cold-encode fallback -> flag forwarded to ``search_facts``;
  * ``search_facts``     -> keyword surface honours the flag;
  * ``recall_as_of``     -> time travel composes recall, flag forwarded;
  * ``client.search``    -> the SDK surface, both live and as_of branches.

Narrowness: ``include_beliefs=True`` un-hides user_belief ONLY — orphaned and
quarantined stay hidden (they have their own audit opt-in, ``include_orphaned``).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from verimem.semantic import Fact, SemanticMemory

BELIEF = "The vendor API is the fastest on the market"
CLAIM = "The vendor API supports webhooks for events"
QUERY = "vendor API fastest market webhooks"


def _mem() -> SemanticMemory:
    return SemanticMemory(db_path=Path(tempfile.mkdtemp()) / "s.db")


def _seed(m: SemanticMemory) -> None:
    m.store(Fact(proposition=BELIEF, topic="user/claim",
                 status="user_belief"), embed="sync")
    m.store(Fact(proposition=CLAIM, topic="user/fact",
                 status="model_claim"), embed="sync")


def _props(hits) -> list[str]:
    return [getattr(f, "proposition", "") for f, *_ in hits]


def test_recall_include_beliefs_surfaces_the_belief_warm_path():
    m = _mem()
    _seed(m)
    assert BELIEF not in _props(m.recall(QUERY, k=5)), "default must hide it"
    got = _props(m.recall(QUERY, k=5, include_beliefs=True))
    assert BELIEF in got, f"opt-in did not surface the belief: {got}"
    assert CLAIM in got, "opt-in must ADD beliefs, not replace the default view"


def test_include_beliefs_does_not_poison_the_corpus_cache():
    """The corpus cache is the DEFAULT view only. An opt-in query must not seed
    it with beliefs (default queries after it stay clean), and a warm default
    cache must not starve the opt-in (beliefs still come back after it)."""
    m = _mem()
    _seed(m)
    # warm the default cache first, then opt in, then default again
    assert BELIEF not in _props(m.recall(QUERY, k=5))
    assert BELIEF in _props(m.recall(QUERY, k=5, include_beliefs=True))
    assert BELIEF not in _props(m.recall(QUERY, k=5)), (
        "belief leaked into the default view after an include_beliefs query "
        "(corpus cache poisoned)")


def test_include_beliefs_is_narrow_orphaned_quarantined_stay_hidden():
    m = _mem()
    _seed(m)
    m.store(Fact(proposition="The vendor API was acquired by MegaCorp",
                 topic="user/dead", status="orphaned"), embed="sync")
    m.store(Fact(proposition="The vendor API leaks customer data",
                 topic="user/quar", status="quarantined"), embed="sync")
    got = _props(m.recall("vendor API acquired leaks fastest", k=10,
                          include_beliefs=True))
    assert BELIEF in got
    assert "The vendor API was acquired by MegaCorp" not in got, (
        "include_beliefs must NOT un-hide orphaned rows")
    assert "The vendor API leaks customer data" not in got, (
        "include_beliefs must NOT un-hide quarantined rows")


def test_search_facts_honours_include_beliefs():
    m = _mem()
    _seed(m)
    assert BELIEF not in [
        f.proposition for f in m.search_facts("vendor", limit=10)]
    got = [f.proposition
           for f in m.search_facts("vendor", limit=10, include_beliefs=True)]
    assert BELIEF in got, f"keyword surface ignored the opt-in: {got}"


def test_cold_encode_fallback_honours_include_beliefs(monkeypatch):
    """When the encode daemon is cold, recall degrades to the keyword fallback —
    the opt-in must survive the degradation (hunt-#3 lesson: the orphan opt-in
    was silently dropped on this exact path)."""
    import verimem.semantic as S

    m = _mem()
    _seed(m)
    monkeypatch.setattr(S, "_encode_prepared_within_budget",
                        lambda *a, **k: None)
    assert BELIEF not in _props(m.recall("vendor fastest", k=5)), \
        "cold default view must still hide beliefs"
    got = _props(m.recall("vendor fastest", k=5, include_beliefs=True))
    assert BELIEF in got, f"cold fallback dropped the opt-in: {got}"


def test_recall_as_of_forwards_include_beliefs():
    from verimem.temporal_context import recall_as_of

    m = _mem()
    _seed(m)
    import time
    now = time.time() + 60  # everything asserted by now
    assert BELIEF not in _props(recall_as_of(m, QUERY, when=now, k=5)), \
        "as_of default view must hide beliefs"
    got = _props(recall_as_of(m, QUERY, when=now, k=5, include_beliefs=True))
    assert BELIEF in got, f"as_of branch dropped the opt-in: {got}"


def test_fusion_extras_cannot_resurrect_beliefs_into_default_view(monkeypatch):
    """The sweep twin the first 7 tests missed (corpora <50 skip the fusion
    floor): PPR/BM25 fusion — default-ON — MATERIALIZES extra-only fact ids via
    ``get(live_only=True)``. If that gate doesn't treat ``user_belief`` as
    hidden, a belief whose text lexically matches the query re-enters the
    DEFAULT view through the fusion side-door, bypassing every SQL filter
    (same leak class as HIGH-2 anchor/entity and the cycle-138 back-door)."""
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "1")
    monkeypatch.setenv("ENGRAM_PPR_FUSION_FLOOR", "0")   # tiny corpus, fusion ON
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")      # isolate the fusion
    m = _mem()
    _seed(m)
    got = _props(m.recall(QUERY, k=5))
    assert BELIEF not in got, (
        f"user_belief resurrected into the DEFAULT view via fusion extras: {got}")
    # and the opt-in still works with fusion on
    got_opt = _props(m.recall(QUERY, k=5, include_beliefs=True))
    assert BELIEF in got_opt


def test_composer_never_composes_over_user_beliefs():
    """Laundering guard: composition derives new admitted facts from stored
    ones. An unverified user assertion must not become an ingredient — the
    derived fact would carry the belief's content WITHOUT its low-trust label
    (worse than serving the belief: the origin disappears)."""
    from verimem.composer import compose_once

    class _M:  # composer only touches mem.semantic
        pass

    m = _M()
    m.semantic = _mem()
    m.semantic.store(Fact(proposition="Rex is a labrador.",
                          topic="user/claim", status="user_belief"),
                     embed="sync")
    m.semantic.store(Fact(proposition="A labrador is a dog.",
                          topic="user/fact", status="model_claim"),
                     embed="sync")
    report = compose_once(m)
    # the chain rex->labrador->dog must NOT fire: its first hop is a belief
    assert report.get("admitted", 0) == 0, (
        f"composition laundered a user_belief into a derived fact: {report}")


def test_client_search_exposes_include_beliefs_with_status():
    from verimem.client import Memory

    mem = Memory(path=Path(tempfile.mkdtemp()) / "sem.db")
    mem.semantic.store(Fact(proposition=BELIEF, topic="user/claim",
                            status="user_belief"), embed="sync")
    mem.semantic.store(Fact(proposition=CLAIM, topic="user/fact",
                            status="model_claim"), embed="sync")
    default_texts = [h["text"] for h in mem.search(QUERY, k=5)]
    assert BELIEF not in default_texts, "SDK default view must hide beliefs"
    hits = mem.search(QUERY, k=5, include_beliefs=True)
    by_text = {h["text"]: h for h in hits}
    assert BELIEF in by_text, f"SDK opt-in did not surface the belief: {list(by_text)}"
    assert by_text[BELIEF]["status"] == "user_belief", (
        "the caller must SEE the epistemic label to caveat the answer")
