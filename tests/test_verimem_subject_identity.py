"""Two modules read the same store and disagreed on what "the same subject" is.

`active_probe` grouped rivals by ``_strip_article(subject).lower()``; the guardian
grouped them by the RAW ``_copula_parse(...)[0]``. On one store holding

    "Rex is a labrador."      (source alice)
    "The Rex is a poodle."    (source bob)

the probe answered ``refuted_proposed`` — a conflict real enough to apply an
ABSORBING label that kills a fact for good — while `correct_read` answered
ACCEPT, serving "labrador" as unchallenged. Measured 2026-07-28, banco 4.

Neither verdict is defensible while the other exists: the same evidence cannot
be both a fatal contradiction and no contradiction at all. So the rule pinned
here is not "the guardian must abstain on this input" — it is that subject
identity has ONE definition (``composer.subject_key``) and every reader asks it,
so the two can no longer drift apart.

The tie to the read-path is direct: an unseen conflict is a silent answer, and
the guardian's whole contract is "never pick silently — the conflict is shown".
"""
from __future__ import annotations

import pytest

from verimem.active_probe import probe_fact
from verimem.epistemic import make_proven
from verimem.guardian import correct_read


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "0")
    from verimem.client import Memory
    return Memory(tmp_path / "s.db")


def test_article_on_the_subject_does_not_hide_the_conflict(mem):
    """"The Rex" and "Rex" are one subject — the guardian must see the clash."""
    mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    mem.add("The Rex is a poodle.", topic="pets", verified_by=["source-doc:bob:t1"])
    out = correct_read(mem, "What breed is Rex?")
    assert out["verdict"] == "ABSTAIN", out
    assert out["answer"] is None, "a hidden conflict is a silent answer"
    assert len(out["evidence"]) == 2, "both sides are shown"


def test_guardian_and_probe_agree_on_what_a_conflict_is(tmp_path, monkeypatch):
    """The invariant: one definition of subject identity, not two.

    This is the test that pins the CLASS. If a future reader grows its own
    notion of 'same subject', the two verdicts diverge again and this fails.

    Each reader gets its OWN store of identical content. Sharing one would let
    the probe apply its ABSORBING ``refuted`` first and hand the guardian a
    store the probe itself rewrote — the guardian would then abstain on
    ``all_refuted`` and the test would pass while measuring nothing.
    """
    for k, v in {"ENGRAM_SOURCE_TRUST": "0", "ENGRAM_RECONCILE_ON_WRITE": "0",
                 "ENGRAM_RECALL_RERANK": "0", "ENGRAM_SEMANTIC_CONFLICT": "0"}.items():
        monkeypatch.setenv(k, v)
    from verimem.client import Memory

    def _seed(name: str):
        m = Memory(tmp_path / name)
        first = m.add("Rex is a labrador.", topic="pets",
                      verified_by=["source-doc:alice:t1"])
        m.add("The Rex is a poodle.", topic="pets",
              verified_by=["source-doc:bob:t1"])
        return m, first["id"]

    probe_mem, target = _seed("probe.db")
    guard_mem, _ = _seed("guard.db")
    probe = probe_fact(probe_mem, target)
    guard = correct_read(guard_mem, "What breed is Rex?")
    probe_sees_conflict = probe["outcome"] == "refuted_proposed"
    guard_sees_conflict = guard["verdict"] in ("ABSTAIN", "CORRECT")
    assert probe_sees_conflict == guard_sees_conflict, (
        f"probe={probe['outcome']} guardian={guard['verdict']} — the same "
        f"evidence cannot be a fatal contradiction for one reader and no "
        f"contradiction at all for the other")


def test_the_winner_may_carry_the_article(mem):
    """Normalising the subject must not disarm the correction itself."""
    mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    b = mem.add("The Rex is a poodle.", topic="pets",
                verified_by=["source-doc:vet:t2"])
    assert mem.semantic.set_epistemic(b["id"], make_proven("qa:vet_registry"))
    out = correct_read(mem, "What breed is Rex?")
    assert out["verdict"] == "CORRECT", out
    assert "poodle" in out["answer"]


def test_distinct_subjects_are_not_merged(mem):
    """The guard must not over-reach: 'Rexy' is not 'Rex'."""
    mem.add("Rex is a labrador.", topic="pets", verified_by=["source-doc:alice:t1"])
    mem.add("Rexy is a poodle.", topic="pets", verified_by=["source-doc:bob:t1"])
    out = correct_read(mem, "What breed is Rex?")
    assert out["verdict"] == "ACCEPT", out
    assert "labrador" in out["answer"]


def test_the_hidden_conflict_reaches_the_production_endpoint(tmp_path, monkeypatch):
    """The same case over ``GET /v1/correct`` — the guardian's only production
    caller (gateway.py). A unit test cannot see a layer-interaction defect, so
    the bench is repeated on the wire that actually serves users.
    """
    monkeypatch.setenv("ENGRAM_SEMANTIC_CONFLICT", "0")
    from fastapi.testclient import TestClient

    from verimem.client import Memory
    from verimem.gateway import GatewayKeys, create_app

    personal = Memory(path=tmp_path / "personal.db")
    app = create_app(data_dir=tmp_path, keys=GatewayKeys(tmp_path / "k.db"),
                     admin_key="adm", local_tenant="op", local_memory=personal)
    client = TestClient(app, base_url="http://localhost")
    personal.add("Rex is a labrador.", topic="pets",
                 verified_by=["source-doc:alice:t1"])
    personal.add("The Rex is a poodle.", topic="pets",
                 verified_by=["source-doc:bob:t1"])
    body = client.get("/v1/correct", params={"q": "What breed is Rex?"}).json()
    assert body["verdict"] == "ABSTAIN", body
    assert body["answer"] is None
    assert len(body["evidence"]) == 2, "the endpoint SHOWS both sides"
