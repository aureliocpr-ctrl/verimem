"""Self-calibrating relevance floor — the store measures its own noise band.

Why (external measurement, HaluEval 2026-07-10, results/external_readpath_*):
e5 cosine scores live in [0.73, 0.95] — answerable and unanswerable queries
are almost perfectly separable (AUROC 0.997 dev / 0.9935 held-out) but ANY
fixed ``min_relevance`` default is wrong somewhere: below the band it never
abstains (false_answer 1.0 — the measured read-path hole), above it it eats
coverage. The right floor depends on the embedder AND the store's content.

So the store estimates it: scrambled in-domain probes — words sampled across
DIFFERENT stored facts, shuffled into nonsense — score like irrelevant
queries (lexically in-domain, semantically nothing). The floor is a high
quantile of that noise band. In-domain scrambling is deliberately
conservative: off-domain probes would score lower and put the floor too low.

Cost: n_probes recall calls at estimation time (~32 embeds, daemon-warm ≈
ms). Deterministic given a seed. Wiring into ``explain(min_relevance="auto")``
is a separate step — this module is the measured mechanism, validated
against the external benchmark store before any default changes.
"""
from __future__ import annotations

import random

__all__ = ["scrambled_probes", "estimate_relevance_floor"]

_MIN_FACTS = 2          # cross-fact scrambling needs at least two sources
_PROBE_WORDS = 10       # ~question-length probes
_MAX_POOL_FACTS = 200   # cap the word pool: enough diversity, bounded cost


_MAX_WORDS_PER_FACT = 2


def scrambled_probes(sm, *, n: int = 32, seed: int = 0) -> list[str]:
    """Deterministic nonsense probes from the store's OWN vocabulary.

    Stratified CROSS-FACT sampling: each probe takes at most
    ``_MAX_WORDS_PER_FACT`` words from any single fact. Without the cap a
    probe can draw 3-4 words from ONE fact and nearly reconstruct it — the
    "noise" band then contains signal and the floor eats real queries (caught
    by the lexical test stub, which scores exactly that failure mode). A
    probe that collides with a stored proposition is discarded outright."""
    facts = sm.all()[:_MAX_POOL_FACTS]
    if len(facts) < _MIN_FACTS:
        return []
    words_by_fact: list[list[str]] = []
    originals: set[str] = set()
    for f in facts:
        text = (getattr(f, "proposition", "") or "").strip()
        originals.add(text.lower())
        ws = [w for w in text.split() if len(w) > 2]
        if ws:
            words_by_fact.append(ws)
    if len(words_by_fact) < _MIN_FACTS:
        return []
    rng = random.Random(seed)
    probes: list[str] = []
    for _ in range(n * 2):          # headroom for collision discards
        if len(probes) >= n:
            break
        order = list(range(len(words_by_fact)))
        rng.shuffle(order)
        words: list[str] = []
        for fi in order:            # round-robin over facts, capped per fact
            if len(words) >= _PROBE_WORDS:
                break
            ws = words_by_fact[fi]
            take = min(_MAX_WORDS_PER_FACT, len(ws),
                       _PROBE_WORDS - len(words))
            words.extend(rng.sample(ws, take))
        if len(words) < min(_PROBE_WORDS, 4):
            continue
        rng.shuffle(words)
        probe = " ".join(words)
        if probe.lower() not in originals:
            probes.append(probe)
    return probes


def estimate_relevance_floor(sm, *, n_probes: int = 32, quantile: float = 0.95,
                             seed: int = 0, k: int = 5) -> float:
    """The store's noise ceiling: ``quantile`` of the max recall score of
    scrambled probes. 0.0 (floor off) when the store is too small to measure
    — a floor guessed from nothing would be worse than none."""
    probes = scrambled_probes(sm, n=n_probes, seed=seed)
    if not probes:
        return 0.0
    maxima: list[float] = []
    for p in probes:
        hits = sm.recall(p, k=k)
        maxima.append(max((float(s) for _, s, *_ in hits), default=0.0))
    if not maxima:
        return 0.0
    maxima.sort()
    idx = min(len(maxima) - 1, max(0, round(quantile * (len(maxima) - 1))))
    return round(maxima[idx], 4)
