"""WF3 fix: L1 dev-claim detectors must NOT quarantine ordinary personal facts."""
from verimem.anti_confab_gate import run_validation_gate as gate


def _persists(prop, **kw):
    return gate(proposition=prop, verified_by=None, topic="user/personal", agent=None, **kw).action == "persist"


def test_personal_facts_persist_and_stay_recallable():
    for p in [
        "The dentist appointment is scheduled for June 30 at 3pm",
        "Team meeting scheduled for every Monday",
        "My rent payment is recurring every month",
        "I confirmed the dinner reservation for Friday",
        "The doctor confirmed the diagnosis is benign",
        "My medication is taken automatically by the dispenser",
        "I finished reading the book last night",
    ]:
        assert _persists(p), f"personal fact wrongly gated: {p!r}"


def test_dev_claims_still_downgrade():
    # software-context dev-confab without evidence -> still quarantined
    for p in [
        "The auth feature is shipped to production",
        "Fixed the bug in the recall module",
        "The deploy pipeline is automated and runs on every commit",
    ]:
        assert gate(proposition=p, verified_by=None, topic="", agent=None).action == "downgrade", p


def test_dev_claim_with_evidence_persists():
    # a real ref suppresses L1 (existing behavior, unchanged)
    assert gate(proposition="Shipped the fix in commit abc1234", topic="", agent=None,
                verified_by=["commit:abc1234"]).action == "persist"


def test_agent_first_person_completion_confab_still_downgrades():
    # critic counterexample (2026-06-20): bare first-person is the AGENT's self-narration
    # register; a completion/automation confab with NO personal-domain noun must STILL gate.
    for p in [
        "I finished the task.",
        "we completed everything, it is all done",
        "I scheduled it to run automatically",
        "Done. Everything is finished and verified.",
    ]:
        assert gate(proposition=p, verified_by=None, topic="", agent=None).action == "downgrade", p
