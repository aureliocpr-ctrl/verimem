"""The grounding write-gate (the moat) is ON by default — mandate 2026-07-17.

For months the moat (source⊢fact entailment, judge AUROC 0.97) shipped OFF by
default: a reader who ran the write path saw no gate and concluded "no moat".
This pins the flip:

* preset ``balanced`` now has ``ground=True`` (the moat runs);
* a ``Memory(llm=...)`` uses that llm as the grounding judge by default (no
  separate ``grounding_llm=`` needed), so building Memory with an llm turns the
  moat ON at the best quality (the LLM judge, 0.98);
* a confabulation whose SOURCE does not entail it is quarantined, a faithful
  fact is admitted;
* SAFE fail-open: with NO judge available (no llm, no local CE) the gate can't
  score, so the write is admitted exactly as before — the flip never breaks a
  user who has no judge configured.
"""
from __future__ import annotations

from verimem.client import _GATE_PRESETS, Memory


class _StubJudge:
    """Grounding judge: replies 'score: N' where N is high iff the fact's key
    token appears in the source (a faithful fact), low otherwise (confab)."""

    def complete(self, system, messages, *, model=None, max_tokens=64):
        text = " ".join(m["content"] for m in messages).lower()
        # the source is in the prompt; a faithful fact shares its distinctive word
        score = 95 if "postgres" in text and "candidate" in text and \
            text.count("postgres") >= 2 else 8

        class R:
            pass
        R.text = f"score: {score}"
        return R()


def test_balanced_preset_has_moat_on():
    assert _GATE_PRESETS["balanced"]["ground"] is True


def test_confab_quarantined_with_llm_judge(tmp_path):
    # the llm passed to Memory is used as the grounding judge by default
    m = Memory(tmp_path / "m.db", llm=_StubJudge())
    src = "We migrated the analytics store to Postgres last quarter."
    faithful = m.add("The analytics store runs on Postgres.", source=src)
    assert faithful["status"] != "quarantined", faithful
    confab = m.add("The analytics store runs on MongoDB.", source=src)
    assert confab["status"] == "quarantined", confab
    assert confab.get("grounding_score") is not None


def test_failopen_with_NO_judge_at_all_admits_as_before(tmp_path, monkeypatch):
    # The docstring's SAFE fail-open case: NO judge AT ALL — no llm AND no local
    # CE on disk. Force the CE absent (else it is now the default judge, 0.6.0).
    # Then the gate can't score → admit exactly as before, never breaking a user
    # who has neither judge.
    monkeypatch.setattr("verimem.local_grounding.local_ce_available", lambda: False)
    m = Memory(tmp_path / "m2.db")
    r = m.add("The analytics store runs on MongoDB.",
              source="We migrated to Postgres last quarter.")
    assert r["stored"] is True
    assert r["status"] != "quarantined"   # fail-open: no llm AND no local CE


def test_moat_ON_with_local_CE_and_no_llm(tmp_path):
    # 0.6.0 BEHAVIOR CHANGE (was fail-open in 0.5.x): with NO llm the local CE is
    # the default judge, so a confab is quarantined out-of-the-box. Skips only if
    # the CE model isn't installed in this environment.
    import pytest

    from verimem.local_grounding import local_ce_available
    if not local_ce_available():
        pytest.skip("local CE model not installed in this environment")
    m = Memory(tmp_path / "m3.db")   # no llm — the CE judges
    r = m.add("The analytics store runs on MongoDB.",
              source="We migrated the analytics store to Postgres last quarter.")
    assert r["status"] == "quarantined", r


def test_explicit_ground_false_still_opts_out(tmp_path):
    m = Memory(tmp_path / "m3.db", llm=_StubJudge())
    r = m.add("The analytics store runs on MongoDB.",
              source="We migrated to Postgres last quarter.", ground=False)
    assert r["status"] != "quarantined"   # per-call override still wins
