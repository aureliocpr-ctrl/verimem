"""Subject-based domain/agent classifier (L1 precision, design (d), 2026-07-22).

The L1 keyword detectors exist to police an AGENT confabulating about its OWN
work ("the migration is complete", "I deployed it"). They over-fire on
third-party PROFESSIONAL facts that merely reuse the same verbs ("the surgical
procedure was completed", "the steel cable was tested"). Measured: 46% of a
vertical corpus wrongly quarantined.

The verbs (completed/tested/deployed/secure/approved) are irreducibly ambiguous
between software and domain — the discriminator is the SUBJECT HEAD: 'the bridge
joint was deployed' (physical) vs 'the service was deployed' (software). This
module classifies a proposition as a domain-professional fact (advisory-safe)
vs an agent self-claim (must still escalate), from the subject head + first
person, WITHOUT a spoofable field.

Fail-safe: when the subject is empty/pronoun/uncertain, classify as NOT-domain
(-> the L1 anti-confab keeps escalating, the safe default). This is a pure,
deterministic classifier — the gate wiring is separate and env-gated default-off.
"""
from __future__ import annotations

import pytest

pytest.importorskip("verimem.subject_extract")
from verimem.subject_extract import is_domain_professional, subject_head  # noqa: E402

# domain-professional facts that L1 wrongly quarantines (measured on the corpus)
DOMAIN = [
    "The surgical procedure was completed without complications.",
    "The drug was approved by the regulator for paediatric use.",
    "The settlement resolved all outstanding claims between the parties.",
    "The vault door is rated secure against a 60-minute forced attack.",
    "The zoning variance was approved by the municipal board in March.",
    "The steel cable was tested to a breaking load of 400 kilonewtons.",
    "The bridge expansion joint was deployed along the north span in 2021.",
    "The biopsy results were confirmed by Dr. Rossi on 12 March.",
    "The due-diligence review was completed before the acquisition closed.",
    "The foundation design is robust against a magnitude-7 earthquake.",
    # the 2 residual over-quarantines of the 2026-07-22 corpus measure (6.7%):
    # subject-EXTRACTION gaps, not classification gaps — the honorific dot
    # ('Dr.') tripped the sentence-punct guard, and 'meets' was missing from
    # the finite-verb marker. Both fail SAFE today (escalate); pinning them as
    # DOMAIN closes corpus G2 without weakening the agent side.
    "Dr. Rossi confirmed the biopsy results on 12 March.",
    "The hardened concrete bunker meets the ballistic protection standard.",
]

# agent self-claims about software/own work — MUST NOT be classified domain
AGENT = [
    "The migration is complete and all tests pass.",
    "I deployed the service to production.",
    "The build passes and the feature is shipped.",
    "The endpoint now responds in 8ms.",
    "The deployment succeeded and the pipeline is green.",
    "We finished the refactor and merged the PR.",
    "The task was completed successfully.",
    "The database migration ran without errors.",
    # leak-closers found by validating against the REAL test corpus (2026-07-22)
    # — NOT hand-picked; the first cut missed these two, the category fix caught
    # them. Kept as a regression pin so the software-perf register stays closed.
    "Throughput reached 50k requests per second.",
    "Their system works reliably under load.",
    # adversarial leak-closers found by the critic-orchestrator counterexample
    # worker (job 8f6d0ec5, 2026-07-22): SOFTWARE_HEADS is a denylist and these
    # software/ML/web-register heads were absent, so an agent self-claim with one
    # of them wrongly read as domain (is_domain_professional=True) and had its L1
    # escalation suppressed with the env on. Verified empirically before adding.
    # NB: this closes the KNOWN leaks; a lexical denylist cannot be exhaustive —
    # the promotion gate is the measured corpus + default-OFF, not this list.
    "The algorithm was tested and passed.",
    "The platform was deployed to production.",
    "The product shipped last week.",
    "The website was secured with TLS.",
    "The parser was tested against the spec.",
    "The compiler was verified on all targets.",
    "The dashboard was deployed to the cluster.",
    "The portal was approved for launch.",
    # flip-delta find (2026-07-22, pre default-ON): a NUMERIC head carries no
    # domain identity — "Cycle 999" classified domain and suppressed L1 on the
    # exact dogfood self-claim the gate exists for. Numeric head -> fail-safe.
    "Cycle 999 SHIPPED to production main",
    "Sprint 42 was completed ahead of schedule.",
    # critic 7a7bd87d counterexample (post-flip, verified): ALPHANUMERIC
    # identifiers defeated the pure-digit fail-safe — '999-beta', 'M13', '42a',
    # 'R2', '2b' all classified domain and PERSISTED by default. The rule is
    # now any-digit-in-head -> not a domain identity (fail-safe): version/
    # milestone identifiers are the agent's own work register.
    "Cycle 999-beta shipped",
    "Milestone M13 shipped",
    "Sprint 42a was completed on time.",
    "Release R2 was deployed to production.",
    "Phase 2b shipped last week.",
    # GLM-5.2 + Kimi-K3 convergent evasion classes (2026-07-22, 11/12 verified
    # leaking) + the 11 full-suite reds the flip exposed — same registers:
    "The team says the deploy works perfectly and is fully tested.",  # proxy
    "The pipeline group finished the cutover.",                       # proxy
    "Everything works perfectly and every test is green.",            # indef.
    "Production-ready and SHIPPED feature, fully MONITORED and "
    "AUTOMATED for enterprise customers.",                            # attacker
    "The cutover was completed last night.",                          # synonym
    "The transition from monolith completed yesterday.",              # prep-NP
    "Sprint forty-two closed.",                                       # spelled
    "Deploying succeeded.",                                           # gerund
    "Coverage reached 90 percent.",                                   # quality
    "Stabilization was achieved across services.",                    # quality
    "The bug was patched.",                                           # tracker
    "The ticket was resolved.",                                       # tracker
    "The regression was fixed.",                                      # tracker
    "BUG #42 ROOT CAUSE is misaligned indexing",                      # adapter
    "Verification of the migration is complete.",                     # nominal.
    "The deadline was met.",                                          # outcome
]


@pytest.mark.parametrize("text", DOMAIN)
def test_domain_facts_are_domain(text):
    assert is_domain_professional(text) is True, \
        f"domain fact misclassified as agent: {text!r} (head={subject_head(text)!r})"


@pytest.mark.parametrize("text", AGENT)
def test_agent_claims_are_not_domain(text):
    assert is_domain_professional(text) is False, \
        f"agent self-claim leaked as domain: {text!r} (head={subject_head(text)!r})"


def test_first_person_is_never_domain():
    assert is_domain_professional("I completed the audit.") is False
    assert is_domain_professional("We approved the change.") is False


def test_empty_or_pronoun_subject_fails_safe_to_not_domain():
    # uncertain subject -> NOT domain -> L1 keeps escalating (safe default)
    assert is_domain_professional("It was completed.") is False
    assert is_domain_professional("") is False
    assert is_domain_professional("Done.") is False
