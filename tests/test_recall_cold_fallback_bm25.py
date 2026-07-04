"""Cold-encode fallback ri-ranka i candidati keyword per BM25, non per recency
(backlog recall-quality, audit 2026-06-14, conf 0.82).

Quando l'encode della query scade (daemon cold/contended -> q_emb=None), il
recall cade su un keyword fallback che `search_facts` ordina per created_at DESC.
Il taglio [:k] sceglieva quindi i k piu' RECENTI, non i piu' RILEVANTI: un gold
col token raro ma vecchio cadeva fuori dal top-k pur essendo nel pool. Ora i
candidati vengono ri-rankati per BM25 prima del taglio.

Cold-path forzato in modo DETERMINISTICO e ROBUSTO ALL'ORDINE dei test: lo store
usa l'encode REALE (fatti embeddati), poi `embedding.encode` viene fatto sollevare
EncodeDelegateUnavailable -> _encode_prepared_within_budget ritorna None
(semantic.py:141-142) SOLO per il recall. NON si monkeypatcha la funzione-modulo
_encode_prepared_within_budget (fragile: sotto pytest-randomly perdeva effetto in
certi ordini -> cold-path non scattava -> flaky in CI, ci 27497341185).
"""
from __future__ import annotations

import time

from engram.semantic import Fact, SemanticMemory


def _force_cold_encode(monkeypatch):
    """Da chiamare DOPO gli store: embedding.encode -> EncodeDelegateUnavailable,
    cosi' il budget-encode del RECALL degrada a None (cold path) in modo
    deterministico, senza toccare lo store gia' avvenuto ne' dipendere dall'ordine
    dei test (monkeypatch su embedding.encode, ripristinato a fine test)."""
    from engram import embedding

    def _raise(*a, **k):
        raise embedding.EncodeDelegateUnavailable("forced cold for test")

    monkeypatch.setattr(embedding, "encode", _raise)


def test_cold_fallback_reranks_by_bm25_not_recency(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    # gold: stored per PRIMO (created_at piu' vecchio), porta il token RARO.
    gold = Fact(proposition="incident deploy log error trace deadbeef9999 origin",
                topic="t")
    sm.store(gold, embed="sync")
    # 8 distrattori PIU' RECENTI col token COMUNE 'deploy' ma NON il raro: il gold
    # finisce 9o per recency -> dentro il pool k*4=12 ma fuori dai k=3 piu' recenti.
    for i in range(8):
        sm.store(Fact(proposition=f"deploy routine status note number {i} nominal",
                      topic="t"), embed="sync")

    _force_cold_encode(monkeypatch)  # ora il recall va in cold-path (q_emb=None)
    hits = sm.recall("deploy deadbeef9999", k=3)
    assert getattr(sm, "_recall_degraded_count", 0) > 0, \
        "il test deve davvero esercitare il cold-encode path (q_emb=None)"
    ids = {f.id for f, _ in hits}
    assert gold.id in ids, (
        "cold-fallback: il gold (token raro) deve entrare nel top-k via BM25, "
        "non essere sepolto dai distrattori piu' recenti (recency)"
    )


def test_cold_fallback_failsoft_when_bm25_empty(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    sm.store(Fact(proposition="alpha note about quarterly budgets", topic="t"),
             embed="sync")
    monkeypatch.setattr("engram.bm25_rank.bm25_fact_ids", lambda *a, **k: [])
    _force_cold_encode(monkeypatch)
    hits = sm.recall("alpha budgets", k=3)  # nessun crash
    assert any("alpha" in f.proposition for f, _ in hits), \
        "fail-soft: senza BM25 il cold-fallback ritorna comunque i keyword-hit"


def test_force_cold_encode_helper_is_deterministic(monkeypatch):
    """Guardia: il helper forza q_emb=None a prescindere dall'ordine (no flaky)."""
    _force_cold_encode(monkeypatch)
    import engram.semantic as _sem
    from engram import embedding
    q = _sem._encode_prepared_within_budget(embedding.as_query("x"), 5.0)
    assert q is None, "embedding.encode->EncodeDelegateUnavailable deve dare q_emb=None"


def test_cold_fallback_is_instant(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    sm.store(Fact(proposition="quick note", topic="t"), embed="sync")
    _force_cold_encode(monkeypatch)
    t0 = time.perf_counter()
    sm.recall("quick", k=3)
    assert time.perf_counter() - t0 < 5.0, "il cold-fallback non deve appendere"


def test_cold_path_gains_ppr_signal_when_fusion_on(tmp_path, monkeypatch):
    """#2 default-ON prereq: con ENGRAM_PPR_FUSION=1 anche il ramo COLD recupera
    un gold entity-linked che il keyword-fallback manca (prima solo i 3 path warm
    lo facevano -> asimmetria cache-vs-cold)."""
    from engram.entity_kg import Entity, EntityStore
    from engram.entity_populate import entity_kg_path_for

    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENGRAM_PPR_FUSION_FLOOR", "0")  # corpus minimo: il fusion e' il soggetto
    monkeypatch.setattr("engram.bm25_rank.bm25_fact_ids", lambda *a, **k: [])  # isola il PPR
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")

    # gold: lessicalmente LONTANO dal query (il keyword-fallback NON lo trova),
    # ma entity-linked all'entita' che il query menziona.
    gold = Fact(proposition="the quarterly budget spreadsheet was archived in march",
                topic="t/gold")
    sm.store(gold, embed="sync")
    for i in range(3):  # decoy che matchano il keyword del query
        sm.store(Fact(proposition=f"alpha_service deployment runbook step {i}",
                      topic="t/d"), embed="sync")

    es = EntityStore(db_path=entity_kg_path_for(sm.db_path))
    eid = es.store(Entity(canonical_name="alpha_service", type="module"))
    es.add_edge(eid, eid, "self", weight=1.0)
    es.link_fact(gold.id, eid)

    q = "alpha_service deployment"
    _force_cold_encode(monkeypatch)  # forza il ramo cold per ENTRAMBI i recall

    monkeypatch.setenv("ENGRAM_PPR_FUSION", "0")  # OFF esplicito (post flip default-ON)
    sm._recall_es = None
    off = {f.id for f, _ in sm.recall(q, k=5)}

    monkeypatch.setenv("ENGRAM_PPR_FUSION", "1")
    sm._recall_es = None
    on = {f.id for f, _ in sm.recall(q, k=5)}

    assert gold.id not in off, "cold OFF: il gold entity-linked (keyword-miss) non c'e'"
    assert gold.id in on, "cold ON: il PPR recupera il gold anche sul ramo cold (#2)"
