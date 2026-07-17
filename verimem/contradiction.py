"""Cycle #110.B (2026-05-16) — Contradiction detector.

Finds pairs of facts that:
  - share the same ``topic``
  - have high embedding cosine similarity (semantic neighbours)
  - DIFFER on a measurable axis (numeric, boolean)

Persists detected pairs in a new ``contradictions`` table (schema v4)
so a daemon scan can run periodically and let callers see the
unresolved set via the MCP tool ``hippo_contradictions_list``.

Why this exists
---------------
Aurelio audit 2026-05-16: HippoAgent has 374 MCP tools but no
background loop that *reasons* about the corpus. Cycle #70 had a
placeholder for a contradiction daemon that was never implemented;
this module is the real thing.

Design choices (cycle 110.B V1)
-------------------------------
- ``numeric_clash`` (high signal): regex-extract numbers from both
  propositions and compare position-by-position. Two facts on the
  same topic that disagree on a number beyond a relative tolerance
  (default 5%) are flagged.
- ``boolean_clash`` (medium signal): negation markers ("not",
  "doesn't", "isn't", "no", "non", "never"). One side has one, the
  other doesn't, on the same topic with high similarity → flag.
- Categorical clash is OUT OF SCOPE for V1 — it requires a relation
  extractor (subject/predicate/object) that we don't have here.

Performance: O(N²) over the corpus, but ``N`` is bounded by topic
(we group first). For 1k facts in 50 topics we're at ~10k comparisons
per scan, which is well under a second on the embedding daemon.
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from . import embedding
from .semantic import Fact, SemanticMemory

# ---------------------------------------------------------------------------
# Schema v4 — contradictions table.
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS contradictions (
    id TEXT PRIMARY KEY,
    fact_a_id TEXT NOT NULL,
    fact_b_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    similarity REAL NOT NULL,
    detected_at REAL NOT NULL,
    resolved_at REAL,
    resolution_note TEXT
);
CREATE INDEX IF NOT EXISTS idx_contradictions_unresolved
    ON contradictions(detected_at)
    WHERE resolved_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_contradictions_pair
    ON contradictions(fact_a_id, fact_b_id, kind);
"""


_NEGATION_TOKENS = frozenset({
    "not", "no", "n't", "non", "never", "neither", "nor",
})


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class Contradiction:
    fact_a_id: str
    fact_b_id: str
    kind: str
    similarity: float
    detected_at: float = field(default_factory=time.time)
    id: str = ""
    resolved_at: float | None = None
    resolution_note: str | None = None

    def __post_init__(self) -> None:
        if not self.id:
            # Deterministic id from the ordered pair + kind, so re-detecting
            # the same pair on a later scan_corpus call produces the same id
            # → INSERT OR IGNORE makes the scan idempotent.
            a, b = sorted([self.fact_a_id, self.fact_b_id])
            digest = hashlib.sha256(
                f"{a}|{b}|{self.kind}".encode(),
            ).hexdigest()
            self.id = digest[:16]


# ---------------------------------------------------------------------------
# Detection primitives
# ---------------------------------------------------------------------------


_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")
# Cycle #123 (2026-05-17): type-aware classification.
# Years: 4-digit between 1900 and 2099 (the only range realistically
# encountered in fact corpora — fact older than 1900 or after 2099
# would be flagged as a noteworthy edge case anyway).
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
# Percent: a (possibly decimal) number immediately preceding a %, with
# optional intervening whitespace. Matches "5%", "5 %", "5.5%", "-3%".
_PERCENT_RE = re.compile(r"-?\d+(?:\.\d+)?(?=\s*%)")


def _extract_numbers(text: str) -> list[float]:
    return [float(m) for m in _NUMBER_RE.findall(text)]


def _classify_numbers(text: str) -> dict[str, list[float]]:
    """Cycle #123: classify extracted numbers by semantic type.

    Returns ``{"year": [...], "percent": [...], "other": [...]}``.
    A number can belong to ``year`` AND ``percent`` simultaneously
    only in pathological cases (e.g. "2024%") — we resolve that by
    prioritising the more specific marker (percent) and stripping it
    from ``other``.
    """
    # Cycle 2026-06-03 (finding sorella D): un numero in range-anno SEGUITO
    # immediatamente da una parola (es. "2024 facts") e' un CONTEGGIO con unita,
    # non un anno -> NON classificarlo come 'year' (altrimenti veniva isolato dal
    # confronto e si perdeva la contraddizione "2024 facts" vs "8000 facts").
    # Resta 'year' quando NON seguito da parola (es. "nel 2024", "2024.", "(2024)").
    years = [
        float(m.group())
        for m in _YEAR_RE.finditer(text)
        if not re.match(r"\s*[A-Za-z]", text[m.end():m.end() + 8])
    ]
    percents = [float(m) for m in _PERCENT_RE.findall(text)]
    all_nums = _extract_numbers(text)
    # ``other`` excludes anything already classified.
    classified = set(years) | set(percents)
    other = [n for n in all_nums if n not in classified]
    return {"year": years, "percent": percents, "other": other}


def _values_clash(
    a_vals: list[float], b_vals: list[float], *,
    tolerance: float,
    text_a: str = "", text_b: str = "",
) -> bool:
    """Detect a meaningful numeric clash between two propositions.

    Cycle #123 (2026-05-17): type-aware comparison via
    ``_classify_numbers``. When ``text_a`` and/or ``text_b`` are passed,
    numbers are grouped by type (year / percent / other) and compared
    *within* type only. This prevents the well-documented false-positive
    where "Tasso 5% nel 2024" and "2024 tasso 5%" — semantically
    equivalent — get flagged as clashing because the positional compare
    pairs 5 with 2024.

    Year tolerance is absolute (±1 year) — relative tolerance on years
    is too tight (a 5% gap on 2024 is 100 years). Percent/other keep
    relative tolerance.

    Backward compat: when neither text is provided, fall back to the
    pre-cycle-123 positional compare so legacy callers (and tests that
    pass raw value lists) keep working unchanged.
    """
    if not a_vals or not b_vals:
        return False

    if text_a or text_b:
        a_typed = _classify_numbers(text_a)
        b_typed = _classify_numbers(text_b)
        for kind in ("year", "percent", "other"):
            a_kind = a_typed[kind]
            b_kind = b_typed[kind]
            if not a_kind or not b_kind:
                continue
            n = min(len(a_kind), len(b_kind))
            for i in range(n):
                a, b = a_kind[i], b_kind[i]
                if kind == "year":
                    if abs(a - b) > 1.0:
                        return True
                else:
                    denom = max(abs(a), abs(b), 1e-9)
                    if abs(a - b) / denom > tolerance:
                        return True
        return False

    # Pre-cycle-123 positional fallback for backward compat.
    n = min(len(a_vals), len(b_vals))
    for i in range(n):
        a, b = a_vals[i], b_vals[i]
        denom = max(abs(a), abs(b), 1e-9)
        if abs(a - b) / denom > tolerance:
            return True
    return False


def _cosine(fact_a: Fact, fact_b: Fact) -> float:
    """Compute cosine on freshly-encoded propositions.

    We re-encode (instead of reading the stored embedding) because the
    public ``Fact`` dataclass intentionally does NOT carry the bytes.
    The embedding cache inside ``verimem.embedding`` makes this cheap.
    """
    import numpy as np

    a = embedding.encode(fact_a.proposition)
    b = embedding.encode(fact_b.proposition)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _has_negation(text: str) -> bool:
    """Token-aware negation check.

    Splits on whitespace + punctuation; matches any of ``_NEGATION_TOKENS``
    plus the suffix ``n't`` on auxiliary verbs (isn't / doesn't / won't /
    can't / shouldn't ...).
    """
    lower = text.lower()
    tokens = re.findall(r"[a-z']+", lower)
    if any(t in _NEGATION_TOKENS for t in tokens):
        return True
    return any(t.endswith("n't") for t in tokens)


def _group_by_topic(facts: list[Fact]) -> dict[str, list[Fact]]:
    by_topic: dict[str, list[Fact]] = {}
    for f in facts:
        by_topic.setdefault(f.topic, []).append(f)
    return by_topic


def detect_numeric_clashes(
    facts: list[Fact], *,
    similarity_threshold: float = 0.75,
    value_tolerance: float = 0.05,
    time_budget_s: float | None = None,
) -> list[Contradiction]:
    """See module docstring. Returns one Contradiction per offending pair.

    ``time_budget_s``: if set, stop and return PARTIAL results once exceeded.
    The pairwise scan is O(N^2) per topic and re-encodes propositions, so on a
    large corpus it could block for minutes (it once ran ~10 min on 8.8k facts);
    the budget guarantees it never blocks longer than ~``time_budget_s``."""
    out: list[Contradiction] = []
    seen_pairs: set[tuple[str, str]] = set()
    start = time.monotonic()
    for _topic, group in _group_by_topic(facts).items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            # >= (not >) so a 0.0 budget returns early deterministically even on
            # coarse-resolution clocks (Windows time.monotonic ~15ms): on the 1st
            # iteration elapsed can be exactly 0.0, and `0.0 > 0.0` is False, which
            # let a pair through and broke the zero-budget guard on CI Windows.
            if time_budget_s is not None and time.monotonic() - start >= time_budget_s:
                return out
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                key = tuple(sorted([a.id, b.id]))
                if key in seen_pairs:
                    continue
                a_vals = _extract_numbers(a.proposition)
                b_vals = _extract_numbers(b.proposition)
                # Cycle #123: pass propositions for type-aware compare.
                if not _values_clash(
                    a_vals, b_vals, tolerance=value_tolerance,
                    text_a=a.proposition, text_b=b.proposition,
                ):
                    continue
                sim = _cosine(a, b)
                if sim < similarity_threshold:
                    continue
                seen_pairs.add(key)
                out.append(Contradiction(
                    fact_a_id=a.id, fact_b_id=b.id,
                    kind="numeric_clash", similarity=sim,
                ))
    return out


def detect_boolean_clashes(
    facts: list[Fact], *,
    similarity_threshold: float = 0.75,
    time_budget_s: float | None = None,
) -> list[Contradiction]:
    """Find same-topic pairs where ONE side has a negation marker and the
    OTHER side does not, with high embedding similarity.

    ``time_budget_s``: stop and return PARTIAL results once exceeded (see
    ``detect_numeric_clashes`` — same O(N^2) never-block guard)."""
    out: list[Contradiction] = []
    seen_pairs: set[tuple[str, str]] = set()
    start = time.monotonic()
    for _topic, group in _group_by_topic(facts).items():
        if len(group) < 2:
            continue
        flags = [(f, _has_negation(f.proposition)) for f in group]
        for i in range(len(flags)):
            # >= (not >) so a 0.0 budget returns early deterministically even on
            # coarse-resolution clocks (Windows time.monotonic ~15ms): on the 1st
            # iteration elapsed can be exactly 0.0, and `0.0 > 0.0` is False, which
            # let a pair through and broke the zero-budget guard on CI Windows.
            if time_budget_s is not None and time.monotonic() - start >= time_budget_s:
                return out
            for j in range(i + 1, len(flags)):
                (a, a_neg), (b, b_neg) = flags[i], flags[j]
                if a_neg == b_neg:
                    continue  # same polarity, not a clash
                key = tuple(sorted([a.id, b.id]))
                if key in seen_pairs:
                    continue
                sim = _cosine(a, b)
                if sim < similarity_threshold:
                    continue
                seen_pairs.add(key)
                out.append(Contradiction(
                    fact_a_id=a.id, fact_b_id=b.id,
                    kind="boolean_clash", similarity=sim,
                ))
    return out


# ---------------------------------------------------------------------------
# Persistence — ContradictionStore.
# ---------------------------------------------------------------------------


class ContradictionStore:
    """SQLite-backed store for detected contradictions.

    Reuses the semantic.db file (same data dir, separate table).
    Schema is idempotently created on first use, so this is safe to
    instantiate before the SemanticMemory migration runs.
    """

    def __init__(self, semantic_db_path: Path) -> None:
        self.db_path = Path(semantic_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=60000;")
        except sqlite3.OperationalError:
            pass
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def add(self, c: Contradiction) -> bool:
        """Insert a contradiction. Returns True if a new row was created,
        False if the (fact_a_id, fact_b_id, kind) triple already exists.

        Determinism: ``Contradiction.id`` is a hash of the ordered pair
        + kind (see ``__post_init__``), so the same logical pair always
        produces the same id and ``INSERT OR IGNORE`` makes scan idempotent.
        """
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT OR IGNORE INTO contradictions "
                "(id, fact_a_id, fact_b_id, kind, similarity, "
                " detected_at, resolved_at, resolution_note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    c.id, c.fact_a_id, c.fact_b_id, c.kind,
                    float(c.similarity), float(c.detected_at),
                    c.resolved_at, c.resolution_note,
                ),
            )
            return cur.rowcount == 1

    def list_unresolved(self, *, limit: int = 100) -> list[Contradiction]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM contradictions "
                "WHERE resolved_at IS NULL "
                "ORDER BY detected_at DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [self._row_to_contradiction(r) for r in rows]

    def list_all(self, *, limit: int = 100) -> list[Contradiction]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM contradictions "
                "ORDER BY detected_at DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [self._row_to_contradiction(r) for r in rows]

    def resolve(self, contradiction_id: str, *, note: str = "") -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE contradictions "
                "SET resolved_at = ?, resolution_note = ? "
                "WHERE id = ? AND resolved_at IS NULL",
                (time.time(), note, contradiction_id),
            )
            return cur.rowcount == 1

    def list_unresolved_for_fact(
        self, fact_id: str, *, limit: int = 50,
    ) -> list[Contradiction]:
        """Cycle #117: return unresolved contradictions that involve
        ``fact_id`` on either side. Used by trust_signal.compute_trust_signal
        to bump the verdict to ``contested``."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM contradictions "
                "WHERE resolved_at IS NULL "
                "AND (fact_a_id = ? OR fact_b_id = ?) "
                "ORDER BY detected_at DESC LIMIT ?",
                (fact_id, fact_id, int(limit)),
            ).fetchall()
        return [self._row_to_contradiction(r) for r in rows]

    def resolve_all_for_fact(self, fact_id: str, *, note: str = "") -> int:
        """Cycle #117: mark every unresolved contradiction involving
        ``fact_id`` as resolved. Returns the number of rows updated."""
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE contradictions "
                "SET resolved_at = ?, resolution_note = ? "
                "WHERE resolved_at IS NULL "
                "AND (fact_a_id = ? OR fact_b_id = ?)",
                (time.time(), note, fact_id, fact_id),
            )
            return cur.rowcount or 0

    def count_unresolved(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM contradictions "
                "WHERE resolved_at IS NULL",
            ).fetchone()
            return int(row[0]) if row else 0

    @staticmethod
    def _row_to_contradiction(r: sqlite3.Row) -> Contradiction:
        return Contradiction(
            id=r["id"],
            fact_a_id=r["fact_a_id"],
            fact_b_id=r["fact_b_id"],
            kind=r["kind"],
            similarity=float(r["similarity"]),
            detected_at=float(r["detected_at"]),
            resolved_at=(
                float(r["resolved_at"]) if r["resolved_at"] is not None else None
            ),
            resolution_note=r["resolution_note"],
        )


# ---------------------------------------------------------------------------
# Daemon-ready entry point.
# ---------------------------------------------------------------------------


def heal_contradictions(
    memory: SemanticMemory,
    store: ContradictionStore | None = None,
    *,
    limit: int = 200,
) -> dict[str, list[str]]:
    """Self-healing pass over ALREADY-detected contradictions.

    For each unresolved pair, if the two facts have DIFFERENT trust
    (``_STATUS_RANK``), supersede the weaker toward the stronger (reusing
    :meth:`SemanticMemory.auto_supersede_on_contradiction` —
    invalidate-not-delete) and mark the contradiction resolved. EQUAL trust →
    left unresolved (human judgement needed: we don't know which side is
    right). If a fact in the pair no longer exists the contradiction is moot →
    resolved.

    Does NOT detect new contradictions (that is :func:`scan_corpus`); it only
    acts on what the detector already found. Reuses ``supersede`` so old rows
    stay in the DB for lineage and merely drop out of the default recall.
    Reversible; never deletes.

    Returns ``{"healed_superseded": [fact_ids], "resolved": [contradiction_ids],
    "skipped_equal_trust": [contradiction_ids], "missing": [contradiction_ids]}``.
    """
    from .semantic import _STATUS_RANK

    if store is None:
        store = ContradictionStore(memory.db_path)
    healed_superseded: list[str] = []
    resolved: list[str] = []
    skipped: list[str] = []
    missing: list[str] = []
    for c in store.list_unresolved(limit=limit):
        fa = memory.get(c.fact_a_id)
        fb = memory.get(c.fact_b_id)
        if fa is None or fb is None:
            # One side is gone → the clash cannot stand → resolve it.
            store.resolve(c.id, note="heal: a fact in the pair no longer exists")
            missing.append(c.id)
            resolved.append(c.id)
            continue
        ra = _STATUS_RANK.get(fa.status, 0)
        rb = _STATUS_RANK.get(fb.status, 0)
        if ra == rb:
            # Equal trust → we cannot decide which is right; leave for review.
            skipped.append(c.id)
            continue
        winner, loser = (fa, fb) if ra > rb else (fb, fa)
        if winner.superseded_by:
            # FIX 2026-06-09 (audit#3-r3 R2): an already-superseded (obsolete)
            # fact must NOT be used to invalidate a LIVE one — its higher
            # status rank is stale. Leave the pair for review.
            skipped.append(c.id)
            continue
        res = memory.auto_supersede_on_contradiction(
            winner.id,
            [loser.id],
            reason=(
                f"heal_contradictions: {c.kind} clash on shared topic, "
                f"lower-trust fact superseded by higher-trust"
            ),
        )
        if loser.id in res.get("superseded", []):
            store.resolve(
                c.id,
                note=(
                    f"heal: {loser.id} ({loser.status}) superseded by "
                    f"{winner.id} ({winner.status})"
                ),
            )
            healed_superseded.append(loser.id)
            resolved.append(c.id)
        else:
            # FIX 2026-06-09 (audit#3-r3 R18): if the loser is ALREADY
            # superseded elsewhere, the clash is moot → resolve it rather than
            # leaving it unresolved forever. A genuine supersede CONFLICT (loser
            # still live) still goes to review.
            fresh_loser = memory.get(loser.id)
            if fresh_loser is not None and fresh_loser.superseded_by:
                store.resolve(
                    c.id,
                    note=f"heal: {loser.id} already superseded elsewhere (moot)",
                )
                resolved.append(c.id)
            else:
                skipped.append(c.id)
    return {
        "healed_superseded": healed_superseded,
        "resolved": resolved,
        "skipped_equal_trust": skipped,
        "missing": missing,
    }


def scan_corpus(
    sm: SemanticMemory,
    *,
    store: ContradictionStore | None = None,
    similarity_threshold: float = 0.75,
    value_tolerance: float = 0.05,
    detect_boolean: bool = True,
    time_budget_s: float | None = 30.0,
) -> dict[str, int]:
    """Run all detectors over the corpus and persist new contradictions.

    Returns a summary dict::

        {
            "scanned_facts": N,
            "new_detected": K,
            "already_known": M,
            "kinds": {"numeric_clash": ..., "boolean_clash": ...},
        }

    Idempotent thanks to deterministic ``Contradiction.id`` +
    ``INSERT OR IGNORE`` in :meth:`ContradictionStore.add`.
    """
    if store is None:
        store = ContradictionStore(sm.db_path)

    # FIX 2026-06-09 (audit#3-r3 R11): only scan LIVE facts. Superseded/obsolete
    # rows produce phantom contradictions (a clash already resolved by
    # supersession) and waste the O(N^2) detection budget on dead rows.
    facts = [f for f in sm.all() if not getattr(f, "superseded_by", None)]
    detected: list[Contradiction] = []
    detected.extend(detect_numeric_clashes(
        facts,
        similarity_threshold=similarity_threshold,
        value_tolerance=value_tolerance,
        time_budget_s=time_budget_s,
    ))
    if detect_boolean:
        detected.extend(detect_boolean_clashes(
            facts, similarity_threshold=similarity_threshold,
            time_budget_s=time_budget_s,
        ))

    kinds: dict[str, int] = {}
    new_count = 0
    already_known = 0
    for c in detected:
        if store.add(c):
            new_count += 1
        else:
            already_known += 1
        kinds[c.kind] = kinds.get(c.kind, 0) + 1

    return {
        "scanned_facts": len(facts),
        "new_detected": new_count,
        "already_known": already_known,
        "kinds": kinds,
    }


__all__ = [
    "Contradiction",
    "ContradictionStore",
    "detect_boolean_clashes",
    "detect_numeric_clashes",
    "scan_corpus",
]
