"""Self-calibrating relevance floor (TRUST-CORE phase C, read-path).

The external measurement (HaluEval dev, 2026-07-10) showed WHY a fixed
min_relevance default cannot work: e5 scores live in [0.73, 0.95] — any
floor picked for one model/store sits below the whole distribution (never
abstains) or eats the coverage. The fix is NOT a better constant: the store
estimates its own noise band — scrambled in-domain probes score like
irrelevant queries — and the floor is a quantile of that band, per store.

Contract pinned here:
  * deterministic given a seed;
  * probes are NOT the stored propositions themselves (else the "noise"
    band is the signal band);
  * a genuinely relevant query must score ABOVE the estimated floor
    (otherwise the floor produces over-abstention by construction);
  * higher quantile → floor at least as high (monotone).
"""
from __future__ import annotations

from verimem.client import Memory
from verimem.relevance_floor import estimate_relevance_floor, scrambled_probes

FACTS = [
    "The Eiffel Tower is a wrought-iron lattice tower in Paris, completed "
    "in 1889 for the World's Fair.",
    "Marie Curie won two Nobel Prizes, in Physics 1903 and Chemistry 1911, "
    "for her work on radioactivity.",
    "The Amazon River in South America discharges more water than any "
    "other river on Earth.",
    "Photosynthesis converts carbon dioxide and water into glucose using "
    "light energy in plant chloroplasts.",
]


def _store(tmp_path):
    mem = Memory(tmp_path / "m.db")
    for f in FACTS:
        mem.add(f, topic="floor", verified_by=["source-doc:test"])
    return mem


def test_scrambled_probes_deterministic_and_not_originals(tmp_path):
    mem = _store(tmp_path)
    p1 = scrambled_probes(mem.semantic, n=8, seed=3)
    p2 = scrambled_probes(mem.semantic, n=8, seed=3)
    assert p1 == p2, "same seed must give identical probes"
    assert len(p1) == 8
    originals = {f.lower() for f in FACTS}
    assert all(p.lower() not in originals for p in p1), (
        "a probe equal to a stored proposition would measure SIGNAL as noise")


def test_probes_are_cross_fact_capped(tmp_path):
    """No probe may draw more than 2 words from a single fact — else the
    noise band contains near-reconstructions of stored facts (signal) and
    the floor eats real queries. Facts get disjoint marked vocabularies so
    provenance of every probe word is decidable."""
    mem = Memory(tmp_path / "m.db")
    vocab = {}
    for tag in ("alpha", "beta", "gamma", "delta"):
        words = [f"{tag}{i:02d}word" for i in range(8)]
        vocab[tag] = set(words)
        mem.add(" ".join(words), topic="floor", verified_by=["source-doc:t"])
    probes = scrambled_probes(mem.semantic, n=12, seed=5)
    assert probes
    for p in probes:
        for tag, words in vocab.items():
            got = sum(1 for w in p.split() if w in words)
            assert got <= 2, f"probe drew {got} words from fact {tag}: {p!r}"


def test_floor_estimate_bounded(tmp_path):
    """Mechanical bounds on the stub embedder. EFFECTIVENESS (relevant query
    clears the floor) is validated on the REAL e5 embedder against the
    HaluEval external store — results/floor_autocal_*.json — because the
    lexical stub's score geometry is not the product's."""
    mem = _store(tmp_path)
    floor = estimate_relevance_floor(mem.semantic, n_probes=16, seed=3)
    assert 0.0 <= floor < 1.0


def test_floor_quantile_monotone(tmp_path):
    mem = _store(tmp_path)
    lo = estimate_relevance_floor(mem.semantic, n_probes=16, seed=3,
                                  quantile=0.5)
    hi = estimate_relevance_floor(mem.semantic, n_probes=16, seed=3,
                                  quantile=0.99)
    assert hi >= lo


def test_empty_store_floor_is_zero(tmp_path):
    mem = Memory(tmp_path / "empty.db")
    assert estimate_relevance_floor(mem.semantic) == 0.0


# ---- product wiring: explain(min_relevance="auto") ---------------------------

def test_explain_auto_resolves_floor_and_reports_it(tmp_path, monkeypatch):
    mem = _store(tmp_path)
    from verimem import relevance_floor
    calls = []
    monkeypatch.setattr(relevance_floor, "estimate_relevance_floor",
                        lambda sm, **kw: calls.append(1) or 0.99)
    report = mem.explain("completely unrelated nonsense query",
                         min_relevance="auto")
    assert report["abstained"] is True, "floor 0.99 must floor everything"
    assert report["min_relevance"] == 0.99, "resolved value must be reported"
    # cached within the TTL: a second explain must not re-estimate
    mem.explain("another query", min_relevance="auto")
    assert len(calls) == 1, "floor must be cached, not re-estimated per query"


def test_explain_numeric_floor_still_works(tmp_path):
    mem = _store(tmp_path)
    report = mem.explain("anything", min_relevance=0.0)
    assert report["min_relevance"] == 0.0
    assert report["abstained"] is False
