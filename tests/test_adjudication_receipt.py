"""Phase 0.1 + 0.2 — adjudication receipt on every write + judge-of-record.

Every write returns a VISIBLE verdict: how it was adjudicated (evidence_class),
WHICH judge decided (judge-of-record), the score, the threshold it was compared
to, and the margin from that threshold. A quarantine is an EXPLICIT verdict with
a reason, never a silent exclusion. A write with no source and no judge is
honestly labelled 'not verified' — no invented judge, score, or margin.
"""
import os

# in-process encoder (no shared daemon), hosted flags — set before import
os.environ["ENGRAM_ENCODE_SERVICE"] = "0"
os.environ.setdefault("VERIMEM_HOSTED", "1")

from verimem.client import Memory  # noqa: E402


class _FakeJudge:
    """A grounding judge returning a fixed 0-100 entailment score (the injected
    LLM judge path — deterministic, no network, no CE model needed)."""

    def __init__(self, score: int) -> None:
        self._score = score

    def complete(self, system, messages, **kw):  # noqa: ANN001
        return type("R", (), {"text": f"Score: {self._score}"})()


def test_admitted_write_carries_judge_of_record_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "claude")  # use injected judge
    m = Memory(str(tmp_path / "ok.db"), grounding_llm=_FakeJudge(96))
    r = m.add("Analytics runs on Postgres.",
              source="We migrated analytics to Postgres last quarter.")
    adj = r["adjudication"]
    assert adj["disposition"] == "admitted"
    assert adj["evidence_class"] == "llm_judge"
    assert adj["judge"]["backend"] == "claude"          # judge-of-record
    assert adj["score"] == 96.0
    assert adj["threshold"] is not None
    assert adj["margin"] == round(96.0 - adj["threshold"], 4)
    assert adj["margin"] > 0


def test_quarantine_is_a_visible_verdict_with_reason(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "claude")
    m = Memory(str(tmp_path / "no.db"), grounding_llm=_FakeJudge(3))
    r = m.add("Analytics runs on MongoDB.",
              source="We migrated analytics to Postgres last quarter.")
    adj = r["adjudication"]
    assert adj["disposition"] == "quarantined"
    assert adj["evidence_class"] == "llm_judge"
    assert adj["score"] == 3.0
    assert adj["threshold"] is not None
    assert adj["margin"] < 0
    assert adj["reason"]        # non-empty: WHY it was blocked (not silent)


def test_unjudged_write_is_not_labelled_verified(tmp_path):
    # no source, no verified_by, no judge → honest 'not verified', no invented data
    m = Memory(str(tmp_path / "bare.db"))
    r = m.add("The sky is a calm shade of blue today.")
    adj = r["adjudication"]
    assert adj["disposition"] == "admitted"
    assert adj["judge"] is None
    assert adj["evidence_class"] in ("lexical_only", "ungated")
    assert adj["score"] is None
    assert adj["margin"] is None
