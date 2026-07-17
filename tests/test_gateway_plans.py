"""Subscription plans + quotas — the SaaS commercial layer."""
from __future__ import annotations

from verimem.gateway_plans import (
    DEFAULT_PLAN,
    F_SOURCE_TRUST,
    F_SSO,
    get_plan,
    is_plan,
    quota_status,
)


def test_unknown_plan_falls_to_least_privilege():
    assert get_plan("free").name == "free"
    assert get_plan("enterprise").name == "enterprise"
    assert get_plan("nonsense").name == DEFAULT_PLAN == "free"   # never grant paid by accident
    assert get_plan(None).name == "free"
    assert is_plan("pro") and not is_plan("platinum")


def test_fact_caps_enforced_per_tier():
    free = get_plan("free")
    assert free.within_facts(999) and not free.within_facts(1000)   # hard cap at 1000
    assert get_plan("enterprise").within_facts(10_000_000)          # unlimited


def test_features_are_gated_by_tier():
    assert not get_plan("free").allows(F_SOURCE_TRUST)   # trust hardening is paid
    assert get_plan("pro").allows(F_SOURCE_TRUST)
    assert get_plan("enterprise").allows(F_SSO)
    assert not get_plan("pro").allows(F_SSO)             # SSO is enterprise-only


def test_quota_status_snapshot():
    q = quota_status(get_plan("free"), facts_used=750)
    assert q["plan"] == "free" and q["facts_remaining"] == 250
    assert q["facts_over_limit"] is False
    over = quota_status(get_plan("free"), facts_used=1200)
    assert over["facts_over_limit"] is True and over["facts_remaining"] == 0
    ent = quota_status(get_plan("enterprise"), facts_used=5_000_000)
    assert ent["facts_limit"] is None and ent["facts_remaining"] is None
    assert ent["facts_over_limit"] is False              # unlimited never over


def test_self_host_is_unmetered():
    """The classic self-host product runs everything, no caps — same code, no money."""
    sh = get_plan("self_host")
    assert sh.max_facts is None and sh.rate_limit_per_minute is None
    assert sh.allows(F_SOURCE_TRUST) and sh.allows(F_SSO)
