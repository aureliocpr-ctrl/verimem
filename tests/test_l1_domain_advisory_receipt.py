"""ENGRAM_L1_DOMAIN_ADVISORY must leave a trace on the receipt.

Critic-orchestrator probe 3 on e41991e (2026-07-21, verified on source): the
switch is read from env in exactly 3 places (def, getenv, predicate) and is
NEVER recorded anywhere — a deployment with the L1 keyword family disarmed
produces receipts INDISTINGUISHABLE from one with the gate fully armed, and a
mid-process env mutation disarms it fleet-wide with no audit record.

For a product whose pitch is verifiable provenance, that is a real hole: the
receipt must say when a defense STOOD DOWN, not only when one acted.

Contract pinned here:
  * when the switch is the reason an L1 keyword hit did not escalate, the gate
    appends a ``L1-domain-advisory-observe`` warning (the existing ``*-observe``
    convention: surfaced, but never owns a block reason nor a ledger credit);
  * the marker flows to the SDK add() receipt and, with VERIMEM_AUDIT_LOG on,
    into the audit row's layers — the auditor's surface;
  * no noise: no marker when the switch is off, when no L1 fired, or when the
    personal/world carve-outs would have suppressed the hit anyway (the switch
    changed nothing there).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.anti_confab_gate import run_validation_gate

MARKER = "L1-domain-advisory-observe"

# trips L1.10 ("works"), no personal/world context — escalates under default
KEYWORD_FACT = "The new arbitration clause works in favour of the tenant."
# personal-context keyword fact: suppressed by _personal_fp with or without the
# switch, so the switch changes nothing and must leave no marker
PERSONAL_FACT = "The dentist appointment is scheduled for Monday."
CLEAN_FACT = "The office is in Milan."


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("ENGRAM_L1_DOMAIN_ADVISORY", raising=False)
    monkeypatch.delenv("ENGRAM_L1_STRICT", raising=False)
    yield


def _gate(fact: str):
    return run_validation_gate(proposition=fact, verified_by=["source-doc:x:1"],
                               topic="t/x", agent=None, validate="full")


def _layers(res) -> list[str]:
    return [str(w.get("layer", "")) for w in res.warnings]


def test_marker_present_when_switch_suppresses_an_escalation(monkeypatch):
    monkeypatch.setenv("ENGRAM_L1_DOMAIN_ADVISORY", "1")
    res = _gate(KEYWORD_FACT)
    assert res.action == "persist"
    assert MARKER in _layers(res), \
        "the receipt must record that L1 escalation was suppressed by the switch"


def test_marker_reason_names_the_env(monkeypatch):
    """An auditor reading the warning must learn WHICH switch disarmed the
    layer, without consulting the deployment's env."""
    monkeypatch.setenv("ENGRAM_L1_DOMAIN_ADVISORY", "1")
    res = _gate(KEYWORD_FACT)
    w = next(x for x in res.warnings if x.get("layer") == MARKER)
    assert "ENGRAM_L1_DOMAIN_ADVISORY" in (w.get("reason") or "")


def test_no_marker_when_switch_off():
    res = _gate(KEYWORD_FACT)
    assert res.action == "downgrade"          # armed default still escalates
    assert MARKER not in _layers(res)


def test_no_marker_without_an_l1_hit(monkeypatch):
    monkeypatch.setenv("ENGRAM_L1_DOMAIN_ADVISORY", "1")
    res = _gate(CLEAN_FACT)
    assert MARKER not in _layers(res), "no L1 hit -> nothing was suppressed"


def test_no_marker_when_personal_carveout_already_suppressed(monkeypatch):
    """_personal_fp would have kept this advisory with the switch OFF too —
    the switch changed nothing, so stamping it would overstate its role."""
    monkeypatch.setenv("ENGRAM_L1_DOMAIN_ADVISORY", "1")
    res = _gate(PERSONAL_FACT)
    assert res.action == "persist"
    assert MARKER not in _layers(res)


def test_marker_is_advisory_never_a_blocking_layer(monkeypatch):
    """The ``*-observe`` convention: the marker records a stand-down, so it must
    never be credited as a blocker in the ledger nor own a block reason."""
    from verimem.client import _blocking_layers, _is_advisory_layer
    assert _is_advisory_layer(MARKER) is True
    monkeypatch.setenv("ENGRAM_L1_DOMAIN_ADVISORY", "1")
    res = _gate(KEYWORD_FACT)
    assert MARKER not in _blocking_layers(res.warnings)


def test_sdk_receipt_carries_the_marker(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ENGRAM_L1_DOMAIN_ADVISORY", "1")
    from verimem.client import Memory
    m = Memory(path=tmp_path / "m.db")
    r = m.add(KEYWORD_FACT, topic="legal/deal", source=KEYWORD_FACT,
              verified_by=["source-doc:dd:1"])
    assert r.get("status") != "quarantined"
    got = [str(w.get("layer", "")) for w in (r.get("warnings") or [])]
    assert MARKER in got, "the customer-facing receipt must show the stand-down"


def test_audit_row_records_the_stand_down(tmp_path: Path, monkeypatch):
    """With the audit trail on, the row for an admitted-under-advisory write
    must be distinguishable from a write under an armed gate — layers carries
    the marker even though nothing ACTED (that is the point being recorded)."""
    monkeypatch.setenv("ENGRAM_L1_DOMAIN_ADVISORY", "1")
    monkeypatch.setenv("VERIMEM_AUDIT_LOG", "1")
    from verimem.client import Memory
    m = Memory(path=tmp_path / "m.db")
    r = m.add(KEYWORD_FACT, topic="legal/deal", source=KEYWORD_FACT,
              verified_by=["source-doc:dd:1"])
    assert r.get("status") != "quarantined"
    rows = m.audit_log(limit=10)
    row = next((x for x in rows if x.get("fact_id") == r.get("id")), None)
    assert row is not None, "audit trail on -> the write must have a row"
    assert MARKER in (row.get("layers") or []), \
        f"the audit row must record the stand-down, got layers={row.get('layers')}"
