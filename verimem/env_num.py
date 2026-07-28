"""Numeric settings read from the environment — one parser, one contract.

Every threshold in this package was parsed with the same idiom:

    try:
        return float(os.environ.get(NAME, DEFAULT))
    except ValueError:
        return DEFAULT

which is correct for typos and wrong for ``nan``: ``float("nan")`` does not
raise. A NaN threshold is worse than a wrong one, because every comparison
against NaN is False — ``score < threshold`` never holds, so the gate admits
everything and reports nothing. The guard stays in the code, stays covered by
its tests, and quietly stops guarding. ``inf`` and ``-inf`` are the same class
seen from either end: one refuses every write, the other admits every write.

Measured 2026-07-28 across the package: 16 of 18 (threshold × poison) pairs
accepted the value, including the always-on composer floor, the CE uncertainty
band, the P85 self-provenance quota, per-source trust, and the ingest grounding
cut. The two that survived did so by accident — ``max(0.0, float(raw))``
filters NaN while ``max(float(raw), 0.0)`` does not, so safety depended on
argument order rather than on a decision.

The contract here: a malformed value is operator error, so fall back to the
DECLARED default. That keeps the failure recoverable and visible in the
default's own documentation, instead of silently disarming a gate.
"""
from __future__ import annotations

import math
import os

__all__ = ["env_float", "finite_or"]


def finite_or(raw: object, default: float | None) -> float | None:
    """``raw`` as a finite float, else ``default``.

    For callers that already hold the string (or that layer extra meanings such
    as ``auto`` / ``off`` on top of it) and only need the numeric contract.

    Pass ``default=None`` to mean "no usable value here" — for callers with a
    CASCADE of sources (a specific env var, then a general one, then a constant)
    that need to fall through to the next rung instead of stopping at the first
    one that happens to be set but malformed. Without it those callers would
    each re-implement the finiteness check, which is how this defect spread in
    the first place.
    """
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)                       # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return value if math.isfinite(value) else default


def env_float(name: str, default: float) -> float:
    """The value of env var ``name`` as a finite float, else ``default``.

    Unset, empty, unparseable and non-finite all resolve to ``default`` — the
    caller gets a number it can compare against, always.
    """
    return finite_or(os.environ.get(name, "").strip(), default)
