"""Fix dei finding dell'adversarial critic (claude-opus-4-8) del 2026-07-16.

Il critic ha dato HOLD sui verdetti "SOLIDO" del loop di audit, trovando difetti
REALI (verificati empiricamente prima del fix):
  HIGH-1  gateway: tenant_id con dot finale (`acme.`) collide con `acme` su
          Windows (che strippa i trailing dot dai nomi directory) → stesso file
          DB → rottura isolamento tenant.
  MED-2   l1_works: il ramo "works as a/an <x>" (fix FP-biografia) sopprimeva
          claim di funzionamento reali ("works as a proxy/drop-in replacement").
  MED-3   l1_security: la lista acquisition (funding/loan/role/…) sopprimeva
          claim di hardening reali ("secured the funding endpoint").
  LOW-5   admission: uno status ignoto/malformato ("user_belief " con spazio)
          riceveva la ragione "carries its own trust verdict" (falsa fiducia).
Questi test pinnano il fix E la non-regressione dei FP originali già risolti.
"""
from __future__ import annotations

import pytest


# ---- HIGH-1: gateway trailing-dot tenant collision --------------------------
def test_gateway_tenant_trailing_dot_rejected(tmp_path):
    from engram.gateway import GatewayKeys

    keys = GatewayKeys(tmp_path / "k.db")
    for bad in ["acme.", "acme..", "acme..."]:
        with pytest.raises(ValueError):
            keys.create(tenant_id=bad)
    # an INTERIOR dot is not stripped by Windows -> stays valid
    assert keys.create(tenant_id="a.b").startswith("vm_")


# ---- MED-2: l1_works functional "as a" must fire again ----------------------
@pytest.mark.parametrize("prop", [
    "the library works as a drop-in replacement",
    "the service works as a proxy",
    "the module works as a cache layer",
])
def test_l1_works_functional_as_a_still_fires(prop):
    from engram.l1_works_detector import detect_unsupported_works_claim as dw
    assert dw(proposition=prop, verified_by=None) is not None, \
        f"functional works-claim wrongly suppressed: {prop!r}"


def test_l1_works_industry_biography_fp_stays_fixed():
    from engram.l1_works_detector import detect_unsupported_works_claim as dw
    # my MEASURED biography FP (works in the X industry) must stay suppressed
    assert dw(proposition="Martin Mark works in the healthcare industry",
              verified_by=None) is None


# ---- MED-3: l1_security infra hardening must fire again ----------------------
@pytest.mark.parametrize("prop", [
    "secured the funding endpoint against attackers",
    "secured the loan API",
    "secured the role service",
])
def test_l1_security_infra_hardening_still_fires(prop):
    from engram.l1_security_detector import detect_unsupported_security_claim as ds
    assert ds(proposition=prop, verified_by=None) is not None, \
        f"security hardening claim wrongly suppressed: {prop!r}"


def test_l1_security_acquisition_fp_stays_fixed():
    from engram.l1_security_detector import detect_unsupported_security_claim as ds
    # my MEASURED FP (secured interviews and job offers) must stay suppressed
    assert ds(proposition="Martin secured interviews and job offers",
              verified_by=None) is None


# ---- LOW-5: admission must not grant false trust to unknown status ----------
def test_admission_unknown_status_no_false_trust_reason():
    from engram.admission_gate import classify_admission
    # malformed (trailing space) = not a known status
    v = classify_admission(topic="t", proposition="x is fastest",
                           status="user_belief ")
    assert "carries its own trust verdict" not in v.reason, \
        "an unknown/malformed status must not be told it carries a trust verdict"
    # a KNOWN non-model_claim status keeps the honest reason
    v2 = classify_admission(topic="t", proposition="x is fastest",
                            status="user_belief")
    assert "carries its own trust verdict" in v2.reason
