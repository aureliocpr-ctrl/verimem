"""Phase-0 rigor harness: aggregate experiment runs across seeds/models with CIs.

The structural fix for the program's #1 weakness (single-seed, single-model, no CI). Any
experiment that produces per-row (score, label) results is fed here and comes out as a
standard, defensible summary: per-cell AUROC, a POOLED bootstrap CI over all rows, and the
mean±std of AUROC across cells. So a headline stops being "0.971 on one seed/one model" and
becomes "0.97 ± std, CI [lo, hi], over S seeds × M models, n pooled".

Pure: takes already-computed run dicts (each ``{"seed","model","rows":[...]}``) plus
extractor callables. No LLM here — the caller runs the benches (optionally in parallel) and
hands the results in. Uses ``benchmark.stats`` for all statistics.
"""
from __future__ import annotations

import math
import statistics
from collections.abc import Callable
from typing import Any

from benchmark.stats import auroc, bootstrap_ci


def summarize_auroc(
    runs: list[dict[str, Any]], *,
    score_fn: Callable[[dict], float],
    label_fn: Callable[[dict], int],
    row_filter: Callable[[dict], bool] | None = None,
    b: int = 4000, seed: int = 0,
) -> dict[str, Any]:
    """Aggregate AUROC across runs. ``runs`` = list of ``{"seed","model","rows":[...]}``.

    Returns a standard schema: per_run cells, pooled AUROC + bootstrap CI over ALL rows,
    and mean±std of the per-cell AUROCs (the cross-condition spread that single-seed hides).
    """
    per_run: list[dict[str, Any]] = []
    pooled_scores: list[float] = []
    pooled_labels: list[int] = []
    for r in runs:
        rows = [row for row in r.get("rows", []) if (row_filter is None or row_filter(row))]
        s = [float(score_fn(row)) for row in rows]
        y = [int(label_fn(row)) for row in rows]
        cell_auc = auroc(s, y) if rows else float("nan")
        per_run.append({"seed": r.get("seed"), "model": r.get("model"),
                        "auroc": (round(cell_auc, 3) if not math.isnan(cell_auc) else None),
                        "n": len(s)})
        pooled_scores.extend(s)
        pooled_labels.extend(y)
    point, lo, hi = bootstrap_ci(pooled_scores, pooled_labels, b=b, seed=seed)
    cell_aucs = [p["auroc"] for p in per_run if p["auroc"] is not None]
    return {
        "per_run": per_run,
        "n_cells": len(per_run),
        "pooled_auroc": round(point, 3) if not math.isnan(point) else None,
        "ci95": [round(lo, 3), round(hi, 3)] if not math.isnan(lo) else None,
        "n_pooled": len(pooled_scores),
        "mean_auroc": round(statistics.mean(cell_aucs), 3) if cell_aucs else None,
        "std_auroc": (round(statistics.pstdev(cell_aucs), 3) if len(cell_aucs) > 1 else 0.0),
        "min_cell_auroc": round(min(cell_aucs), 3) if cell_aucs else None,
    }


def load_runs(specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Load run dicts from JSON files. ``specs`` = ``[{"path","seed","model"}]``; the file's
    ``rows`` are attached. Missing/empty files are skipped (so partial matrices still summarize)."""
    import json
    from pathlib import Path
    out: list[dict[str, Any]] = []
    for sp in specs:
        p = Path(sp["path"])
        if not p.exists() or p.stat().st_size == 0:
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        out.append({"seed": sp.get("seed"), "model": sp.get("model"),
                    "rows": d.get("rows", [])})
    return out


__all__ = ["summarize_auroc", "load_runs"]
