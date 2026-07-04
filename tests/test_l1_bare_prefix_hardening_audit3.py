"""audit#3 (2026-06-09, 8-agent code audit) — close the residual bare-prefix
evidence holes in the L1.x anti-confab detectors that the 2026-06-03 hardening
skipped: security (L1.12), production-ready `coverage:` branch (L1.11), and
approval/monitored/automated (L1.16/17/18).

A bare/negated evidence ref ('audit:planned', 'coverage:tbd', 'approval:pending',
'alert:planned', 'cron:someday') must STILL fire the warning; genuine outcome /
artifact refs must STILL be accepted (no over-tightening).
"""
from __future__ import annotations

import pytest

from engram.l1_approval_detector import detect_unsupported_approval_claim
from engram.l1_automated_detector import detect_unsupported_automated_claim
from engram.l1_monitored_detector import detect_unsupported_monitored_claim
from engram.l1_production_ready_detector import detect_unsupported_prod_ready_claim
from engram.l1_security_detector import detect_unsupported_security_claim

# --- NEGATIVE: a not-done / bare ref must NOT suppress the warning ---

@pytest.mark.parametrize("vb", [
    ["audit:planned_next_quarter"], ["pentest:scheduled"],
    ["bandit:todo"], ["semgrep:later"],
])
def test_security_bare_prefix_still_warns(vb):
    assert detect_unsupported_security_claim(
        proposition="System is secure", verified_by=vb) is not None


@pytest.mark.parametrize("vb", [["coverage:planned"], ["coverage:tbd"], ["coverage:later"]])
def test_prod_ready_coverage_no_number_still_warns(vb):
    assert detect_unsupported_prod_ready_claim(
        proposition="System is production-ready", verified_by=vb) is not None


@pytest.mark.parametrize("vb", [
    ["approval:pending"], ["review:requested"], ["pr:open"], ["ticket:jira_42"],
])
def test_approval_no_outcome_still_warns(vb):
    assert detect_unsupported_approval_claim(
        proposition="Change approved by the board", verified_by=vb) is not None


@pytest.mark.parametrize("vb", [["alert:planned"], ["metric:tbd"]])
def test_monitored_negated_still_warns(vb):
    assert detect_unsupported_monitored_claim(
        proposition="Endpoint is monitored", verified_by=vb) is not None


@pytest.mark.parametrize("vb", [["cron:someday"], ["schedule:planned"], ["workflow:manual"]])
def test_automated_negated_still_warns(vb):
    assert detect_unsupported_automated_claim(
        proposition="Backup runs automatically", verified_by=vb) is not None


# --- POSITIVE guards: genuine evidence must STILL be accepted (no over-tighten) ---

def test_security_real_outcome_accepted():
    assert detect_unsupported_security_claim(
        proposition="System is secure",
        verified_by=["pentest:report_2026_PASS"]) is None
    # artifact ref stays bare-accepted
    assert detect_unsupported_security_claim(
        proposition="System is hardened",
        verified_by=["threat_model:tm_17"]) is None


def test_prod_ready_coverage_with_number_accepted():
    assert detect_unsupported_prod_ready_claim(
        proposition="System is production-ready",
        verified_by=["coverage:92_percent"]) is None


def test_approval_real_outcome_accepted():
    for vb in (["pr:1234_approved"], ["approval:doc_signed"], ["email:manager_approval"]):
        assert detect_unsupported_approval_claim(
            proposition="Change approved", verified_by=vb) is None


def test_monitored_artifact_pointer_accepted():
    for vb in (["dashboard:/grafana/board"], ["prometheus:rule_45_active"]):
        assert detect_unsupported_monitored_claim(
            proposition="Service is monitored", verified_by=vb) is None


def test_automated_real_schedule_accepted():
    for vb in (["cron:0_2_*_*_*"], ["workflow:weekly_backup"]):
        assert detect_unsupported_automated_claim(
            proposition="Job is automated", verified_by=vb) is None
