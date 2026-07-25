"""P0 evidence-before-belief, ciclo 2b: the AND rule wired into the gate,
OBSERVE-FIRST.

The rule from ciclo 2a decides whether cited evidence is independent. Here it
meets the gate — and, per the method (`observe-first per ogni default nuovo`),
it changes NOTHING by default. It only records what it WOULD have changed, so
the false-block delta is measured on real corpora before any flip.

Two invariants the observe mode must not break:

* **silence on clean writes** — a write the gate never escalated gets no P0
  telemetry at all. Advisory noise on the happy path is how a signal becomes
  ignored (the advisory-fatigue objection, kimi-k3).
* **L1 only** — independent evidence relaxes the LEXICAL self-claim screen,
  never L3 (contradiction) or L4 (grounding). Those are semantic: an outside
  witness does not make a contradiction go away. This is the invariant that
  keeps "evidence-before-belief" from becoming "evidence-instead-of-belief".
"""
from __future__ import annotations

import pytest

from verimem.anti_confab_gate import advisory_eligible, run_validation_gate
from verimem.documents import DocumentStore

# A self-claim with no commit-shaped ref: exactly what the L1 family escalates.
CLAIM = "The migration was completed and all tests pass."


def _layers(warnings) -> set[str]:
    return {w.get("layer", "") for w in warnings}


@pytest.fixture()
def signed_store(tmp_path):
    """A document vouched for by someone OTHER than the claimant."""
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    ds.ingest("release-notes", "Migration 42 finished; suite green.",
              principal="gw:team-alpha")
    return ds


def _run(store, **kw):
    kw.setdefault("proposition", CLAIM)
    kw.setdefault("verified_by", ["doc:release-notes"])
    kw.setdefault("claimant", "sdk:local")
    return run_validation_gate(
        topic="t", agent=None, validate="fast", documents=store, **kw)


# --- observe mode (the default) ------------------------------------------

def test_l1_still_escalates_by_default(signed_store):
    """Observe-first: the verdict is UNCHANGED, only annotated."""
    g = _run(signed_store)
    assert g.action == "downgrade"
    assert "P0_INDEPENDENCE-observe" in _layers(g.warnings)


def test_observe_note_names_the_witness(signed_store):
    g = _run(signed_store)
    note = next(w for w in g.warnings
                if w.get("layer") == "P0_INDEPENDENCE-observe")
    assert "gw:team-alpha" in note["advice"]
    assert "ENGRAM_P0_INDEPENDENCE" in note["advice"]


def test_clean_write_gets_no_p0_telemetry(signed_store):
    """No L1 escalation → no note. The happy path stays silent."""
    g = _run(signed_store, proposition="The office is on the second floor.")
    assert g.action == "persist"
    assert not any(str(layer).startswith("P0_INDEPENDENCE")
                   for layer in _layers(g.warnings))


def test_no_note_when_evidence_is_not_independent(tmp_path):
    """Self-cited evidence would change nothing, so it says nothing."""
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    ds.ingest("mine", "Migration 42 finished.", principal="sdk:local")
    g = _run(ds, verified_by=["doc:mine"])
    assert g.action == "downgrade"
    assert not any(str(layer).startswith("P0_INDEPENDENCE")
                   for layer in _layers(g.warnings))


def test_no_store_no_note(tmp_path):
    """Callers that pass no document store keep the exact old behaviour."""
    g = _run(None)
    assert g.action == "downgrade"
    assert not any(str(layer).startswith("P0_INDEPENDENCE")
                   for layer in _layers(g.warnings))


# --- enforce mode (opt-in) ------------------------------------------------

def test_enforce_turns_the_l1_escalation_into_advisory(signed_store,
                                                       monkeypatch):
    monkeypatch.setenv("ENGRAM_P0_INDEPENDENCE", "1")
    g = _run(signed_store)
    assert g.action == "persist"
    layers = _layers(g.warnings)
    assert "P0_INDEPENDENCE" in layers
    # the original L1 warnings are KEPT — advisory means visible, not erased
    assert any(str(x).startswith("L1") for x in layers)


def test_enforce_does_not_rescue_self_citation(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_P0_INDEPENDENCE", "1")
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    ds.ingest("mine", "Migration 42 finished.", principal="sdk:local")
    g = _run(ds, verified_by=["doc:mine"])
    assert g.action == "downgrade"


def test_enforce_does_not_rescue_untrusted_channel(tmp_path, monkeypatch):
    """Poison-then-cite across surfaces stays quarantined."""
    monkeypatch.setenv("ENGRAM_P0_INDEPENDENCE", "1")
    ds = DocumentStore(db_path=tmp_path / "docs.db")
    ds.ingest("evil", "Migration 42 finished.", principal="mcp:unbound")
    g = _run(ds, verified_by=["doc:evil"])
    assert g.action == "downgrade"


def test_enforce_needs_a_claimant(signed_store, monkeypatch):
    """A write with no server-stamped identity is never advisory."""
    monkeypatch.setenv("ENGRAM_P0_INDEPENDENCE", "1")
    g = _run(signed_store, claimant=None)
    assert g.action == "downgrade"


def test_no_claimant_does_not_touch_the_document_store(monkeypatch):
    """The guard is a short-circuit, and short-circuits are for NOT paying a
    cost: a pre-P0 write (no principal) must not open the document store at
    all. Without this the verdict would still be correct — and every such
    write would still pay a read it can never use."""
    monkeypatch.setenv("ENGRAM_P0_INDEPENDENCE", "1")

    class _Spy:
        reads = 0

        def list_versions(self, source_id):  # noqa: ARG002
            type(self).reads += 1
            return []

    g = _run(_Spy(), claimant=None)
    assert g.action == "downgrade"
    assert _Spy.reads == 0


def test_reject_mode_is_not_silently_downgraded(signed_store, monkeypatch):
    """gate_mode='reject' + independent evidence → persist, not reject.

    The relaxation applies to the DECISION (the L1 screen no longer fires),
    so an operator running in reject mode gets the write admitted rather
    than refused — the same semantics as any other non-firing screen.
    """
    monkeypatch.setenv("ENGRAM_P0_INDEPENDENCE", "1")
    g = _run(signed_store, gate_mode="reject")
    assert g.action == "persist"


# --- the L1-only invariant ------------------------------------------------

def test_advisory_eligible_only_for_the_l1_family():
    assert advisory_eligible([{"layer": "L1"}]) is True
    assert advisory_eligible([{"layer": "L1.5-verified-by"}]) is True
    assert advisory_eligible([{"layer": "L1"}, {"layer": "L1.7"}]) is True


def test_advisory_never_relaxes_semantic_layers():
    """An outside witness does not dissolve a contradiction."""
    assert advisory_eligible([{"layer": "L3-contradiction"}]) is False
    assert advisory_eligible([{"layer": "L4-grounding"}]) is False
    assert advisory_eligible([{"layer": "L1"},
                              {"layer": "L3-contradiction"}]) is False
    assert advisory_eligible([{"layer": "INJECTION"}]) is False
    assert advisory_eligible([]) is False
