"""Semantic (NLI) contradiction / entailment detector — the missing moat layer.

Measured gap (benchmark/semantic_conflict_bench.py): Engram's ENTIRE write-time
conflict stack is lexical — coherence_check (token-Jaccard + numeric + explicit
negation), validate_claim ("puramente lessicale"), facts_disagreement ("not
authoritative NLI"), quantity_match ("pure lexical"). On 6 conflicts where the
WORDS differ but the MEANING conflicts (cosine 0.80-0.87, no number / no negation
token) they catch 0/6. The cosine is high enough that the conflict IS detectable —
the detectors just never use meaning as the trigger.

This module adds the semantic trigger as a 2-stage gate, mirroring the rest of the
stack (cheap pre-filter → precise confirm, opt-in, observational):

  1. cosine pre-filter — only sibling pairs above ``min_cosine`` are candidates
     (cheap, bounds cost; reuses ``contradiction._cosine``);
  2. an NLI ``RelationJudge`` classifies each candidate CONTRADICTION / ENTAILMENT
     / NEUTRAL. The judge is INJECTED: a subscription ``claude -p`` judge
     (``LLMRelationJudge``, O5 — zero external API key) today, a local NLI
     cross-encoder when one is cached (offline-scalable). Tests use a stub.

Why NLI and not "high cosine ⇒ conflict": complementary facts about the same
subject ("John lives in Rome" / "John is 30") ALSO score cosine ~0.85 but are NOT
a conflict. Only an entailment model separates *contradiction* from *different
attribute*; that discrimination is where a model earns its keep and an ``if``
cannot. Fail-safe: an unreadable verdict resolves to NEUTRAL — a wrong
CONTRADICTION would wrongly impugn a true fact, a wrong NEUTRAL only misses a
warning (the same precision-over-recall asymmetry as the rest of the anti-confab
stack).
"""
from __future__ import annotations

import re
from collections.abc import Callable
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from .coherence_check import CoherenceWarning
from .contradiction import _cosine


class Relation(str, Enum):
    CONTRADICTION = "contradiction"
    ENTAILMENT = "entailment"
    NEUTRAL = "neutral"


_NLI_SYSTEM = (
    "You compare two statements that may be about the same subject. Decide their "
    "logical relation:\n"
    "- CONTRADICTION: they cannot both be true (same subject and attribute, "
    "conflicting value).\n"
    "- ENTAILMENT: they assert the SAME fact (paraphrase, synonyms, or one "
    "clearly implies the other).\n"
    "- NEUTRAL: about different attributes, or unrelated — both can be true.\n"
    "A leading [timestamp] marks WHEN each statement was asserted. The world "
    "evolves: if the values differ but the timestamps order them as a sequence (an "
    "earlier value later replaced by a newer one), that is EVOLUTION over time, NOT "
    "a contradiction → answer NEUTRAL. Answer CONTRADICTION only for values that are "
    "incompatible at the SAME time (or when no timestamps distinguish them).\n"
    "Reply with EXACTLY one word: CONTRADICTION, ENTAILMENT, or NEUTRAL."
)


def _fact_ts(fact: Any) -> str | None:
    """Best-available 'when asserted' stamp for a fact, as a sortable string.

    Prefers ``created_at`` (assertion time; for live-captured facts this tracks
    when-true — a reasonable proxy, with the caveat that BACKFILLED facts carry a
    misleading created_at). Epoch floats are rendered ISO for the judge's clarity;
    pre-formatted string stamps pass through. Returns None when absent.
    """
    for attr in ("created_at", "ts", "timestamp"):
        v = getattr(fact, attr, None)
        if v in (None, "", 0, 0.0):
            continue
        if isinstance(v, (int, float)):
            try:
                from datetime import datetime, timezone
                return datetime.fromtimestamp(float(v), tz=timezone.utc).strftime("%Y-%m-%d")
            except (OverflowError, OSError, ValueError):
                return None
        return str(v)
    return None


def _stamp(prop: str, fact: Any) -> str:
    """Prefix ``[timestamp] `` to a proposition when the fact carries one, so the
    judge can reconcile temporal supersession from a genuine same-time conflict
    (measured: HaluMem contradiction-FPR 0.10→0.0125 at preserved recall, 2026-06-20)."""
    ts = _fact_ts(fact)
    return f"[{ts}] {prop}" if ts else prop


_CONTRA_WORDS = frozenset(
    {"contradiction", "contradicts", "contradict", "contradictory"})
_ENTAIL_WORDS = frozenset(
    {"entailment", "entails", "entail", "entailed", "duplicate", "same"})


def parse_relation(text: str) -> Relation:
    """Map a judge's reply to a Relation by its FIRST word. Fail-safe to NEUTRAL:
    an empty, verbose, or NEGATED verdict ("no contradiction") must never
    fabricate a contradiction (precision over recall — a false contradiction
    impugns a true fact). Substring matching would misread "no contradiction" as
    CONTRADICTION — exactly the dangerous direction — so we anchor on the first
    token, which is what the one-word judge prompt elicits."""
    t = (text or "").strip().lower()
    if not t:
        return Relation.NEUTRAL
    first = re.split(r"[^a-z]+", t, maxsplit=1)[0]
    if first in _CONTRA_WORDS:
        return Relation.CONTRADICTION
    if first in _ENTAIL_WORDS:
        return Relation.ENTAILMENT
    return Relation.NEUTRAL


def build_nli_prompt(a: str, b: str) -> tuple[str, list[dict[str, str]]]:
    """(system, messages) for the NLI judge. Pure."""
    return _NLI_SYSTEM, [{"role": "user", "content": f"A: {a}\nB: {b}"}]


@runtime_checkable
class RelationJudge(Protocol):
    def classify(self, a: str, b: str) -> Relation: ...


class LLMRelationJudge:
    """NLI via an injected LLM (live: ``verimem.llm.ClaudeCLILLM`` / the lean
    benchmark client — subscription, no external API key)."""

    def __init__(self, llm: Any, *, model: str | None = None) -> None:
        self.llm = llm
        self.model = model

    def classify(self, a: str, b: str) -> Relation:
        system, messages = build_nli_prompt(a, b)
        try:
            resp = self.llm.complete(system, messages, model=self.model, max_tokens=8)
        except Exception:  # noqa: BLE001 — a judge error must not crash a write
            return Relation.NEUTRAL
        return parse_relation(getattr(resp, "text", "") or "")


class FixedRelationJudge:
    """Always returns ``rel`` — for tests / a no-op default."""

    def __init__(self, rel: Relation = Relation.NEUTRAL) -> None:
        self.rel = rel

    def classify(self, a: str, b: str) -> Relation:
        return self.rel


def detect_semantic_conflicts(
    new_fact: Any, siblings: list[Any], judge: RelationJudge, *,
    min_cosine: float = 0.7,
    cosine_fn: Callable[[Any, Any], float] = _cosine,
) -> list[CoherenceWarning]:
    """Return semantic warnings for ``new_fact`` vs ``siblings``.

    Stage 1 (cosine_fn ≥ ``min_cosine``) narrows to candidates — the costly judge
    is consulted ONLY on those. Stage 2 (judge): CONTRADICTION → a
    ``semantic_conflict`` warning (the conflict the lexical stack misses);
    ENTAILMENT → a ``semantic_duplicate`` warning (the paraphrase-duplicate
    token-Jaccard misses); NEUTRAL → nothing. Pure / observational — no mutation.
    """
    out: list[CoherenceWarning] = []
    new_id = getattr(new_fact, "id", None)
    new_prop = getattr(new_fact, "proposition", "") or ""
    new_stamped = _stamp(new_prop, new_fact)
    for sib in siblings:
        if getattr(sib, "id", None) == new_id:
            continue
        if cosine_fn(new_fact, sib) < min_cosine:
            continue
        rel = judge.classify(
            new_stamped, _stamp(getattr(sib, "proposition", "") or "", sib))
        if rel is Relation.CONTRADICTION:
            out.append(CoherenceWarning(
                kind="semantic_conflict", other_fact_id=getattr(sib, "id", ""),
                details="nli=contradiction"))
        elif rel is Relation.ENTAILMENT:
            out.append(CoherenceWarning(
                kind="semantic_duplicate", other_fact_id=getattr(sib, "id", ""),
                details="nli=entailment"))
    return out


__all__ = [
    "Relation",
    "RelationJudge",
    "LLMRelationJudge",
    "FixedRelationJudge",
    "parse_relation",
    "build_nli_prompt",
    "detect_semantic_conflicts",
]
