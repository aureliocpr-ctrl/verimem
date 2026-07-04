"""TDD for benchmark/epistemic_harness.py — multi-seed/model aggregation."""
from __future__ import annotations

from benchmark.epistemic_harness import summarize_auroc


def _run(seed, model, rows):  # noqa: ANN001
    return {"seed": seed, "model": model, "rows": rows}


# rows shaped like a write-path bench: {"label": 0/1, "score": float}
def _sep_rows():
    return [{"label": 1, "score": 90}, {"label": 1, "score": 85},
            {"label": 0, "score": 10}, {"label": 0, "score": 20}]


def test_pooled_and_perrun_separable() -> None:
    runs = [_run(0, "sonnet", _sep_rows()), _run(1, "sonnet", _sep_rows())]
    out = summarize_auroc(runs, score_fn=lambda r: r["score"], label_fn=lambda r: r["label"])
    assert out["n_cells"] == 2
    assert out["pooled_auroc"] == 1.0
    assert out["mean_auroc"] == 1.0
    assert out["std_auroc"] == 0.0
    assert out["ci95"][0] <= 1.0 <= out["ci95"][1] + 1e-9
    assert out["n_pooled"] == 8


def test_cross_cell_spread_is_reported() -> None:
    good = _sep_rows()
    bad = [{"label": 1, "score": 10}, {"label": 1, "score": 20},
           {"label": 0, "score": 90}, {"label": 0, "score": 85}]  # inverted -> AUROC 0
    out = summarize_auroc([_run(0, "a", good), _run(1, "b", bad)],
                          score_fn=lambda r: r["score"], label_fn=lambda r: r["label"])
    aucs = sorted(p["auroc"] for p in out["per_run"])
    assert aucs == [0.0, 1.0]
    assert out["mean_auroc"] == 0.5
    assert out["std_auroc"] > 0.0
    assert out["min_cell_auroc"] == 0.0


def test_row_filter_applied() -> None:
    rows = _sep_rows() + [{"label": 2, "score": 50}]  # a 3rd-class row to filter out
    out = summarize_auroc([_run(0, "m", rows)], score_fn=lambda r: r["score"],
                          label_fn=lambda r: r["label"], row_filter=lambda r: r["label"] in (0, 1))
    assert out["n_pooled"] == 4
    assert out["pooled_auroc"] == 1.0
