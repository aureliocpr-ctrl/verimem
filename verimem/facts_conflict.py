"""Contradiction detection over the semantic-memory facts table.

The bug this addresses (observed 2026-05-11): two facts on the same
topic claimed the OPPOSITE state of the world ("F#5 IS in main" and
"F#5 is NOT in main"). The recall surface returned both and never
flagged that they couldn't both be true — so the next session, the
other Claude instance read "F#5 not in main" and acted on stale
information. That is memory pollution.

This module ships the *detection* side: given the current facts pool
(optionally narrowed by topic), return pairs of facts that are
semantically near-duplicates but assert opposite polarity. The
caller (UI, audit job, or future auto-supersede) decides what to do
with the conflict — typically surface to the user, who knows which
one survived.

V1 heuristic — intentionally simple, falsifiable:

  polarity(text) = "negative" if the text contains a negation marker
                   (NOT, never, no longer, deprecated, broken, etc.)
                   else "positive"
  signature(text)  = embedding(text with negation markers stripped)

  conflict(a, b) iff
      polarity(a) ≠ polarity(b)
      AND cosine(signature(a), signature(b)) ≥ min_semantic

Stripping markers before embedding is the key: it brings "F#5 IS in
main" and "F#5 is NOT in main" close in embedding space (they
otherwise sit further apart because the negation flips meaning).

What this doesn't do (yet): full NLI entailment, sarcasm, "the old
fact is still correct because the world rolled back". Those need a
LLM call and a richer trust model. V1 catches the common case where
a fact got rewritten but the old one was never deleted.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

# Lab stress-test rumore (project/lab/, lab/: worker che scrivono fact a
# raffica per provare il locking SQLite) + transient test fact (test/:
# sopravvivono tra sessioni e creano FP per token-overlap su glue). La tupla
# vive in _telemetry_prefixes (TEST_TOPIC_PREFIXES) come single source of truth.
from ._telemetry_prefixes import TEST_TOPIC_PREFIXES as _DEFAULT_EXCLUDE_TOPIC_PREFIXES
from .quantity_match import (
    conflict_from_parts as _qm_conflict_from_parts,
)
from .quantity_match import (
    content_tokens as _qm_content_tokens,
)
from .quantity_match import (
    extract_quantities as _qm_extract_quantities,
)
from .semantic import Fact

# SYNTACTIC markers — genuine clause-level negations that flip the
# polarity of the assertion. Counted with parity so "NOT not in main"
# (double negation) resolves to positive, as natural language intends.
#
# CRITICAL: order matters. Longer/more-specific alternatives come
# first in the alternation so "non ancora" matches as one token
# rather than as "non" + "ancora". Using a single combined pattern
# with `findall` guarantees non-overlapping matches; iterating
# multiple separate patterns would double-count ("NON ancora" hit
# by both "non ancora" AND "non" would flip parity twice).
_SYNTACTIC_NEGATION_RE: re.Pattern = re.compile(
    r"\b(?:no\s+longer|non\s+ancora|non\s+pi[uù]|never|not|non|mai)\b",
    re.IGNORECASE,
)

# LEXICAL status markers — adjectives/verbs that describe a negative
# state of the subject without being a real negation of the clause.
# A sentence containing "broken" can be positive ("the broken endpoint
# is now fixed") or negative ("the endpoint is broken"). These don't
# affect polarity on their own; they're only stripped from the surface
# so two phrasings of the same fact ("broken endpoint is fixed" and
# "endpoint is fixed") land at near-identical cosine.
_LEXICAL_NEGATIVE_RE: re.Pattern = re.compile(
    r"\b(?:deprecated|obsolete|broken|rolled\s+back|reverted|superseded)\b",
    re.IGNORECASE,
)

_WHITESPACE = re.compile(r"\s+")

# F#10-bug2: sentinel inserted in place of stripped markers. The
# sentence-transformer collapses short fragments toward the model
# centroid (a 1-2 token leftover like "since v3" embeds near every
# other terse temporal phrase), producing spurious cross-topic
# cosine ≥ 0.7 matches. Inserting a stable sentinel preserves
# sentence length and positional context, so the embedding of the
# stripped form stays anchored to the rest of the sentence rather
# than collapsing.
_STRIP_SENTINEL = " __X__ "


def has_negation(text: str) -> bool:
    """True iff `text` contains an ODD number of syntactic negations.

    Counts only true clause-level negations (not/never/no longer/
    non/non ancora/non più/mai) and applies parity, so a double
    negation ("F#5 is NOT not in main") resolves to positive — which
    is what natural language intends. Lexical status markers
    (broken/deprecated/...) do NOT count here: a sentence can mention
    them in a positive context ("the broken endpoint is now fixed")
    and should not be misclassified as negative.
    """
    if not text:
        return False
    return len(_SYNTACTIC_NEGATION_RE.findall(text)) % 2 == 1


def strip_negation(text: str) -> str:
    """Remove every negation marker (both syntactic AND lexical);
    collapse resulting whitespace.

    The output is the "neutral surface" of the assertion, used as the
    embedding key so a positive and a negative fact about the same
    state of the world land near each other in cosine space. Lexical
    markers are stripped here (but NOT counted in `has_negation`) so
    "the broken endpoint is fixed" and "the endpoint is fixed" map
    to the same neutral surface — same polarity, no false conflict.
    """
    if not text:
        return ""
    out = _SYNTACTIC_NEGATION_RE.sub(_STRIP_SENTINEL, text)
    out = _LEXICAL_NEGATIVE_RE.sub(_STRIP_SENTINEL, out)
    return _WHITESPACE.sub(" ", out).strip()


@dataclass(frozen=True)
class ConflictPair:
    """One pair of facts believed to assert opposite polarity on the
    same proposition. Order is (positive_fact, negative_fact) for
    deterministic display."""
    positive: Fact
    negative: Fact
    semantic_similarity: float

    def as_dict(self) -> dict:
        return {
            "positive": {
                "id": self.positive.id,
                "proposition": self.positive.proposition,
                "topic": self.positive.topic,
                "confidence": self.positive.confidence,
                "created_at": self.positive.created_at,
            },
            "negative": {
                "id": self.negative.id,
                "proposition": self.negative.proposition,
                "topic": self.negative.topic,
                "confidence": self.negative.confidence,
                "created_at": self.negative.created_at,
            },
            "semantic_similarity": float(self.semantic_similarity),
        }


_CONTENT_TOKEN_RE = re.compile(r"[A-Za-z0-9#]+")
_STOPWORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "of", "in", "on", "at", "to", "for", "with", "by", "from",
    "and", "or", "but", "as", "it", "its", "this", "that", "these", "those",
    "il", "lo", "la", "i", "gli", "le", "un", "una", "uno",
    "di", "da", "con", "su", "per", "tra", "fra", "e", "o", "ma", "ed",
    # F#21 — sentinel char emitted by `strip_negation`. We tokenise
    # `__X__` as the single letter `x` (underscores split). Without
    # this exclusion the sentinel inflates Jaccard union with a
    # token that carries no semantic content.
    "x",
})


def _content_tokens(text: str) -> set[str]:
    """Lowercased tokens (preserving `#` for identifiers like `F#5`)
    with English + Italian stopwords removed. Used by
    `find_conflicting_pairs` as a length-tolerant similarity metric."""
    return {
        t.lower() for t in _CONTENT_TOKEN_RE.findall(text or "")
        if t.lower() not in _STOPWORDS
    }


def _overlap_coefficient(a: set[str], b: set[str]) -> float:
    """Szymkiewicz-Simpson coefficient: |A ∩ B| / min(|A|, |B|).

    Length-tolerant alternative to Jaccard. A short fragment that is
    a near-subset of a longer one scores high. Used for F#21
    contradiction detection where the "truth" is typically a long
    descriptive proposition and the "poison" is a short bare
    negation — Jaccard penalises the length asymmetry, overlap
    coefficient doesn't.
    """
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def find_conflicting_pairs(
    facts: list[Fact],
    *,
    min_overlap: float = 0.30,
    min_shared_tokens: int = 2,
    topic: str | None = None,
    exclude_topic_prefixes: tuple[str, ...] | None = None,
) -> list[ConflictPair]:
    """Return every (positive, negative) fact pair that asserts the
    opposite polarity on a near-duplicate proposition.

    F#21 — algorithm switched from cosine-on-embeddings to
    content-token Jaccard. The cosine path failed on the canonical
    real-world case (long truth "F#5 IS in main as of commit X" vs
    short poison "F#5 is NOT in main") because the propositions
    diverged on the tail tokens, dragging stripped cosine below 0.7
    even though they manifestly assert opposite things about the
    same subject. Token-Jaccard is length-tolerant: the truth shares
    `{f#5, main}` with every poison variant; that overlap is exactly
    what flags the conflict. Stopwords (English + Italian) are
    removed so common glue tokens don't inflate Jaccard.

    Args:
      facts: pool to scan. Caller usually passes `semantic.all()` or
        a topic-filtered subset.
      min_overlap: Jaccard threshold on content tokens of the
        negation-stripped propositions. Default 0.30 catches real
        contradictions while keeping cross-topic noise out.
      topic: when set, filter `facts` to that exact topic first.

    Returns: pairs sorted by Jaccard descending (most clear-cut
    contradiction first). `semantic_similarity` on the returned
    ConflictPair carries the Jaccard score (field name kept stable
    for callers that already read it).
    """
    # Cycle 161 precision fix: drop noise-prefix topics by default.
    # Audit 2026-05-19 measured precision 0/30 (100% FP) on the
    # production corpus; 17/30 FP came from lab-stress + test/ topic
    # prefixes pairing with unrelated work via 2-token glue overlap.
    # Caller passes `()` to disable (e.g. when auditing the noise pool
    # itself).
    if exclude_topic_prefixes is None:
        exclude_topic_prefixes = _DEFAULT_EXCLUDE_TOPIC_PREFIXES
    pool = [
        f for f in facts
        if (not topic or f.topic == topic)
        and not any(
            (f.topic or "").startswith(p) for p in exclude_topic_prefixes
        )
    ]
    if len(pool) < 2:
        return []

    strippeds = [strip_negation(f.proposition) for f in pool]
    polarities = [has_negation(f.proposition) for f in pool]
    token_sets = [_content_tokens(s) for s in strippeds]

    pos_idx = [i for i, p in enumerate(polarities) if not p]
    neg_idx = [i for i, p in enumerate(polarities) if p]
    if not pos_idx or not neg_idx:
        return []

    out: list[ConflictPair] = []
    for pi in pos_idx:
        if not token_sets[pi]:
            continue
        for ni in neg_idx:
            if not token_sets[ni]:
                continue
            shared = token_sets[pi] & token_sets[ni]
            # Belt+braces: |shared| ≥ min_shared_tokens (default 2)
            # AVOIDS the failure mode where a single common token
            # like "main" between unrelated facts gives high overlap
            # coefficient on a 2-token poison.
            if len(shared) < min_shared_tokens:
                continue
            score = _overlap_coefficient(token_sets[pi], token_sets[ni])
            if score < float(min_overlap):
                continue
            out.append(ConflictPair(
                positive=pool[pi],
                negative=pool[ni],
                semantic_similarity=score,
            ))
    out.sort(key=lambda p: -p.semantic_similarity)
    return out


@dataclass(frozen=True)
class NumericConflictPair:
    """Two facts that assert a DIFFERENT value for the SAME unit about the
    same subject (e.g. "TTL of 30 minutes" vs "expire after 45 minutes").

    Distinct from :class:`ConflictPair` (polarity flip). Both facts are
    positive-polarity here — the inconsistency is the NUMBER, which the
    polarity scanner is blind to."""
    fact_a: Fact
    fact_b: Fact
    unit: str
    value_a: float
    value_b: float

    def as_dict(self) -> dict:
        return {
            "fact_a": {
                "id": self.fact_a.id,
                "proposition": self.fact_a.proposition,
                "topic": self.fact_a.topic,
                "confidence": self.fact_a.confidence,
                "created_at": self.fact_a.created_at,
            },
            "fact_b": {
                "id": self.fact_b.id,
                "proposition": self.fact_b.proposition,
                "topic": self.fact_b.topic,
                "confidence": self.fact_b.confidence,
                "created_at": self.fact_b.created_at,
            },
            "unit": self.unit,
            "value_a": float(self.value_a),
            "value_b": float(self.value_b),
        }


def find_numeric_conflicts(
    facts: list[Fact],
    *,
    topic: str | None = None,
    exclude_topic_prefixes: tuple[str, ...] | None = None,
    min_overlap: float = 0.30,
    min_shared_tokens: int = 2,
) -> list[NumericConflictPair]:
    """Return fact pairs that state a DIFFERENT value for the same unit about
    the same subject — numeric inconsistencies already sitting in the corpus.

    The write-time gate (``validate_claim``) blocks these going IN (when
    ``validate='full'``); this scans what is ALREADY stored. Both use the
    same :mod:`quantity_match` core, so the two views agree by construction.

    CORPUS SUITABILITY (measured, A3 — do not overclaim): this is meaningful
    on a corpus of ATOMIC FACTUAL ASSERTIONS (specs/configs: "TTL = 30 min").
    It is NOT meaningful on an event-LOG corpus, where numbers are snapshots
    of a moment ("4537 tests pass", "52 files changed") rather than stable
    claims — two such facts state different counts at different times, which
    is NOT a contradiction. A live scan of one such corpus surfaced ~27k
    pairs that are almost all incidental-count noise even after the standalone
    -number anchor + topical prefilter. So: topic-scope it and point it at
    stable-assertion facts; do NOT run it corpus-wide and call the output
    "inconsistencies". (The write-time detector is the primary value.)

    Same noise-prefix exclusion as :func:`find_conflicting_pairs`. Quantities
    and content tokens are pre-computed once per fact; only facts carrying a
    quantity enter the O(m²) pair loop (m ≪ corpus). Pure lexical, no
    embedding, read-only — the caller decides what to do with the findings.
    """
    if exclude_topic_prefixes is None:
        exclude_topic_prefixes = _DEFAULT_EXCLUDE_TOPIC_PREFIXES
    pool = [
        f for f in facts
        if (not topic or f.topic == topic)
        and not any(
            (f.topic or "").startswith(p) for p in exclude_topic_prefixes
        )
    ]
    # Pre-compute per fact: quantities, the numeric-core content tokens, and
    # the BROAD content tokens (this module's `_content_tokens`, #-preserving)
    # used for the topical near-duplicate prefilter. Keep only facts with a
    # standalone number.
    items: list[tuple[Fact, set, set, set]] = []
    for f in pool:
        q = _qm_extract_quantities(f.proposition)
        if not q:
            continue
        items.append((
            f, q,
            _qm_content_tokens(f.proposition),   # numeric-core distinct guard
            _content_tokens(f.proposition),      # broad topical-overlap guard
        ))

    # Candidate enumeration via unit→value buckets: a conflict needs two facts
    # that share a unit with DIFFERENT values, so we only ever compare the
    # cross-product of distinct value groups within each unit. This skips the
    # (huge) set of same-value and disjoint-unit pairs — a naive O(m²) over the
    # live corpus times out. Each surviving candidate is then gated by a
    # TOPICAL near-duplicate prefilter (the polarity scanner's proven overlap-
    # coefficient ≥ min_overlap + ≥ min_shared_tokens — empirically the lever
    # that turns a noisy narrative corpus from ~700k false hits into real
    # ones) and finally confirmed by the shared numeric core.
    unit_vals: dict[str, dict[float, list[int]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for idx, (_f, q, _c, _fc) in enumerate(items):
        for (u, v) in q:
            if u:
                unit_vals[u][v].append(idx)

    candidates: set[tuple[int, int]] = set()
    for _unit, by_val in unit_vals.items():
        vals = list(by_val)
        for x in range(len(vals)):
            for y in range(x + 1, len(vals)):
                for ia in by_val[vals[x]]:
                    for ib in by_val[vals[y]]:
                        candidates.add((ia, ib) if ia < ib else (ib, ia))

    out: list[NumericConflictPair] = []
    for ia, ib in candidates:
        fa, qa, ca, fca = items[ia]
        fb, qb, cb, fcb = items[ib]
        # Topical near-duplicate prefilter (same precision mechanism as the
        # polarity scanner): the two facts must really be about the same thing
        # before a numeric mismatch counts as an inconsistency.
        shared = fca & fcb
        if len(shared) < min_shared_tokens:
            continue
        if _overlap_coefficient(fca, fcb) < float(min_overlap):
            continue
        conf = _qm_conflict_from_parts(qa, ca, qb, cb)
        if conf is None:
            continue
        unit, va, vb = conf
        out.append(NumericConflictPair(
            fact_a=fa, fact_b=fb, unit=unit, value_a=va, value_b=vb,
        ))
    # Most-recently-touched conflict first (likeliest to matter now).
    out.sort(
        key=lambda p: -max(
            float(p.fact_a.created_at or 0.0),
            float(p.fact_b.created_at or 0.0),
        )
    )
    return out


__all__ = [
    "ConflictPair",
    "NumericConflictPair",
    "find_conflicting_pairs",
    "find_numeric_conflicts",
    "has_negation",
    "strip_negation",
]
