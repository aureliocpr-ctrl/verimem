"""Cycle 266 (2026-05-23) — Automated meta-rule mining from git log.

Pioneering singolarità #23 candidate: M-rules (cycle 264) were derived
manually from critic-gate verdicts. Hypothesis: M-rules are extractable
AUTOMATICALLY from commit message patterns (A1/A2/A3/A4/B2 keywords +
"honest", "violation", "falsified", "marketing", etc).

This script parses git log on a range, categorises commits by
detected pattern, and emits a JSON of mined lesson candidates that
can be compared with the cycle-264 hand-curated set.

Falsifiable claim: automated mining recovers at least 70% of the
manually-curated cycle-264 M-rules from commit messages alone.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Pattern → category mapping. Manually curated from cycle 253-263
# commit observations.
PATTERNS: dict[str, list[str]] = {
    "A1_anti_confab": [
        r"\bA1\b", r"anti-confab", r"non.invent", r"non.so",
        r"verified.empiric", r"actual\b",
    ],
    "A2_anti_hallucination": [
        r"\bA2\b", r"hallucination", r"non.dichiarare", r"empirico",
        r"\d+/\d+\s+PASS",
    ],
    "A3_sincerity": [
        r"\bA3\b", r"sincerit", r"stop.check", r"honest", r"onesto",
    ],
    "A4_anti_marketing": [
        r"\bA4\b", r"marketing", r"violation", r"hype", r"reframe",
        r"disclosure", r"disclaim",
    ],
    "B2_falsification": [
        r"\bB2\b", r"falsif", r"FALSIFIED", r"popperian",
        r"counterexample",
    ],
    "B4_chain": [
        r"\bB4\b", r"catena", r"5-element", r"5-elementi",
    ],
    "B6_curiosity": [
        r"\bB6\b", r"curiosit", r"investigat", r"probe",
    ],
    "O2_TDD": [
        r"\bTDD\b", r"RED.*GREEN", r"regression\s+\d+",
    ],
    "O3_critic_gate": [
        r"critic.gate", r"adversarial.review", r"claim.holds",
        r"claim.fails", r"critic.orchestrator",
    ],
    "M_meta_rule": [
        r"\bM[3-9]\b", r"\bM1[0-9]\b", r"meta.rul", r"meta.regol",
    ],
    "WIRE_disclose": [
        r"wire", r"production.caller", r"dead.code",
        r"not.yet.wired", r"opt.in",
    ],
    "REVEALING_creating": [
        r"revealing", r"creating", r"latent", r"cliff.edge",
    ],
    "REPLICATED_sample": [
        r"replicated.injection", r"single.sample",
        r"N>?=?\s*\d+", r"deferred",
    ],
    # Cycle 300: Conv-Commit style patterns (closes cycle 268
    # generalization gap on engram-orchestrator/clp terse style).
    "CONV_feat": [r"^feat\(", r"^feat:\s", r"\bfeat\(.{1,20}\):"],
    "CONV_fix": [r"^fix\(", r"^fix:\s", r"\bfix\(.{1,20}\):"],
    "CONV_refactor": [r"^refactor\(", r"^refactor:\s"],
    "CONV_release": [r"^release\(", r"^release:\s", r"v\d+\.\d+\.\d+"],
    "CONV_test": [r"^test\(", r"^test:\s"],
    "CONV_docs": [r"^docs\(", r"^docs:\s"],
    "LOOP_naming": [r"\bLOOP\s+\d+", r"\bloop\s+\d+", r"\bcycle\s+\d+"],
}

#: Cycle-264 hand-curated rules (ground truth for falsifiability)
GROUND_TRUTH_RULES = {
    "M3_BENCH_FIRST": ["A2_anti_hallucination", "B6_curiosity"],
    "M4_CRITIC_GATE_NON_OPTIONAL": ["O3_critic_gate"],
    "M5_WIRE_OR_DISCLOSE": ["WIRE_disclose", "A4_anti_marketing"],
    "M6_A4_REFRAMING_POSITIVE": ["A4_anti_marketing", "B2_falsification"],
    "M7_PARTITION_SHAPE_vs_COUNT": [
        "REVEALING_creating",
    ],
    "M8_CHAIN_OF_THOUGHT_PRESERVATION": ["M_meta_rule"],
    "M9_CLIFF_EDGE_CALIBRATION": ["REVEALING_creating"],
    "M10_MASTER_FACT_RATIO": ["WIRE_disclose"],
    "M11_REPLICATED_SAMPLE_EXTENSION": ["REPLICATED_sample"],
    "M12_REVEALING_vs_CREATING": ["REVEALING_creating"],
}


def parse_git_log(repo_dir: Path, n_commits: int = 50) -> list[dict]:
    """Parse git log into list of {sha, subject, body}."""
    result = subprocess.run(
        [
            "git", "log",
            f"-n{n_commits}",
            "--pretty=format:%H%x00%s%x00%b%x1f",
        ],
        cwd=str(repo_dir),
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return []
    out: list[dict] = []
    raw = result.stdout
    entries = [e for e in raw.split("\x1f") if e.strip()]
    for entry in entries:
        parts = entry.split("\x00")
        if len(parts) < 2:
            continue
        sha = parts[0].strip()
        subject = parts[1].strip()
        body = parts[2].strip() if len(parts) >= 3 else ""
        out.append({"sha": sha, "subject": subject, "body": body})
    return out


def detect_patterns(text: str) -> list[str]:
    """Find which PATTERNS keys match the text."""
    matches: list[str] = []
    for category, regexes in PATTERNS.items():
        for rgx in regexes:
            if re.search(rgx, text, re.IGNORECASE):
                matches.append(category)
                break
    return matches


def mine_lessons(commits: list[dict]) -> dict:
    """Categorise commits by detected pattern and emit lessons summary."""
    by_category: dict[str, list[str]] = defaultdict(list)
    by_sha: dict[str, list[str]] = {}

    for c in commits:
        full = f"{c['subject']}\n{c['body']}"
        cats = detect_patterns(full)
        if cats:
            by_sha[c["sha"][:10]] = cats
            for cat in cats:
                by_category[cat].append(c["sha"][:10])

    # Pattern co-occurrence: which categories appear together?
    co_occur: Counter = Counter()
    for sha, cats in by_sha.items():
        for i in range(len(cats)):
            for j in range(i + 1, len(cats)):
                pair = tuple(sorted([cats[i], cats[j]]))
                co_occur[pair] += 1

    # Recall against cycle-264 ground truth
    recall: dict[str, dict] = {}
    for rule, expected_cats in GROUND_TRUTH_RULES.items():
        found = []
        for cat in expected_cats:
            if by_category.get(cat):
                found.append(cat)
        recall[rule] = {
            "expected_categories": expected_cats,
            "found_categories": found,
            "recall_score": (
                len(found) / len(expected_cats)
                if expected_cats else 0.0
            ),
        }

    overall_recall = (
        sum(r["recall_score"] for r in recall.values()) / len(recall)
        if recall else 0.0
    )

    return {
        "n_commits_analyzed": len(commits),
        "n_commits_with_patterns": len(by_sha),
        "patterns_count": {
            cat: len(set(shas)) for cat, shas in by_category.items()
        },
        "top_co_occurrences": {
            f"{a}+{b}": count
            for (a, b), count in co_occur.most_common(10)
        },
        "ground_truth_recall": recall,
        "overall_recall": float(overall_recall),
        "falsifiable_claim_test": (
            "PASS (>=0.70)" if overall_recall >= 0.70 else "FAIL (<0.70)"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Repo directory (default: cwd)",
    )
    parser.add_argument("--n", type=int, default=50)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    commits = parse_git_log(args.repo, n_commits=args.n)
    if not commits:
        print("[error] no commits parsed", file=sys.stderr)
        return 1

    lessons = mine_lessons(commits)
    payload = json.dumps(lessons, indent=2)
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
