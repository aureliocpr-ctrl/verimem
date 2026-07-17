"""Per-tenant, per-domain self-trust learned online — REMORSE graft, phase-1 SHADOW.

Provenance: grafted 2026-07-16 from the remorse lab (Code/remorse/remorse/
{ledger,sim,eval_m}.py, 29/29 tests; handoff fact ab53896fe93e +
HANDOFF-VERIMEM.md, Aurelio's mandate). Proven there: meta of 3 experts at
91-122% of the local best on 21/21 corpora; sim closes 90.6% of the
gap-to-oracle. The DEMONSTRATED config is frozen here — do not tune it
without new data:

* experts = lessons@14d, exposure, hazard@14d with the lab's exact smoothing
  ``(num + 0.25) / (den + 5.0)``;
* meta weights ``w *= exp(eta * MRR)`` with eta=3, fixed-share alpha=0.05
  applied per-WINDOW only, UNIFORM cold start (kNN profiling refuted: +37%
  regret; multi-half-life grids refuted: they dilute on short histories);
* anti-poisoning: an unverified external error report weighs 0.2 (halves the
  poisoning damage — the attack is economic, not epistemic).

Non-negotiable design rules (each backed by a falsification in the lab):
1. two separate targets — audit-confirmed errors, NEVER generic corrections
   (a dirty numerator FLIPS verdicts: gold 3/3, regex precision 22%);
2. the denominator (exposure) is MANDATORY — without it the per-domain trust
   predicts the calendar (perm p=0.93).

Phase-1 SHADOW semantics (the 13/7 dead-gates lesson): this module only
OBSERVES and LOGS — nothing here may alter a request, so ``ShadowLedger``
swallows every internal error and the state is in-process (a restart is a
UNIFORM cold start by design; persistence is phase 2, per-tenant flag ON for
new tenants — never "off by default").
"""
from __future__ import annotations

import math
from collections import defaultdict

DAY = 86400.0

#: The demonstrated horizon for both lessons and exposure decay.
HALF_LIFE_DAYS = 14.0

#: Lab smoothing constants for the hazard rate (eval_m.py line 46).
_NUM_PRIOR = 0.25
_DEN_PRIOR = 5.0

#: Anti-poisoning: weight of an unverified EXTERNAL error report.
EXTERNAL_WEIGHT = 0.2

#: Shadow-only advice threshold (LOGGED, never applied in phase 1).
_ADVICE_HAZARD = 0.10

PREDICTORS = ("lessons_only", "exposure_only", "hazard_x_exposure")


class ConsequenceLedger:
    """Decay-weighted mass of events per domain (verbatim from the lab).

    Every documented event is ``(t, domain, weight)``; a domain's mass at
    ``now`` is the sum of its weights decayed exponentially with the chosen
    half-life. Future events are invisible (no clock-skew credit)."""

    def __init__(self, half_life_days: float = HALF_LIFE_DAYS, alpha: float = 0.1):
        if half_life_days <= 0:
            raise ValueError("half_life_days must be > 0 (math.inf = no decay)")
        self.half_life = half_life_days * DAY
        self.alpha = alpha
        self._events: dict[str, list[tuple[float, float]]] = defaultdict(list)

    def record(self, t: float, domain: str, weight: float = 1.0) -> None:
        self._events[domain].append((t, weight))

    def mass(self, domain: str, now: float) -> float:
        total = 0.0
        for t, w in self._events.get(domain, ()):
            age = now - t
            if age < 0:
                continue  # future events: invisible to the ledger
            if math.isinf(self.half_life):
                total += w
            else:
                total += w * 2.0 ** (-age / self.half_life)
        return total

    def domains(self) -> list[str]:
        return list(self._events.keys())


class AdaptiveMeta:
    """Expert-advice weights over the 3 predictors, per-window updates.

    UNIFORM cold start; at the close of a window each predictor's observed
    MRR multiplies its weight by ``exp(eta * mrr)``; normalize; then
    fixed-share redistributes ``alpha`` uniformly so no expert ever dies
    (Herbster-Warmuth) — the drifting-world recovery the lab measured."""

    def __init__(self, eta: float = 3.0, alpha: float = 0.05):
        self.eta = eta
        self.alpha = alpha
        k = len(PREDICTORS)
        self.weights: dict[str, float] = {p: 1.0 / k for p in PREDICTORS}

    def update_window(self, mrr_by_predictor: dict[str, float]) -> None:
        w = {p: self.weights[p] * math.exp(self.eta * float(mrr_by_predictor.get(p, 0.0)))
             for p in PREDICTORS}
        tot = sum(w.values()) or 1.0
        k = len(PREDICTORS)
        self.weights = {p: (1 - self.alpha) * (v / tot) + self.alpha / k
                        for p, v in w.items()}


class ShadowLedger:
    """Phase-1 shadow: observe (tenant, topic) traffic, LOG decisions only.

    Numerator = audit-confirmed errors (``observe_error``; external unverified
    reports weigh ``EXTERNAL_WEIGHT``). Denominator = recall exposure
    (``observe_recall``) — mandatory, else trust predicts the calendar.
    ``decision`` returns the 3 expert estimates + meta weights + the smoothed
    hazard rate and a shadow-only advice; it NEVER raises (log-only safety:
    a broken shadow must never break a request)."""

    def __init__(self) -> None:
        self._lessons: dict[str, ConsequenceLedger] = {}
        self._exposure: dict[str, ConsequenceLedger] = {}
        self._meta: dict[str, AdaptiveMeta] = {}

    def _led(self, book: dict[str, ConsequenceLedger], tenant: str) -> ConsequenceLedger:
        led = book.get(tenant)
        if led is None:
            led = book[tenant] = ConsequenceLedger(HALF_LIFE_DAYS)
        return led

    # ── observations (both swallow everything: shadow-only safety) ──────────
    def observe_recall(self, tenant: str, topics: list[str] | None, *,
                       now: float) -> None:
        try:
            for topic in topics or ():
                self._led(self._exposure, str(tenant)).record(
                    float(now), str(topic), 1.0)
        except Exception:  # noqa: BLE001 — shadow must never break a request
            pass

    def observe_error(self, tenant: str, topic: str, *, now: float,
                      external: bool = False) -> None:
        try:
            weight = EXTERNAL_WEIGHT if external else 1.0
            self._led(self._lessons, str(tenant)).record(
                float(now), str(topic), weight)
        except Exception:  # noqa: BLE001
            pass

    def close_window(self, tenant: str, mrr_by_predictor: dict[str, float]) -> None:
        """Per-window meta update — fed by the shadow-log analysis (phase 1
        produces the windows; applying the weights to routing is phase 2)."""
        try:
            meta = self._meta.setdefault(str(tenant), AdaptiveMeta())
            meta.update_window(mrr_by_predictor)
        except Exception:  # noqa: BLE001
            pass

    # ── the logged decision ─────────────────────────────────────────────────
    def decision(self, tenant: str, topic: str, *, now: float) -> dict:
        try:
            tenant, topic = str(tenant), str(topic)
            num = self._led(self._lessons, tenant).mass(topic, now)
            den = self._led(self._exposure, tenant).mass(topic, now)
            rate = (num + _NUM_PRIOR) / (den + _DEN_PRIOR)
            meta = self._meta.setdefault(tenant, AdaptiveMeta())
            estimates = {"lessons_only": num, "exposure_only": den,
                         "hazard_x_exposure": rate * den}
            return {"tenant": tenant, "topic": topic,
                    "lessons_mass": round(num, 4),
                    "exposure_mass": round(den, 4),
                    "hazard": round(rate, 4),
                    "estimates": {k: round(v, 4) for k, v in estimates.items()},
                    "meta_weights": {k: round(v, 4)
                                     for k, v in meta.weights.items()},
                    "advice": "verify" if rate > _ADVICE_HAZARD else "trust"}
        except Exception:  # noqa: BLE001 — degraded but present, never raising
            return {"tenant": str(tenant), "topic": str(topic), "hazard": None,
                    "advice": "trust", "error": "shadow_internal"}


#: process-wide shadow instance (phase 1 is in-process by design — a restart
#: is a uniform cold start; per-tenant persistence lands with phase 2).
_shadow: ShadowLedger | None = None


def get_shadow() -> ShadowLedger:
    global _shadow
    if _shadow is None:
        _shadow = ShadowLedger()
    return _shadow


def reset_shadow() -> None:
    """Tests only."""
    global _shadow
    _shadow = None
