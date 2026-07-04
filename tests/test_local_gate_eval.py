"""Unit tests for benchmark/local_gate_eval.py — the CE-NLI local-gate bench harness.

The CE model itself is NOT loaded here (injection-only contract, like
cross_encoder_rerank): ``score_pairs`` takes an injected scorer, ``build_pairs``
is pure dataset plumbing, ``evaluate`` is pure math. What must hold:

* build_pairs pairs every memory point with ITS OWN session dialogue span,
  labels clean=1 / interference=0 / foreign=0, and is seed-deterministic.
* the calib/heldout split is BY USER (no session shared across splits — the
  leakage would inflate agreement).
* evaluate calibrates the threshold on calib only, and reports heldout rates.
"""
from __future__ import annotations

import json

import pytest

from benchmark.local_gate_eval import build_pairs, evaluate, score_pairs, split_by_user


def _mini_jsonl(tmp_path, n_users=4):
    """Synthetic HaluMem-shaped corpus: each user has 2 sessions, each session has
    1 clean (secondary) + 1 interference memory point."""
    p = tmp_path / "mini.jsonl"
    with open(p, "w", encoding="utf-8") as f:
        for ui in range(n_users):
            sessions = []
            for si in range(2):
                sessions.append({
                    "dialogue": [
                        {"role": "user", "content": f"I adopted a dog named Rex{ui}{si}."},
                        {"role": "assistant", "content": "Nice!"},
                        {"role": "user", "content": f"I work as a baker in town {ui}."},
                    ],
                    "memory_points": [
                        {"memory_source": "secondary",
                         "memory_content": f"User {ui} has a dog named Rex{ui}{si}."},
                        {"memory_source": "interference",
                         "memory_content": f"User {ui} has a cat named Felix{ui}{si}."},
                    ],
                })
            f.write(json.dumps({"sessions": sessions}) + "\n")
    return p


def test_build_pairs_labels_and_own_session_pairing(tmp_path):
    pairs = build_pairs(_mini_jsonl(tmp_path), seed=7, n_clean=8, n_interference=8,
                        n_foreign=4, budget=500)
    kinds = {p["kind"] for p in pairs}
    assert kinds == {"clean", "interference", "foreign"}
    for p in pairs:
        assert p["label"] == (1 if p["kind"] == "clean" else 0)
        assert p["fact"] and p["span"]
        if p["kind"] == "clean":
            # the own-session span must contain the dog line that grounds the fact
            name = p["fact"].split("named ")[1].rstrip(".")
            assert name in p["span"]
        if p["kind"] == "foreign":
            # a foreign fact must come from a DIFFERENT user than the span's owner
            assert p["fact_user"] != p["span_user"]


def test_build_pairs_deterministic_and_capped(tmp_path):
    src = _mini_jsonl(tmp_path)
    a = build_pairs(src, seed=7, n_clean=5, n_interference=5, n_foreign=3, budget=500)
    b = build_pairs(src, seed=7, n_clean=5, n_interference=5, n_foreign=3, budget=500)
    assert a == b
    assert sum(1 for p in a if p["kind"] == "clean") <= 5
    assert sum(1 for p in a if p["kind"] == "interference") <= 5
    assert sum(1 for p in a if p["kind"] == "foreign") <= 3


def test_split_by_user_no_leakage(tmp_path):
    pairs = build_pairs(_mini_jsonl(tmp_path, n_users=6), seed=7, n_clean=24,
                        n_interference=24, n_foreign=12, budget=500)
    calib, held = split_by_user(pairs, seed=7, calib_frac=0.5)
    cu = {p["span_user"] for p in calib}
    hu = {p["span_user"] for p in held}
    assert cu and hu
    assert cu.isdisjoint(hu), "a user's sessions must not straddle the split"
    assert len(calib) + len(held) == len(pairs)


def test_score_pairs_injected_scorer_order():
    pairs = [{"span": "s1", "fact": "f1"}, {"span": "s2", "fact": "f2"}]
    seen: list[tuple[str, str]] = []

    def scorer(batch):
        seen.extend(batch)
        return [float(10 * (i + 1)) for i in range(len(batch))]

    out = score_pairs(pairs, scorer)
    assert out == [10.0, 20.0]
    assert seen == [("s1", "f1"), ("s2", "f2")]


def test_evaluate_calibrates_on_calib_and_reports_heldout():
    # calib: perfectly separated at 50 — Youden threshold lands in (40, 60]
    calib = [{"kind": "clean", "label": 1}, {"kind": "interference", "label": 0}]
    calib_scores = [60.0, 40.0]
    held = [
        {"kind": "clean", "label": 1}, {"kind": "clean", "label": 1},
        {"kind": "interference", "label": 0}, {"kind": "foreign", "label": 0},
    ]
    held_scores = [80.0, 45.0, 20.0, 70.0]  # one clean FN, one foreign FP
    r = evaluate(calib, calib_scores, held, held_scores)
    assert 40.0 < r["threshold"] <= 60.0
    assert r["heldout"]["clean"]["admit_rate"] == 0.5
    assert r["heldout"]["interference"]["admit_rate"] == 0.0
    assert r["heldout"]["foreign"]["admit_rate"] == 1.0
    assert 0.0 <= r["auroc_heldout"] <= 1.0
    assert r["n_calib"] == 2 and r["n_heldout"] == 4


def test_evaluate_empty_class_is_honest():
    calib = [{"kind": "clean", "label": 1}, {"kind": "interference", "label": 0}]
    held = [{"kind": "clean", "label": 1}]
    r = evaluate(calib, [90.0, 10.0], held, [95.0])
    assert r["heldout"]["clean"]["admit_rate"] == 1.0
    # no negatives on heldout -> AUROC must be None, not a fabricated number
    assert r["auroc_heldout"] is None


def test_main_requires_dataset(tmp_path):
    from benchmark.local_gate_eval import main
    missing = tmp_path / "nope.jsonl"
    with pytest.raises(SystemExit):
        main(["--jsonl", str(missing), "--models", "stub", "--out",
              str(tmp_path / "o.json")])


# ---- v2 levers: sentence-max pooling + speaker naming --------------------------------


def test_split_units_turns_and_bigrams():
    from benchmark.local_gate_eval import split_units
    span = "user: I have a dog.\nassistant: Nice!\nuser: I bake bread."
    units = split_units(span, bigrams=True)
    assert "user: I have a dog." in units
    assert "user: I bake bread." in units
    # adjacent-turn bigram covers cross-turn evidence
    assert "user: I have a dog.\nassistant: Nice!" in units
    solo = split_units(span, bigrams=False)
    assert all("\n" not in u for u in solo)


def test_split_units_breaks_long_lines():
    from benchmark.local_gate_eval import split_units
    long_line = "This is one. " * 60  # single 780-char line, no newlines
    units = split_units(long_line, max_unit_chars=200, bigrams=False)
    assert len(units) > 1
    assert all(len(u) <= 220 for u in units)


def test_sent_max_scorer_takes_the_best_unit():
    from benchmark.local_gate_eval import make_sent_max_scorer

    def base(batch):
        # only the exact evidence unit scores high
        return [90.0 if "dog" in prem else 5.0 for prem, _h in batch]

    scorer = make_sent_max_scorer(base, bigrams=False)
    out = scorer([
        ("user: I have a dog.\nassistant: Nice!\nuser: I bake bread.", "User has a dog."),
        ("user: I bake bread.\nassistant: Yum!", "User has a dog."),
    ])
    assert out[0] == 90.0  # max over units finds the dog turn
    assert out[1] == 5.0   # no unit supports it


def test_build_pairs_speaker_naming(tmp_path):
    p = tmp_path / "named.jsonl"
    doc = {"sessions": [{
        "dialogue": [
            {"role": "user", "content": "Hello, remember me?"},
            {"role": "assistant", "content": "Of course."},
        ],
        "memory_points": [
            {"memory_source": "system", "memory_content": "User's name is Ada Lovelace"},
            {"memory_source": "secondary", "memory_content": "Ada Lovelace greeted the assistant."},
        ],
    }]}
    p.write_text(json.dumps(doc) + "\n", encoding="utf-8")
    pairs = build_pairs(p, seed=1, n_clean=5, n_interference=5, n_foreign=0,
                        budget=500, speakers=True)
    spans = "\n".join(x["span"] for x in pairs)
    assert "Ada Lovelace:" in spans
    assert "user:" not in spans


def test_evaluate_reports_per_kind_auroc():
    calib = [{"kind": "clean", "label": 1}, {"kind": "foreign", "label": 0}]
    held = [
        {"kind": "clean", "label": 1},
        {"kind": "interference", "label": 0},
        {"kind": "foreign", "label": 0},
    ]
    r = evaluate(calib, [80.0, 10.0], held, [90.0, 30.0, 10.0])
    assert r["auroc_clean_vs_interference"] == 1.0
    assert r["auroc_clean_vs_foreign"] == 1.0
