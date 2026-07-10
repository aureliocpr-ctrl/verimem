"""Gate red-team — adversarial corpus vs the real admission path.

Aurelio mandate 2026-07-10 (pre-revenue): the anti-confab / anti-halluc /
anti-sycophancy gate must be HARD, and proven hard against attack — not just
against the tests that shipped it. This runs a VERSIONED corpus
(``data/gate_redteam_v1.jsonl``, data not code) through the SAME path a real
write takes (``Memory.add``, L1.x + L1.20 semantic), and measures two things
honestly:

  * CATCH-RATE per attack category — of the hostile items, how many the gate
    quarantined/rejected (did NOT admit clean);
  * FALSE-POSITIVE cost — of the benign items, how many the gate wrongly
    quarantined (the number that makes a trust product unusable if too high).

A hostile item is "caught" iff its stored status is NOT ``model_claim``/
``verified`` clean admission (i.e. quarantined or rejected). A benign item is
a false positive iff it was quarantined/rejected. No LLM judge — the verdict
is the store's own final status, so the number is reproducible.

Run: ``python benchmark/gate_redteam.py`` (add ``--out results/x.json``).
Honest by design: it prints the items that SLIPPED (hostile-admitted) and the
FALSE POSITIVES (benign-blocked) so a hole is a to-do, never hidden.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

_DEFAULT_CORPUS = Path(__file__).parent / "data" / "gate_redteam_v1.jsonl"


def load_corpus(path: Path) -> list[dict[str, Any]]:
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items


def _admitted_clean(status: str) -> bool:
    """A clean admission is anything NOT held back by the gate."""
    return status not in ("quarantined", "rejected", "empty")


def evaluate(items: list[dict[str, Any]], *, db_path: Path | None = None
             ) -> dict[str, Any]:
    from engram.client import Memory
    if db_path is None:
        db_path = Path(tempfile.mkdtemp()) / "redteam.db"
    mem = Memory(db_path)

    by_cat: dict[str, dict[str, int]] = defaultdict(
        lambda: {"n": 0, "caught": 0, "hostile": 0, "benign": 0,
                 "false_pos": 0})
    slipped: list[dict[str, Any]] = []      # hostile but admitted clean
    false_pos: list[dict[str, Any]] = []    # benign but blocked

    for it in items:
        res = mem.add(it["proposition"], topic="redteam",
                      verified_by=it.get("verified_by"))
        status = res.get("status", "unknown")
        clean = _admitted_clean(status)
        cat = by_cat[it["cat"]]
        cat["n"] += 1
        row = {"id": it["id"], "cat": it["cat"], "status": status,
               "proposition": it["proposition"][:80]}
        if it["hostile"]:
            cat["hostile"] += 1
            if not clean:
                cat["caught"] += 1
            else:
                slipped.append(row)
        else:
            cat["benign"] += 1
            if not clean:
                cat["false_pos"] += 1
                false_pos.append(row)

    hostile = [i for i in items if i["hostile"]]
    benign = [i for i in items if not i["hostile"]]
    n_caught = sum(c["caught"] for c in by_cat.values())
    n_fp = sum(c["false_pos"] for c in by_cat.values())
    return {
        "corpus_size": len(items),
        "hostile": len(hostile),
        "benign": len(benign),
        "catch_rate": round(n_caught / max(1, len(hostile)), 4),
        "false_positive_rate": round(n_fp / max(1, len(benign)), 4),
        "by_category": {k: dict(v) for k, v in sorted(by_cat.items())},
        "slipped": slipped,        # hostile that got in — the holes to fix
        "false_positives": false_pos,  # benign that got blocked — the FP cost
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(_DEFAULT_CORPUS))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    items = load_corpus(Path(a.corpus))
    report = evaluate(items)

    print(f"corpus: {report['corpus_size']} "
          f"({report['hostile']} hostile, {report['benign']} benign)")
    print(f"CATCH-RATE:          {report['catch_rate']:.1%} "
          f"({sum(c['caught'] for c in report['by_category'].values())}"
          f"/{report['hostile']} hostile caught)")
    print(f"FALSE-POSITIVE rate: {report['false_positive_rate']:.1%} "
          f"({len(report['false_positives'])}"
          f"/{report['benign']} benign blocked)")
    print("\nby category:")
    for cat, c in report["by_category"].items():
        if c["hostile"]:
            print(f"  {cat:26s} caught {c['caught']}/{c['hostile']}")
        else:
            print(f"  {cat:26s} FP {c['false_pos']}/{c['benign']}")
    if report["slipped"]:
        print(f"\n⚠ SLIPPED ({len(report['slipped'])}) — hostile admitted clean:")
        for r in report["slipped"]:
            print(f"    [{r['cat']}] {r['id']}: {r['proposition']}")
    if report["false_positives"]:
        print(f"\n⚠ FALSE POSITIVES ({len(report['false_positives'])}) — benign blocked:")
        for r in report["false_positives"]:
            print(f"    [{r['cat']}] {r['id']}: {r['proposition']}")

    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(report, indent=1, ensure_ascii=False),
                               encoding="utf-8")
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
