"""Selective-prediction DEPLOYMENT metrics at declared λ operating points.

The gap this run closes (Oxford 2603.21172 via the cortex research bridge,
action #1): our published AUROC (0.9916, external_readpath heldout) says the
relevance scores DISCRIMINATE; it does not say the store OPERATES at the
declared risk when the operator sets the SLA knob λ (`engram/sla.py` — whose
own docstring declares the score→P(correct) mapping "a separate, validated
wiring step, NOT asserted here"). This is that step, measured:

  * E-AURC on the held-out split (excess over the oracle ranking);
  * TCE at λ ∈ {0.5, 1, 3, 9} on RAW e5 relevance scores — expected to be bad
    (the e5 band is compressed: scores are not probabilities), reported
    honestly, inoperable points DECLARED;
  * the same table after a pure PAV isotonic calibration FIT ON DEV ONLY
    (the fixer never reads the eval split) and applied held-out — does a
    simple monotone map make the λ knob operate at its declared risk?

Protocol facts: same store/build/retrieval as external_readpath (real gate,
real embedder, one retrieval pass per query); correct = retrieval-hit@k
(id-decidable, the harness's existing proxy); unanswerable queries count as
records with correct=False (answering one is a false answer). Dev and heldout
use DISJOINT item and unanswerable ranges, declared below.

    python -m benchmark.selective_deployment
"""
from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Any

from benchmark.external_readpath import build_store, load_split
from engram.selective_metrics import (
    aurc,
    e_aurc,
    isotonic_fit,
    tce_at_lambda,
)

RESULTS_DIR = Path(__file__).parent / "results"
LAMBDAS = (0.5, 1.0, 3.0, 9.0)


def collect_records(items: list[dict], unans_questions: list[str],
                    db_path: Path, *, k: int = 5,
                    ) -> tuple[list[tuple[float, bool]], dict[str, Any]]:
    """One store build + one retrieval pass per query → selective records
    (confidence=top relevance score, correct). Blocked ingests are honest
    misses (score 0.0, wrong) — same accounting as the readpath harness."""
    mem, fact_ids, ingest = build_store(items, db_path)
    records: list[tuple[float, bool]] = []
    for item, fid in zip(items, fact_ids):
        if fid is None:
            records.append((0.0, False))
            continue
        hits = mem.search(item["question"], k=k)
        top = max((h.get("score", 0.0) for h in hits), default=0.0)
        records.append((top, any(h.get("id") == fid for h in hits)))
    for q in unans_questions:
        hits = mem.search(q, k=k)
        top = max((h.get("score", 0.0) for h in hits), default=0.0)
        records.append((top, False))          # answering unanswerable = wrong
    return records, ingest


def lambda_table(records: list[tuple[float, bool]]) -> list[dict[str, Any]]:
    return [
        {k: (round(v, 4) if isinstance(v, float) else v)
         for k, v in tce_at_lambda(records, lam).items()}
        for lam in LAMBDAS
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()

    # DISJOINT splits, declared: dev = dev items + unanswerable[:50];
    # heldout = heldout items + unanswerable[50:150].
    dev_items = load_split("dev")
    held_items = load_split("heldout")
    unans_all = [r["question"] for r in load_split("unanswerable")]
    unans_dev, unans_held = unans_all[:50], unans_all[50:150]

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        td = Path(td)
        dev_records, dev_ingest = collect_records(
            dev_items, unans_dev, td / "dev.db", k=args.k)
        held_records, held_ingest = collect_records(
            held_items, unans_held, td / "held.db", k=args.k)

    cal = isotonic_fit(dev_records)            # fit on DEV ONLY
    held_cal = [(cal(c), ok) for c, ok in held_records]

    report = {
        "dataset": "HaluEval qa (MIT), external_readpath splits",
        "protocol": {
            "correct": "retrieval-hit@k (id-decidable)",
            "k": args.k,
            "dev": {"n_answerable": len(dev_items),
                    "n_unanswerable": len(unans_dev), "ingest": dev_ingest},
            "heldout": {"n_answerable": len(held_items),
                        "n_unanswerable": len(unans_held),
                        "ingest": held_ingest},
            "calibration": "isotonic (pure PAV) fit on dev records only",
            "note": "raw confidences are e5 relevance scores, NOT probabilities"
                    " — that mismatch is exactly what TCE measures",
        },
        "heldout_raw": {
            "aurc": round(aurc(held_records), 4),
            "e_aurc": round(e_aurc(held_records), 4),
            "tce_at_lambda": lambda_table(held_records),
        },
        "heldout_calibrated": {
            "aurc": round(aurc(held_cal), 4),
            "e_aurc": round(e_aurc(held_cal), 4),
            "tce_at_lambda": lambda_table(held_cal),
        },
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    print(json.dumps(report, indent=2))
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"selective_deployment_{time.strftime('%Y-%m-%d')}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
