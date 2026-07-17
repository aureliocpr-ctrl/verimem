"""Review 5-lenti C5: a corpus-cache rebuild driven by a CROSS-PROCESS commit
(SQLite data_version changed; this instance's _cache_version did not) used to
be saved under the SAME generation number. Version-keyed consumers — the ANN
pool, ``query_pool(..., version=self._cache_version)`` — then kept serving
indices computed for the OLD matrix: IndexError on the shrunken facts list
(``facts = [facts[i] for i in _pool]``) or silently wrong rows, persisting
until some local mutation happened to bump the counter.

The ANN cache's own contract is already covered (test_ann_background_build:
never serve a mismatched version) — the missing half was the generation bump,
tested here hermetically (no faiss needed: the invariant lives in semantic).
Full-stack repro with a live HNSW index: benchmark/results/
workflow_5lenti_findings.json (C5).
"""
from __future__ import annotations

from verimem.semantic import Fact, SemanticMemory


def test_cross_process_delete_opens_a_new_cache_generation(tmp_path) -> None:
    sm_a = SemanticMemory(db_path=tmp_path / "s.db")
    for i in range(6):
        sm_a.store(Fact(id=f"f{i}", proposition=f"shared note {i}", topic="t"),
                   embed="sync")
    assert sm_a.recall("shared note", k=3)  # builds the corpus cache
    gen_before = sm_a._cache_version
    facts_before = len(sm_a._corpus_cache["facts"])

    sm_b = SemanticMemory(db_path=tmp_path / "s.db")  # e.g. the GDPR script
    assert sm_b.delete("f0") is True

    assert sm_a.recall("shared note", k=3)  # revalidates -> rebuild
    assert len(sm_a._corpus_cache["facts"]) == facts_before - 1, \
        "rebuild picked up the cross-process delete"
    assert sm_a._cache_version != gen_before, (
        "a data_version-driven rebuild must open a NEW generation — the ANN "
        "pool is keyed on _cache_version and would otherwise serve indices "
        "computed for the OLD matrix (review C5)")
