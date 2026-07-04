"""FORGIA pezzo #79 — regression guard on `make help`.

Ensures every documented bench / CI target is still wired in the
Makefile. A future cleanup that accidentally drops a target from the
.PHONY list (or removes a `## doc-comment`) would silently break
`make help` discoverability — this test catches it.

We don't shell out to `make` (Windows CI may not have it). Instead we
parse the Makefile directly with the same awk-style filter `make help`
uses.
"""
from __future__ import annotations

import re
from pathlib import Path

_MAKEFILE = Path(__file__).resolve().parents[1] / "Makefile"

# Every target listed here MUST have a `## doc-comment` in the Makefile
# (matching the regex below). New targets should be added here when
# they're committed.
_EXPECTED_TARGETS = {
    "help", "install", "install-dev", "install-full",
    "lint", "lint-fix", "typecheck", "test", "test-fast", "cov",
    "sec-ruff", "sec-bandit", "sec-audit", "sec",
    "build", "clean", "wheel", "sdist", "smoke",
    "docker-build", "docker-run", "release-dry",
    "bench-mock", "bench-real", "bench-skill", "bench-memory",
    "bench-summary", "bench-ablation", "bench-compare",
    "bench-clean", "bench-help", "bench-all", "bench-quick",
    "bench-csv",
    "ci", "ci-fast", "stats",
}


_HELP_RE = re.compile(r"^([a-zA-Z_\-]+):.*?## (.*)$")


def test_makefile_help_lists_expected_targets():
    body = _MAKEFILE.read_text(encoding="utf-8").splitlines()
    documented: dict[str, str] = {}
    for line in body:
        m = _HELP_RE.match(line)
        if m:
            documented[m.group(1)] = m.group(2)
    missing = _EXPECTED_TARGETS - documented.keys()
    assert not missing, (
        f"Makefile is missing `## doc-comment` lines for these "
        f"targets: {sorted(missing)}\n"
        f"All documented targets: {sorted(documented.keys())}"
    )
