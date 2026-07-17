"""Anti-sycophancy on the REAL write path (2026-07-04, loop iter 1).

The evidence-over-authority gate (``classify_conflict`` /
``require_evidence_to_supersede``) drops the measured cave-rate 0.5 -> 0.0, but
until now it lived ONLY in the standalone bench: the wired write-path
reconciliation (``reconcile_fact_on_write`` <- ``reconcile_against_corpus`` <-
``SemanticMemory.reconcile_new_fact`` <- ``store()``) never threaded it. So a
deployment that turns on auto-supersede (which the HaluMem *Updating* slice
needs, to actually apply knowledge updates) had NO protection: a bare, confident,
merely-newer assertion would sycophantically supersede stored, evidenced truth.

These tests make the anti-sycophancy gate REACHABLE and CORRECT from the write
path, with the safe composition: when auto-supersede is enabled, evidence is
REQUIRED by default (a bare claim can only contest, never supersede) unless a
deployment explicitly opts out. Default (no env) is byte-identical: contest-only.
"""
from __future__ import annotations

from verimem.contradiction import ContradictionStore
from verimem.semantic import Fact, SemanticMemory
from verimem.truth_reconciliation import reconcile_fact_on_write

_NOW = 1_000_000_000.0
_DAY = 86400.0


def _pair(old_conf=0.7, new_status="model_claim", new_conf=0.99, new_verified=None):
    old = Fact(id="old", proposition="the capital of Zorvia is Helmsford", topic="geo",
               status="model_claim", confidence=old_conf, created_at=_NOW - 5 * _DAY)
    new = Fact(id="new", proposition="the capital of Zorvia is Brantol", topic="geo",
               status=new_status, confidence=new_conf, created_at=_NOW,
               verified_by=new_verified)
    return old, new


# --- behavioural: the gate at the wired reconcile function ---

def test_bare_assertion_does_not_supersede_with_evidence_gate(tmp_path) -> None:
    """A confident, newer, but EVIDENCE-FREE contradiction must NOT supersede a
    stored fact when the evidence gate is on — it can only contest. This is the
    anti-sycophancy property, now reachable from the write-path function."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    old, new = _pair()  # new: model_claim conf 0.99, no verified_by -> bare
    sm.store(old)
    sm.store(new)
    cs = ContradictionStore(sm.db_path)
    res = reconcile_fact_on_write(sm, new, [old], now=_NOW, contradiction_store=cs,
                                  require_evidence=True)
    assert "old" not in res["superseded"], "bare assertion must not supersede"
    assert "old" in res["contested"], "the conflict must be recorded (contested)"
    assert sm.get("old").superseded_by is None, "stored truth held"


def test_evidenced_correction_still_supersedes_with_gate(tmp_path) -> None:
    """The gate must not over-rigidify: a LEGITIMATE evidenced correction still
    applies (supersedes) even with the evidence gate on."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    old, new = _pair(new_status="verified", new_conf=0.8,
                     new_verified=("source:doc#4",))
    sm.store(old)
    sm.store(new)
    cs = ContradictionStore(sm.db_path)
    res = reconcile_fact_on_write(sm, new, [old], now=_NOW, contradiction_store=cs,
                                  require_evidence=True)
    assert "old" in res["superseded"], "evidenced correction must still apply"
    assert sm.get("old").superseded_by == "new"


def test_gate_off_default_bare_still_supersedes(tmp_path) -> None:
    """Regression: with the gate OFF (default), the prior recency+authority
    behaviour is unchanged — a newer, at-least-as-authoritative bare claim
    supersedes. (This is the sycophancy the gate exists to stop.)"""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    old, new = _pair()
    sm.store(old)
    sm.store(new)
    cs = ContradictionStore(sm.db_path)
    res = reconcile_fact_on_write(sm, new, [old], now=_NOW, contradiction_store=cs)
    assert "old" in res["superseded"], "default (no gate) unchanged"


# --- store() env wiring (deterministic spy; no entity-KG needed) ---

def _spy_reconcile(monkeypatch, sm):
    captured: dict = {}

    def spy(f, **k):
        captured.update(k)
        return {"superseded": [], "contested": []}

    monkeypatch.setattr(sm, "reconcile_new_fact", spy)
    return captured


def test_store_forwards_evidence_gate_on_by_default_when_supersede_on(
        tmp_path, monkeypatch) -> None:
    """Enabling auto-supersede turns the anti-sycophancy gate ON by default in its
    TIERED form (iter 3): protect evidenced facts, allow bare->bare updates. store()
    forwards protect_evidenced=True, require_evidence=False — no extra env."""
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "1")
    monkeypatch.setenv("ENGRAM_RECONCILE_AUTO_SUPERSEDE", "1")
    monkeypatch.delenv("ENGRAM_RECONCILE_REQUIRE_EVIDENCE", raising=False)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    cap = _spy_reconcile(monkeypatch, sm)
    sm.store(Fact(id="x", proposition="Acme Corp uses Postgres", topic="t"))
    assert cap.get("auto_supersede") is True
    assert cap.get("require_evidence") is False
    assert cap.get("protect_evidenced") is True


def test_store_evidence_gate_explicit_opt_out(tmp_path, monkeypatch) -> None:
    """A deployment can explicitly opt out of ALL protection (dangerous, allowed):
    ENGRAM_RECONCILE_REQUIRE_EVIDENCE=0 -> neither strict nor tiered."""
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "1")
    monkeypatch.setenv("ENGRAM_RECONCILE_AUTO_SUPERSEDE", "1")
    monkeypatch.setenv("ENGRAM_RECONCILE_REQUIRE_EVIDENCE", "0")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    cap = _spy_reconcile(monkeypatch, sm)
    sm.store(Fact(id="x", proposition="Acme Corp uses Postgres", topic="t"))
    assert cap.get("auto_supersede") is True
    assert cap.get("require_evidence") is False
    assert cap.get("protect_evidenced") is False


def test_store_strict_gate_when_require_evidence_env_1(tmp_path, monkeypatch) -> None:
    """ENGRAM_RECONCILE_REQUIRE_EVIDENCE=1 forces STRICT (require_evidence=True,
    tiered off): max safety, the deployment's explicit call."""
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "1")
    monkeypatch.setenv("ENGRAM_RECONCILE_AUTO_SUPERSEDE", "1")
    monkeypatch.setenv("ENGRAM_RECONCILE_REQUIRE_EVIDENCE", "1")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    cap = _spy_reconcile(monkeypatch, sm)
    sm.store(Fact(id="x", proposition="Acme Corp uses Postgres", topic="t"))
    assert cap.get("require_evidence") is True
    assert cap.get("protect_evidenced") is False


def test_store_default_reconcile_stays_contest_only(tmp_path, monkeypatch) -> None:
    """Byte-identical default: reconcile-on-write without auto-supersede forwards
    auto_supersede=False and require_evidence=False (contest-only, unchanged)."""
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "1")
    monkeypatch.delenv("ENGRAM_RECONCILE_AUTO_SUPERSEDE", raising=False)
    monkeypatch.delenv("ENGRAM_RECONCILE_REQUIRE_EVIDENCE", raising=False)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    cap = _spy_reconcile(monkeypatch, sm)
    sm.store(Fact(id="x", proposition="Acme Corp uses Postgres", topic="t"))
    assert cap.get("auto_supersede") is False
    assert cap.get("require_evidence") is False
    assert cap.get("protect_evidenced") is False
