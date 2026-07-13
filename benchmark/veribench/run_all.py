"""VeriBench — one reproducible entrypoint for the whole result.

    python -m benchmark.veribench.run_all              # full (n=200), both corpora
    python -m benchmark.veribench.run_all --n 10       # fast smoke of the wiring

Runs, in order, and consolidates into one report:
  1. the real run (verimem vs a no-abstention baseline vs a scrambled validity
     control) on HaluEval — the pre-registered H1 check;
  2. the mem0 head-to-head (real, offline, same e5) on HaluEval AND SQuAD v2 —
     each system at its own oracle floor.

A single command so anyone can reproduce every number in README.md from scratch.
Deterministic (fixed splits + seeds, model-free scoring). Needs the corpora built
(`external_readpath --make-samples` and `make_squad_corpus`); it builds SQuAD on
demand if missing.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from . import run_mem0, run_real

_RESULTS = Path(__file__).resolve().parents[1] / "results"


def _ensure_squad() -> None:
    from benchmark.external_readpath import DATA_DIR
    if not (DATA_DIR / "squad_v2_heldout.jsonl").exists():
        from benchmark.make_squad_corpus import build
        build()


def run(*, n: int, tau: float, k: int) -> dict:
    _ensure_squad()
    out: dict = {"benchmark": "VeriBench/run_all", "n": n, "tau": tau, "k": k,
                 "parts": {}}
    out["parts"]["real_halueval"] = run_real.run(
        n=n, tau=tau, k=k, corpus="halueval_qa")
    out["parts"]["mem0_halueval"] = run_mem0.run(
        n=n, tau=tau, k=k, corpus="halueval_qa")
    out["parts"]["mem0_squad_v2"] = run_mem0.run(
        n=n, tau=tau, k=k, corpus="squad_v2")
    return out


def _one_liners(out: dict) -> list[str]:
    lines = []
    for name, part in out["parts"].items():
        for sysname, sc in part["systems"].items():
            rk = round(sc["correct"] / sc["n"], 3) if sc["n"] else 0.0
            lines.append(f"{name:<16} {sysname:<20} cover={sc['coverage']:.2f} "
                         f"r@k={rk:.3f} NET5={sc['net']['lambda_5']:+.3f}")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--tau", type=float, default=0.80)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if not run_mem0.mz.mem0_available():
        raise SystemExit("mem0 / chromadb not installed — cannot run the "
                         "head-to-head parts.")
    out = run(n=args.n, tau=args.tau, k=args.k)
    print("\n=== VeriBench/run_all — every headline number, one command ===")
    for line in _one_liners(out):
        print(line)

    dest = Path(args.out) if args.out else (
        _RESULTS / f"veribench_run_all_{time.strftime('%Y-%m-%d')}.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nsaved -> {dest}")


if __name__ == "__main__":
    main()
