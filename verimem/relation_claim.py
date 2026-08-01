"""Relations a fact asserts and its source does not — the CE's blind spot.

The local cross-encoder scores similarity, so it sees every word of the source
in the fact and reports high confidence. That is correct for a faithful
restatement and wrong for a claim that adds a RELATION between the source's
facts: a cause, a completed state, a certainty, a computed quantity. Measured
2026-07-28 across five domains, the CE classified 8 of 11 deformations
correctly and all three misses were of exactly this kind — scoring 88, 100 and
100, far above the escalation band [40, 80) that exists to catch its doubts.
The net hangs under the cases it never drops.

These relations are announced lexically, which makes them cheap to spot. The
trigger is not "the fact contains 'because'" — that fires on most prose and
would drown the judge in noise. It is an ASYMMETRY: the fact announces a
relation the source never announces. A causal claim drawn from a causal source
adds nothing and stays silent here.

What this module does NOT do is decide. It routes: a flagged write goes to a
reasoning judge that can read the relation, so a false positive costs one call
and a false negative costs the thing the product sells. That asymmetry is why
the patterns below are deliberately generous.
"""
from __future__ import annotations

import re

__all__ = ["unverified_relation", "RELATION_KINDS"]

#: kind -> the surface forms that ANNOUNCE it. Word-bounded on purpose:
#: "delivered" is a completed state, "delivery" is not ("out for delivery" is
#: precisely the source that must NOT license "was delivered").
_PATTERNS: dict[str, re.Pattern[str]] = {
    "causal": re.compile(
        r"\b(because|caused by|due to|owing to|thanks to|led to|leads to|"
        r"resulted in|results in|as a result of|on account of|triggered by|"
        r"a causa di|perch[ée]|dovuto a|grazie a|ha causato|ha portato a)\b",
        re.IGNORECASE),
    "completion": re.compile(
        r"\b(delivered|completed|finished|resolved|closed|shipped|settled|"
        r"fixed|deployed|released|signed off|consegnato|completato|"
        r"risolto|chiuso|firmato)\b", re.IGNORECASE),
    "modality": re.compile(
        r"\b(prevents?|prevented|guarantees?|ensures?|cures?|eliminates?|"
        r"proves?|proven|always|never|all patients|every case|no side effects|"
        r"previene|garantisce|elimina|dimostra|sempre|mai)\b",
        re.IGNORECASE),
    "derived-quantity": re.compile(
        r"(\d+(?:\.\d+)?\s*%|\bpercent\b|\bpercentage\b|\btotal(?:s|ling)?\b|"
        r"\bsum of\b|\baverage\b|\bgrew\b|\bgrowth of\b|\brose by\b|"
        r"\bincreased by\b|\bdecreased by\b|\bdoubled\b|\bhalved\b|"
        r"\bper cento\b|\btotale\b|\bmedia\b)", re.IGNORECASE),
}

#: The kinds this module knows about, in the order they are checked. Causation
#: first: it is the one a similarity model can never see, since both of its
#: terms are already in the source and only the link is invented.
RELATION_KINDS = ("causal", "modality", "completion", "derived-quantity")

#: A completed state has a SHAPE, not just a vocabulary: an auxiliary plus a
#: past participle. The hand-written ``completion`` list above knew ``firmato``
#: and not ``pagato`` — found 2026-07-29 on an invoicing case, where "il totale
#: e gia stato PAGATO" scored 99.8 against a source reading "scadenza 30
#: giorni", which says the opposite. Enumerating verbs is the same defect cured
#: on the critic-orchestrator the night before: a list of what someone happened
#: to imagine. These two patterns match the CONSTRUCTION and capture the
#: participle, so the check below can ask the only question that matters —
#: does the source name this completed action at all?
_PARTICIPLE_IT = re.compile(
    r"\b(?:è|e|sono|era|erano|fu|furono|viene|vengono|venne|verrà|sarà)\s+"
    r"(?:gi[àa]\s+|poi\s+|infine\s+)?stat[oiae]\s+"
    r"(?:gi[àa]\s+|poi\s+|infine\s+)?"
    r"(\w{3,}(?:at[oaie]|it[oaie]|ut[oaie]|s[oaie]|t[oaie]))\b",
    re.IGNORECASE)

#: English keeps the auxiliary adjacent, so the same shape reads directly. The
#: irregular participles are the ones a corpus of records actually uses; -ed
#: covers the rest of the class without listing it.
_PARTICIPLE_EN = re.compile(
    r"\b(?:was|were|has been|have been|had been|is|are|been)\s+"
    r"(?:already\s+|now\s+|fully\s+|finally\s+)?"
    r"(\w{3,}ed|paid|sent|done|made|built|won|lost|found|given|taken|"
    r"written|signed|shipped|met|held|drawn|withdrawn)\b",
    re.IGNORECASE)


def _completed_action_absent_from(source: str, fact: str) -> bool:
    """True when ``fact`` announces a completed action in the passive/perfect
    and ``source`` never names it.

    The participle itself is the probe, not its stem: "inviato per la firma"
    contains *firma* but not *firmato*, and sending something for signature is
    precisely the source that must NOT license "è stato firmato". Matching on
    the stem would call that faithful.
    """
    for pat in (_PARTICIPLE_IT, _PARTICIPLE_EN):
        for m in pat.finditer(fact):
            participle = m.group(1)
            if not re.search(rf"\b{re.escape(participle)}\b", source,
                             re.IGNORECASE):
                return True
    return False


def unverified_relation(source: str | None, fact: str | None) -> str | None:
    """The kind of relation ``fact`` announces that ``source`` does not, or None.

    Returns the FIRST kind found (see :data:`RELATION_KINDS`); callers use it to
    route the write to a judge that reasons, not to reject it. Both sides empty
    or missing is not a relation.
    """
    f = (fact or "").strip()
    s = (source or "").strip()
    if not f:
        return None
    for kind in RELATION_KINDS:
        pat = _PATTERNS[kind]
        if pat.search(f) and not pat.search(s):
            return kind
    # Same kind, reached by shape instead of vocabulary — see
    # _completed_action_absent_from. Checked after the named patterns so a
    # sentence they already recognise keeps its existing answer.
    if _completed_action_absent_from(s, f):
        return "completion"
    return None
