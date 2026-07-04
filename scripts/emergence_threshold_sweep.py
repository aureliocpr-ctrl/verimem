"""Cycle 240 (2026-05-23) — exploratory threshold sweep for emergence detector.

The default cycle-219 / 230 / 235 threshold (purity≥0.4, cohesion≥0.2)
on the live corpus surfaces ONLY ONE candidate
(``emerging_skill_master-fact``).  This script systematically probes
weaker thresholds to quantify the "shadow zone" — communities that
exist topologically but don't yet cross the default emergence floor.

Output: a purity × cohesion matrix of candidate counts + top-3 names
per cell.  Useful for tuning the cycle-219 defaults to corpus growth
without changing code.

Usage::

    python -m scripts.emergence_threshold_sweep [--db PATH] [--out FILE]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def sweep(db_path: Path) -> dict:
    """Run the detector with a grid of (purity, cohesion) thresholds."""
    from engram.skill_emergence_detector import detect_emerging_skills

    purities = [0.6, 0.5, 0.4, 0.3, 0.2, 0.1]
    cohesions = [0.3, 0.2, 0.1, 0.05]
    grid: list[dict] = []
    for p in purities:
        for c in cohesions:
            cands = detect_emerging_skills(
                db_path,
                min_community_size=4,
                min_topic_purity=p,
                min_cohesion=c,
                max_n=10,
            )
            grid.append({
                "purity": p,
                "cohesion": c,
                "n_candidates": len(cands),
                "top_names": [
                    str(c.get("suggested_skill_name", ""))
                    for c in cands[:3]
                ],
                "top_evidence": [
                    {
                        "name": str(c.get("suggested_skill_name", "")),
                        "size": int(c.get("size", 0)),
                        "purity": float(c.get("topic_purity", 0.0)),
                        "cohesion": float(c.get("cohesion", 0.0)),
                    }
                    for c in cands[:3]
                ],
            })
    return {"db_path": str(db_path), "grid": grid}


def render(result: dict) -> str:
    lines = [
        "=" * 70,
        "Emergence detector threshold sweep (cycle 240)",
        f"db: {result['db_path']}",
        "=" * 70,
        "",
        "rows = min_topic_purity, cols = min_cohesion",
        "",
    ]
    cohesions = sorted({g["cohesion"] for g in result["grid"]}, reverse=True)
    purities = sorted({g["purity"] for g in result["grid"]}, reverse=True)
    header = "purity ↓ / cohesion → " + "  ".join(
        f"{c:>5.2f}" for c in cohesions
    )
    lines.append(header)
    lines.append("-" * len(header))
    for p in purities:
        row = [f"{p:>5.2f}              "]
        for c in cohesions:
            entry = next(
                g for g in result["grid"]
                if g["purity"] == p and g["cohesion"] == c
            )
            row.append(f"{entry['n_candidates']:>5d}")
        lines.append("  ".join(row))
    lines.append("")
    # Surface notable candidates from the loosest cell.
    loosest = max(result["grid"], key=lambda g: g["n_candidates"])
    lines.append(
        f"Loosest cell: purity={loosest['purity']}, "
        f"cohesion={loosest['cohesion']} → "
        f"{loosest['n_candidates']} candidates",
    )
    for e in loosest["top_evidence"]:
        lines.append(
            f"  {e['name']}  size={e['size']} "
            f"purity={e['purity']:.2f} cohesion={e['cohesion']:.2f}",
        )
    lines.append("=" * 70)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        default=str(Path.home() / ".engram" / "semantic" / "semantic.db"),
    )
    parser.add_argument(
        "--out",
        default=str(
            Path.home() / ".engram" / "emergence_threshold_sweep.json",
        ),
    )
    args = parser.parse_args(argv)
    db = Path(args.db)
    if not db.exists():
        print(f"db not found: {db}", file=sys.stderr)
        return 2
    result = sweep(db)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(render(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
