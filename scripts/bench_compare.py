"""FORGIA pezzo #47 — Diff two bench summary JSON files.

Usage:
    python scripts/bench_compare.py BEFORE.json AFTER.json [--threshold 0.05]

Loads two `bench_with_without_hippo.summary.json` files, computes
deltas per (condition, provider), and flags cells where success_rate
or mean_tokens / mean_latency moved by more than `--threshold`
(default ±5 %). Useful to catch perf regressions across a code change
or a provider model bump.

Exit code:
  0 — all cells within threshold
  1 — at least one cell exceeded threshold (the diff is printed)
  2 — file load / parse error

The output is markdown so it can land directly in a PR comment.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Windows fix (cycle #88 CI 2026-05-16): output contains "+∞" / "∞"
# when delta is infinite. Windows cp1252 stdout can't encode it, so
# force UTF-8 if available.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except (AttributeError, ValueError):
    pass


def _load(path: Path) -> dict[tuple[str, str], dict[str, float]]:
    """Parse 'condition|provider' keys back into tuples.

    FORGIA #96: defensively handle non-object payloads, empty files,
    and non-numeric values — surfaces a clear error to the caller
    instead of a stack trace from `dict.items()` or `float(str)`.
    """
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"summary file is empty: {path}")
    raw = json.loads(text)
    if not isinstance(raw, dict):
        raise ValueError(
            f"summary file must contain a JSON object: {path} "
            f"(got {type(raw).__name__})"
        )
    out: dict[tuple[str, str], dict[str, float]] = {}
    for k, v in raw.items():
        if not isinstance(v, dict):
            continue  # skip malformed cells, don't crash the whole diff
        cond, _, prov = k.partition("|")
        coerced: dict[str, float] = {}
        for kk, vv in v.items():
            try:
                coerced[kk] = float(vv)
            except (TypeError, ValueError):
                continue
        out[(cond, prov)] = coerced
    return out


def _delta(before: float, after: float) -> tuple[float, str]:
    """Return (relative_change, formatted_arrow)."""
    if before == 0:
        if after == 0:
            return 0.0, "="
        return float("inf"), "+∞"
    rel = (after - before) / abs(before)
    arrow = "↑" if rel > 0 else "↓" if rel < 0 else "="
    return rel, arrow


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("before", type=Path)
    p.add_argument("after", type=Path)
    p.add_argument("--threshold", type=float, default=0.05,
                   help="relative-change threshold beyond which a cell "
                        "is flagged (default 0.05 = ±5%%).")
    p.add_argument("--metric", choices=["success_rate", "mean_tokens",
                                          "mean_latency_s"],
                   default="success_rate",
                   help="which metric to gate on for the exit code.")
    p.add_argument("--top-n", type=int, default=0,
                   help="show only the top N rows by absolute Δ% on the "
                        "gate metric (0 = all rows).")
    args = p.parse_args()

    try:
        before = _load(args.before)
        after = _load(args.after)
    except Exception as exc:  # noqa: BLE001
        print(f"error loading: {exc}", file=sys.stderr)
        return 2

    keys = sorted(set(before) | set(after))
    rows: list[tuple[str, str, str]] = [
        ("(condition, provider)", "metric",
         "before → after (Δ%)"),
    ]
    flagged = False
    # FORGIA #72: collect rows + their abs Δ% on the gate metric, then
    # optionally trim to the top-N by absolute change.
    rows_with_rank: list[tuple[float, tuple[str, str, str]]] = []
    for key in keys:
        b = before.get(key, {})
        a = after.get(key, {})
        max_rel_for_gate = 0.0
        for metric in ("success_rate", "mean_tokens", "mean_latency_s",
                        "mean_attempts"):
            bv = b.get(metric, 0.0)
            av = a.get(metric, 0.0)
            rel, arrow = _delta(bv, av)
            if metric == "success_rate":
                fmt_b = f"{bv:.2f}"
                fmt_a = f"{av:.2f}"
            elif metric == "mean_tokens" or metric == "mean_attempts":
                fmt_b = f"{bv:.1f}"
                fmt_a = f"{av:.1f}"
            else:  # mean_latency_s
                fmt_b = f"{bv:.2f}s"
                fmt_a = f"{av:.2f}s"
            rel_pct = (
                "+∞" if rel == float("inf")
                else f"{rel * 100:+.1f}%"
            )
            row = (
                f"{key[0]} {key[1]}",
                metric,
                f"{fmt_b} → {fmt_a} ({arrow}{rel_pct})",
            )
            if metric == args.metric and rel != float("inf"):
                max_rel_for_gate = abs(rel)
            rows_with_rank.append((max_rel_for_gate, row))
            if metric == args.metric and abs(rel) > args.threshold and rel != float(
                "inf",
            ):
                flagged = True

    # FORGIA #72: optional top-N trimming.
    data_rows = [r for _rk, r in rows_with_rank]
    if args.top_n > 0:
        # Sort all rows by their associated gate-metric absolute Δ
        # (descending), keep the first top_n unique rows.
        rows_with_rank.sort(key=lambda t: t[0], reverse=True)
        seen_keys = set()
        kept = []
        for rk, r in rows_with_rank:
            key = (r[0], r[1])
            if key in seen_keys:
                continue
            kept.append(r)
            seen_keys.add(key)
            if len(kept) >= args.top_n:
                break
        data_rows = kept

    # Markdown table
    print(f"## Bench diff — `{args.before.name}` → `{args.after.name}`\n")
    print(f"| {' | '.join(rows[0])} |")
    print("|" + "|".join("---" for _ in rows[0]) + "|")
    for r in data_rows:
        print(f"| {' | '.join(r)} |")
    print()
    print(f"Gate metric: `{args.metric}`. Threshold: ±{args.threshold * 100:.0f}%.")
    print(f"Result: {'**REGRESSION DETECTED**' if flagged else 'within threshold ✓'}")
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
