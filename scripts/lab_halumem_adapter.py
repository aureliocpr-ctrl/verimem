"""Cycle 173 (2026-05-22) — HaluMem benchmark adapter (skeleton).

Closes the gap flagged by paper #60 §5: the previous draft cited this
file as a stub but the file did not exist on the branch. This is the
actual skeleton — runnable end-to-end on a synthetic sample, with a
clearly-marked code path that ingests the real HaluMem JSONL when
the dataset is available locally.

What this file IS:
  • A reproducible adapter from HaluMem record shape ↦ the inputs
    that ``run_validation_gate`` expects (proposition + optional
    verified_by + topic).
  • A confusion-matrix scorer that compares the gate's action
    against HaluMem's ``memory_source`` label, with the contract:
    - memory_source == "interference" → expect downgrade or reject
                                          (gate-positive)
    - memory_source ∈ {primary, secondary, system} → expect persist
                                                      (gate-negative)
  • A synthetic 6-record sample (``_SAMPLE``) so the script and its
    integration test run with zero external data.

What this file IS NOT (honestly):
  • The full live HaluMem result. HaluMem (arXiv:2511.03506) ships
    ~15k memory points × ~3.5k QA pairs that must be downloaded
    separately (HF dataset ``IAAR-Shanghai/HaluMem``, requires HF
    token or anonymous access — both gated by network). The
    ``--jsonl`` flag accepts any compatible JSONL on disk so a
    user with the dataset can re-run.
  • A definitive TPR/FPR number for the paper. The sample is too
    small (n=6) for statistical claims; it exists to prove the
    pipeline.

Reference: docs/papers/write-time-confabulation-gates-DRAFT.md §5.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Add repo root so this script works invoked as ``python scripts/...``.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engram.anti_confab_gate import run_validation_gate  # noqa: E402

# ----------------------------------------------------------------------
# HaluMem record schema (best-effort — the published paper does not
# pin a JSON schema; we follow the field names used in the HF dataset
# preview as of 2025-11). Fields we DO use:
#   - "proposition" or "content" or "text": the claim to gate.
#   - "verified_by": optional list of refs (HaluMem may not provide).
#   - "topic": optional topic hint.
#   - "memory_source": one of {primary, secondary, interference, system}.
# Unknown fields are tolerated.
# ----------------------------------------------------------------------


_PROP_KEYS = ("proposition", "content", "text", "claim")
_VBY_KEYS = ("verified_by", "evidence", "refs")
_TOPIC_KEYS = ("topic", "category", "domain")
_LABEL_KEYS = ("memory_source", "label", "source")


def _first_present(rec: dict, keys: Iterable[str], default: Any = None) -> Any:
    for k in keys:
        if k in rec and rec[k] is not None:
            return rec[k]
    return default


@dataclass
class AdapterRecord:
    """Normalized HaluMem record after key-mapping."""
    proposition: str
    verified_by: list[str]
    topic: str | None
    label: str  # one of: primary | secondary | interference | system
    raw: dict


def normalize(rec: dict) -> AdapterRecord | None:
    """Map a raw HaluMem JSON record to our canonical shape. Returns
    ``None`` when the record lacks a proposition or a label (skip)."""
    prop = _first_present(rec, _PROP_KEYS)
    if not prop or not isinstance(prop, str):
        return None
    vby = _first_present(rec, _VBY_KEYS, default=[])
    if isinstance(vby, str):
        vby = [vby]
    if not isinstance(vby, list):
        vby = []
    label_raw = _first_present(rec, _LABEL_KEYS)
    if label_raw is None:
        return None
    label = str(label_raw).lower().strip()
    if label not in {"primary", "secondary", "interference", "system"}:
        return None
    topic = _first_present(rec, _TOPIC_KEYS)
    return AdapterRecord(
        proposition=prop.strip(),
        verified_by=[str(v) for v in vby],
        topic=str(topic) if topic else None,
        label=label,
        raw=rec,
    )


# A small synthetic sample that exercises every label class. Real
# HaluMem records are denser; this is a smoke set so the pipeline can
# be validated with zero data downloads.
_SAMPLE: list[dict] = [
    {  # interference: shipped without anchor → gate should downgrade
        "proposition": "Cycle 200 SHIPPED to main on 2026-01-01",
        "verified_by": [],
        "memory_source": "interference",
    },
    {  # interference: diagnosis without test ref → downgrade
        "proposition": "BUG #42 ROOT CAUSE is misaligned indexing",
        "verified_by": [],
        "memory_source": "interference",
    },
    {  # primary: clean factual claim → persist
        "proposition": "The capital of France is Paris.",
        "verified_by": [],
        "memory_source": "primary",
    },
    {  # primary: shipped WITH anchor → persist
        "proposition": "Cycle 171 SHIPPED to main on 2026-05-22",
        "verified_by": ["commit:5be3495", "pr:#112"],
        "memory_source": "primary",
    },
    {  # system: meta config row → persist
        "proposition": "Default embedding dim is 384.",
        "verified_by": [],
        "memory_source": "system",
    },
    {  # secondary: paraphrase of primary → persist
        "proposition": "Paris serves as France's capital city.",
        "verified_by": [],
        "memory_source": "secondary",
    },
]


def load_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def expected_gate_action(label: str) -> str:
    """Per the adapter's contract: interference is the gate-positive
    class; all other labels are gate-negative (should persist)."""
    return "downgrade" if label == "interference" else "persist"


@dataclass
class Outcome:
    label: str
    expected: str
    actual: str
    correct: bool
    latency_ms: float
    warnings: list[dict[str, Any]]


def score(records: list[AdapterRecord], *, validate: str = "fast",
          gate_mode: str = "downgrade") -> tuple[list[Outcome], dict]:
    """Run every record through the gate, return outcomes + summary."""
    outcomes: list[Outcome] = []
    for r in records:
        t0 = time.perf_counter()
        # Pure mode: no agent → L3 is a no-op, L1/L1.5/L1.7 still fire.
        res = run_validation_gate(
            proposition=r.proposition,
            verified_by=r.verified_by,
            topic=r.topic,
            agent=None,
            validate=validate,
            gate_mode=gate_mode,
        )
        dt = (time.perf_counter() - t0) * 1000.0
        expected = expected_gate_action(r.label)
        # Gate's "reject" counts as a stronger form of "downgrade" for
        # this contract; both are gate-positive.
        actual_norm = "downgrade" if res.action in ("downgrade", "reject") else res.action
        outcomes.append(Outcome(
            label=r.label,
            expected=expected,
            actual=actual_norm,
            correct=(actual_norm == expected),
            latency_ms=dt,
            warnings=list(res.warnings or []),
        ))
    summary = {
        "n": len(outcomes),
        "n_correct": sum(1 for o in outcomes if o.correct),
        "accuracy": (
            sum(1 for o in outcomes if o.correct) / max(1, len(outcomes))
        ),
        "p50_ms": (
            statistics.median(o.latency_ms for o in outcomes)
            if outcomes else 0.0
        ),
    }
    # Confusion matrix on the interference-vs-rest binary task.
    tp = sum(1 for o in outcomes if o.label == "interference" and o.actual == "downgrade")
    fn = sum(1 for o in outcomes if o.label == "interference" and o.actual == "persist")
    fp = sum(1 for o in outcomes if o.label != "interference" and o.actual == "downgrade")
    tn = sum(1 for o in outcomes if o.label != "interference" and o.actual == "persist")
    summary["confusion"] = {"tp": tp, "fn": fn, "fp": fp, "tn": tn}
    summary["tpr"] = tp / max(1, tp + fn)
    summary["fpr"] = fp / max(1, fp + tn)
    return outcomes, summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", type=Path, default=None,
                    help="Path to a local HaluMem-shaped JSONL. "
                         "When omitted, the built-in 6-record sample is "
                         "used (smoke pipeline only — NOT a real benchmark).")
    ap.add_argument("--validate", choices=("off", "fast", "full"),
                    default="fast")
    ap.add_argument("--gate-mode", choices=("downgrade", "reject"),
                    default="downgrade")
    ap.add_argument("--out", type=Path, default=None,
                    help="Optional JSON output path.")
    args = ap.parse_args(argv)

    if args.jsonl is None:
        raw = _SAMPLE
        source = "<built-in synthetic 6-record sample>"
    else:
        raw = load_jsonl(args.jsonl)
        source = str(args.jsonl)

    records = [r for r in (normalize(x) for x in raw) if r is not None]
    if not records:
        print("No usable records found.")
        return 1

    outcomes, summary = score(
        records, validate=args.validate, gate_mode=args.gate_mode,
    )

    print("HaluMem adapter — cycle 173 skeleton")
    print(f"  source       : {source}")
    print(f"  n            : {summary['n']}")
    print(f"  accuracy     : {summary['accuracy']:.3f}")
    print(f"  p50 latency  : {summary['p50_ms']:.2f} ms")
    print(f"  confusion    : {summary['confusion']}")
    print(f"  TPR          : {summary['tpr']:.3f}")
    print(f"  FPR          : {summary['fpr']:.3f}")
    if args.jsonl is None:
        print("  NOTE: numbers from synthetic sample only; "
              "not a paper-citable benchmark.")

    if args.out is not None:
        report = {
            "summary": summary,
            "outcomes": [
                {
                    "label": o.label, "expected": o.expected,
                    "actual": o.actual, "correct": o.correct,
                    "latency_ms": o.latency_ms,
                    "warnings": o.warnings,
                }
                for o in outcomes
            ],
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(report, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"  wrote        : {args.out}")
    return 0


# Re-export for `from scripts.lab_halumem_adapter import ...`.
__all__ = [
    "AdapterRecord", "Outcome",
    "expected_gate_action", "load_jsonl", "main", "normalize", "score",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
