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
caller (behind ENGRAM_SOURCE_TRUST, default OFF; no default flip before the
held-out reproduction on real VeriMem data).
"""
from __future__ import annotations

import os
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = ["SourceTrustBook", "canonical_source", "enabled", "threshold",
           "load_book", "save_book"]

_NEUTRAL = 0.5

# ---- gate wiring knobs (behind-flag, default OFF — TRUST_CORE.md guard-rail:
# no default flip before the held-out reproduction on real VeriMem data) ------

_TRUTHY = {"1", "true", "yes", "on"}


def enabled() -> bool:
    """ENGRAM_SOURCE_TRUST=1 turns the write-gate consultation on."""
    return os.environ.get("ENGRAM_SOURCE_TRUST", "").strip().lower() in _TRUTHY


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
    ``verified_by`` (``source-doc:X:...`` → ``X``), else ``fallback``."""
    for ref in verified_by or []:
        if isinstance(ref, str):
            m = _SOURCE_REF_RE.match(ref.strip())
            if m:
                return m.group(1)
    return fallback


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

    def _ledger(self, source: str) -> _Ledger:
        led = self._sources.get(source)
        if led is None:
            led = self._sources[source] = _Ledger()
        return led

    # ---- consistency channel (write-stream, use-independent) ----------------

    def observe_confirmation(self, sources: list[str]) -> None:
        """≥2 DISTINCT sources asserted the same accepted value → all rise.
        A single (or self-duplicated) source cannot confirm itself."""
        distinct = sorted({s for s in sources if s})
        if len(distinct) < 2:
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
    def from_dict(cls, data: dict[str, Any]) -> "SourceTrustBook":
        book = cls()
        for s, row in (data or {}).items():
            book._sources[s] = _Ledger(
                confirms=float(row.get("confirms", 0.0)),
                contradicts=float(row.get("contradicts", 0.0)),
                good=float(row.get("good", 0.0)),
                bad=float(row.get("bad", 0.0)))
        return book


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
