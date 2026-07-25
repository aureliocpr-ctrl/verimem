"""Machine-checkable proof outranks a model's opinion.

The gate has two kinds of evidence about a write. One is a PROOF it can inspect:
``pytest:test_x_PASS``, ``qa:<scenario>_PASS``, ``ci:<id>:green`` — a reference to
a process that ran and reported an outcome, recognised by
:func:`l1_tested_detector._has_tested_evidence` and already used there to decide
that a "verified" claim is supported rather than quarantined. The other is a
JUDGEMENT: the NLI cross-encoder saying two statements look contradictory.

They are not equal, and until now the store treated them as if they were. Found
by dogfooding on the real corpus 2026-07-25: the OEIS organism verifies relations
between integer sequences with an exact check and writes each with its evidence.
Of 9 verified relations, 2 survived — the other 7 were RETIRED in pairs by the
same-source supersede, because

    +A000032(n) -3*A000045(n+1) +A000045(n+2) = 0
    +A000032(n)   +A000045(n)   -2*A000045(n+1) = 0

are two DISTINCT properties of the same sequences, both true, both proven, and a
cross-encoder reads "same subject, different numbers" as a contradiction.
Measured on that pair: every deterministic detector (numeric, version, date,
negation) returns None. The verdict came from the model alone.

So the rule this module expresses: when BOTH sides carry machine-checkable
evidence, a model's opinion is not enough to retire either. Retiring is
irreversible; keeping both is not — the asymmetry ``quantity_match`` states as
"a false conflict downgrades a true fact, the opposite of the trust we sell".

What this module deliberately does NOT do:
  * it does not promote any status to ``verified``. ``client.py`` and
    ``provenance_validator.py`` refuse a caller that tries to forge that status,
    because it would bypass the moat, and this rule does not smuggle it back in;
  * it does not make anything untouchable. A DETERMINISTIC conflict still retires
    the older value — that path never consults this rule. Someone who forged a
    fake ``verified_by`` would gain coexistence, not immunity;
  * it does not raise anyone's trust. Two proven facts simply both stay.

Why the rank floor could not do this job: ``_STATUS_RANK`` puts ``verified`` (3)
above ``model_claim`` (2) and the floor stops a weaker write from retiring a
stronger one — but every write from every production path lands as
``model_claim``, so the comparison is always ``2 <= 2`` and the floor has never
protected anything. Fixing that would mean assigning ``verified`` at write time,
which is exactly the forgery the design refuses.
"""
from __future__ import annotations

from collections.abc import Iterable

from .l1_tested_detector import _has_tested_evidence

__all__ = ["both_machine_checked", "is_machine_checked"]


def is_machine_checked(verified_by: Iterable[str] | None) -> bool:
    """True when ``verified_by`` cites a process that ran and reported an
    outcome. Thin alias over the gate's own recogniser, on purpose: one notion of
    "proof" for the whole store — a second copy would drift, and this codebase
    has already paid for that with three divergent copies of its own rules."""
    return _has_tested_evidence(verified_by)


def both_machine_checked(vb_a: Iterable[str] | None,
                         vb_b: Iterable[str] | None) -> bool:
    """True when BOTH sides carry machine-checkable evidence.

    Symmetric by construction: the rule is about two proofs meeting, so one-sided
    evidence leaves the gate's behaviour untouched.
    """
    return is_machine_checked(vb_a) and is_machine_checked(vb_b)
