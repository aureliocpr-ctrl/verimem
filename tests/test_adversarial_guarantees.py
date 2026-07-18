"""The deterministic "must not pass" guarantee, adversarial + claim-vs-reality
(2026-07-18). A self-cited receipt must NEVER buy a higher trust status:
`status='verified'` requires a receipt that passes EMPIRICAL I/O verification
(a real file:line under repo_root, or a real commit), and `repo_root=None`
demotes everything (paranoid default). `verified_by` on the SDK is PROVENANCE,
not a status upgrade — this pins that the README no longer over-claims it.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.provenance_validator import validate_verified_refs
from verimem.semantic import Fact, SemanticMemory

REPO = Path(__file__).resolve().parents[1]
REAL_REF = "file:verimem/__init__.py:1"           # exists under the repo root
FORGED = [
    ["pytest:test_x"], ["exit 0"], ["bash:echo hi"], ["sha256:deadbeef"],
    ["url:banana"], ["file:/etc/passwd:1"], ["file:ghost_zzz.py:99999"],
    ["commit deadbeef1234"], [], ["trust-me-i-am-verified"],
]


# ---- the gate contract (pure, no model) --------------------------------------

@pytest.mark.parametrize("refs", FORGED)
def test_forged_receipts_never_validate(refs):
    assert validate_verified_refs(refs, repo_root=REPO) is False


def test_real_receipt_validates_only_with_repo_root():
    assert validate_verified_refs([REAL_REF], repo_root=REPO) is True
    # paranoid default: no repo_root => cannot verify => False
    assert validate_verified_refs([REAL_REF], repo_root=None) is False


# ---- the store() demotion gate (end-to-end, needs the model for embed) -------

def _sm(tmp_path, repo_root):
    return SemanticMemory(db_path=tmp_path / "s.db", repo_root=repo_root)


@pytest.mark.parametrize("refs", FORGED)
def test_store_demotes_forged_verified_to_model_claim(tmp_path, refs):
    sm = _sm(tmp_path, REPO)
    f = Fact(proposition=f"forged {refs}", status="verified", verified_by=refs)
    sm.store(f, embed="skip")
    assert f.status == "model_claim", f"forged {refs} kept 'verified'"


def test_store_keeps_verified_with_a_real_receipt(tmp_path):
    sm = _sm(tmp_path, REPO)
    f = Fact(proposition="real", status="verified", verified_by=[REAL_REF])
    sm.store(f, embed="skip")
    assert f.status == "verified", "a real file:line receipt must keep 'verified'"


def test_store_demotes_verified_when_no_repo_root(tmp_path):
    sm = _sm(tmp_path, None)   # multi-tenant gateway default
    f = Fact(proposition="real but no root", status="verified", verified_by=[REAL_REF])
    sm.store(f, embed="skip")
    assert f.status == "model_claim", "no repo_root must demote even a real receipt"


# ---- claim-vs-reality: SDK verified_by is provenance, not a 'verified' badge --

def test_sdk_verified_by_is_provenance_not_a_verified_status(tmp_path):
    from verimem.local_grounding import local_ce_available
    if not local_ce_available():
        pytest.skip("needs the embedding/CE stack")
    from verimem.client import Memory
    m = Memory(tmp_path / "m.db", repo_root=str(REPO))
    r = m.add("Deploy pipeline is green.", verified_by=[REAL_REF])
    assert r["status"] != "verified", (
        "SDK verified_by must not self-certify a 'verified' status")
