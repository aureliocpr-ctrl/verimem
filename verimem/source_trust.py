"""Per-source trust book — two complementary channels, pure update rules.

Task #17, from the Vivarium transfer (docs at Code/vivarium/docs/
TRANSFER-TO-VERIMEM.md, verified on a real-gate clone) under this repo's
guard-rails (benchmark/TRUST_CORE.md):

  * **consistency** — USE-INDEPENDENT agreement on the write stream: sources
    that confirm an accepted value together rise, a contradictor falls. It is
    measured for every writing source, used or not, so a source punished
    unfairly (stale world) climbs back by agreeing — no absorbing trap
    (outcome-only collapsed 32% of lab worlds; EWMA made it 40%).
  * **outcome** — a-posteriori feedback (a claim failed in use). It exists
    because consistency alone falls to the TRUSTED SLEEPER (build reputation
    everywhere, lie where unwitnessed: wrong 0.89 in the lab). Penalties take
    an attenuation ``weight`` so stale facts blame the source less
    (attribution-aware, task #18 wires the age logic).
  * **trust = min(channels)** — conservative by design: each channel covers
    the other's NAMED hole; averaging would mask exactly the failure the
    other channel exists to catch.

Counts are Laplace-smoothed proportions: bounded, interpretable, and new
evidence dilutes old verdicts (rehabilitation on both channels). Pure logic:
no I/O, no store dependency — persistence and gate wiring live with the
caller (behind ENGRAM_SOURCE_TRUST, default OFF). The held-out reproduction on
real VeriMem data now exists (benchmark/source_trust_realcorpus.py, HaluEval QA:
reproduction_holds 3/3 seeds under honest coherence, degrades under heavy honest
noise) — it INFORMS a default flip but does not perform it; the flip stays a
product decision.
"""
from __future__ import annotations

import os
import re
import sqlite3
import time
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any

__all__ = ["SourceTrustBook", "canonical_source", "enabled",
           "independence_enabled", "independence_deconfounded", "threshold",
           "load_book", "save_book"]

_NEUTRAL = 0.5

#: Independence clustering (Vivarium collusion/complementarity transfer): two
#: sources whose report vectors agree at/above this over >= _COPY_MIN_SHARED
#: co-reported keys are treated as COPIES of one feed and collapse to one witness.
_COPY_AGREEMENT = 0.9
_COPY_MIN_SHARED = 3

#: Deconfounded independence (Vivarium P88, cartel_kill_v56): raw agreement is
#: CONFOUNDED by shared TRUTH — honest sources agree because both are right, so
#: agreement alone false-merges them (v1 flagged 3.6/4 honest). Conditioning on the
#: AUDIT — co-admission of values REVEALED FALSE — isolates collusion: honest peers
#: reject falsehoods (~0), colluders both admit them (~1). The audit is the
#: do-operator that separates collusion from consensus.
_COLLUSION_CPARAM = 0.5       # min P(both admit | audited-false) to call a pair colluding
_COLLUSION_MIN_SHARED = 2     # shared audited-false keys needed to judge a pair

# ---- gate wiring knobs (behind-flag, default OFF — TRUST_CORE.md guard-rail:
# no default flip before the held-out reproduction on real VeriMem data) ------

_TRUTHY = {"1", "true", "yes", "on"}


def enabled() -> bool:
    """ENGRAM_SOURCE_TRUST=1 turns the write-gate consultation on."""
    return os.environ.get("ENGRAM_SOURCE_TRUST", "").strip().lower() in _TRUTHY


def independence_enabled() -> bool:
    """ENGRAM_SOURCE_INDEPENDENCE=1 makes a confirmation require >=2 INDEPENDENT
    clusters (copies/colluders of one feed collapse to one witness), not just >=2
    distinct source-IDs. Separate flag, default OFF: it can only strengthen the
    gate, and needs the held-out real-corpus reproduction before any default flip."""
    return os.environ.get("ENGRAM_SOURCE_INDEPENDENCE", "").strip().lower() in _TRUTHY


def independence_deconfounded() -> bool:
    """ENGRAM_SOURCE_INDEPENDENCE_DECONFOUND=1 uses the P88 audit-conditioned
    collusion signal (co-admission of audit-revealed-FALSE values) instead of raw
    agreement, so honest sources that agree because both are RIGHT are no longer
    false-merged. Needs ENGRAM_SOURCE_INDEPENDENCE too; default OFF."""
    return os.environ.get(
        "ENGRAM_SOURCE_INDEPENDENCE_DECONFOUND", "").strip().lower() in _TRUTHY


def threshold() -> float:
    """Below this trust the write is quarantined (never rejected — quarantine
    is rehabilitable, rejection is not; the consistency channel must be able
    to fish a source back out). Env ENGRAM_SOURCE_TRUST_MIN, default 0.25."""
    try:
        return float(os.environ.get("ENGRAM_SOURCE_TRUST_MIN", "0.25"))
    except ValueError:
        return 0.25


_SOURCE_REF_RE = re.compile(r"^(?:source-doc|source|src|doc|file):([^:]+)",
                            re.IGNORECASE)


def canonical_source(verified_by: list[str] | None,
                     fallback: str = "user") -> str:
    """The reputation key for a write: the first source-like ref in
    ``verified_by`` (``source-doc:X:...`` → ``X``), else ``fallback``.

    P85 self-provenance: an engine-signed ref (``actor:composer:...``)
    canonicalises to the NAMESPACED ``actor:composer`` — never the ``user``
    fallback, never a plain source id. Engine writes stay distinguishable
    everywhere downstream, and ``_is_self`` filters them from testimony."""
    from .self_provenance import actor_of, is_self_ref
    for ref in verified_by or []:
        if isinstance(ref, str):
            if is_self_ref(ref):
                name = actor_of(ref)
                if name:
                    return f"actor:{name}"
                continue
            m = _SOURCE_REF_RE.match(ref.strip())
            if m:
                return m.group(1)
    return fallback


def _is_self(source: str) -> bool:
    """A canonicalised source id that names the engine itself (P85)."""
    return isinstance(source, str) and source.strip().lower().startswith("actor:")


@dataclass
class _Ledger:
    confirms: float = 0.0
    contradicts: float = 0.0
    good: float = 0.0
    bad: float = 0.0

    def consistency(self) -> float:
        return (self.confirms + 1.0) / (self.confirms + self.contradicts + 2.0)

    def outcome(self) -> float:
        return (self.good + 1.0) / (self.good + self.bad + 2.0)


@dataclass
class SourceTrustBook:
    """Pure, deterministic per-source reputation state."""

    _sources: dict[str, _Ledger] = field(default_factory=dict)
    #: Per-source report vectors {source: {key: value}} — the substrate for
    #: independence clustering (transient / in-memory, per write-stream).
    _reports: dict[str, dict[str, str]] = field(default_factory=dict)
    #: Audit anchor {key: value-revealed-false} — the do-operator for DECONFOUNDED
    #: independence (Vivarium P88): colluders co-admit these, honest sources do not.
    _false_value: dict[str, str] = field(default_factory=dict)

    def _ledger(self, source: str) -> _Ledger:
        led = self._sources.get(source)
        if led is None:
            led = self._sources[source] = _Ledger()
        return led

    # ---- consistency channel (write-stream, use-independent) ----------------

    def record_report(self, source: str, key: str, value: str) -> None:
        """Remember that ``source`` asserted ``value`` for ``key`` — the substrate
        for independence clustering (copies of one feed report identical
        ``(key, value)`` rows). In-memory / per write-stream; call as writes arrive."""
        if source and key:
            self._reports.setdefault(source, {})[str(key)] = str(value)

    def mark_false(self, key: str, value: str) -> None:
        """Audit anchor / do-operator (Vivarium P88): record that ``value`` asserted
        for ``key`` was revealed FALSE (failed in use, or a contradiction the audit
        resolved against it). Deconfounds independence — colluders co-ADMIT these,
        honest sources (who track truth) do not."""
        if key:
            self._false_value[str(key)] = str(value)

    def _agreement(self, a: str, b: str) -> float:
        ra, rb = self._reports.get(a, {}), self._reports.get(b, {})
        shared = ra.keys() & rb.keys()
        if len(shared) < _COPY_MIN_SHARED:
            return 0.0  # too little co-reporting to call them copies -> independent
        return sum(1 for k in shared if ra[k] == rb[k]) / len(shared)

    def _collusion_signal(self, a: str, b: str) -> float:
        """P(both admitted the audited-FALSE value | keys audited false that both
        reported) — the deconfounded replacement for raw agreement. Honest peers ~0
        (they reject falsehoods), colluders ~1. Unconfounded by shared truth because
        it conditions on the audit (Vivarium P88)."""
        fv = self._false_value
        ra, rb = self._reports.get(a, {}), self._reports.get(b, {})
        shared = [k for k in fv if k in ra and k in rb]
        if len(shared) < _COLLUSION_MIN_SHARED:
            return 0.0
        return sum(1 for k in shared if ra[k] == fv[k] and rb[k] == fv[k]) / len(shared)

    def independent_clusters(self, sources: list[str], *,
                             deconfounded: bool = False) -> int:
        """Number of INDEPENDENT source clusters: correlated sources collapse to ONE,
        so N copies/colluders of a single origin count as one witness — closing the
        manufactured-consensus hole that distinct source-IDs leave open (Vivarium
        collusion: naive 2-confirm wrong 1.0 -> cluster-aware blocked).

        Two clustering signals:

        * default (``deconfounded=False``) — raw report-vector AGREEMENT. Simple, but
          CONFOUNDED by shared truth: honest sources that agree because both are RIGHT
          also merge (Vivarium v1: 3.6/4 honest false-merged). Use when no audit
          signal exists yet.
        * ``deconfounded=True`` (Vivarium P88, cartel_kill_v56) — co-admission of
          AUDIT-REVEALED-FALSE values (see ``mark_false``). The audit is the
          do-operator: honest peers reject falsehoods so they do NOT merge, colluders
          both admit them so they do. The mature signal — it removes the common-cause
          false positives — and needs accumulated audit anchors to bite (until then
          nobody merges, i.e. every source counts as independent: fail-open, never a
          silent false-merge)."""
        src = sorted({s for s in sources if s})
        parent = {s: s for s in src}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for a, b in combinations(src, 2):
            merge = (self._collusion_signal(a, b) >= _COLLUSION_CPARAM if deconfounded
                     else self._agreement(a, b) >= _COPY_AGREEMENT)
            if merge:
                parent[find(a)] = find(b)
        return len({find(s) for s in src})

    def accept_value(self, candidates: dict[str, list[str]], *,
                     deconfounded: bool = False) -> tuple[str, list[str]] | None:
        """Independence-aware ACCEPTANCE for one key. ``candidates`` maps each asserted
        value to the sources asserting it; return ``(value, sources)`` of the value
        backed by the most INDEPENDENT witnesses (>=2 and a UNIQUE maximum), else None.

        This is the rule the real-path reproduction (benchmark/independence_validation
        .py) proved necessary: counting RAW sources hands a write-majority cartel the
        'accepted' slot — they self-confirm, honest sources become the contradictors,
        trust inverts (honest 0.28 < cartel 0.95). Counting INDEPENDENT clusters makes N
        colluders of one feed a single witness, so a genuinely-corroborated honest value
        (>=2 independent sources) wins regardless of cartel SIZE. A tie on independent
        witnesses is a real conflict → accept NEITHER (fail-safe: never confirm on an
        ambiguous majority)."""
        ranked = []
        for value, srcs in candidates.items():
            # P85: engine-signed sources are never independent witnesses — an
            # echo chamber of actor ids must not win (or tie) an acceptance.
            clean = [s for s in srcs if s and not _is_self(s)]
            n = self.independent_clusters(clean, deconfounded=deconfounded)
            ranked.append((n, value, sorted(set(clean))))
        ranked.sort(key=lambda r: (-r[0], r[1]))
        if not ranked or ranked[0][0] < 2:
            return None
        if len(ranked) > 1 and ranked[1][0] == ranked[0][0]:
            return None                       # tie on independent witnesses -> ambiguous
        return (ranked[0][1], ranked[0][2])

    def observe_confirmation(self, sources: list[str], *,
                             require_independent: bool = False,
                             deconfounded: bool = False) -> None:
        """≥2 DISTINCT sources asserted the same accepted value → all rise. A single
        (or self-duplicated) source cannot confirm itself. With
        ``require_independent`` (the independence-aware write-gate) the ≥2 must be ≥2
        INDEPENDENT clusters, so copies/colluders of one feed cannot self-confirm;
        ``deconfounded`` selects the P88 audit-conditioned signal (see
        ``independent_clusters``)."""
        # P85: engine-signed sources neither witness nor earn reputation —
        # self-echo cannot manufacture the >=2 agreement, and the engine's
        # facts are admitted through VERIFICATION, not reputation.
        distinct = sorted({s for s in sources if s and not _is_self(s)})
        n = (self.independent_clusters(distinct, deconfounded=deconfounded)
             if require_independent else len(distinct))
        if n < 2:
            return
        for s in distinct:
            self._ledger(s).confirms += 1.0

    def observe_contradiction(self, source: str) -> None:
        """``source`` contradicted a value accepted/confirmed by others."""
        if source:
            self._ledger(source).contradicts += 1.0

    # ---- outcome channel (a-posteriori) --------------------------------------

    def observe_outcome(self, source: str, *, good: bool,
                        weight: float = 1.0) -> None:
        """A claim by ``source`` succeeded/failed in use. ``weight`` < 1
        attenuates the blame (stale fact, shared derivation — task #18)."""
        if not source:
            return
        w = min(1.0, max(0.0, float(weight)))
        led = self._ledger(source)
        if good:
            led.good += w
        else:
            led.bad += w

    # ---- reads ----------------------------------------------------------------

    def consistency(self, source: str) -> float:
        led = self._sources.get(source)
        return led.consistency() if led else _NEUTRAL

    def outcome(self, source: str) -> float:
        led = self._sources.get(source)
        return led.outcome() if led else _NEUTRAL

    def trust(self, source: str) -> float:
        """Conservative combination: the weaker OBSERVED channel decides.

        A channel with no evidence does not cap the other — else every
        source without recorded outcomes would be pinned to the 0.5 prior
        forever (caught by test_trusted_sleeper...: 'honest' must clear 0.6
        on consistency alone). The sleeper hole stays covered: the moment
        bad outcomes exist, that channel bites through the min."""
        led = self._sources.get(source)
        if led is None:
            return _NEUTRAL
        channels = []
        if led.confirms or led.contradicts:
            channels.append(led.consistency())
        if led.good or led.bad:
            channels.append(led.outcome())
        return min(channels) if channels else _NEUTRAL

    # ---- persistence-friendly round-trip --------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {s: {"confirms": led.confirms, "contradicts": led.contradicts,
                    "good": led.good, "bad": led.bad}
                for s, led in self._sources.items()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SourceTrustBook:
        book = cls()
        for s, row in (data or {}).items():
            book._sources[s] = _Ledger(
                confirms=float(row.get("confirms", 0.0)),
                contradicts=float(row.get("contradicts", 0.0)),
                good=float(row.get("good", 0.0)),
                bad=float(row.get("bad", 0.0)))
        return book


# ---- auto-confirmation on write (independence-aware acceptance) --------------

def _accept_by_count(candidates: dict[str, list[str]]) -> tuple[str, list[str]] | None:
    """Naive >=2-DISTINCT acceptance (the pre-independence baseline, kept for A/B):
    the value with the most distinct sources, >=2 and a unique max, else None. This
    is what a write-majority cartel defeats — independence replaces it."""
    ranked = sorted(
        ((len({s for s in srcs if s}), v, sorted({s for s in srcs if s}))
         for v, srcs in candidates.items()),
        key=lambda r: (-r[0], r[1]))
    if not ranked or ranked[0][0] < 2:
        return None
    if len(ranked) > 1 and ranked[1][0] == ranked[0][0]:
        return None
    return (ranked[0][1], ranked[0][2])


def auto_confirm_agreement(book: SourceTrustBook, subject_key: str,
                           reports: dict[str, str], *, independence: bool = False,
                           deconfound: bool = False) -> dict[str, Any]:
    """Turn a set of sources asserting values about ONE subject into consistency-
    channel updates. ``reports`` maps ``source -> asserted value`` (already grouped by
    subject). Records the report vectors, picks the accepted value (independence-aware
    when ``independence`` — the fix the real-path reproduction demanded, so a
    write-majority cartel cannot win acceptance), confirms its sources, and contradicts
    the divergent ones. Returns ``{accepted, confirmed, contradicted}``.

    ONLY touches the consistency channel — never the outcome channel: temporal
    supersession is the world moving, not a source lying (semantic.py store() note,
    the reverted #20b attribution error).

    P85: engine-signed reporters (``actor:*``) are stripped up front — they can
    neither vote a value into acceptance nor be confirmed/contradicted."""
    clean = {s: str(v) for s, v in reports.items()
             if s and v and not _is_self(s)}
    for src, val in clean.items():
        book.record_report(src, str(subject_key), val)
    candidates: dict[str, list[str]] = {}
    for src, val in clean.items():
        candidates.setdefault(val, []).append(src)
    accepted = (book.accept_value(candidates, deconfounded=deconfound)
                if independence else _accept_by_count(candidates))
    if accepted is None:
        return {"accepted": None, "confirmed": [], "contradicted": []}
    acc_val, acc_srcs = accepted
    book.observe_confirmation(acc_srcs, require_independent=independence,
                              deconfounded=deconfound)
    contradicted: list[str] = []
    for val, srcs in candidates.items():
        if val == acc_val:
            continue
        for s in sorted({x for x in srcs if x}):
            book.observe_contradiction(s)
            contradicted.append(s)
    return {"accepted": acc_val, "confirmed": acc_srcs,
            "contradicted": sorted(set(contradicted))}


# ---- attribution-aware blame attenuation (task #18b, transfer law L3) --------

_STALE_WEIGHT_FLOOR = 0.2


def stale_weight(age_s: float, *, half_life_s: float) -> float:
    """Outcome-blame weight for a fact of age ``age_s`` in a world whose
    values live ``half_life_s`` on average: full blame young, half at one
    half-life, floored at 0.2 (an old fact's failure still says SOMETHING
    about its source — zero would let liars launder through time). No
    half-life info → full blame: fail-safe, never silently soft. This is
    the L3 law made a number: staleness blames the CLAIM's age, not the
    source wholesale."""
    if half_life_s <= 0 or age_s <= 0:
        return 1.0
    return max(_STALE_WEIGHT_FLOOR, 0.5 ** (age_s / half_life_s))


def half_life_s() -> float:
    """The world's value half-life for outcome attenuation.
    Env ENGRAM_SOURCE_TRUST_HALF_LIFE_DAYS, default 7 days."""
    try:
        days = float(os.environ.get("ENGRAM_SOURCE_TRUST_HALF_LIFE_DAYS", "7"))
    except ValueError:
        days = 7.0
    return max(0.0, days) * 86400.0


# ---- persistence (the store's own SQLite, one small table) -------------------

_TABLE_SQL = """CREATE TABLE IF NOT EXISTS source_trust (
    source TEXT PRIMARY KEY,
    confirms REAL NOT NULL DEFAULT 0,
    contradicts REAL NOT NULL DEFAULT 0,
    good REAL NOT NULL DEFAULT 0,
    bad REAL NOT NULL DEFAULT 0,
    updated_at REAL NOT NULL
)"""


def load_book(db_path: str | Path) -> SourceTrustBook:
    """Read the persisted book (empty book if the table is absent)."""
    book = SourceTrustBook()
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute(_TABLE_SQL)
            rows = conn.execute(
                "SELECT source, confirms, contradicts, good, bad "
                "FROM source_trust").fetchall()
    except sqlite3.Error:
        return book
    for s, c, x, g, b in rows:
        book._sources[s] = _Ledger(confirms=c, contradicts=x, good=g, bad=b)
    return book


# Process-wide book cache keyed by db path: the client (gate consult, dossier)
# and the store-side supersession hook must mutate the SAME in-memory book, or
# one path's writes are invisible to the other's cached copy (the #20b bug:
# the client cached its book, observe_supersessions loaded a second one, they
# diverged). SQLite stays the source of truth across processes.
_BOOK_CACHE: dict[str, SourceTrustBook] = {}


def get_book(db_path: str | Path) -> SourceTrustBook:
    """Shared per-path book (loaded once, then the live in-memory object)."""
    key = str(db_path)
    book = _BOOK_CACHE.get(key)
    if book is None:
        book = _BOOK_CACHE[key] = load_book(key)
    return book


def reset_book_cache() -> None:
    """Test hook: drop the process cache so a fresh db path starts clean."""
    _BOOK_CACHE.clear()


def save_book(db_path: str | Path, book: SourceTrustBook) -> None:
    """Upsert every ledger row. Best-effort: reputation persistence must
    never break a write."""
    now = time.time()
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute(_TABLE_SQL)
            conn.executemany(
                "INSERT INTO source_trust "
                "(source, confirms, contradicts, good, bad, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(source) DO UPDATE SET "
                "confirms=excluded.confirms, contradicts=excluded.contradicts,"
                " good=excluded.good, bad=excluded.bad, "
                "updated_at=excluded.updated_at",
                [(s, led.confirms, led.contradicts, led.good, led.bad, now)
                 for s, led in book._sources.items()])
            conn.commit()
    except sqlite3.Error:
        pass
