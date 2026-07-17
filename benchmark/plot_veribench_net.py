"""Render the NET(λ) figure for the VeriBench preprint from the committed
result JSONs. NET(λ) = (correct − λ·wrong)/n is linear in λ, so each system is a
straight line drawn from its own (correct, wrong, n); nothing is hand-plotted.
Output: docs/papers/figures/net_lambda_halueval.{png,pdf}.

    python -m benchmark.plot_veribench_net
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).parent
RES = ROOT / "results"
OUT = ROOT.parent / "docs" / "papers" / "figures"


def _net(correct: float, wrong: float, n: float, lam: np.ndarray) -> np.ndarray:
    return (correct - lam * wrong) / n


def main() -> None:
    halu = json.loads((RES / "veribench_mem0_halueval-qa_2026-07-13.json")
                      .read_text(encoding="utf-8"))["systems"]
    real = json.loads((RES / "veribench_real_halueval-qa_2026-07-13.json")
                      .read_text(encoding="utf-8"))["systems"]

    lam = np.linspace(1, 10, 200)
    # (label, correct, wrong, n, style) — every number read from the JSON
    series = [
        ("Verimem · floor τ=0.8 (default)",
         halu["verimem_tau"]["correct"], halu["verimem_tau"]["wrong"],
         halu["verimem_tau"]["n"], dict(color="#2E6B4F", lw=2.4)),
        ("mem0 · bolted floor 0.75 (tuned on eval)",
         halu["mem0_best_floor"]["correct"], halu["mem0_best_floor"]["wrong"],
         halu["mem0_best_floor"]["n"], dict(color="#6A8CAF", lw=1.8, ls="--")),
        ("mem0 · as shipped (no floor)",
         halu["mem0_as_shipped"]["correct"], halu["mem0_as_shipped"]["wrong"],
         halu["mem0_as_shipped"]["n"], dict(color="#B8742E", lw=1.8)),
        ("Same store, floor OFF (control)",
         real["no_abstention_baseline"]["correct"],
         real["no_abstention_baseline"]["wrong"],
         real["no_abstention_baseline"]["n"], dict(color="#A03030", lw=1.4, ls=":")),
    ]

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    for label, c, w, n, style in series:
        ax.plot(lam, _net(c, w, n, lam), label=label, **style)
    ax.axhline(0, color="#444", lw=0.9)
    ax.set_xlabel("λ  (cost of a wrong answer, in units of one abstention)")
    ax.set_ylabel("NET(λ) = (correct − λ·wrong) / n")
    ax.set_title("VeriBench NET(λ) — HaluEval QA (300 probes)", fontsize=12)
    ax.set_xlim(1, 10)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8, loc="lower left", framealpha=0.9)
    ax.annotate("as-shipped mem0 turns net-negative past λ=2",
                xy=(2, 0), xytext=(3.1, -0.55), fontsize=8, color="#B8742E",
                arrowprops=dict(arrowstyle="->", color="#B8742E", lw=0.8))
    fig.tight_layout()

    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "net_lambda_halueval.png", dpi=160)
    fig.savefig(OUT / "net_lambda_halueval.pdf")
    print(f"saved -> {OUT / 'net_lambda_halueval.png'}")
    # sanity: print the crossover λ for the two ungated arms (correct/wrong)
    for label, c, w, n, _ in series:
        cx = (c / w) if w else float("inf")
        print(f"  {label}: crossover λ = {cx:.2f}")


if __name__ == "__main__":
    main()
