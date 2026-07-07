"""DocumentIndex — semantic search over whole files with exact citation (roadmap #1).

The missing middle of the document RAG pipeline:

    file --extract_text--> text --chunk_text--> chunks --embed--> THIS INDEX
    search(query) -> chunks with (source_id, version, start, end) = exact citation

Design:
  - Versioning is delegated to the Documents tier (``DocumentStore``: snapshot
    per content-hash, idempotent re-ingest). Same content -> no re-chunking.
  - Only the LATEST version of each source is searched — an updated document
    supersedes its older chunks (no stale citations).
  - The embedder is INJECTED (any object with ``encode(list[str]) -> vectors``);
    default lazily adapts ``engram.embedding.encode`` (the shared model/service).
    Tests run hermetic with a fake — no model load.
  - Provenance invariant inherited from ``chunking``: ``original[start:end] ==
    chunk text`` exactly, so every search hit can cite file + offsets. This is
    the provenance moat applied to documents (legal cases, books, code).

Isolated store (own SQLite), like the Documents tier: NOT wired into
``SemanticMemory.recall`` — document chunks are cited context, not accepted facts.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np

from .chunking import chunk_text
from .documents import DocumentStore
from .file_extract import extract_text

_SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id     TEXT NOT NULL,
    source_id  TEXT NOT NULL,
    version    INTEGER NOT NULL,
    idx        INTEGER NOT NULL,
    start      INTEGER NOT NULL,
    end        INTEGER NOT NULL,
    text       TEXT NOT NULL,
    uri        TEXT DEFAULT '',
    vec        BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_id, version);
"""


class _DefaultEmbedder:
    """Adapter over the shared ``engram.embedding.encode`` (model or service)."""

    def encode(self, texts: list[str]) -> np.ndarray:
        from .embedding import encode

        return np.asarray(encode(list(texts)), dtype=np.float32)


class DocumentIndex:
    """Chunk-level semantic index with exact provenance over the Documents tier."""

    def __init__(self, db_path: Path | str | None = None, embedder=None,
                 chunk_size: int = 1000, overlap: int = 150,
                 document_store: DocumentStore | None = None) -> None:
        self.db_path = Path(db_path) if db_path else (
            Path(DocumentStore().db_path).parent / "document_index.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.embedder = embedder or _DefaultEmbedder()
        self.chunk_size = int(chunk_size)
        self.overlap = int(overlap)
        # Snapshot/versioning tier lives NEXT TO the index db by default so a
        # tmp-dir test stays fully isolated from the user's real Documents tier.
        self.docs = document_store or DocumentStore(
            db_path=self.db_path.parent / "documents.db")
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    # --- write ----------------------------------------------------------
    def index_document(self, source_id: str, content: str, uri: str = "",
                       meta: dict | None = None) -> dict:
        """Snapshot + chunk + embed ``content``. Idempotent per content-hash.

        Returns ``{source_id, doc_id, version, is_new, chunks_indexed}``.
        Same content re-indexed -> ``chunks_indexed == 0`` (no duplicate work).
        """
        snap = self.docs.ingest(source_id, content, uri=uri, meta=meta)
        if not snap["is_new"]:
            return {"source_id": source_id, "doc_id": snap["id"],
                    "version": snap["version"], "is_new": False,
                    "chunks_indexed": 0}
        chunks = chunk_text(content, chunk_size=self.chunk_size,
                            overlap=self.overlap)
        if chunks:
            vecs = np.asarray(self.embedder.encode([c.text for c in chunks]),
                              dtype=np.float32)
            conn = self._connect()
            try:
                conn.executemany(
                    "INSERT INTO chunks(doc_id, source_id, version, idx, start, "
                    "end, text, uri, vec) VALUES(?,?,?,?,?,?,?,?,?)",
                    [(snap["id"], source_id, snap["version"], c.index, c.start,
                      c.end, c.text, uri, vecs[i].tobytes())
                     for i, c in enumerate(chunks)],
                )
                conn.commit()
            finally:
                conn.close()
        return {"source_id": source_id, "doc_id": snap["id"],
                "version": snap["version"], "is_new": True,
                "chunks_indexed": len(chunks)}

    def index_file(self, path: Path | str, source_id: str | None = None,
                   meta: dict | None = None) -> dict:
        """Extract text from a real file (pdf/docx/html/txt) and index it."""
        p = Path(path)
        text = extract_text(p)
        m = dict(meta or {})
        m.setdefault("filename", p.name)
        return self.index_document(source_id if source_id is not None else str(p),
                                   text, uri=f"file://{p}", meta=m)

    # --- read -----------------------------------------------------------
    def search(self, query: str, k: int = 5) -> list[dict]:
        """Cosine top-k over the LATEST version of every source.

        Each hit carries the exact citation: ``{text, score, source_id, version,
        start, end, uri, doc_id}`` with ``original[start:end] == text``.
        """
        q = (query or "").strip()
        if not q:
            return []
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT c.* FROM chunks c JOIN (SELECT source_id, MAX(version) AS mv "
                "FROM chunks GROUP BY source_id) m "
                "ON c.source_id = m.source_id AND c.version = m.mv",
            ).fetchall()
        finally:
            conn.close()
        if not rows:
            return []
        qv = np.asarray(self.embedder.encode([q]), dtype=np.float32)[0]
        qn = float(np.linalg.norm(qv)) or 1.0
        scored = []
        for r in rows:
            v = np.frombuffer(r["vec"], dtype=np.float32)
            vn = float(np.linalg.norm(v)) or 1.0
            score = float(np.dot(qv, v) / (qn * vn))
            scored.append((score, r))
        scored.sort(key=lambda t: (-t[0], t[1]["source_id"], t[1]["idx"]))
        return [{"text": r["text"], "score": round(s, 6),
                 "source_id": r["source_id"], "version": r["version"],
                 "start": r["start"], "end": r["end"], "uri": r["uri"] or "",
                 "doc_id": r["doc_id"]}
                for s, r in scored[:max(1, int(k))]]

    # --- discovery ------------------------------------------------------
    def stats(self) -> dict:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS n, COUNT(DISTINCT source_id) AS sources "
                "FROM chunks").fetchone()
            return {"chunks": int(row["n"]), "sources": int(row["sources"]),
                    "db_path": str(self.db_path)}
        finally:
            conn.close()


__all__ = ["DocumentIndex"]


def _self_check() -> dict:  # pragma: no cover - manual smoke helper
    """Quick manual smoke: python -c "from engram.document_index import _self_check; print(_self_check())" """
    import tempfile

    class _E:
        def encode(self, texts):
            import hashlib
            out = []
            for t in texts:
                h = hashlib.sha256((t or "").encode()).digest()
                out.append([b / 255.0 for b in h[:16]])
            return out

    d = Path(tempfile.mkdtemp()) / "x.db"
    ix = DocumentIndex(db_path=d, embedder=_E())
    ix.index_document("s", "hello world " * 50)
    return ix.stats()
