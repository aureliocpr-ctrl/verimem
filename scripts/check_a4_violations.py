"""Cycle 270 (2026-05-23) — A4-violation pre-flight check.

Pioneering singolarità #26: scripted detector that warns BEFORE commit
when a commit message contains "marketing"-style claims about a NEW
module that has no production caller yet.

Background:
- Cycle 258 critic-orchestrator flagged "ARCHITECTURAL CURE SHIPPED"
  for second_pass_louvain (dead code production-side).
- Cycle 262 same-class gap for stable_partition.
- M5 WIRE-OR-DISCLOSE rule born from these failures.

This script REIFIES M5 as automated pre-flight gate. Detects:

1. Marketing pattern in commit msg: "shipped", "production-ready",
   "cure", "fix", "real solution", etc.
2. New files added in same commit (via git diff --cached --name-only --diff-filter=A).
3. For each NEW Python module, count import sites OUTSIDE tests/.
4. If marketing pattern AND zero non-test importers → WARN (or BLOCK).

Falsifiable test (cycle 270 self-validation):
- Replay cycle 253 commit msg "ARCHITECTURAL CURE SHIPPED" + new file
  engram/second_pass_louvain.py with ZERO non-test importers → MUST
  trigger WARN.
- Replay cycle 254 commit msg "production bench --auto-copy honest
  empirical results" (no marketing pattern, no new module) → MUST pass.

Usage:
    python -m scripts.check_a4_violations \\
        --commit-msg "..." \\
        --new-files engram/foo.py engram/bar.py
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

#: Marketing-pattern regexes (case-insensitive)
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


def has_marketing_pattern(text: str) -> list[str]:
    """Return matched marketing patterns (empty if none)."""
    matches: list[str] = []
    for rgx in MARKETING_PATTERNS:
        if re.search(rgx, text, re.IGNORECASE):
            matches.append(rgx)
    return matches


def _module_to_dotted(module_path: str) -> str:
    """Map a repo-relative module path to its dotted import name.

    'engram/foo.py' -> 'verimem.foo'; 'engram/__init__.py' -> 'engram'.
    """
    # SCAN-68 FIX 2026-06-02 (NONNA): removesuffix, NON rstrip('.py') che
    # rimuove il SET di char {'.','p','y'} dalla coda (policy.py->polic).
    rel = module_path.replace("\\", "/").removesuffix(".py")
    if rel.endswith("/__init__"):
        rel = rel[: -len("/__init__")]
    return rel.replace("/", ".")


def count_non_test_importers(
    module_path: str,
    repo_dir: Path,
) -> int:
    """Grep repo for imports of the module, excluding tests/.

    module_path e.g. 'engram/foo.py' → search for 'from verimem.foo' or
    'import verimem.foo'.
    """
    if not module_path.endswith(".py"):
        return -1
    # Build dotted name: engram/foo.py → verimem.foo (suffix-safe helper)
    dotted = _module_to_dotted(module_path)

    # Grep
    result = subprocess.run(
        ["git", "grep", "-l", "-E",
         f"from {dotted}|import {dotted}"],
        cwd=str(repo_dir),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 and not result.stdout:
        return 0
    files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
    # Exclude tests/* and the module itself
    non_test = [
        f for f in files
        if not f.startswith("tests/")
        and not f.endswith("test_" + Path(module_path).name)
        and f != module_path
    ]
    return len(non_test)


def check(commit_msg: str, new_files: list[str], repo_dir: Path) -> dict:
    """Run the A4 pre-flight check.

    Returns dict with:
      verdict: "OK" | "WARN" | "BLOCK"
      marketing_matches: list of regex hits in commit_msg
      new_modules_no_caller: list of new modules with no non-test import
    """
    marketing = has_marketing_pattern(commit_msg)
    no_callers: list[str] = []
    if new_files:
        for f in new_files:
            if not f.endswith(".py"):
                continue
            n = count_non_test_importers(f, repo_dir)
            if n == 0:
                no_callers.append(f)

    if marketing and no_callers:
        verdict = "BLOCK"
        reason = (
            "Commit message contains marketing patterns "
            f"{marketing} AND new modules {no_callers} have ZERO "
            "non-test importers (dead code per M5 WIRE-OR-DISCLOSE)."
        )
    elif marketing:
        verdict = "WARN"
        reason = (
            f"Marketing patterns {marketing} but all new modules have "
            "importers (OK per M5)."
        )
    elif no_callers:
        verdict = "WARN"
        reason = (
            f"New modules {no_callers} have ZERO importers but commit "
            "message is not marketing (M5 advisory, acceptable for "
            "test-only modules)."
        )
    else:
        verdict = "OK"
        reason = "No marketing patterns and all new modules have callers."

    return {
        "verdict": verdict,
        "reason": reason,
        "marketing_matches": marketing,
        "new_modules_no_caller": no_callers,
        "n_new_files_checked": len(new_files),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit-msg", required=True, type=str)
    parser.add_argument("--new-files", nargs="*", default=[])
    parser.add_argument(
        "--repo", type=Path, default=Path.cwd(),
    )
    parser.add_argument(
        "--exit-on-block",
        action="store_true",
        help="Exit code 1 if verdict is BLOCK (for pre-commit hook).",
    )
    args = parser.parse_args()

    result = check(args.commit_msg, args.new_files, args.repo)
    print(f"VERDICT: {result['verdict']}")
    print(f"REASON: {result['reason']}")
    if result["marketing_matches"]:
        print(f"  marketing patterns: {result['marketing_matches']}")
    if result["new_modules_no_caller"]:
        print(f"  modules without callers: {result['new_modules_no_caller']}")

    if args.exit_on_block and result["verdict"] == "BLOCK":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
