"""R48: Top outlier episode summary."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class _Ep:
    id: str
    task_text: str
    outcome: str
    tokens_used: int = 0


def test_empty_returns_empty():
    from engram.outlier_summary import summarize_top_outliers
    out = summarize_top_outliers([])
    assert out["outliers"] == []


def test_outlier_with_explanation():
    from engram.outlier_summary import summarize_top_outliers
    eps = [
        _Ep(f"e{i}", "task X", "success", 100) for i in range(10)
    ]
    eps.append(_Ep("anom", "task X", "failure", 10000))
    out = summarize_top_outliers(eps)
    if out["outliers"]:
        first = out["outliers"][0]
        assert "explanation" in first
        assert first["id"] == "anom"


def test_top_k_limit():
    from engram.outlier_summary import summarize_top_outliers
    eps = [_Ep(f"e{i}", "X", "success", 100) for i in range(5)]
    eps += [_Ep(f"o{i}", "X", "failure", 10000) for i in range(10)]
    out = summarize_top_outliers(eps, top_k=3)
    assert len(out["outliers"]) <= 3


def test_payload_shape():
    from engram.outlier_summary import summarize_top_outliers
    out = summarize_top_outliers([])
    for k in ("outliers", "n_total_scanned"):
        assert k in out


def test_entry_keys():
    from engram.outlier_summary import summarize_top_outliers
    eps = [_Ep(f"e{i}", "X", "success") for i in range(5)]
    eps.append(_Ep("anom", "X", "failure"))
    out = summarize_top_outliers(eps)
    if out["outliers"]:
        for k in ("id", "task_text", "explanation"):
            assert k in out["outliers"][0]
