"""Evidence the writer already cited — in the PROSE, where nothing can check it.

An L1 detector quarantines a claim and answers "no evidence in verified_by; add
one of task:<id>_closed, pytest:<t>_PASS, ...". Often the writer HAS the
evidence and put it in the sentence: "Wave 72 skills_recent done, last commit
ff2aaa3e". Measured on the live corpus 2026-07-28: of 509 quarantined facts,
174 (34.2%) name a commit SHA, a file:line, a pytest/EXIT result or a PR in
their own text — 95 commits, 69 test results, 30 file:line, 18 PRs.

The detector is RIGHT to ignore them. A SHA inside prose is an assertion; the
same SHA in ``verified_by`` is checkable, and provenance_validator does check it
(it runs ``git rev-parse``). Reading evidence out of the sentence would let a
writer clear its own gate by describing proof it never had.

So this does not admit anything and does not soften a verdict. It only makes the
advice specific: the gate can SEE the reference it is asking for, and saying
"you cited commit ff2aaa3e — pass it in verified_by to have it verified" is the
difference between a rejection a writer can act on and one they cannot.
"""
from __future__ import annotations

import re

__all__ = ["evidence_in_text", "hint_for"]

#: Loose on purpose: this text is never trusted, only quoted back. A false match
#: costs a slightly odd hint; a miss costs the writer the one thing they needed
#: to be told.
_REFS: dict[str, re.Pattern[str]] = {
    "commit": re.compile(r"\b(?:commit|sha)[:\s]+([a-f0-9]{6,40})\b", re.IGNORECASE),
    "file": re.compile(r"\b([\w./-]+\.(?:py|md|toml|json|ts|tsx|js|rs|go):\d+)"),
    "test": re.compile(r"\b((?:pytest|EXIT=\d+|exit code \d+)[\w:.\-/]*)", re.IGNORECASE),
    "pr": re.compile(r"\b((?:PR|issue)\s*#\d+)\b", re.IGNORECASE),
}

#: kind -> the verified_by form that MAKES it checkable
_AS_REF = {
    "commit": "commit:{}",
    "file": "file:{}",
    "test": "pytest:{}_PASS",
    "pr": "pr:{}_merged",
}


def evidence_in_text(proposition: str | None) -> list[tuple[str, str]]:
    """``[(kind, cited_value)]`` for every evidence reference named in the prose."""
    text = proposition or ""
    found: list[tuple[str, str]] = []
    for kind, pat in _REFS.items():
        m = pat.search(text)
        if m:
            found.append((kind, m.group(1)))
    return found


def hint_for(proposition: str | None) -> str | None:
    """A sentence naming what the writer already cited and how to make it count,
    or None when the prose cites nothing."""
    found = evidence_in_text(proposition)
    if not found:
        return None
    parts = [f"{_AS_REF[k].format(v)}" for k, v in found]
    cited = ", ".join(f"'{v}'" for _k, v in found)
    return (f"this text already cites {cited} — pass it in verified_by "
            f"(e.g. {', '.join(parts)}) so the gate can VERIFY it; a reference "
            f"inside the proposition is an assertion, not evidence")
