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

from dataclasses import dataclass, field
from typing import Any

__all__ = ["SourceTrustBook"]

_NEUTRAL = 0.5


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
