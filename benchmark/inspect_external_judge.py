"""Inspect external-judge sweep misses: which confabs did the judge admit,
and are they judge misses or dataset-label noise? Prints each label=0 row with
score >= threshold next to its source/claim so the failure class is visible.

    python -m benchmark.inspect_external_judge benchmark/results/moat_external_judge_sonnet_2026-07-17.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from benchmark.moat_external_judge import _LOADERS


def main() -> int:
    res = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    seed = res.get("seed", 42)
    thr = res["threshold"]
    for corpus, r in res["per_corpus"].items():
        pairs = _LOADERS[corpus](len(r["rows"]), seed)
        assert len(pairs) == len(r["rows"]), (corpus, len(pairs), len(r["rows"]))
        print(f"\n=== {corpus}: label=0 scored >= {thr} (admitted confabs) ===")
        n = 0
        for p, row in zip(pairs, r["rows"]):
            if row["label"] == 0 and row["score"] >= thr:
                n += 1
                src = p["source"].replace("\n", " / ")
                print(f"[{n}] score={row['score']}")
                print(f"    SRC: {src[:220]}")
                print(f"    CLM: {p['claim'][:220]}")
        print(f"  -> {n} admitted confabs / {r['n_neg']}")
        print(f"\n=== {corpus}: label=1 scored < {thr} (rejected faithful) ===")
        n = 0
        for p, row in zip(pairs, r["rows"]):
            if row["label"] == 1 and row["score"] < thr:
                n += 1
                src = p["source"].replace("\n", " / ")
                print(f"[{n}] score={row['score']}")
                print(f"    SRC: {src[:220]}")
                print(f"    CLM: {p['claim'][:220]}")
        print(f"  -> {n} rejected faithful / {r['n_pos']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
