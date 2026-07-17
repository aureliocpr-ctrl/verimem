"""Subscription plans + quotas — the commercial layer of the Verimem SaaS.

The multi-tenant gateway (auth, isolation, metering, backups) already exists; this is
what turns it into a sellable managed service: named tiers with enforced limits, so a
tenant on ``free`` cannot use what ``pro``/``enterprise`` pay for. Pure, deterministic,
no I/O — the gateway attaches a plan to each key and enforces these limits at the edge.

Design: limits are ``None`` = unlimited (enterprise), a positive int = a hard cap.
Features are an allow-set so gating a capability is a membership test, not a scatter of
``if plan == ...`` across the code. The classic self-host product simply runs without a
plan (``UNLIMITED``) — the plans exist only where money does, the SaaS.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# feature flags a plan may grant (checked by membership, not string compares)
F_SOURCE_TRUST = "source_trust"      # the two-channel trust hardening
F_BACKUPS = "backups"                # hot backups / restore
F_SSO = "sso"                        # enterprise identity
F_AIRGAP = "airgap"                  # verified zero-egress deploy
F_PRIORITY = "priority_support"


@dataclass(frozen=True)
class Plan:
    """A subscription tier. ``None`` limits mean unlimited."""

    name: str
    max_facts: int | None                    # stored facts per tenant
    rate_limit_per_minute: int | None        # requests/min per key
    max_document_bytes: int                  # single-document ingest cap
    features: frozenset[str] = field(default_factory=frozenset)

    def allows(self, feature: str) -> bool:
        return feature in self.features

    def within_facts(self, current: int) -> bool:
        return self.max_facts is None or current < self.max_facts


_MB = 1024 * 1024

#: The catalogue. Ordered free → enterprise; ``self_host`` is the un-metered classic
#: product (everything on, no caps) so the same code serves both business models.
PLANS: dict[str, Plan] = {
    "free": Plan("free", max_facts=1_000, rate_limit_per_minute=60,
                 max_document_bytes=10 * _MB,
                 features=frozenset()),
    "pro": Plan("pro", max_facts=100_000, rate_limit_per_minute=600,
                max_document_bytes=50 * _MB,
                features=frozenset({F_SOURCE_TRUST, F_BACKUPS})),
    "enterprise": Plan("enterprise", max_facts=None, rate_limit_per_minute=None,
                       max_document_bytes=200 * _MB,
                       features=frozenset({F_SOURCE_TRUST, F_BACKUPS, F_SSO,
                                           F_AIRGAP, F_PRIORITY})),
    "self_host": Plan("self_host", max_facts=None, rate_limit_per_minute=None,
                      max_document_bytes=200 * _MB,
                      features=frozenset({F_SOURCE_TRUST, F_BACKUPS, F_SSO,
                                          F_AIRGAP, F_PRIORITY})),
}

DEFAULT_PLAN = "free"


def get_plan(name: str | None) -> Plan:
    """Resolve a plan name to its Plan; unknown/empty → the ``free`` default (fail
    to the LEAST privilege, never accidentally grant a paid tier)."""
    return PLANS.get((name or "").strip().lower(), PLANS[DEFAULT_PLAN])


def is_plan(name: str | None) -> bool:
    return (name or "").strip().lower() in PLANS


def quota_status(plan: Plan, *, facts_used: int) -> dict[str, Any]:
    """A tenant-facing snapshot of headroom — what a dashboard/402 shows."""
    remaining = (None if plan.max_facts is None
                 else max(0, plan.max_facts - facts_used))
    return {
        "plan": plan.name,
        "facts_used": facts_used,
        "facts_limit": plan.max_facts,
        "facts_remaining": remaining,
        "facts_over_limit": not plan.within_facts(facts_used),
        "rate_limit_per_minute": plan.rate_limit_per_minute,
        "max_document_bytes": plan.max_document_bytes,
        "features": sorted(plan.features),
    }


__all__ = ["Plan", "PLANS", "DEFAULT_PLAN", "get_plan", "is_plan", "quota_status",
           "F_SOURCE_TRUST", "F_BACKUPS", "F_SSO", "F_AIRGAP", "F_PRIORITY"]
