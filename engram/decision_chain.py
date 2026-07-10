"""Decision chain — decisions as first-class, explainable records (task #15).

Mandate (Aurelio 2026-07-10): "salvare la catena delle decisioni: il perché
di errori o cose scelte, per scalare la concatenazione e l'intelligenza".
verimem already answers "how do you know X?" (explain → chain of custody);
a decision record makes it answer "why did we choose X?" — the choice, the
alternatives rejected, the evidence CITED (fact ids), the expected outcome,
and later what actually happened.

v1 storage: a dedicated ISOLATED store (the documents.py pattern), a DB of
its own, never ``semantic.db`` — the facts table has no free-form metadata
column, and a decision is a different kind of object (it CITES facts, it is
not one). Evidence ids point INTO the fact corpus; a consumer resolves them
with the store's existing ``explain``/``get``.

Outcome-loop guard-rail (TRUST_CORE.md, reputation-inversion): recording an
outcome updates ONLY its decision record, REQUIRES evidence (an outcome
without ``verified_by`` would be a model_claim), and NEVER scores the cited
sources. Source-level reputation stays in engram.source_trust behind its own
flag; decisions never feed it. Design doc: docs/DECISION_CHAIN_DESIGN.md.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["Decision", "DecisionStore"]


@dataclass
class Decision:
    id: str
    decision: str
    topic: str = "decisions/general"
    alternatives: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)   # cited fact ids
    expected: str = ""
    revisit_at: float | None = None
    decided_at: float = 0.0
    outcome: str | None = None
    outcome_verified_by: list[str] = field(default_factory=list)
    outcome_at: float | None = None


_TABLE = """CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    decision TEXT NOT NULL,
    topic TEXT NOT NULL,
    alternatives TEXT NOT NULL DEFAULT '[]',
    evidence TEXT NOT NULL DEFAULT '[]',
    expected TEXT NOT NULL DEFAULT '',
    revisit_at REAL,
    decided_at REAL NOT NULL,
    outcome TEXT,
    outcome_verified_by TEXT NOT NULL DEFAULT '[]',
    outcome_at REAL
)"""


class DecisionStore:
    """Isolated per-DB store of decision records — never touches semantic.db."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.execute(_TABLE)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def record(self, *, decision: str, topic: str = "decisions/general",
               alternatives: list[str] | None = None,
               evidence: list[str] | None = None, expected: str = "",
               revisit_at: float | None = None,
               ts: float | None = None) -> str:
        """Store a decision; return its id. ``evidence`` are fact ids CITED at
        decision time (resolvable via the fact corpus)."""
        did = uuid.uuid4().hex[:16]
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO decisions (id, decision, topic, alternatives, "
                "evidence, expected, revisit_at, decided_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (did, decision, topic,
                 json.dumps(list(alternatives or [])),
                 json.dumps(list(evidence or [])),
                 expected, revisit_at, ts if ts is not None else time.time()))
            conn.commit()
        return did

    def record_outcome(self, decision_id: str, outcome: str, *,
                       verified_by: list[str],
                       ts: float | None = None) -> bool:
        """Attach the measured outcome. REQUIRES evidence (guard-rail: an
        unverified outcome is a model_claim, not a fact) and updates ONLY this
        record — never the cited sources' reputation."""
        if not verified_by:
            raise ValueError(
                "an outcome needs verified_by evidence (bench/test/runtime "
                "ref) — an unsupported outcome is a model_claim, not truth")
        with self._conn() as conn:
            cur = conn.execute(
                "UPDATE decisions SET outcome=?, outcome_verified_by=?, "
                "outcome_at=? WHERE id=?",
                (outcome, json.dumps(list(verified_by)),
                 ts if ts is not None else time.time(), decision_id))
            conn.commit()
            return cur.rowcount > 0

    def _row(self, r: sqlite3.Row) -> Decision:
        return Decision(
            id=r["id"], decision=r["decision"], topic=r["topic"],
            alternatives=json.loads(r["alternatives"]),
            evidence=json.loads(r["evidence"]),
            expected=r["expected"], revisit_at=r["revisit_at"],
            decided_at=r["decided_at"], outcome=r["outcome"],
            outcome_verified_by=json.loads(r["outcome_verified_by"]),
            outcome_at=r["outcome_at"])

    def get(self, decision_id: str) -> Decision | None:
        with self._conn() as conn:
            r = conn.execute("SELECT * FROM decisions WHERE id=?",
                             (decision_id,)).fetchone()
        return self._row(r) if r else None

    def list(self, *, topic: str | None = None,
             limit: int = 100) -> list[Decision]:
        """Decisions newest-first, optionally filtered by topic."""
        q = "SELECT * FROM decisions"
        params: list = []
        if topic:
            q += " WHERE topic=?"
            params.append(topic)
        q += " ORDER BY decided_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(q, params).fetchall()
        return [self._row(r) for r in rows]

    def why(self, question: str, *, limit: int = 5) -> list[Decision]:
        """"Why did we choose X?" — keyword-overlap match over decisions,
        best first. Lexical by design: the decision text is short and the
        query names the choice; a semantic layer can wrap this later, but the
        cited-evidence chain is the point, not fuzzy ranking."""
        import re
        stop = {"why", "did", "we", "choose", "the", "a", "an", "to", "use",
                "for", "of", "on", "in", "is", "our", "what", "was"}
        terms = {w for w in re.findall(r"[a-z0-9]+", question.lower())
                 if w not in stop and len(w) > 1}
        if not terms:
            return []
        scored: list[tuple[int, Decision]] = []
        for d in self.list(limit=1000):
            hay = f"{d.decision} {' '.join(d.alternatives)} {d.topic}".lower()
            hits = sum(1 for t in terms if t in hay)
            if hits:
                scored.append((hits, d))
        scored.sort(key=lambda kv: (-kv[0], -kv[1].decided_at))
        return [d for _, d in scored[:limit]]
