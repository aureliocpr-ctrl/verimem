"""Tier Documents/Sources — snapshot versionati-per-hash delle fonti.

Quarto store ISOLATO (come Tier C ``transcript_index``): snapshot grezzi delle
fonti/documenti (MD, articoli, pagine web) tenuti FUORI dal corpus di recall
accettato (``semantic.db``). Scopi:
  (a) continuità-MD versionata: linki un MD -> Engram ne tiene copie per-hash;
  (b) base d'ingest per la distillazione *gated* -> ``facts`` con provenienza
      (fase successiva, NON in questo modulo).

Invarianti di sicurezza (perché NON inquina il corpus accettato):
  - **Store SEPARATO** (DB dedicato, mai ``semantic.db``) -> isolamento
    by-construction. NON è wired in ``SemanticMemory.recall``.
  - Nessun embedding qui: è uno store documentale grezzo, non semantico. La
    promozione document -> Fact (gated, con provenance) è una fase successiva.

Versioning:
  - chiave di versione = ``(source_id, content_hash)`` con ``content_hash =
    sha256(content)``.
  - re-ingest dello STESSO contenuto sullo STESSO source_id = IDEMPOTENTE
    (nessuna nuova riga, ritorna l'esistente).
  - contenuto CAMBIATO sullo stesso source_id -> versione incrementale.
  - source_id diversi hanno versioning indipendente.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from .config import CONFIG


def _content_hash(content: str) -> str:
    """sha256 esadecimale del contenuto (chiave di versione)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@dataclass
class Document:
    """Snapshot versionato di una fonte/documento (grezzo, non semantico)."""

    source_id: str
    content: str
    uri: str = ""
    meta: dict = field(default_factory=dict)
    content_hash: str = ""
    version: int = 0
    fetched_at: float = 0.0
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])


def default_db_path() -> Path:
    """Path di default del tier documents — DB dedicato, SEPARATO da semantic.db.

    Override con env ``HIPPO_DOCUMENTS_DB`` (config ops + isolamento nei test).
    """
    env = os.environ.get("HIPPO_DOCUMENTS_DB", "").strip()
    if env:
        return Path(env)
    return Path(CONFIG.data_dir) / "documents" / "documents.db"


_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id            TEXT PRIMARY KEY,
    source_id     TEXT NOT NULL,
    version       INTEGER NOT NULL,
    content_hash  TEXT NOT NULL,
    content       TEXT NOT NULL,
    uri           TEXT DEFAULT '',
    meta          TEXT DEFAULT '{}',
    fetched_at    REAL DEFAULT 0,
    UNIQUE(source_id, content_hash)
);
CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source_id);
"""


class DocumentStore:
    """Store isolato di snapshot versionati-per-hash. NON wired nel recall."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else default_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
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

    # --- write ---------------------------------------------------------
    def ingest(self, source_id: str, content: str, uri: str = "",
               meta: dict | None = None, fetched_at: float = 0.0,
               principal: str | None = None) -> dict:
        """Persisti uno snapshot. IDEMPOTENTE su ``(source_id, content_hash)``.

        Ritorna ``{id, version, is_new, content_hash}``:
          - contenuto già presente per il source_id -> riga esistente, ``is_new=False``;
          - contenuto nuovo -> versione = ``max(version)+1`` per quel source_id, ``is_new=True``.

        ``principal`` (P0 v9): server-stamped identity of WHO indexed this
        snapshot → ``meta.indexed_by`` + ``meta.indexed_at``. Recorded only on
        the FIRST ingest of a given content (idempotent re-ingest never
        rewrites the original provenance — that first identity is exactly what
        the poison-then-cite rule needs). Absent when no principal is given:
        absence = untrusted class, never a fake default.
        """
        chash = _content_hash(content)
        conn = self._connect()
        try:
            existing = conn.execute(
                "SELECT id, version FROM documents WHERE source_id=? AND content_hash=?",
                (source_id, chash),
            ).fetchone()
            if existing is not None:
                return {"id": existing["id"], "version": existing["version"],
                        "is_new": False, "content_hash": chash}
            row = conn.execute(
                "SELECT COALESCE(MAX(version), 0) AS m FROM documents WHERE source_id=?",
                (source_id,),
            ).fetchone()
            version = int(row["m"]) + 1
            doc_id = uuid.uuid4().hex[:16]
            m = dict(meta or {})
            if principal is not None:
                m["indexed_by"] = principal
                m["indexed_at"] = time.time()
            conn.execute(
                "INSERT INTO documents(id, source_id, version, content_hash, content, "
                "uri, meta, fetched_at) VALUES(?,?,?,?,?,?,?,?)",
                (doc_id, source_id, version, chash, content, uri,
                 json.dumps(m), float(fetched_at)),
            )
            conn.commit()
            return {"id": doc_id, "version": version, "is_new": True, "content_hash": chash}
        finally:
            conn.close()

    def ingest_file(self, path: Path | str, source_id: str | None = None,
                    meta: dict | None = None, fetched_at: float = 0.0,
                    principal: str | None = None) -> dict:
        """Snapshot di un file (caso d'uso continuità-MD: linka un MD -> copia
        versionata in Engram). ``source_id`` default = path del file; re-ingest
        idempotente finché il contenuto non cambia (poi nuova versione)."""
        p = Path(path)
        content = p.read_text(encoding="utf-8")
        sid = source_id if source_id is not None else str(p)
        m = dict(meta or {})
        m.setdefault("filename", p.name)
        return self.ingest(sid, content, uri=f"file://{p}", meta=m,
                           fetched_at=fetched_at, principal=principal)

    # --- read ----------------------------------------------------------
    def _row_to_doc(self, r: sqlite3.Row) -> Document:
        return Document(
            source_id=r["source_id"], content=r["content"], uri=r["uri"] or "",
            meta=json.loads(r["meta"] or "{}"), content_hash=r["content_hash"],
            version=r["version"], fetched_at=r["fetched_at"] or 0.0, id=r["id"],
        )

    def get(self, doc_id: str) -> Document | None:
        conn = self._connect()
        try:
            r = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
            return self._row_to_doc(r) if r else None
        finally:
            conn.close()

    def get_latest(self, source_id: str) -> Document | None:
        conn = self._connect()
        try:
            r = conn.execute(
                "SELECT * FROM documents WHERE source_id=? ORDER BY version DESC LIMIT 1",
                (source_id,),
            ).fetchone()
            return self._row_to_doc(r) if r else None
        finally:
            conn.close()

    def list_versions(self, source_id: str) -> list[Document]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM documents WHERE source_id=? ORDER BY version ASC",
                (source_id,),
            ).fetchall()
            return [self._row_to_doc(r) for r in rows]
        finally:
            conn.close()

    # --- discovery (rende il tier ISPEZIONABILE da CLI/MCP/agent) ------
    _LATEST_JOIN = (
        "FROM documents d JOIN (SELECT source_id, MAX(version) AS mv "
        "FROM documents GROUP BY source_id) m "
        "ON d.source_id=m.source_id AND d.version=m.mv "
    )

    def list_sources(self, limit: int = 200) -> list[dict]:
        """Elenca le fonti — SOLO la versione piu' alta di ogni ``source_id``.

        Metadati ispezionabili (no contenuto pieno): source_id, version, uri,
        filename, n. caratteri, fetched_at. Ordine: fetched_at desc, source_id asc.
        Rende il tier visibile a un agente SENZA toccare il corpus di recall.
        """
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT d.source_id, d.version, d.uri, d.meta, d.fetched_at, "
                "length(d.content) AS clen " + self._LATEST_JOIN +
                "ORDER BY d.fetched_at DESC, d.source_id ASC LIMIT ?",
                (int(limit),),
            ).fetchall()
            out: list[dict] = []
            for r in rows:
                meta = json.loads(r["meta"] or "{}")
                out.append({
                    "source_id": r["source_id"], "version": r["version"],
                    "uri": r["uri"] or "", "filename": meta.get("filename", ""),
                    "chars": int(r["clen"] or 0), "fetched_at": r["fetched_at"] or 0.0,
                })
            return out
        finally:
            conn.close()

    def search(self, query: str, limit: int = 10, snippet_chars: int = 160) -> list[dict]:
        """Ricerca LESSICALE (non semantica) sul contenuto della versione piu'
        alta di ogni ``source_id``.

        La query e' divisa in termini (whitespace): un documento matcha se
        contiene TUTTI i termini (AND, case-insensitive, in qualunque ordine/
        posizione) — piu' utile della frase contigua per query multi-parola.
        Tier grezzo by-design: NESSUN embedding. Snippet attorno al primo termine
        che compare. Query vuota -> ``[]``. Non tocca ``semantic.db`` (isolato).
        """
        q = (query or "").strip()
        terms = [tok.lower() for tok in q.split() if tok.strip()]
        if not terms:
            return []
        conn = self._connect()
        try:
            # AND di termini: ogni termine deve essere un substring del contenuto.
            # instr() su lower() = ASCII case-fold (limite: accenti non foldati).
            where = " AND ".join(["instr(lower(d.content), ?) > 0"] * len(terms))
            rows = conn.execute(
                "SELECT d.source_id, d.version, d.uri, d.meta, d.content "
                + self._LATEST_JOIN +
                "WHERE " + where + " "
                "ORDER BY d.fetched_at DESC, d.source_id ASC LIMIT ?",
                (*terms, int(limit)),
            ).fetchall()
            out: list[dict] = []
            half = max(0, snippet_chars // 2)
            for r in rows:
                content = r["content"] or ""
                cl = content.lower()
                positions = [p for p in (cl.find(t) for t in terms) if p >= 0]
                idx = min(positions) if positions else 0
                start = max(0, idx - half)
                end = min(len(content), idx + half)
                snippet = content[start:end].strip()
                if start > 0:
                    snippet = "…" + snippet
                if end < len(content):
                    snippet = snippet + "…"
                meta = json.loads(r["meta"] or "{}")
                out.append({
                    "source_id": r["source_id"], "version": r["version"],
                    "uri": r["uri"] or "", "filename": meta.get("filename", ""),
                    "snippet": snippet,
                })
            return out
        finally:
            conn.close()


__all__ = ["Document", "DocumentStore", "default_db_path"]
