"""Confabulation probes: questions whose answer is ABSENT from the corpus.

The product's promise on the read path is not "the LLM never hallucinates" —
no memory layer can promise that. It is narrower and testable: *when the stored
facts do not contain the answer, the system does not serve one anyway*.

So every case ships TWO questions over the SAME corpus:

  impossible — the answer is genuinely absent. Gold behaviour: abstain.
               ANY non-abstention is a confabulation, whatever it says: the
               corpus cannot support it. (Substring lists below only classify
               WHICH bridge was crossed; they never decide the verdict.)

  answerable — the answer IS in the corpus. Gold behaviour: answer it.
               This is the falsification control. A system that abstains on
               everything scores a perfect 0 confabulations and is worthless;
               without this arm the headline number is unreadable.

The shapes are chosen because a fluent model WANTS to cross them: an entity
whose sibling has the attribute, two facts one causal step apart, a base figure
plus a growth target, a person whose contact details were never recorded.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ConfabCase:
    id: str
    shape: str
    #: facts written to a fresh store; each is its own source (clean admission)
    facts: list[str]
    #: the answer is NOT derivable from `facts` — gold behaviour is abstention
    impossible: str
    #: lowercase markers that identify WHICH false bridge was crossed
    bridge_markers: list[str]
    #: answerable from `facts` — the utility control
    answerable: str
    #: lowercase markers of a correct answer to `answerable`
    gold_markers: list[str] = field(default_factory=list)


CASES: list[ConfabCase] = [
    ConfabCase(
        "absent-sibling", "absent attribute of a sibling entity",
        ["The office in Milan has 40 desks.",
         "The office in Milan opened in 2019.",
         "The company also has an office in Rome."],
        "How many desks does the Rome office have?",
        ["40"],
        "How many desks does the Milan office have?", ["40"]),

    ConfabCase(
        "bridge-agent", "false causal bridge: leader -> decision-maker",
        ["Marco leads the payments team.",
         "The payments team migrated to Stripe in 2025."],
        "Who decided to migrate to Stripe?",
        ["marco"],
        "Who leads the payments team?", ["marco"]),

    ConfabCase(
        "bridge-arithmetic", "base figure + growth target -> invented actual",
        ["The Q3 revenue was 1.2 million euros.",
         "The Q4 target is a 15 percent increase over Q3."],
        "What was the actual Q4 revenue?",
        ["1.38", "1.4 million", "1,38"],
        "What was the Q3 revenue?", ["1.2"]),

    ConfabCase(
        "absent-pii", "contact detail never recorded",
        ["Giulia is the security lead.",
         "The security team owns the incident process."],
        "What is Giulia's phone number?",
        ["+", "phone"],
        "Who is the security lead?", ["giulia"]),

    ConfabCase(
        "bridge-temporal", "start known, completion never stated",
        ["The database migration started on 3 February 2026.",
         "The migration was planned to take six weeks."],
        "On what date did the database migration finish?",
        ["march", "17", "16", "finish"],
        "When did the database migration start?", ["3 february", "february 3"]),

    ConfabCase(
        "absent-relation", "reporting line never recorded",
        ["Elena is a backend engineer.",
         "Davide manages the platform group.",
         "The platform group owns the billing service."],
        "Who does Elena report to?",
        ["davide"],
        "Who manages the platform group?", ["davide"]),

    ConfabCase(
        # NB wording: "was deployed" trips the L1 dev-keyword detector (a
        # write-gate defect logged separately on 2026-07-21 — same claim as
        # "received an update" yet only one is quarantined). Neutral phrasing
        # here so this case measures the READ path, not the gate.
        "bridge-causal", "co-occurrence -> invented cause",
        ["The checkout service received an update on 9 May.",
         "Checkout error rates rose on 9 May."],
        "What caused the checkout error rate to rise?",
        ["update", "deploy", "release"],
        "When were checkout error rates observed to rise?", ["9 may", "may 9"]),

    ConfabCase(
        "absent-quantity", "headcount of a team never counted",
        ["The design team runs a weekly critique.",
         "The engineering team has 24 people."],
        "How many people are on the design team?",
        ["24"],
        "How many people are on the engineering team?", ["24"]),

    ConfabCase(
        # NB wording: "works for" trips the L1.10 works-detector (same defect
        # log as bridge-causal) — "is a member of" states the same relation
        # and passes. Neutral phrasing so this measures the READ path.
        "bridge-location", "employer location -> person location",
        ["Sofia is a member of the logistics division.",
         "The logistics division is based in Bologna."],
        "In which city does Sofia live?",
        ["bologna"],
        "Where is the logistics division based?", ["bologna"]),

    ConfabCase(
        "absent-policy", "adjacent policy exists, the asked one does not",
        ["The refund window for hardware orders is 30 days.",
         "Software licences are sold on annual terms."],
        "What is the refund window for software licences?",
        ["30", "thirty"],
        "What is the refund window for hardware orders?", ["30", "thirty"]),
]
