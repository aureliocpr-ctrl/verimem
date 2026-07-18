"""Source-echo disarm for the L1 shape detectors (vertical probe 2026-07-18).

The L1.x "lacks evidence" detectors judge the claim SHAPE against
``verified_by`` tags only; a documental write (``source=``) never enters
their judgment. Certified consequence on sourced ingest (visure, referti,
relazioni di calcolo): "La Rev C (approvata il 22/05/2026) …" whose source
itself states "APPROVATA … il 22/05/2026" was QUARANTINED by L1.16 — the
gate hid the truthful, sourced update from recall while (without a judge)
a fabricated claim on the same source was admitted.

Contract: an L1 warning whose ``matched_text`` literally appears in the
provided source WITH THE SAME NEGATION POLARITY becomes advisory
(``source_echo=True``); when EVERY L1 warning is echoed this way, L1 does
not escalate to quarantine — admission of sourced writes is L4's job (the
grounding judge, when present, still quarantines fabricated inferences).

The polarity guard closes the obvious hole: "la diagnosi è stata
confermata" against a source saying "NON confermata" shares the token but
inverts the meaning — that echo must NOT disarm.
"""
from __future__ import annotations

import re
from typing import Any

# Same cap philosophy as the gate's lexical scan: bound the work on
# pathological inputs; a real document echo lands well within this.
_SOURCE_SCAN_CAP = 20_000

# Negators considered when comparing claim vs source polarity around the
# matched text (IT + EN — the L1 keyword families are IT/EN too).
_NEGATORS = frozenset({
    "non", "né", "ne'", "mai", "senza", "nessun", "nessuna", "nessuno",
    "not", "no", "never", "without", "n't", "cannot", "unconfirmed",
})

#: how many tokens BEFORE the match participate in the polarity window.
_POLARITY_WINDOW = 6


def _norm(text: str) -> str:
    return " ".join((text or "")[:_SOURCE_SCAN_CAP].lower().split())


def _window_negated(text_norm: str, at: int) -> bool:
    """True if a negator occurs within the last ``_POLARITY_WINDOW`` tokens
    before position ``at`` (match start) in ``text_norm``."""
    prefix = text_norm[:at]
    tokens = re.findall(r"[\w']+", prefix)[-_POLARITY_WINDOW:]
    return any(t in _NEGATORS for t in tokens)


def _occurrences(haystack: str, needle: str) -> list[int]:
    out, start = [], 0
    while True:
        i = haystack.find(needle, start)
        if i < 0:
            return out
        out.append(i)
        start = i + 1


def apply_source_echo(warnings: list[dict[str, Any]], proposition: str,
                      source: str | None) -> bool:
    """Mark L1 warnings echoed by ``source`` (mutates them: ``source_echo``)
    and return True iff EVERY L1 warning was echoed with agreeing polarity —
    i.e. L1 must not escalate this sourced write."""
    if not source:
        return False
    l1 = [w for w in warnings
          if str(w.get("layer", "")).startswith("L1")]
    if not l1:
        return False
    src_n = _norm(source)
    prop_n = _norm(proposition)
    all_echoed = True
    for w in l1:
        matched = _norm(str(w.get("matched_text") or ""))
        if not matched:
            all_echoed = False  # nothing to compare -> never disarm blind
            continue
        prop_hits = _occurrences(prop_n, matched)
        claim_negated = any(_window_negated(prop_n, i) for i in prop_hits) \
            if prop_hits else False
        echo = any(_window_negated(src_n, i) == claim_negated
                   for i in _occurrences(src_n, matched))
        if echo:
            w["source_echo"] = True
        else:
            all_echoed = False
    return all_echoed


__all__ = ["apply_source_echo"]
