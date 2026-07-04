"""Cycle 259 (2026-05-23) — B6 investigation: WHY emergence pipeline pre-set
is empty on resting production corpus.

Hypothesis (cycle 257 finding):
    At adaptive thresholds (purity~0.194, cohesion~0.097) at |V|=2084,
    detect_emerging_skills returns ∅ candidates pre-write. Self-writes
    activate candidates. WHY?

Approach:
    Sweep purity x cohesion threshold matrix on a RESTING safe-copy DB
    (no writes injected). Plot the activation curve: at what threshold
    does the first candidate appear?

If pre-set is empty because thresholds are too strict → activation at
lower thresholds will reveal latent candidates. If pre-set is empty
because the corpus topology itself disallows any community to satisfy
the structural conditions → no threshold will activate candidates.

Output: JSON matrix purity x cohesion -> count + first candidate
appearance.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
from pathlib import Path


def probe(semantic_db_src: Path) -> dict:
    """Sweep emergence thresholds on a safe-copy of the resting corpus."""
    from engram.skill_emergence_detector import detect_emerging_skills

    # Safe-copy production corpus to tempdir
    td = Path(tempfile.mkdtemp(prefix="engram_probe_"))
    db = td / "semantic.db"
    shutil.copy2(semantic_db_src, db)
    print(f"[probe] safe-copy at {db}", file=sys.stderr)

    purity_grid = [0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.60]
    cohesion_grid = [0.02, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30]

    results: list[dict] = []
    t_start = time.time()
    for p in purity_grid:
        for c in cohesion_grid:
            candidates = detect_emerging_skills(
                db,
                min_community_size=4,
                min_topic_purity=float(p),
                min_cohesion=float(c),
                max_n=50,
                seed=42,
            )
            results.append({
                "purity": float(p),
                "cohesion": float(c),
                "count": len(candidates),
                "names": sorted({
                    str(cd.get("suggested_skill_name", ""))
                    for cd in candidates
                    if cd.get("suggested_skill_name")
                })[:5],  # cap at 5 for readability
            })

    # Cleanup
    shutil.rmtree(td, ignore_errors=True)

    # Find the lowest (p, c) at which count > 0
    activation_points = [
        r for r in results if r["count"] > 0
    ]
    first_activation = None
    if activation_points:
        # Sort by (purity desc, cohesion desc) — find LOWEST threshold
        # that gives candidates (= highest p and c that still activate).
        sorted_acts = sorted(
            activation_points,
            key=lambda r: (-r["purity"], -r["cohesion"]),
        )
        first_activation = sorted_acts[0]

    return {
        "n_purity": len(purity_grid),
        "n_cohesion": len(cohesion_grid),
        "matrix": results,
        "first_activation_point": first_activation,
        "elapsed_s": float(time.time() - t_start),
    }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--semantic-db",
        type=Path,
        default=Path.home() / ".engram" / "semantic" / "semantic.db",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if not args.semantic_db.exists():
        print(f"[error] DB not found: {args.semantic_db}", file=sys.stderr)
        return 1

    result = probe(args.semantic_db)
    payload = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
