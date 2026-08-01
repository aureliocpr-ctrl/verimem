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
#: UNO spazio, mai `\s+`: il testo arriva qui gia' collassato (vedi _WS_RUN),
#: quindi una corsa di spazi non esiste piu' e chiedere «uno o piu'» sarebbe
#: solo il permesso di backtrackare. Con un quantificatore la garanzia stava a
#: dieci righe di distanza, dentro l'unica funzione che collassa: bastava usare
#: questo regex da un altro punto del modulo per riportarsi in casa il blow-up
#: senza rompere niente di visibile.
_CLAUSE_BOUNDARY = re.compile(
    r"(?:(?<=[.;:]) )"                         # sentence end
    r"|(?:, ?(?=(?:e|ma|mentre|and|but|while|whereas)\b))"  # comma + coordinator
    r"|(?: (?=(?:mentre|whereas|while|perch[ée]|because|poich[ée]|"
    r"quindi|therefore|cosicch[ée]|so that)\b))",
    re.IGNORECASE,
)

#: Below this a fragment is punctuation or a stray token, not a claim.
_MIN_CLAUSE_CHARS = 25

#: Collapse whitespace runs BEFORE the boundary regex ever sees the text.
#: _CLAUSE_BOUNDARY has variable-width whitespace next to lookaheads, so on a
#: run of spaces whose lookahead fails the engine retries from every position —
#: quadratic. Measured on this module the day it was written:
#:
#:      2 000 spaces ->    0.3 s
#:      8 000 spaces ->    5.2 s
#:     16 000 spaces ->   20.8 s
#:     32 000 spaces ->   82.9 s
#:
#: and this module reads the text of user-written facts. CodeQL flagged it
#: (py/polynomial-redos, high) on the same pull request that introduced it —
#: after I had read the identical warning in quantity_match.py earlier the same
#: day and written the bug anyway.
#:
#: Collapsing first is linear and removes the input that causes the blow-up.
#: Newlines become single spaces, which costs nothing here: this counts
#: assertions, it does not reformat anything.
#:
#: 2026-08-01 — this alone was NOT the whole cure, and CodeQL kept flagging the
#: same line after it. The collapse made the module fast (0.000 s on the 32 000
#: spaces that used to take 82.9 s) but left the guarantee POSITIONAL: it held
#: because the one caller collapses first, not because the regex is safe. So
#: the boundary now asks for a single space and this pair is what protects the
#: split — collapse here, no quantifier there. Neither half is decoration.
_WS_RUN = re.compile(r"\s+")


def split_claim_clauses(proposition: str | None) -> list[str]:
    """The proposition's clauses, or a single-element list when it makes one
    claim. Short fragments are merged back into the previous clause rather than
    dropped — a dangling ", e i due" is part of what came before, and counting
    it alone would inflate the number of assertions."""
    text = _WS_RUN.sub(" ", (proposition or "")).strip()
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
