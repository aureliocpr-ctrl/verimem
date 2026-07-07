"""DocumentIndex — the semantic layer over the Documents tier (roadmap #1).

file -> extract_text -> chunk_text -> embed -> store -> search(query) returns
chunks WITH exact provenance (source_id, version, start, end): the citation moat
applied to documents. The embedder is INJECTED so these tests run hermetic with a
deterministic fake (no model download, no GPU, no load) — the real
sentence-transformers embedder plugs in via the same interface.
"""
from __future__ import annotations

import math
import re

from engram.document_index import DocumentIndex


class FakeEmbedder:
    """Deterministic bag-of-words hashing embedder (32-dim, L2-normalized)."""

    DIM = 32

    def encode(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            v = [0.0] * self.DIM
            for tok in re.findall(r"[a-z0-9]+", (t or "").lower()):
                v[hash(tok) % self.DIM] += 1.0
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
        return out


def _mk(tmp_path) -> DocumentIndex:
    return DocumentIndex(db_path=tmp_path / "docidx.db", embedder=FakeEmbedder(),
                         chunk_size=200, overlap=40)


def test_index_document_chunks_and_counts(tmp_path) -> None:
    idx = _mk(tmp_path)
    text = ("The reactor manual describes safety valves. " * 12 +
            "Emergency shutdown requires the red lever. " * 12)
    r = idx.index_document("manual", text, uri="file://manual.txt")
    assert r["chunks_indexed"] > 1
    assert r["source_id"] == "manual"


def test_search_returns_relevant_chunk_with_exact_provenance(tmp_path) -> None:
    idx = _mk(tmp_path)
    filler = "Cooking pasta needs salted water and patience. " * 10
    needle = "The zorbium capacitor requires quarterly calibration by a technician. "
    text = filler + needle + filler
    idx.index_document("manual", text)

    hits = idx.search("zorbium capacitor calibration", k=3)
    assert hits, "search must return hits"
    top = hits[0]
    assert "zorbium" in top["text"].lower()
    # PROVENANCE: offsets must slice the ORIGINAL text back to the chunk exactly
    assert text[top["start"]:top["end"]] == top["text"]
    assert top["source_id"] == "manual"
    assert top["version"] >= 1


def test_reindex_same_content_is_idempotent(tmp_path) -> None:
    idx = _mk(tmp_path)
    text = "Stable content that does not change. " * 20
    r1 = idx.index_document("doc", text)
    r2 = idx.index_document("doc", text)
    assert r2["is_new"] is False
    assert r2["chunks_indexed"] == 0, "same content -> no re-chunking"
    # search still works and cites version 1
    hits = idx.search("stable content", k=2)
    assert hits and hits[0]["version"] == r1["version"]


def test_new_version_supersedes_in_search(tmp_path) -> None:
    idx = _mk(tmp_path)
    idx.index_document("doc", "Old fact: the meeting is on Monday. " * 8)
    idx.index_document("doc", "New fact: the meeting moved to Friday. " * 8)
    hits = idx.search("meeting day", k=3)
    assert hits
    # only the LATEST version of a source is searched
    assert all(h["version"] == 2 for h in hits if h["source_id"] == "doc")
    assert "friday" in hits[0]["text"].lower()


def test_index_file_txt(tmp_path) -> None:
    f = tmp_path / "notes.txt"
    f.write_text("Project kickoff notes: the deadline is March 3rd. " * 10,
                 encoding="utf-8")
    idx = _mk(tmp_path)
    r = idx.index_file(f)
    assert r["chunks_indexed"] >= 1
    hits = idx.search("project deadline", k=2)
    assert hits and "march" in hits[0]["text"].lower()


def test_search_empty_index_returns_empty(tmp_path) -> None:
    idx = _mk(tmp_path)
    assert idx.search("anything", k=3) == []
