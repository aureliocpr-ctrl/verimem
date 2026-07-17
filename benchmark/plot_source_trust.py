"""Render the source-trust reproduction figure for the VeriBench preprint from
the committed real-corpus result (seed 11). Grouped bars: per condition, the
consistency-trust of cartel / honest / liar sources — the numbers read straight
from the JSON, nothing hand-set. Output:
docs/papers/figures/source_trust_realcorpus.{png,pdf}.

    python -m benchmark.plot_source_trust
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


def main() -> None:
    d = json.loads((RES / "source_trust_realcorpus_seed11_2026-07-13.json")
                   .read_text(encoding="utf-8"))
    conds = [("OFF", "off"), ("ON\n(naive ≥2)", "on"),
             ("ON+INDEP\n(raw)", "on_indep"),
             ("ON+INDEP\n+DECONF", "on_indep_deconf")]
    roles = [("cartel", "cartel_consistency", "#B8742E"),
             ("honest", "honest_consistency", "#2E6B4F"),
             ("liar", "liar_consistency", "#A03030")]

    x = np.arange(len(conds))
    w = 0.26
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for i, (label, key, color) in enumerate(roles):
        vals = [d[ck][key] for _, ck in conds]
        bars = ax.bar(x + (i - 1) * w, vals, w, label=label, color=color)
        ax.bar_label(bars, fmt="%.2f", fontsize=7, padding=1)
    ax.axhline(0.25, color="#444", lw=0.9, ls=":")
    ax.text(3.42, 0.255, "quarantine floor", fontsize=7, color="#444", va="bottom")
    ax.set_xticks(x)
    ax.set_xticklabels([c for c, _ in conds], fontsize=8)
    ax.set_ylabel("per-source consistency trust")
    ax.set_ylim(0, 1.05)
    ax.set_title("Source-trust on a real corpus (HaluEval, seed 11) — "
                 "the cartel is demolished by deconfounding", fontsize=10.5)
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(fontsize=8, loc="upper right", framealpha=0.9)
    fig.tight_layout()

    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "source_trust_realcorpus.png", dpi=160)
    fig.savefig(OUT / "source_trust_realcorpus.pdf")
    print(f"saved -> {OUT / 'source_trust_realcorpus.png'}")
    for label, ck in conds:
        r = d[ck]
        print(f"  {label.replace(chr(10),' '):18} cartel={r['cartel_consistency']} "
              f"honest={r['honest_consistency']} liar={r['liar_consistency']}")


if __name__ == "__main__":
    main()
