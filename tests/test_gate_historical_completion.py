"""L1.13 completion detector must NOT quarantine HISTORICAL WORLD-FACTS.

Moat e2e opus bench (2026-07-17) surfaced a false positive: the faithful fact
"The bridge was completed in 1998" was quarantined by L1.13 — the completion
detector fired on the word "completed". But L1.13 exists to catch the AGENT
confabulating completion of ITS OWN WORK ("task done", "I finished the task"),
NOT third-person historical statements about a structure/artifact being
completed in a given year. A passive completion verb anchored to a calendar
year, with NO software/dev artifact, is a world-fact — keep it recallable.

The moat (L4-grounding) was IMPECCABLE in that bench (12/12 confab quarantined,
0 faithful quarantined by grounding); the sole miss came from this pre-existing
lexical L1 gate, so the fix lives in the escalation arm, not the moat.
"""
from engram.anti_confab_gate import run_validation_gate as gate


def _action(prop, **kw):
    return gate(proposition=prop, verified_by=None, topic="user", agent=None,
                **kw).action


def test_historical_completion_worldfacts_persist():
    # passive completion + a calendar year, no dev signal -> world-fact, recallable
    for p in [
        "The bridge was completed in 1998.",
        "The tower was completed in 1889.",
        "The cathedral was finished in 1965.",
        "The novel was finished in 1866.",
        "The stadium was built in 2004.",
        "The company was founded in 1911.",
        "The factory was closed in 1987.",
        "Il ponte fu completato nel 1998.",
    ]:
        assert _action(p) == "persist", f"world-fact wrongly quarantined: {p!r}"


def test_agent_completion_confab_still_downgrades():
    # regression: the self-narration register L1.13 exists for MUST stay caught,
    # even when the fix is live (no passive-completion-with-year construction).
    for p in [
        "I finished the task.",
        "we completed everything, it is all done",
        "Done. Everything is finished and verified.",
        "The auth feature is shipped to production",
    ]:
        assert _action(p) == "downgrade", f"confab wrongly freed: {p!r}"


def test_dev_completion_with_year_still_downgrades():
    # a dev artifact + year is NOT a historical world-fact: the moat's reason
    # to gate is intact (dev context present), so it must still escalate.
    for p in [
        "The migration was completed in 2023.",
        "The deployment was finished in 2024.",
    ]:
        assert _action(p) == "downgrade", f"dev confab wrongly freed: {p!r}"
