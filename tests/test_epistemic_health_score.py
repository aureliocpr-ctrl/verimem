"""TDD for engram.epistemic_health — corpus epistemic-health audit (Ph4)."""
from __future__ import annotations

import types

from engram.epistemic_health import FactAudit, audit_corpus, audit_one, health_report


def _f(fid, prop, source=None):  # noqa: ANN001
    return types.SimpleNamespace(id=fid, proposition=prop, source=source)


def test_audit_one_grounded() -> None:
    a = audit_one(_f("1", "Paris is the capital", "France's capital is Paris"),
                  grounder=lambda s, p: 95.0, threshold=85)
    assert a.has_source is True
    assert a.grounded is True


def test_audit_one_ungrounded() -> None:
    a = audit_one(_f("2", "X", "an unrelated source"), grounder=lambda s, p: 20.0, threshold=85)
    assert a.grounded is False


def test_audit_one_no_source_is_none() -> None:
    a = audit_one(_f("3", "X", None), grounder=lambda s, p: 99.0)
    assert a.has_source is False
    assert a.grounded is None  # unauditable, NOT failed


def test_audit_one_freshness_applied() -> None:
    a = audit_one(_f("1", "p", "src"), grounder=lambda s, p: 90.0, freshness_fn=lambda f: False)
    assert a.fresh is False


def test_health_report_fractions() -> None:
    audits = [
        FactAudit("1", True, True, None, False),
        FactAudit("2", True, False, None, False),
        FactAudit("3", False, None, None, False),  # no source -> unauditable
    ]
    r = health_report(audits)
    assert r["n"] == 3
    assert r["provenance_coverage"] == round(2 / 3, 3)
    assert r["grounded_fraction"] == 0.5  # 1 grounded of 2 audited
    assert r["n_grounding_audited"] == 2
    assert r["ungrounded_fact_ids"] == ["2"]


def test_health_report_composite_perfect() -> None:
    audits = [FactAudit("1", True, True, None, False), FactAudit("2", True, True, None, False)]
    assert health_report(audits)["composite"] == 1.0


def test_health_report_contested_lowers_score() -> None:
    audits = [FactAudit("1", True, True, None, True), FactAudit("2", True, True, None, False)]
    r = health_report(audits)
    assert r["uncontested_fraction"] == 0.5


def test_audit_corpus_driver() -> None:
    facts = [_f("1", "p", "a source that grounds it"), _f("2", "q", None)]
    r = audit_corpus(facts, grounder=lambda s, p: 90.0, threshold=85)
    assert r["n"] == 2
    assert r["provenance_coverage"] == 0.5
    assert r["grounded_fraction"] == 1.0


def test_empty_corpus() -> None:
    assert health_report([])["composite"] is None


def test_dict_facts_supported() -> None:
    a = audit_one({"id": "d1", "proposition": "p", "source": "grounding src"},
                  grounder=lambda s, p: 90.0, threshold=85)
    assert a.fact_id == "d1"
    assert a.grounded is True
