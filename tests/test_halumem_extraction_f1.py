"""Guards for the Extraction-F1 harness pure logic: the embedding precision/recall/F1
matcher and the gold/dialogue extractors. Hermetic — _embed_matrix is monkeypatched with
controlled unit vectors, so no model load and the matcher math is asserted exactly."""
from __future__ import annotations

import numpy as np

import benchmark.halumem_extraction_f1 as E


def _ortho(label_to_vec):
    """Return an _embed_matrix stub mapping each text to a fixed unit vector."""
    def _stub(texts):
        if not texts:
            return np.zeros((0, len(next(iter(label_to_vec.values())))), dtype=np.float32)
        return np.stack([label_to_vec[t] for t in texts])
    return _stub


def test_prf_perfect_match(monkeypatch):
    v = {"a": np.array([1.0, 0.0]), "b": np.array([0.0, 1.0])}
    monkeypatch.setattr(E, "_embed_matrix", _ortho(v))
    p, r, f1, n = E._prf(["a", "b"], ["a", "b"], thr=0.9)
    assert (p, r, f1, n) == (1.0, 1.0, 1.0, 2)


def test_prf_half_precision(monkeypatch):
    # pred = [a (matches gold a), c (matches nothing)] ; gold = [a]
    v = {"a": np.array([1.0, 0.0]), "c": np.array([0.0, 1.0])}
    monkeypatch.setattr(E, "_embed_matrix", _ortho(v))
    p, r, f1, n = E._prf(["a", "c"], ["a"], thr=0.9)
    assert p == 0.5 and r == 1.0 and n == 2  # 1 of 2 preds precise; the 1 gold recalled


def test_prf_half_recall(monkeypatch):
    # pred = [a] ; gold = [a, b] -> recalls 1 of 2
    v = {"a": np.array([1.0, 0.0]), "b": np.array([0.0, 1.0])}
    monkeypatch.setattr(E, "_embed_matrix", _ortho(v))
    p, r, f1, n = E._prf(["a"], ["a", "b"], thr=0.9)
    assert p == 1.0 and r == 0.5


def test_prf_empty_pred_is_zero(monkeypatch):
    monkeypatch.setattr(E, "_embed_matrix", _ortho({"a": np.array([1.0, 0.0])}))
    assert E._prf([], ["a"], thr=0.9) == (0.0, 0.0, 0.0, 0)


def test_gold_and_session_extractors():
    session = {
        "memory_points": [{"memory_content": "User likes tea"}, {"memory_content": ""},
                          {"memory_content": "  User is from Rome  "}],
        "dialogue": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": ""}],
    }
    assert E._gold_facts(session) == ["User likes tea", "User is from Rome"]
    txt = E._session_text(session)
    assert "user: hi" in txt and txt.count("\n") == 0  # empty turn skipped
