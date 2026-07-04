"""Cycle 2026-05-27 (round 9) — L1.17 monitored/observed claim detector.

Pattern claim "monitored 24/7" / "observed in production" senza dashboard/
alert/metric evidence reale. Closes observability gap (ortogonal a tutti).

Patterns:
- English: monitored, observed, tracked, watched, alerted
- Italian: monitorato, monitorata, osservato, tracciato

Evidence accepted:
- dashboard:<url> or grafana:<board>
- alert:<id>_configured or prometheus:<rule>
- metric:<name>_published or telemetry:<source>
- sentry:<project>_active or datadog:<id>
- log:<path>_tracked
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from .l1_evidence import ref_is_negated as _ref_is_negated

_MONITORED_PATTERN = re.compile(
    r"\b(?:monitored|observed|tracked|watched|alerted|"
    r"monitorato|monitorata|monitorati|monitorate|"
    r"osservato|osservata|"
    r"tracciato|tracciata)\b",
    re.IGNORECASE,
)

_MONITORED_EVIDENCE_PREFIXES: tuple[str, ...] = (
    "dashboard:", "grafana:", "kibana:",
    "alert:", "prometheus:", "alertmanager:",
    "metric:", "telemetry:", "metrics:",
    "sentry:", "datadog:", "newrelic:",
    "log:", "logs:",
)


@dataclass(frozen=True)
class MonitoredClaimWarning:
    matched_text: str
    advice: str


def _has_monitored_evidence(verified_by: Iterable[str] | None) -> bool:
    if not verified_by:
        return False
    for ref in verified_by:
        if not isinstance(ref, str):
            continue
        lower = ref.lower()
        # FIX 2026-06-09 (audit#3): a ref whose payload is a not-done modifier
        # ('alert:planned', 'metric:tbd') does NOT prove the thing is monitored.
        # The artifact-pointer refs (dashboard:/grafana:/prometheus:rule_active)
        # stay valid — only the explicit not-yet refs are rejected.
        if _ref_is_negated(ref):
            continue
        if any(lower.startswith(p) for p in _MONITORED_EVIDENCE_PREFIXES):
            return True
    return False


def detect_unsupported_monitored_claim(
    *,
    proposition: str,
    verified_by: Iterable[str] | None,
) -> MonitoredClaimWarning | None:
    if not proposition:
        return None
    m = _MONITORED_PATTERN.search(proposition)
    if m is None:
        return None
    matched_text = m.group(0)
    if _has_monitored_evidence(verified_by):
        return None
    return MonitoredClaimWarning(
        matched_text=matched_text,
        advice=(
            f"Proposition contains monitoring claim {matched_text!r} but "
            f"no observability evidence in verified_by. Add at least "
            f"one of: dashboard:<url>, grafana:<board>, alert:<id>, "
            f"prometheus:<rule>, metric:<name>, sentry:<project>."
        ),
    )


__all__ = ["MonitoredClaimWarning", "detect_unsupported_monitored_claim"]
