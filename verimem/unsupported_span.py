"""How MANY claims a rejected proposition makes — not which one is guilty.

When the moat refuses a write it says "the source does not support this
proposition". True, and hard to act on: a 190-character sentence usually asserts
three things, the source carries two, and the writer guesses. Measured on myself
2026-07-29 — three consecutive rejections of one checkpoint, each attempt
removing a different piece.

The obvious fix does NOT work, and was tried before this docstring was written.
Scoring each clause against the source with the same CE, on the two real
rejections of that day:

    "L'astensione era spenta per SDK/console/gateway"     40.6   <- the guilty one
    "e su venti domande il gate non toglie risposte"       0.1   <- the source PROVES this

Backwards. An isolated clause loses its context, and the CE reads lexical
overlap: the clause the numbers actually support shares no words with a source
made of numbers. Ablation (rescore the proposition WITHOUT each clause, pick the
one whose removal helps most) was tried next and scored 0 of 2. Both are gone;
pointing at the wrong clause is worse than pointing at none, because it sends
the writer to delete the part that was true.

What survives is what can be said WITHOUT a model: how many separate assertions
the sentence makes. The moat judges them as one block, so a single unproven
piece sinks the rest — and splitting is exactly what worked, by hand, all three
times. Counting is free and cannot be wrong in the way a pointer can.

The split does NOT cut on a bare ``e``/``and``: "SDK, console e gateway" is one
list, not three claims. It cuts where a NEW assertion starts — a subordinating
or contrastive conjunction, or a comma followed by a coordinating one.
"""
from __future__ import annotations

import re

__all__ = ["split_claim_clauses"]

#: Where a new assertion starts. Italian and English, both directions of
#: contrast, plus the causal and consecutive links — those are precisely the
#: joins that carry an inference the source may never have made.
_CLAUSE_BOUNDARY = re.compile(
    r"(?:(?<=[.;:])\s+)"                       # sentence end
    r"|(?:,\s*(?=(?:e|ma|mentre|and|but|while|whereas)\b))"  # comma + coordinator
    r"|(?:\s+(?=(?:mentre|whereas|while|perch[ée]|because|poich[ée]|"
    r"quindi|therefore|cosicch[ée]|so that)\b))",
    re.IGNORECASE,
)

#: Below this a fragment is punctuation or a stray token, not a claim.
_MIN_CLAUSE_CHARS = 25


def split_claim_clauses(proposition: str | None) -> list[str]:
    """The proposition's clauses, or a single-element list when it makes one
    claim. Short fragments are merged back into the previous clause rather than
    dropped — a dangling ", e i due" is part of what came before, and scoring it
    alone would produce a meaningless number."""
    text = (proposition or "").strip()
    if not text:
        return []
    parts: list[str] = []
    for raw in _CLAUSE_BOUNDARY.split(text):
        piece = (raw or "").strip(" \t,;")
        if not piece:
            continue
        if len(piece) < _MIN_CLAUSE_CHARS and parts:
            parts[-1] = f"{parts[-1]}, {piece}"
        else:
            parts.append(piece)
    return parts or [text]
