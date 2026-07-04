"""FORGIA pezzo #258 — Wave 57: metrics export CSV/JSON.

Dump per-day metrics in CSV or JSON for external dashboards.
Useful per spreadsheet analysis or piping into Grafana/Prometheus
exporters.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass


@dataclass
class _FakeEp:
    outcome: str = "success"
    tokens_used: int = 0
    created_at: float = 0.0


def _eps_for_days(n_days: int, eps_per_day: int = 3):
    now = time.time()
    out = []
    for d in range(n_days):
        for _ in range(eps_per_day):
            out.append(_FakeEp(
                outcome="success",
                tokens_used=100,
                created_at=now - d * 86400.0,
            ))
    return out


def test_csv_format_default():
    from engram.metrics_export import export_metrics

    out = export_metrics(episodes=[], format="csv")
    assert isinstance(out, str)
    # CSV must have a header line.
    assert "date" in out.split("\n")[0].lower()


def test_json_format():
    from engram.metrics_export import export_metrics

    out = export_metrics(episodes=[], format="json")
    parsed = json.loads(out)
    assert isinstance(parsed, list)


def test_csv_lines_match_days():
    from engram.metrics_export import export_metrics

    eps = _eps_for_days(3, eps_per_day=2)
    out = export_metrics(episodes=eps, format="csv", window_days=7)
    lines = [line for line in out.split("\n") if line.strip()]
    # Header + 3 day rows.
    assert len(lines) == 4


def test_window_filters_old_episodes():
    from engram.metrics_export import export_metrics

    now = time.time()
    eps = [
        _FakeEp("success", 100, now),
        _FakeEp("success", 100, now - 86400 * 100),  # outside window
    ]
    out = export_metrics(episodes=eps, format="json", window_days=7)
    parsed = json.loads(out)
    assert len(parsed) == 1


def test_csv_includes_columns():
    from engram.metrics_export import export_metrics

    eps = _eps_for_days(1, eps_per_day=1)
    out = export_metrics(episodes=eps, format="csv")
    header = out.split("\n")[0]
    for col in ("date", "n_success", "n_failure", "tokens"):
        assert col in header


def test_json_records_have_required_keys():
    from engram.metrics_export import export_metrics

    eps = _eps_for_days(1, eps_per_day=2)
    out = export_metrics(episodes=eps, format="json")
    parsed = json.loads(out)
    if parsed:
        for k in ("date", "n_success", "n_failure", "tokens"):
            assert k in parsed[0]
