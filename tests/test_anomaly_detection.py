"""R11: Anomaly detection on episodes.

Flag episodes that deviate from the dominant pattern:
- Outlier outcome (success in a failure-heavy task family, or vice-versa)
- Outlier token count (3+ stddev above mean for similar tasks)
- Outlier step count
- Outlier creation time gap (sudden burst or silence)

Use case: surface "weird" episodes for human review.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _Ep:
    id: str
    task_text: str
    outcome: str
    tokens_used: int = 0
    num_steps: int = 1
    created_at: float = 0.0


def test_empty_returns_no_anomalies():
    from engram.anomaly_detection import detect_anomalies

    out = detect_anomalies([])
    assert out["anomalies"] == []
    assert out["n_total_scanned"] == 0


def test_outlier_outcome():
    from engram.anomaly_detection import detect_anomalies

    # 10 success on same task family, then 1 failure
    eps = [_Ep(f"e{i}", "exploit CVE-X", "success", tokens_used=100)
           for i in range(10)]
    eps.append(_Ep("anom", "exploit CVE-X", "failure", tokens_used=100))
    out = detect_anomalies(eps, min_cluster_size=3)
    anom_ids = [a["id"] for a in out["anomalies"]]
    assert "anom" in anom_ids


def test_outlier_tokens():
    from engram.anomaly_detection import detect_anomalies

    # 10 eps with ~100 tokens, 1 with 10000
    eps = [_Ep(f"e{i}", "task X", "success", tokens_used=100)
           for i in range(10)]
    eps.append(_Ep("big", "task X", "success", tokens_used=10000))
    out = detect_anomalies(eps, min_cluster_size=3)
    anom_ids = [a["id"] for a in out["anomalies"]]
    assert "big" in anom_ids


def test_no_anomaly_when_homogeneous():
    from engram.anomaly_detection import detect_anomalies

    eps = [_Ep(f"e{i}", "task X", "success", tokens_used=100)
           for i in range(10)]
    out = detect_anomalies(eps, min_cluster_size=3)
    assert out["anomalies"] == []


def test_anomaly_includes_reason():
    from engram.anomaly_detection import detect_anomalies

    eps = [_Ep(f"e{i}", "task X", "success") for i in range(5)]
    eps.append(_Ep("odd", "task X", "failure"))
    out = detect_anomalies(eps, min_cluster_size=3)
    if out["anomalies"]:
        a = out["anomalies"][0]
        assert "reason" in a
        assert a["reason"]


def test_min_cluster_size_filter():
    """Small clusters (< min_cluster_size) shouldn't trigger anomaly checks."""
    from engram.anomaly_detection import detect_anomalies

    eps = [
        _Ep("e1", "rare task", "success"),
        _Ep("e2", "rare task", "failure"),
    ]
    out = detect_anomalies(eps, min_cluster_size=5)
    # Cluster too small → no anomaly even though outcomes differ
    assert out["anomalies"] == []


def test_payload_shape():
    from engram.anomaly_detection import detect_anomalies
    out = detect_anomalies([])
    for k in ("anomalies", "n_total_scanned", "n_clusters_checked"):
        assert k in out
