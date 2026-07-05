"""TrustReport (F3, iter 47 — mandato "affidabile per un GIUDICE").

Every answer must be able to carry its evidence dossier — the chain of custody
of the facts behind it: WHAT was used (proposition), WHERE it came from
(provenance, writer_role), HOW trusted it is (status, verified_by, grounding
score), WHEN it was true (asserted_at) vs learned (created_at), what it
REPLACED (supersession history), what it CONFLICTS with (declared disputes),
and — when there is nothing — an explicit ABSTAINED verdict instead of a guess.

This is the anti-confab / anti-hallucination / anti-sycophancy gate made ATOMIC:
one object, JSON-serializable, produced for any query. Hermetic, no LLM.
"""
from __future__ import annotations

import json
import time

from engram.semantic import Fact, SemanticMemory
from engram.trust_report import build_trust_report

_DAY = 86400.0


def _seed(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    now = time.time()
    old = Fact(id="t-old", topic="client/rossi",
               proposition="Client Rossi's budget is 300k",
               asserted_at=now - 200 * _DAY, confidence=0.6)
    cur = Fact(id="t-cur", topic="client/rossi",
               proposition="Client Rossi's budget is 500k",
               asserted_at=now - 10 * _DAY, confidence=0.8,
               source_episodes=["conversation:mar-2026"],
               writer_role="conversational_ingest")
    rival = Fact(id="t-riv", topic="client/rossi",
                 proposition="Client Rossi's budget is 450k",
                 asserted_at=now - 5 * _DAY)
    for f in (old, cur, rival):
        sm.store(f, embed="sync")
    sm.supersede("t-old", "t-cur", reason="update")
    from engram.contradiction import Contradiction, ContradictionStore
    ContradictionStore(sm.db_path).add(Contradiction(
        fact_a_id="t-cur", fact_b_id="t-riv",
        kind="update-conflict", similarity=0.9))
    return sm


def test_report_carries_full_chain_of_custody(tmp_path) -> None:
    sm = _seed(tmp_path)
    rep = build_trust_report(sm, "Rossi budget", k=5)
    assert rep["abstained"] is False
    used = {e["id"]: e for e in rep["facts"]}
    assert "t-cur" in used, "the live fact is in the dossier"
    cur = used["t-cur"]
    # custody chain: provenance + writer + trust status + both clocks
    assert cur["provenance"] == ["conversation:mar-2026"]
    assert cur["writer_role"] == "conversational_ingest"
    assert cur["status"] in ("model_claim", "provisional", "verified")
    assert cur["asserted_at"] is not None and cur["created_at"] is not None
    # what it REPLACED (history) and what it CONFLICTS with (declared)
    assert any("300k" in h["proposition"] for h in cur["history"]), \
        "the superseded predecessor is declared in the dossier"
    assert any("450k" in d["proposition"] for d in cur["disputes"]), \
        "the unresolved rival is DECLARED, not hidden"


def test_report_abstains_explicitly_when_no_evidence(tmp_path) -> None:
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    rep = build_trust_report(sm, "cryptozoology of Mars", k=5)
    assert rep["abstained"] is True and rep["facts"] == []
    assert rep["reason"], "an abstention carries its why"


def test_report_is_json_serializable(tmp_path) -> None:
    sm = _seed(tmp_path)
    rep = build_trust_report(sm, "Rossi budget", k=5)
    js = json.dumps(rep)          # must not raise
    assert "500k" in js
