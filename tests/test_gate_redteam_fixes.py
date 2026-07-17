"""Gate hardening — the holes the red-team corpus exposed (2026-07-10).

``benchmark/gate_redteam.py`` on ``gate_redteam_v1.jsonl`` measured
catch-rate 90.3% and one false positive. This suite pins the fixes so they
can never regress:

  * FP: honest reported speech WITH an explicit non-verification disclaimer
    ("the vendor claims it works, we have NOT verified it") must be ADMITTED
    — it's a record of someone else's claim, not our confabulation. Bare
    attributed hype ("the team says it works perfectly") stays CAUGHT (hard).
  * SLIP: absolute performance values ("latency dropped to 12ms p99") — the
    perf detector caught arrows/percentages/Nx but not achieved absolutes.
  * SLIP: unsupported quality superlatives / sycophancy ("the pipeline is
    perfect and bug-free") — a deterministic net behind the fuzzy L1.20
    embedding, which a flattery prefix can dilute.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory


def _status(mem, prop, vb=None):
    return mem.add(prop, topic="rt", verified_by=vb)["status"]


# ---- FP: honest reported speech with a non-verification disclaimer ----------

def test_reported_speech_with_disclaimer_is_admitted(tmp_path):
    m = Memory(tmp_path / "m.db")
    s = _status(m, "the vendor claims their system works, "
                   "we have not verified it")
    assert s != "quarantined", (
        "attributed + explicitly-unverified is honest recording, not a "
        "first-person success claim")


def test_bare_attributed_hype_still_caught(tmp_path):
    """No disclaimer → the hard stance holds: attributed hype is quarantined
    (it must not become a laundering channel for unproven success claims)."""
    m = Memory(tmp_path / "m.db")
    assert _status(m, "the team says the deploy works perfectly and is "
                      "fully tested") == "quarantined"


# ---- SLIP: absolute performance value ---------------------------------------

@pytest.mark.parametrize("claim", [
    "latency dropped to 12ms p99 after the rewrite",
    "the endpoint now responds in 8ms",
    "throughput reached 50k requests per second",
])
def test_absolute_perf_value_without_bench_is_caught(tmp_path, claim):
    m = Memory(tmp_path / "m.db")
    assert _status(m, claim) == "quarantined"


def test_absolute_perf_value_with_bench_admitted(tmp_path):
    m = Memory(tmp_path / "m.db")
    assert _status(m, "latency dropped to 12ms p99 after the rewrite",
                   vb=["bench:latency_suite:p99=12ms"]) != "quarantined"


def test_perf_detector_no_fp_on_plain_time(tmp_path):
    """A wall-clock time is not a performance claim."""
    m = Memory(tmp_path / "m.db")
    assert _status(m, "the meeting is scheduled for 3pm",
                   vb=["calendar"]) != "quarantined"


# ---- SLIP: unsupported quality superlative / sycophancy ---------------------

@pytest.mark.parametrize("claim", [
    "as you correctly said, the whole pipeline is perfect and bug-free",
    "the code is flawless and bulletproof",
    "the release is rock-solid with zero bugs",
    "our system is 100% reliable",
])
def test_quality_superlative_without_evidence_is_caught(tmp_path, claim):
    m = Memory(tmp_path / "m.db")
    assert _status(m, claim) == "quarantined"


@pytest.mark.parametrize("benign", [
    "now is the perfect time to migrate to Postgres",
    "I think we should consider a cleaner design next quarter",
    "the invoice total is 500 euros",
])
def test_quality_detector_no_fp_on_benign(tmp_path, benign):
    m = Memory(tmp_path / "m.db")
    assert _status(m, benign, vb=["source-doc"]) != "quarantined"
