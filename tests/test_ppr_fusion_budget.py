"""PPR fusion rispetta un wall-clock budget (default-ON prereq #1, audit round-2
2026-06-14).

Il fusion ON-path eseguiva l'entity-PPR power iteration (nx.pagerank max_iter=200
sul grafo full-corpus) SINCRONO e non-cappato — l'unico costo non-budgetato del
recall ON (il CE-rerank ha gia' il suo budget). Sotto contention CPU e' lo stesso
failure-mode di hang gia' fixato per il rerank. Ora il fusion gira su un
daemon-thread joinato per un budget; overrun -> si tengono gli hits reranked.
"""
from __future__ import annotations

import time

from verimem.semantic import Fact, SemanticMemory


def test_ppr_fusion_respects_wallclock_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "1")
    monkeypatch.setenv("ENGRAM_PPR_FUSION_FLOOR", "0")  # corpus minimo: testa il budget, non il floor
    monkeypatch.setenv("ENGRAM_PPR_FUSION_BUDGET_S", "0.05")

    def _slow_ppr(*a, **k):  # simula il power-iteration non-cappato sotto contention
        time.sleep(2.0)
        return []

    monkeypatch.setattr("verimem.ppr_seed.ppr_seeded_fact_ids", _slow_ppr)
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    hits = [(Fact(proposition="x", topic="t"), 0.9)]

    t0 = time.perf_counter()
    out = sm._maybe_fuse_ppr("some query about alpha", hits, 5)
    elapsed = time.perf_counter() - t0

    assert elapsed < 1.0, (
        f"il fusion deve rispettare il budget 0.05s, non aspettare i 2s del PPR "
        f"lento (elapsed {elapsed:.2f}s)"
    )
    assert out == hits, "su overrun gli hits (gia' reranked) restano invariati"


def test_ppr_fusion_budget_zero_runs_synchronously(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "1")
    monkeypatch.setenv("ENGRAM_PPR_FUSION_FLOOR", "0")  # corpus minimo: testa il budget, non il floor
    monkeypatch.setenv("ENGRAM_PPR_FUSION_BUDGET_S", "0")  # 0 = no cap
    called: dict[str, bool] = {}

    def _fast_ppr(*a, **k):
        called["ppr"] = True
        return []

    monkeypatch.setattr("verimem.ppr_seed.ppr_seeded_fact_ids", _fast_ppr)
    monkeypatch.setattr("verimem.bm25_rank.bm25_fact_ids", lambda *a, **k: [])
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    hits = [(Fact(proposition="x", topic="t"), 0.9)]

    out = sm._maybe_fuse_ppr("q", hits, 5)
    assert called.get("ppr"), "budget=0 deve eseguire il fusion SINCRONO (PPR chiamato)"
    assert out == hits, "nessun extra signal -> hits invariati"


def test_fusion_skipped_below_corpus_floor(tmp_path, monkeypatch):
    """#3 default-ON prereq: su corpus < floor la fusione e' saltata (overhead)."""
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "1")
    monkeypatch.setenv("ENGRAM_PPR_FUSION_FLOOR", "50")
    called: dict[str, bool] = {}

    def _spy(*a, **k):
        called["ppr"] = True
        return []

    monkeypatch.setattr("verimem.ppr_seed.ppr_seeded_fact_ids", _spy)
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    sm.store(Fact(proposition="x note one", topic="t"), embed="sync")  # corpus=1 < 50
    hits = [(Fact(proposition="y", topic="t"), 0.9)]
    out = sm._maybe_fuse_ppr("query", hits, 5)
    assert "ppr" not in called, "sotto il corpus-floor il PPR non deve girare"
    assert out == hits, "sotto il floor -> hits invariati (no fusione)"


def test_fusion_runs_above_corpus_floor(tmp_path, monkeypatch):
    """floor=0 -> la fusione gira (la corpus-size non la blocca)."""
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "1")
    monkeypatch.setenv("ENGRAM_PPR_FUSION_FLOOR", "0")
    monkeypatch.setenv("ENGRAM_PPR_FUSION_BUDGET_S", "0")  # sincrono, deterministico
    called: dict[str, bool] = {}

    def _spy(*a, **k):
        called["ppr"] = True
        return []

    monkeypatch.setattr("verimem.ppr_seed.ppr_seeded_fact_ids", _spy)
    monkeypatch.setattr("verimem.bm25_rank.bm25_fact_ids", lambda *a, **k: [])
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    sm.store(Fact(proposition="x note one", topic="t"), embed="sync")
    hits = [(Fact(proposition="y", topic="t"), 0.9)]
    sm._maybe_fuse_ppr("query", hits, 5)
    assert called.get("ppr"), "floor=0 -> la fusione gira (PPR chiamato)"


def test_fusion_is_default_on_after_flip(tmp_path, monkeypatch):
    """Flip 2026-06-15: SENZA ENGRAM_PPR_FUSION il fusion e' ATTIVO (default-ON)."""
    monkeypatch.delenv("ENGRAM_PPR_FUSION", raising=False)  # nessun env -> default
    monkeypatch.setenv("ENGRAM_PPR_FUSION_FLOOR", "0")
    monkeypatch.setenv("ENGRAM_PPR_FUSION_BUDGET_S", "0")
    called: dict[str, bool] = {}

    def _spy(*a, **k):
        called["ppr"] = True
        return []

    monkeypatch.setattr("verimem.ppr_seed.ppr_seeded_fact_ids", _spy)
    monkeypatch.setattr("verimem.bm25_rank.bm25_fact_ids", lambda *a, **k: [])
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    sm.store(Fact(proposition="x note one", topic="t"), embed="sync")
    sm._maybe_fuse_ppr("query", [(Fact(proposition="y", topic="t"), 0.9)], 5)
    assert called.get("ppr"), "senza env il fusion deve essere ON di default (flip)"


def test_fusion_opt_out_via_env(tmp_path, monkeypatch):
    """ENGRAM_PPR_FUSION=0 disattiva il fusion (opt-out byte-identico al pre-flip)."""
    monkeypatch.setenv("ENGRAM_PPR_FUSION", "0")
    monkeypatch.setenv("ENGRAM_PPR_FUSION_FLOOR", "0")
    called: dict[str, bool] = {}
    monkeypatch.setattr("verimem.ppr_seed.ppr_seeded_fact_ids",
                        lambda *a, **k: called.update(ppr=True) or [])
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    hits = [(Fact(proposition="y", topic="t"), 0.9)]
    out = sm._maybe_fuse_ppr("query", hits, 5)
    assert "ppr" not in called, "ENGRAM_PPR_FUSION=0 -> fusion OFF (opt-out)"
    assert out == hits
