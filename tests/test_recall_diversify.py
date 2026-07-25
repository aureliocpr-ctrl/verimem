"""Deep-then-compress: recuperare in profondità e consegnare k DIVERSI.

Misurato 2026-07-25 sulle 5 domande multi-hop che LoCoMo ci fa sbagliare, con
la predizione dichiarata prima dell'esito:

    k=30 (default oggi)         1/5
    k=100 grezzo                2/5
    k=100 -> MMR 30             3/5   <-- stesso numero di chunk del primo

Il meccanismo, leggibile nei singoli casi: la profondità porta dentro evidenza
che a k=30 non c'era (un elemento a rank 77), e la compressione la rende
usabile — con 100 chunk grezzi il modello ne aggrega di meno, non di più.

DEFAULT OFF, e non per prudenza rituale: sul recall reale del prodotto la
ridondanza dei top-30 è 7.0% contro il 77.5% del bench conversazionale, quindi
su un corpus di proposizioni distinte questa selezione non ha nulla da
comprimere e sarebbe solo lavoro in più. Vive dove serve — corpora
conversazionali, documenti chunkati con overlap — e va misurata sul bench
completo prima di qualunque flip.
"""
from __future__ import annotations

import numpy as np

from verimem.diversify import mmr_select


def _v(*xs) -> np.ndarray:
    a = np.asarray(xs, dtype=np.float32)
    return a / (np.linalg.norm(a) or 1.0)


# Four dimensions, not three, and deliberately so: in 3-D two vectors both
# close to the query are necessarily close to EACH OTHER, so MMR has no room
# to discriminate and a test built there measures the geometry, not the code.
# Real embeddings live in hundreds of dimensions, where two items can be
# equally relevant and still point elsewhere — which is the whole situation
# this function exists for.
QUERY = _v(1.0, 0.0, 0.0, 0.0)
#          relevance   similarity to dup1
# dup1       0.950            1.00
# dup2       0.943            0.999   <- a near-duplicate of dup1
# dup3       0.936            0.999
# other      0.900            0.855   <- slightly less relevant, points elsewhere
# far        0.600            0.540
ITEMS = [
    ("dup1", _v(0.95, 0.312, 0.000, 0.00)),
    ("dup2", _v(0.94, 0.330, 0.020, 0.00)),
    ("dup3", _v(0.93, 0.350, 0.030, 0.00)),
    ("other", _v(0.90, 0.000, 0.435, 0.00)),
    ("far", _v(0.60, 0.000, 0.000, 0.80)),
]


def test_pure_relevance_returns_the_duplicates():
    """lambda=1 è il comportamento di oggi: i tre near-duplicate vincono."""
    picked = mmr_select(ITEMS, QUERY, n=3, lam=1.0)
    assert [p[0] for p in picked] == ["dup1", "dup2", "dup3"]


def test_diversification_breaks_the_duplicate_block():
    """With a big relevance gap the duplicates SHOULD still win at lam=0.7 —
    relevance is allowed to dominate, that is the point of the knob. The
    diversification has to bite when the gap narrows, which is the real case:
    in a conversational context the near-duplicates are not dramatically more
    relevant than the distinct chunk, they are merely first."""
    picked = [p[0] for p in mmr_select(ITEMS, QUERY, n=2, lam=0.7)]
    assert picked[0] == "dup1", "the most relevant item must still lead"
    assert "other" in picked, (
        "no distinct item survived even at a narrow relevance gap: this is "
        "pure relevance in disguise")


def test_lambda_controls_the_tradeoff():
    """The knob must move the outcome, or it is decoration. Same pool, two
    lambdas, different answers."""
    greedy = [p[0] for p in mmr_select(ITEMS, QUERY, n=3, lam=1.0)]
    diverse = [p[0] for p in mmr_select(ITEMS, QUERY, n=3, lam=0.3)]
    assert greedy != diverse
    assert greedy == ["dup1", "dup2", "dup3"]
    assert len({"other", "far"} & set(diverse)) >= 1


def test_never_returns_more_than_asked_or_duplicates_an_item():
    picked = mmr_select(ITEMS, QUERY, n=3, lam=0.5)
    assert len(picked) == 3
    assert len({p[0] for p in picked}) == 3


def test_n_larger_than_the_pool_returns_the_pool():
    picked = mmr_select(ITEMS, QUERY, n=99, lam=0.5)
    assert len(picked) == len(ITEMS)


def test_empty_pool_is_empty_not_an_error():
    assert mmr_select([], QUERY, n=5, lam=0.5) == []


def test_a_zero_vector_does_not_produce_nan():
    """A fact whose embedding never landed must not poison the ranking."""
    items = [*ITEMS, ("zero", np.zeros(4, dtype=np.float32))]
    picked = mmr_select(items, QUERY, n=6, lam=0.5)
    assert len(picked) == 6
    assert all(isinstance(p[0], str) for p in picked)


def test_mixed_dimensions_degrade_instead_of_exploding():
    """Dimension drift is a real state in a long-lived store (a re-embedded
    corpus, a model swap). Ranking such an item against a query it cannot be
    compared to would invent a similarity; raising would lose a recall. It goes
    to the tail, after everything that could be scored."""
    items = [*ITEMS, ("wrong_dim", np.ones(7, dtype=np.float32))]
    picked = mmr_select(items, QUERY, n=6, lam=0.7)
    names = [p[0] for p in picked]
    assert len(picked) == 6
    assert names[-1] == "wrong_dim", "the uncomparable item must not rank"
    assert names[0] == "dup1"


def test_all_items_uncomparable_returns_them_unranked():
    items = [("a", np.ones(7, dtype=np.float32)),
             ("b", np.ones(7, dtype=np.float32))]
    picked = mmr_select(items, QUERY, n=2, lam=0.7)
    assert [p[0] for p in picked] == ["a", "b"]


def test_first_pick_is_the_most_relevant_not_the_first_in_the_list():
    """Order of arrival must not decide. A pool whose best item sits in the
    middle catches an implementation that just takes items[0]."""
    pool = [
        ("mediocre", _v(0.70, 0.71, 0.00, 0.00)),
        ("best", _v(0.99, 0.14, 0.00, 0.00)),
        ("worst", _v(0.50, 0.86, 0.00, 0.00)),
    ]
    assert mmr_select(pool, QUERY, n=1, lam=1.0)[0][0] == "best"
    assert mmr_select(pool, QUERY, n=1, lam=0.3)[0][0] == "best"


def test_redundancy_is_measured_against_the_NEAREST_pick_not_the_average():
    """Canonical MMR penalises by the maximum similarity to what is already
    chosen. Averaging dilutes it: an item that duplicates ONE pick but differs
    from the others looks acceptable, and near-duplicates creep back in — the
    precise failure this function exists to prevent.

    Pool: `a` and `b` are mutually distant and get picked first; `dup_of_a` is
    a near-copy of `a` but far from `b`, so averaging halves its penalty, while
    `fresh` is moderately far from both.
    """
    pool = [
        ("a", _v(0.90, 0.44, 0.00, 0.00)),
        ("b", _v(0.88, 0.00, 0.47, 0.00)),
        ("dup_of_a", _v(0.895, 0.446, 0.00, 0.00)),
        ("fresh", _v(0.80, 0.20, 0.20, 0.52)),
    ]
    picked = [p[0] for p in mmr_select(pool, QUERY, n=3, lam=0.55)]
    assert picked[:2] == ["a", "b"], f"unexpected head: {picked}"
    assert picked[2] == "fresh", (
        f"third pick was {picked[2]!r}: a duplicate of an earlier pick slipped "
        f"through, which is what averaging the redundancy does")


def test_selection_is_deterministic():
    """Two runs must agree — a ranking that shifts between calls is not a
    ranking, and would make any A/B unreproducible."""
    a = [p[0] for p in mmr_select(ITEMS, QUERY, n=4, lam=0.6)]
    b = [p[0] for p in mmr_select(ITEMS, QUERY, n=4, lam=0.6)]
    assert a == b


def test_lambda_zero_ignores_relevance_entirely():
    """The knob has to actually reach both ends, or it is not a knob."""
    picked = [p[0] for p in mmr_select(ITEMS, QUERY, n=3, lam=0.0)]
    assert picked[0] == "dup1"          # first pick is always the most relevant
    assert "far" in picked, "with no relevance term the outlier must be taken"
