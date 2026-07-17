"""Deterministic corroboration — the trust-RESTORE complement to Tier-1.

Tier-1 (evidence_requirement) WITHHOLDS trust from a specific, unsourced
claim. Corroboration is how such a claim earns trust back WITHOUT an LLM and
WITHOUT a human: if the same specific value is asserted INDEPENDENTLY by
≥N other facts (different topics → not the same fact saved twice), that is
real evidence — multiple witnesses agreeing.

This is the positive twin of ``facts_conflict.find_numeric_conflicts``:
conflict = same unit, DIFFERENT value; corroboration = same unit, SAME value.
Both reuse the :mod:`quantity_match` core (anchor + unit normalisation +
contrast guard) so write-time, conflict-scan and corroboration share one
semantics.

HONEST SCOPE (to be benchmarked before any "it works" claim): "same value
repeated" is strong evidence for a STABLE fact (a config value mentioned
across sources) but can also be a moment-snapshot logged repeatedly
("4554 facts" in three handoffs). The distinct-topic requirement filters
same-context duplicates; it does NOT by itself distinguish a durable fact
from a repeated tally. Measure on the real corpus first.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ._telemetry_prefixes import TEST_TOPIC_PREFIXES
from .quantity_match import agreement_from_parts, content_tokens, extract_quantities
from .semantic import Fact

_DEFAULT_EXCLUDE_TOPIC_PREFIXES: tuple[str, ...] = TEST_TOPIC_PREFIXES


@dataclass(frozen=True)
class Corroboration:
    """Two facts in DIFFERENT topics that assert the SAME value for the same
    unit about the same subject — mutual, independent corroboration."""
    fact_a: Fact
    fact_b: Fact
    unit: str
    value: float

    def as_dict(self) -> dict:
        return {
            "fact_a": {"id": self.fact_a.id, "topic": self.fact_a.topic,
                       "proposition": self.fact_a.proposition},
            "fact_b": {"id": self.fact_b.id, "topic": self.fact_b.topic,
                       "proposition": self.fact_b.proposition},
            "unit": self.unit, "value": float(self.value),
        }


def find_corroborations(
    facts: list[Fact],
    *,
    min_overlap: float = 0.30,
    min_shared_tokens: int = 2,
    require_distinct_topic: bool = True,
    exclude_topic_prefixes: tuple[str, ...] | None = None,
) -> list[Corroboration]:
    """Return fact pairs that independently corroborate the same specific.

    Same precision guards as the conflict scanner — a topical near-duplicate
    prefilter (≥ ``min_shared_tokens`` shared distinctive words and overlap-
    coefficient ≥ ``min_overlap``) — PLUS, by default, a DISTINCT-TOPIC
    requirement so a fact duplicated within one topic is not mistaken for
    independent corroboration. Pure lexical, read-only.
    """
    if exclude_topic_prefixes is None:
        exclude_topic_prefixes = _DEFAULT_EXCLUDE_TOPIC_PREFIXES
    pool = [
        f for f in facts
        if not any((f.topic or "").startswith(p) for p in exclude_topic_prefixes)
    ]
    items: list[tuple[Fact, set, set]] = []
    for f in pool:
        q = extract_quantities(f.proposition)
        if not q:
            continue
        items.append((f, q, content_tokens(f.proposition)))

    # Bucket by (unit, value): corroboration lives WITHIN a value group
    # (conflict lived across value groups).
    uv: dict[tuple[str, float], list[int]] = defaultdict(list)
    for idx, (_f, q, _c) in enumerate(items):
        for (u, v) in q:
            if u:
                uv[(u, v)].append(idx)

    seen: set[tuple[int, int]] = set()
    out: list[Corroboration] = []
    for (_unit, _val), idxs in uv.items():
        if len(idxs) < 2:
            continue
        for i in range(len(idxs)):
            for j in range(i + 1, len(idxs)):
                ia, ib = idxs[i], idxs[j]
                key = (ia, ib) if ia < ib else (ib, ia)
                if key in seen:
                    continue
                fa, qa, ca = items[ia]
                fb, qb, cb = items[ib]
                if require_distinct_topic and (fa.topic or "") == (fb.topic or ""):
                    continue
                shared = ca & cb
                if len(shared) < min_shared_tokens:
                    continue
                if len(shared) / max(1, min(len(ca), len(cb))) < float(min_overlap):
                    continue
                ag = agreement_from_parts(qa, ca, qb, cb)
                if ag is None:
                    continue
                seen.add(key)
                out.append(Corroboration(
                    fact_a=fa, fact_b=fb, unit=ag[0], value=ag[1],
                ))
    return out


def corroboration_index(
    facts: list[Fact], **kwargs,
) -> dict[str, int]:
    """Map fact_id → number of DISTINCT other facts that corroborate it.

    A specific claim with a high count is independently witnessed (deterministic
    trust signal); a singleton (0) is unverified until sourced/judged.
    """
    counts: dict[str, set[str]] = defaultdict(set)
    for c in find_corroborations(facts, **kwargs):
        counts[c.fact_a.id].add(c.fact_b.id)
        counts[c.fact_b.id].add(c.fact_a.id)
    return {fid: len(peers) for fid, peers in counts.items()}


__all__ = ["Corroboration", "find_corroborations", "corroboration_index"]
