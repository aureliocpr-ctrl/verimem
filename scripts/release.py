#!/usr/bin/env python3
"""Release helper.

Usage:
    python scripts/release.py 0.2.0
    python scripts/release.py 0.2.0 --dry-run
    python scripts/release.py 0.2.0 --no-push    # build + tag locally only

What it does, in order:
    1. Validate the new version (PEP 440-ish: X.Y.Z[aN|bN|rcN|.devN]).
    2. Verify the working tree is clean (no uncommitted changes).
    3. Update the `version =` line in pyproject.toml.
    4. Run the test suite.
    5. Build sdist + wheel into dist/.
    6. Commit the bump, tag `vX.Y.Z`.
    7. Push the branch + tag (skipped with --no-push or --dry-run).

This script does NOT publish to PyPI — that step is intentionally left to a
separate manual `twine upload` so a human always reviews the artefacts.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"

VERSION_RE = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:(?P<pre>a|b|rc)(?P<preN>\d+))?"
    r"(?:\.dev(?P<devN>\d+))?$"
)


def run(cmd: list[str], *, check: bool = True, dry_run: bool = False) -> subprocess.CompletedProcess[str]:
    print(f"$ {' '.join(cmd)}", flush=True)
    if dry_run:
        return subprocess.CompletedProcess(cmd, 0, "", "")
    return subprocess.run(cmd, check=check, text=True)  # noqa: S603 — controlled args


def validate_version(v: str) -> None:
    if not VERSION_RE.match(v):
        sys.exit(f"error: version {v!r} doesn't match PEP 440-ish X.Y.Z[aN|bN|rcN|.devN]")


def working_tree_clean() -> bool:
    out = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, check=True,  # noqa: S603 S607
    )
    return out.stdout.strip() == ""


def current_version() -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
    if not m:
        sys.exit("error: no `version = \"…\"` line in pyproject.toml")
    return m.group(1)


def bump_version(new: str, *, dry_run: bool) -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    new_text, count = re.subn(
        r'^(version\s*=\s*)"[^"]+"',
        rf'\1"{new}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        sys.exit("error: failed to rewrite version in pyproject.toml")
    if dry_run:
        print(f"(dry-run) would write pyproject.toml with version={new}")
        return
    PYPROJECT.write_text(new_text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("version", help="new version, e.g. 0.2.0 or 0.2.0rc1")
    ap.add_argument("--dry-run", action="store_true", help="print actions without changing anything")
    ap.add_argument("--no-push", action="store_true", help="skip `git push` of branch + tag")
    ap.add_argument("--skip-tests", action="store_true", help="skip the test suite (NOT recommended)")
    ap.add_argument("--branch", default="main", help="expected branch (default: main)")
    args = ap.parse_args()

    validate_version(args.version)

    cur = current_version()
    if cur == args.version:
        sys.exit(f"error: version is already {cur}")
    print(f"bump: {cur} → {args.version}")

    if not args.dry_run and not working_tree_clean():
        sys.exit("error: working tree is dirty — commit or stash first")

    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True, text=True, check=True,  # noqa: S603 S607
    ).stdout.strip()
    if branch != args.branch:
        print(f"warning: current branch is {branch!r}, expected {args.branch!r}")

    bump_version(args.version, dry_run=args.dry_run)

    if not args.skip_tests:
        run([sys.executable, "-m", "pytest", "-q", "-m", "not slow and not e2e"],
            dry_run=args.dry_run)

    # Clean dist/ before building so we don't ship stale wheels.
    if (ROOT / "dist").exists() and not args.dry_run:
        for f in (ROOT / "dist").iterdir():
            f.unlink()
    run([sys.executable, "-m", "build"], dry_run=args.dry_run)

    tag = f"v{args.version}"
    run(["git", "add", str(PYPROJECT.relative_to(ROOT))], dry_run=args.dry_run)
    run(["git", "commit", "-m", f"release: {tag}"], dry_run=args.dry_run)
    run(["git", "tag", "-a", tag, "-m", f"release {tag}"], dry_run=args.dry_run)

    if args.no_push or args.dry_run:
        print(f"\nbuilt artefacts in dist/ and tagged {tag}.")
        print("skipped push — run `git push origin <branch> && git push origin --tags` when ready.")
        return 0

    run(["git", "push", "origin", branch], dry_run=args.dry_run)
    run(["git", "push", "origin", tag], dry_run=args.dry_run)
    print(f"\nrelease {tag} pushed. Upload manually with:")
    print(f"    twine upload dist/hippoagent-{args.version}*")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
