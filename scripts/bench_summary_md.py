"""Render the bench-harness summary JSON as a markdown table.

Usage:
    python scripts/bench_summary_md.py [path-to-summary.json]

Default path: data/bench_with_without_hippo.summary.json. Output goes to
stdout — pipe to a file or paste into README/FORGIA.

The table shows one row per (condition × provider) cell, sorted by
provider then condition so each provider's three rows sit together
for easy visual diffing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Windows fix (cycle #88 CI 2026-05-16): the rendered table contains
# "∞" (∞) when tokens_per_success is float('inf'). On Windows the
# default stdout encoding is cp1252 which can't encode that char, so
# ``print(rendered)`` raises UnicodeEncodeError. Force UTF-8 on stdout
# (Python 3.7+ supports the reconfigure attribute).
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except (AttributeError, ValueError):
    # Older Python or non-tty stream: silently fall back to default.
    pass

from engram.config import CONFIG


def render_table(summary: dict[str, dict[str, float]],
                  *, sort_by: str = "", top_n: int = 0) -> str:
    rows: list[tuple[str, str, dict[str, float]]] = []
    for key, stats in summary.items():
        # key was joined as "condition|provider"
        cond, _, prov = key.partition("|")
        rows.append((prov, cond, stats))
    if sort_by:
        # FORGIA pezzo #126: sort by a chosen metric (descending).
        rows.sort(key=lambda r: -r[2].get(sort_by, 0.0))
    else:
        rows.sort(key=lambda r: (r[0], r[1]))  # provider, condition
    if top_n > 0:
        # FORGIA pezzo #128: keep the first N rows after sort.
        rows = rows[:top_n]

    out = ["| provider | condition | n | success | tokens | latency_s | attempts | tok/success | errors |",
           "|---|---|--:|--:|--:|--:|--:|--:|--:|"]
    for prov, cond, s in rows:
        # FORGIA pezzo #118: render tokens_per_success (or "∞" when absent).
        tps = s.get("tokens_per_success", float("inf"))
        tps_fmt = "∞" if tps == float("inf") else f"{int(tps)}"
        out.append(
            f"| {prov} | {cond} | {int(s['n'])} | "
            f"{s['success_rate']:.2f} | "
            f"{int(s['mean_tokens'])} | "
            f"{s['mean_latency_s']:.2f} | "
            f"{s['mean_attempts']:.1f} | "
            f"{tps_fmt} | "
            f"{int(s['n_errors'])} |"
        )
    return "\n".join(out)


def render_csv(summary: dict[str, dict[str, float]]) -> str:
    """FORGIA pezzo #104: render the summary as CSV (Excel-friendly)."""
    rows: list[tuple[str, str, dict[str, float]]] = []
    for key, stats in summary.items():
        cond, _, prov = key.partition("|")
        rows.append((prov, cond, stats))
    rows.sort(key=lambda r: (r[0], r[1]))
    out = ["provider,condition,n,success_rate,mean_tokens,"
           "mean_latency_s,mean_attempts,n_errors"]
    for prov, cond, s in rows:
        out.append(
            f"{prov},{cond},{int(s['n'])},"
            f"{s['success_rate']:.4f},"
            f"{s['mean_tokens']:.2f},"
            f"{s['mean_latency_s']:.4f},"
            f"{s['mean_attempts']:.2f},"
            f"{int(s['n_errors'])}"
        )
    return "\n".join(out)


def render_by_iter_table(by_iter: dict[str, dict[str, float]]) -> str:
    """FORGIA #71: render the per-iter summary (compounding curve)."""
    rows: list[tuple[str, str, int, dict[str, float]]] = []
    for key, stats in by_iter.items():
        # key was joined as "condition|provider|iterN"
        parts = key.split("|")
        if len(parts) < 3:
            continue
        cond, prov = parts[0], parts[1]
        try:
            it = int(parts[2].removeprefix("iter"))
        except ValueError:
            continue
        rows.append((prov, cond, it, stats))
    rows.sort(key=lambda r: (r[0], r[1], r[2]))

    out = ["| provider | condition | iter | n | success | tokens | latency_s |",
           "|---|---|--:|--:|--:|--:|--:|"]
    for prov, cond, it, s in rows:
        out.append(
            f"| {prov} | {cond} | {it} | {int(s['n'])} | "
            f"{s['success_rate']:.2f} | "
            f"{int(s['mean_tokens'])} | "
            f"{s['mean_latency_s']:.2f} |"
        )
    return "\n".join(out)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    by_iter = "--by-iter" in sys.argv
    csv_mode = "--csv" in sys.argv
    # FORGIA pezzo #122: --filter <provider> keeps only matching cells.
    filter_idx = next((i for i, a in enumerate(sys.argv)
                        if a == "--filter"), -1)
    filter_provider = (
        sys.argv[filter_idx + 1] if filter_idx >= 0
        and filter_idx + 1 < len(sys.argv) else ""
    )
    path = Path(args[0]) if args else (
        CONFIG.data_dir / (
            "bench_with_without_hippo.by_iter.json"
            if by_iter else "bench_with_without_hippo.summary.json"
        )
    )
    if not path.exists():
        print(f"summary not found: {path}", file=sys.stderr)
        return 1
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        print(f"summary file is empty: {path}", file=sys.stderr)
        return 1
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        # FORGIA #95: surface a clear error for corrupted JSON instead
        # of dumping a raw stack trace.
        print(f"summary file is not valid JSON: {path}: {exc}",
              file=sys.stderr)
        return 1
    if not isinstance(payload, dict):
        print(f"summary file must contain a JSON object: {path}",
              file=sys.stderr)
        return 1
    if filter_provider:
        # Keys are "condition|provider" (or "...|iterN") — keep only those
        # whose provider field matches.
        suffix = f"|{filter_provider}"
        payload = {
            k: v for k, v in payload.items()
            if (suffix in k) or k.endswith(filter_provider)
            or (filter_provider in k.split("|"))
        }
        if not payload:
            print(f"no cells matched provider filter: {filter_provider}",
                  file=sys.stderr)
            return 1
    # FORGIA pezzo #124: --filter-condition keeps only matching condition.
    fc_idx = next((i for i, a in enumerate(sys.argv)
                    if a == "--filter-condition"), -1)
    filter_condition = (
        sys.argv[fc_idx + 1] if fc_idx >= 0 and fc_idx + 1 < len(sys.argv) else ""
    )
    if filter_condition:
        payload = {
            k: v for k, v in payload.items()
            if k.split("|", 1)[0] == filter_condition
        }
        if not payload:
            print(f"no cells matched condition filter: {filter_condition}",
                  file=sys.stderr)
            return 1
    sort_idx = next((i for i, a in enumerate(sys.argv)
                      if a == "--sort-by"), -1)
    sort_metric = (
        sys.argv[sort_idx + 1] if sort_idx >= 0
        and sort_idx + 1 < len(sys.argv) else ""
    )
    top_idx = next((i for i, a in enumerate(sys.argv)
                     if a == "--top"), -1)
    top_n = 0
    if top_idx >= 0 and top_idx + 1 < len(sys.argv):
        try:
            top_n = int(sys.argv[top_idx + 1])
        except ValueError:
            top_n = 0
    if by_iter:
        rendered = render_by_iter_table(payload)
    elif csv_mode:
        rendered = render_csv(payload)
    else:
        rendered = render_table(payload, sort_by=sort_metric, top_n=top_n)
    # FORGIA #106: optional --save <path> writes to a file instead of stdout.
    save_idx = next((i for i, a in enumerate(sys.argv)
                      if a == "--save"), -1)
    if save_idx >= 0 and save_idx + 1 < len(sys.argv):
        out_path = Path(sys.argv[save_idx + 1])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered + "\n", encoding="utf-8")
        print(f"wrote {out_path}", file=sys.stderr)
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
