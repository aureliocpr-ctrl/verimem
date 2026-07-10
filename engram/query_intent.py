"""Query intent router — the read-path twin of gate_router (surface map thesis).

F1 unifying thesis (docs/TEST_SURFACE_MAP.md): the robust engine CLASSIFIES
before it acts. The write path routes on PROVENANCE (gate_router: whose claim
is this?). The read path must route on INTENT: what OPERATION does the query
ask for? Semantic recall answers "find the relevant item" — but "how many
times…", "everything except…", "list all…" are SET operations over the whole
corpus, not top-k similarity (measured: recall k=5 saw 5/12 mentions,
undercount 58%). Routing them to a scan/count instead of recall is the fix at
the right layer.

Deterministic, lexical, sub-millisecond, EN+IT (mirrors prompt_injection's
discipline: anchored patterns, a false-positive-guarded default). This module
only CLASSIFIES; the caller (Memory / gateway) dispatches — FIND stays the
safe default, so an unrouted query behaves exactly as today.
"""
from __future__ import annotations

import re

FIND = "find"        # default: semantic recall, top-k (unchanged behavior)
COUNT = "count"      # "how many…": scan + count the whole matching set
EXCLUDE = "exclude"  # "everything except / not about X": set difference
LIST_ALL = "list_all"  # "list all / every…": enumerate the set, not top-k

# COUNT — a cardinality question. EN + IT. Anchored so "how many people came"
# routes to count but "how many ways to say hi" (rhetorical) still safely
# falls through to FIND if no corpus term follows (caller decides).
_COUNT = re.compile(
    r"(?i)\b(?:how\s+many|how\s+much|number\s+of|count\s+(?:of|the)|"
    r"how\s+often|how\s+frequently|"
    r"quant[ei]|quante\s+volte|numero\s+di|conta(?:re)?\s+(?:i|le|gli|quant))\b")

# LIST_ALL — enumerate the whole set (not the best few).
_LIST_ALL = re.compile(
    r"(?i)\b(?:list\s+all|show\s+all|show\s+me\s+all|all\s+the|every\s+|"
    r"each\s+of|enumerate|"
    r"elenca(?:re)?|mostra(?:mi)?\s+tutt[ei]|tutt[ei]\s+(?:i|le|gli)|ogni)\b")

# EXCLUDE — a set-difference / negation query embeddings can't honor.
_EXCLUDE = re.compile(
    r"(?i)\b(?:not\s+about|except|excluding|other\s+than|without|"
    r"that\s+(?:are|is|do|does|did)\s+n[o']t|"
    r"tranne|eccetto|senza|che\s+non|diver[sc])\b")


def classify_query_intent(query: str | None) -> str:
    """Return the OPERATION a query asks for: count / exclude / list_all /
    find. FIND is the default (unchanged recall) so misclassification is
    always safe — a query is only re-routed on a clear cardinality /
    enumeration / exclusion signal."""
    q = (query or "").strip()
    if not q:
        return FIND
    # COUNT wins over LIST_ALL ("how many of all…" is a count).
    if _COUNT.search(q):
        return COUNT
    if _EXCLUDE.search(q):
        return EXCLUDE
    if _LIST_ALL.search(q):
        return LIST_ALL
    return FIND


def is_set_operation(query: str | None) -> bool:
    """True when the query needs a whole-set scan, not top-k recall — the
    single bit a dispatcher needs to choose count/scan over recall."""
    return classify_query_intent(query) != FIND


# Function/intent words to strip so the CONTENT terms remain (the entity the
# count/exclusion is ABOUT). Small + EN/IT; the goal is "how many times did I
# discuss Project Helios" -> "project helios" for the scan.
_STOP = frozenset({
    "did", "do", "does", "have", "has", "i", "we", "you", "my", "our", "the",
    "a", "an", "of", "about", "in", "on", "to", "is", "are", "was", "were",
    "how", "many", "much", "times", "time", "number", "list", "show", "me",
    "all", "every", "each", "often", "frequently", "count",
    "discuss", "discussed", "mention", "mentioned", "talk", "talked", "say",
    "said", "there", "any", "some", "with",
    "ho", "hai", "abbiamo", "di", "del", "della", "le", "gli", "un", "una",
    "quante", "quanti", "volte", "volta", "numero", "elenca", "mostrami",
    "mostra", "tutti", "tutte", "ogni", "parlato", "discusso", "menzionato",
    "che", "non", "sono",
})


def content_terms(query: str | None) -> str:
    """Strip the intent/function words, leaving the entity the operation is
    about — what a scan/count should match on. Lexical, order-preserving."""
    q = _COUNT.sub(" ", query or "")
    q = _EXCLUDE.sub(" ", q)
    q = _LIST_ALL.sub(" ", q)
    toks = [t for t in re.findall(r"[\w]+", q)
            if t.lower() not in _STOP and len(t) > 1]
    return " ".join(toks)


__all__ = ["FIND", "COUNT", "EXCLUDE", "LIST_ALL",
           "classify_query_intent", "is_set_operation", "content_terms"]
