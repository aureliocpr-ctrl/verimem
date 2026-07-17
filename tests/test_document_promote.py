"""doc->Fact GATED promotion (roadmap #1 last brick): a retrieved document chunk
becomes a Fact in the recall corpus THROUGH the anti-confab gate, with the exact
file citation as provenance. The chunk itself never bypasses the gate: it enters
as a low-trust model_claim whose verified_by IS the citation (file + offsets) —
the reader can always open the file at the exact position and check.
"""
from __future__ import annotations

import math
import re

from verimem.document_index import DocumentIndex
from verimem.document_promote import promote_chunk_to_fact
from verimem.semantic import SemanticMemory


class _FakeEmbedder:
    DIM = 32

    def encode(self, texts):
        out = []
        for t in texts:
            v = [0.0] * self.DIM
            for tok in re.findall(r"[a-z0-9]+", (t or "").lower()):
                v[hash(tok) % self.DIM] += 1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out


def _indexed_hit(tmp_path):
    idx = DocumentIndex(db_path=tmp_path / "docidx.db", embedder=_FakeEmbedder(),
                        chunk_size=200, overlap=40)
    text = ("Norme varie del condominio. " * 8 +
            "Il rogito della casa di Albi risale al 12 marzo 2019. " +
            "Altre clausole e dettagli minori. " * 8)
    idx.index_document("atti/rogito.txt", text, uri="file://atti/rogito.txt")
    hits = idx.search("data del rogito della casa", k=1)
    assert hits
    return hits[0]


def test_promote_creates_gated_fact_with_citation(tmp_path) -> None:
    hit = _indexed_hit(tmp_path)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    res = promote_chunk_to_fact(sm, hit, topic="documents/promoted", embed="sync")
    assert res["stored"] is True
    f = sm.get(res["fact_id"])
    assert f is not None
    assert f.status == "model_claim", "promotion never launders trust"
    assert f.writer_role == "document_promote", "no trusted-hook bypass"
    cite = f"file:{hit['source_id']}:{hit['start']}-{hit['end']}"
    blob = " ".join([*(f.verified_by or []), *(f.source_episodes or [])])
    assert cite in blob, f"exact citation must be in provenance: {blob!r}"
    assert hit["text"].strip()[:40] in f.proposition, "chunk text preserved"


def test_promote_with_claim_override_keeps_citation(tmp_path) -> None:
    # The caller can promote a DISTILLED claim (one sentence) instead of the raw
    # chunk — the citation still anchors it to the exact file position.
    hit = _indexed_hit(tmp_path)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    res = promote_chunk_to_fact(
        sm, hit, claim="Il rogito della casa di Albi e del 12 marzo 2019.",
        topic="documents/promoted", embed="sync")
    f = sm.get(res["fact_id"])
    assert "12 marzo 2019" in f.proposition
    assert f"file:{hit['source_id']}" in " ".join([*(f.verified_by or []),
                                                   *(f.source_episodes or [])])


def test_promote_rejects_empty_chunk(tmp_path) -> None:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    res = promote_chunk_to_fact(sm, {"text": "  ", "source_id": "x",
                                     "start": 0, "end": 2, "version": 1})
    assert res["stored"] is False and "error" in res
