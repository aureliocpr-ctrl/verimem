"""Cycle 288 (2026-05-23) — Meta-rule evolution timeline.

Pioneering singolarità #29: parse commit history and emit, for each
M/S-rule, the BIRTH commit (first introduction) vs APPLICATION
commits (subsequent reference). Reveals the temporal trajectory of
rule reification across the session.

Output: JSON timeline + ASCII gantt-like summary.

Falsifiable: every M-rule M3-M12 should have BIRTH cycle == 264
(cycle when ossessive v3 introduced) per fact 13a2be73b299.
Every S-rule S1-S5 should have BIRTH cycle == 267 per fact
c69c6140886f.

Usage:
    python -m scripts.track_meta_rule_evolution --n 50 --output evo.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# Rules and their canonical references
RULES_TO_TRACK = {
    "M3_BENCH_FIRST": [r"\bM3\b", r"BENCH.FIRST", r"BENCH-FIRST"],
    "M4_CRITIC_GATE": [r"\bM4\b", r"CRITIC.GATE.NON.OPTIONAL"],
    "M5_WIRE_OR_DISCLOSE": [r"\bM5\b", r"WIRE.OR.DISCLOSE"],
    "M6_A4_REFRAMING": [r"\bM6\b", r"A4.REFRAMING.POSITIVE"],
    "M7_PARTITION_VS_COUNT": [r"\bM7\b", r"PARTITION.*COUNT", r"SHAPE.*COUNT"],
    "M8_CHAIN_OF_THOUGHT": [r"\bM8\b", r"CHAIN.OF.THOUGHT"],
    "M9_CLIFF_EDGE": [r"\bM9\b", r"CLIFF.EDGE"],
    "M10_MASTER_FACT_RATIO": [r"\bM10\b", r"MASTER.FACT.RATIO"],
    "M11_REPLICATED_SAMPLE": [r"\bM11\b", r"REPLICATED.SAMPLE"],
    "M12_REVEALING_VS_CREATING": [
        r"\bM12\b", r"REVEALING.*CREATING", r"REVEALING.*DYNAMICS",
    ],
    "M13_SECOND_CALL_SITE": [
        r"\bM13\b", r"SECOND.CALL.SITE", r"second.call.site.COVERAGE",
    ],
    "M14_EMPIRICAL_HEADLINE": [
        r"\bM14\b", r"EMPIRICAL.HEADLINE", r"HEADLINE.PROTECTION",
    ],
    "M15_DOCSTRING_VS_ASSERT": [
        r"\bM15\b", r"DOCSTRING.VS.ASSERT", r"DOCSTRING.*ASSERT.*PARITY",
    ],
    "M16_POST_FIX_CRITIC": [
        r"\bM16\b", r"POST.FIX.CRITIC", r"POST.FIX.CRITIC.VALIDATION",
    ],
    "M17_SNAPSHOT_FREEZE": [
        r"\bM17\b", r"SNAPSHOT.FREEZE", r"LIVE.CORPUS.SNAPSHOT",
    ],
    "M18_NARROW_CRITIC_CLAIMS": [
        r"\bM18\b", r"NARROW.CRITIC.CLAIMS", r"CRITIC.TIMEOUT.BROAD",
    ],
    "S1_EMPIRICAL_DISCIPLINE": [r"\bS1\b.*EMPIRICAL", r"EMPIRICAL.DISCIPLINE"],
    "S2_PROCESS_DISCIPLINE": [r"\bS2\b.*PROCESS", r"PROCESS.DISCIPLINE"],
    "S3_WIRING_DISCIPLINE": [r"\bS3\b.*WIRING", r"WIRING.DISCIPLINE"],
    "S4_REFRAMING_DISCIPLINE": [
        r"\bS4\b.*REFRAMING", r"REFRAMING.DISCIPLINE",
    ],
    "S5_LEVEL_OF_EFFECT": [r"\bS5\b.*LEVEL", r"LEVEL.OF.EFFECT"],
}


def parse_commits(repo: Path, n: int) -> list[dict]:
    """Parse last N commits with sha, cycle, subject, body."""
    result = subprocess.run(
        ["git", "log", f"-n{n}", "--pretty=format:%H%x00%s%x00%b%x1f"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return []
    out: list[dict] = []
    entries = [e for e in result.stdout.split("\x1f") if e.strip()]
    for entry in entries:
        parts = entry.split("\x00")
        if len(parts) < 2:
            continue
        sha = parts[0].strip()
        subject = parts[1].strip()
        body = parts[2].strip() if len(parts) >= 3 else ""
        cycle_m = re.search(r"cycle\s*(\d+)", subject, re.IGNORECASE)
        cycle = int(cycle_m.group(1)) if cycle_m else None
        out.append({
            "sha": sha[:10],
            "cycle": cycle,
            "subject": subject,
            "body": body,
        })
    return out


def detect_rules_in_commit(commit: dict) -> list[str]:
    text = f"{commit['subject']}\n{commit['body']}"
    found: list[str] = []
    for rule, patterns in RULES_TO_TRACK.items():
        for rgx in patterns:
            if re.search(rgx, text, re.IGNORECASE):
                found.append(rule)
                break
    return found


def build_timeline(commits: list[dict]) -> dict:
    """For each rule: birth cycle (first mention) + application cycles."""
    timeline: dict[str, dict] = defaultdict(
        lambda: {"birth": None, "applications": []},
    )

    # Commits are in reverse chronological order; reverse to get
    # chronological for birth detection.
    chrono_commits = list(reversed(commits))
    for c in chrono_commits:
        if c["cycle"] is None:
            continue
        rules = detect_rules_in_commit(c)
        for r in rules:
            if timeline[r]["birth"] is None:
                timeline[r]["birth"] = {
                    "cycle": c["cycle"],
                    "sha": c["sha"],
                    "subject": c["subject"][:80],
                }
            else:
                timeline[r]["applications"].append({
                    "cycle": c["cycle"],
                    "sha": c["sha"],
                    "subject": c["subject"][:80],
                })

    # Compute aggregate stats
    summary = {
        "n_rules_tracked": len(RULES_TO_TRACK),
        "n_rules_with_birth": sum(
            1 for v in timeline.values() if v["birth"]
        ),
        "n_rules_with_applications": sum(
            1 for v in timeline.values() if v["applications"]
        ),
        "rules_never_referenced": [
            r for r in RULES_TO_TRACK
            if timeline.get(r, {}).get("birth") is None
        ],
    }

    return {
        "summary": summary,
        "timeline": dict(timeline),
    }


def emit_ascii_gantt(timeline_data: dict) -> str:
    """Compact ASCII gantt: rule | birth_cycle | n_applications | apply_range."""
    lines = ["RULE                       | BIRTH | APPLIED N | RANGE      "]
    lines.append("-" * 70)
    for rule, info in timeline_data["timeline"].items():
        if not info["birth"]:
            continue
        birth = info["birth"]["cycle"]
        apps = info["applications"]
        n_apps = len(apps)
        if apps:
            app_cycles = sorted({a["cycle"] for a in apps})
            range_str = f"{app_cycles[0]}-{app_cycles[-1]}"
        else:
            range_str = "(no apps)"
        lines.append(
            f"{rule:26s} | {birth:5d} | {n_apps:9d} | {range_str:10s}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--n", type=int, default=40)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    commits = parse_commits(args.repo, args.n)
    if not commits:
        print("[error] no commits parsed", file=sys.stderr)
        return 1
    data = build_timeline(commits)
    payload = json.dumps(data, indent=2)
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    print(emit_ascii_gantt(data))
    print()
    print(f"Summary: {data['summary']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
