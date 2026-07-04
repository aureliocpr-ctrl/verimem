"""Cycle 274 (2026-05-23) — Audit A4 violations across full commit history.

Runs scripts/check_a4_violations.py marketing-pattern detector against
every commit in a range, aggregates verdicts. Reveals anti-pattern
frequency over time.

Usage:
    python -m scripts.audit_a4_history --since cycle253-second-pass-louvain~1
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

# Re-use MARKETING_PATTERNS from sibling script
MARKETING_PATTERNS = [
    r"\bshipped\b",
    r"production.ready",
    r"\bcure\b(?!.*test)",
    r"real\s+mitigation",
    r"real\s+solution",
    r"architectural\s+cure",
    r"definitive(?!\s+test)",
    r"complete\s+elimination",
    r"breakthrough",
]


def parse_commit_range(repo: Path, n: int) -> list[dict]:
    """Get last N commits with sha + subject + body + added-files list."""
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
        # Get added files via git show
        files_res = subprocess.run(
            [
                "git", "show", "--diff-filter=A", "--name-only",
                "--format=", sha,
            ],
            cwd=str(repo),
            capture_output=True,
            text=True,
        )
        added = [
            f.strip()
            for f in files_res.stdout.splitlines()
            if f.strip() and f.strip().endswith(".py")
        ]
        out.append({
            "sha": sha[:10],
            "subject": subject,
            "added_py_files": added,
            "body_excerpt": body[:200],
        })
    return out


def detect_marketing(text: str) -> list[str]:
    matches = []
    for rgx in MARKETING_PATTERNS:
        if re.search(rgx, text, re.IGNORECASE):
            matches.append(rgx)
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--n", type=int, default=25)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    commits = parse_commit_range(args.repo, args.n)
    per_commit: list[dict] = []
    counter: Counter = Counter()
    pattern_freq: Counter = Counter()

    for c in commits:
        full = f"{c['subject']}\n{c['body_excerpt']}"
        m = detect_marketing(full)
        for p in m:
            pattern_freq[p] += 1
        # Classify
        if m and c["added_py_files"]:
            verdict = "WARN_or_BLOCK"
        elif m:
            verdict = "WARN_marketing_only"
        elif c["added_py_files"]:
            verdict = "OK_new_files_no_marketing"
        else:
            verdict = "OK_clean"
        counter[verdict] += 1
        per_commit.append({
            "sha": c["sha"],
            "subject": c["subject"],
            "marketing_matches": m,
            "added_files": c["added_py_files"],
            "verdict_class": verdict,
        })

    report = {
        "n_commits": len(commits),
        "by_verdict_class": dict(counter),
        "marketing_pattern_freq": dict(pattern_freq.most_common()),
        "per_commit": per_commit,
    }

    payload = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)

    # Summary
    print(json.dumps({
        "n_commits": report["n_commits"],
        "by_verdict_class": report["by_verdict_class"],
        "marketing_pattern_freq": report["marketing_pattern_freq"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
