"""TRUST-CORE block B — external read-path harness (HaluEval QA), TDD.

The harness measures hallucination-on-recall sub-mode (a) miss→fabrication
WITHOUT an LLM: ground truth is what the store contains, so support is
decidable (see benchmark/TRUST_CORE.md §2). Fixtures are inline — tests never
depend on the downloaded dataset.
"""
from __future__ import annotations

import json

import pytest

from benchmark.external_readpath import (
    build_store,
    eval_answerable,
    eval_unanswerable,
    make_samples,
    run_readpath,
)

ITEMS = [
    {"knowledge": "The Eiffel Tower is a wrought-iron lattice tower in Paris, "
                  "completed in 1889 for the World's Fair.",
     "question": "In which city is the Eiffel Tower located?",
     "right_answer": "Paris",
     "hallucinated_answer": "London"},
    {"knowledge": "Marie Curie won two Nobel Prizes, in Physics 1903 and "
                  "Chemistry 1911, for her work on radioactivity.",
     "question": "How many Nobel Prizes did Marie Curie win?",
     "right_answer": "two",
     "hallucinated_answer": "one"},
    {"knowledge": "The Amazon River in South America discharges more water "
                  "than any other river on Earth.",
     "question": "Which river discharges the most water on Earth?",
     "right_answer": "the Amazon River",
     "hallucinated_answer": "the Nile"},
]

UNRELATED_QUESTIONS = [
    "What is the boiling point of liquid nitrogen at sea level?",
    "Who composed the opera Turandot?",
]


# ---- sampling ---------------------------------------------------------------

def test_make_samples_deterministic_and_disjoint(tmp_path):
    src = tmp_path / "qa_data.json"
    rows = [{"knowledge": f"K{i}", "question": f"Q{i}",
             "right_answer": f"A{i}", "hallucinated_answer": f"H{i}"}
            for i in range(50)]
    src.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    out1 = make_samples(src, tmp_path / "s1", n_dev=10, n_heldout=20, seed=42)
    out2 = make_samples(src, tmp_path / "s2", n_dev=10, n_heldout=20, seed=42)

    dev1 = (tmp_path / "s1" / "halueval_qa_dev.jsonl").read_text("utf-8")
    dev2 = (tmp_path / "s2" / "halueval_qa_dev.jsonl").read_text("utf-8")
    assert dev1 == dev2, "same seed must give byte-identical samples"
    assert out1["n_dev"] == 10 and out1["n_heldout"] == 20

    dev_qs = {json.loads(ln)["question"] for ln in dev1.splitlines()}
    held = (tmp_path / "s1" / "halueval_qa_heldout.jsonl").read_text("utf-8")
    held_qs = {json.loads(ln)["question"] for ln in held.splitlines()}
    assert not dev_qs & held_qs, "dev and heldout must be disjoint"
    assert out1 == out2


# ---- store build ------------------------------------------------------------

def test_build_store_maps_items_to_fact_ids(tmp_path):
    mem, fact_ids, ingest = build_store(ITEMS, tmp_path / "m.db")
    assert len(fact_ids) == len(ITEMS)
    # every non-blocked item maps to a real stored fact
    for fid in fact_ids:
        if fid is not None:
            assert mem.get(fid) is not None
    # external knowledge carries its source ref; blocked count is reported
    assert 0 <= ingest["blocked"] <= len(ITEMS)
    assert ingest["admitted"] + ingest["blocked"] == len(ITEMS)


# ---- answerable: retrieval hit is id-decidable ------------------------------

def test_answerable_hit_on_own_knowledge(tmp_path):
    mem, fact_ids, _ = build_store(ITEMS, tmp_path / "m.db")
    rows = eval_answerable(mem, ITEMS, fact_ids, k=3, tau=0.0)
    assert len(rows) == len(ITEMS)
    # a 3-fact store queried with its own questions must hit at least 2/3
    assert sum(r["retrieval_hit"] for r in rows) >= 2
    assert all(set(r) >= {"retrieval_hit", "abstained"} for r in rows)


# ---- unanswerable: abstention -----------------------------------------------

def test_unanswerable_abstains_at_high_tau(tmp_path):
    mem, _, _ = build_store(ITEMS, tmp_path / "m.db")
    rows = eval_unanswerable(mem, UNRELATED_QUESTIONS, k=3, tau=0.99)
    assert all(r["abstained"] for r in rows), (
        "tau=0.99 must abstain on everything — if this fails the floor is "
        "not wired to explain()")


def test_unanswerable_answers_at_zero_tau(tmp_path):
    """tau=0 disables the floor → the system 'answers' junk. This asserts the
    HARNESS measures the failure mode, i.e. false_answer is representable."""
    mem, _, _ = build_store(ITEMS, tmp_path / "m.db")
    rows = eval_unanswerable(mem, UNRELATED_QUESTIONS, k=3, tau=0.0)
    assert any(not r["abstained"] for r in rows)


# ---- floor semantics stays pinned to the product path ------------------------

def test_abstains_matches_explain(tmp_path):
    """The one-pass shortcut (_abstains over search scores) must agree with
    the product decision explain(min_relevance=τ) — else benchmark numbers
    drift from what a customer actually gets."""
    from benchmark.external_readpath import _abstains
    mem, _, _ = build_store(ITEMS, tmp_path / "m.db")
    queries = [ITEMS[0]["question"], UNRELATED_QUESTIONS[0]]
    for q in queries:
        hits = mem.search(q, k=3)
        for tau in (0.3, 0.9):
            assert _abstains(hits, tau) == bool(
                mem.explain(q, k=3, min_relevance=tau).get("abstained")), \
                f"drift at tau={tau} for {q!r}"


# ---- end-to-end report ------------------------------------------------------

def test_run_readpath_report_shape(tmp_path):
    report = run_readpath(ITEMS, UNRELATED_QUESTIONS, tmp_path / "m.db",
                          k=3, tau=0.5)
    for key in ("n_answerable", "n_unanswerable", "retrieval_hit_rate",
                "abstention_rate", "false_answer_rate", "tau", "k",
                "ingest"):
        assert key in report, key
    assert report["n_answerable"] == 3
    assert report["n_unanswerable"] == 2
    assert 0.0 <= report["retrieval_hit_rate"] <= 1.0
    assert report["false_answer_rate"] == pytest.approx(
        1.0 - report["abstention_rate"])
