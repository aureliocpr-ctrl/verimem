"""Adjudication log — an append-only, per-write audit trail of the gate's verdicts
(Phase 0.2b).

``Memory.add()`` already returns an adjudication receipt (disposition, evidence_class,
judge, score, threshold, reason, confidence_tier) — a reasoned, visible verdict per
write. But it is only RETURNED; nothing persists it. An enterprise / compliance
deployment needs that verdict stored and queryable after the fact: "show me every
write we quarantined last month and exactly why." This module is that store.

Design (mirrors ``decision_chain.py`` / ``documents.py``): an ISOLATED store with a DB
of its own (``adjudications.db`` next to ``semantic.db``), never the facts table. It is
append-only by contract — an audit trail you can rewrite is not an audit trail — and it
is deliberately a plain, well-indexed table so that a later tamper-evidence hash-chain
(task #24) can be layered ON TOP without reshaping it.

Opt-in: nothing writes here unless the caller wires it (``Memory`` does so behind an
env flag), so the default write path is unchanged and pays no extra I/O.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["AdjudicationRecord", "AdjudicationLog"]


@dataclass
class AdjudicationRecord:
    id: str
    ts: float
    topic: str
    disposition: str                       # admitted | quarantined | rejected
    proposition: str
    fact_id: str | None = None             # the stored fact id, when one exists
    evidence_class: str | None = None      # cross_encoder | llm_judge | ...
    judge: str | None = None               # local | claude | interactive | None
    score: float | None = None
    threshold: float | None = None
    reason: str = ""
    layers: list[str] = field(default_factory=list)


_TABLE = """CREATE TABLE IF NOT EXISTS adjudications (
    id TEXT PRIMARY KEY,
    ts REAL NOT NULL,
    topic TEXT NOT NULL,
    disposition TEXT NOT NULL,
    proposition TEXT NOT NULL,
    fact_id TEXT,
    evidence_class TEXT,
    judge TEXT,
    score REAL,
    threshold REAL,
    reason TEXT NOT NULL DEFAULT '',
    layers TEXT NOT NULL DEFAULT '[]'
)"""

_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_adj_ts ON adjudications(ts DESC)",
    "CREATE INDEX IF NOT EXISTS idx_adj_disposition ON adjudications(disposition)",
    "CREATE INDEX IF NOT EXISTS idx_adj_topic ON adjudications(topic)",
)


class AdjudicationLog:
    """Isolated per-DB, append-only log of gate verdicts — never touches semantic.db."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.execute(_TABLE)
            for stmt in _INDEXES:
                conn.execute(stmt)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def record(self, *, disposition: str, topic: str, proposition: str,
               fact_id: str | None = None, evidence_class: str | None = None,
               judge: str | None = None, score: float | None = None,
               threshold: float | None = None, reason: str = "",
               layers: list[str] | None = None, ts: float | None = None) -> str:
        """Append one adjudication; return its id. Never updates an existing row —
        the log is append-only."""
        rid = uuid.uuid4().hex[:16]
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO adjudications (id, ts, topic, disposition, proposition, "
                "fact_id, evidence_class, judge, score, threshold, reason, layers) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (rid, ts if ts is not None else time.time(), topic, disposition,
                 proposition, fact_id, evidence_class, judge,
                 None if score is None else float(score),
                 None if threshold is None else float(threshold),
                 reason, json.dumps(list(layers or []))))
            conn.commit()
        return rid

    def _row(self, r: sqlite3.Row) -> AdjudicationRecord:
        return AdjudicationRecord(
            id=r["id"], ts=r["ts"], topic=r["topic"],
            disposition=r["disposition"], proposition=r["proposition"],
            fact_id=r["fact_id"], evidence_class=r["evidence_class"],
            judge=r["judge"], score=r["score"], threshold=r["threshold"],
            reason=r["reason"], layers=json.loads(r["layers"]))

    def get(self, record_id: str) -> AdjudicationRecord | None:
        with self._conn() as conn:
            r = conn.execute("SELECT * FROM adjudications WHERE id=?",
                             (record_id,)).fetchone()
        return self._row(r) if r else None

    def list(self, *, disposition: str | tuple[str, ...] | list[str] | None = None,
             topic: str | None = None, limit: int = 100) -> list[AdjudicationRecord]:
        """Adjudications newest-first, optionally filtered by disposition (a single
        value or a set of them) and/or topic."""
        q = "SELECT * FROM adjudications"
        clauses: list[str] = []
        params: list = []
        if disposition is not None:
            disps = [disposition] if isinstance(disposition, str) else list(disposition)
            clauses.append(f"disposition IN ({','.join('?' * len(disps))})")
            params.extend(disps)
        if topic is not None:
            clauses.append("topic = ?")
            params.append(topic)
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        q += " ORDER BY ts DESC, id DESC LIMIT ?"
        params.append(int(limit))
        with self._conn() as conn:
            rows = conn.execute(q, params).fetchall()
        return [self._row(r) for r in rows]
