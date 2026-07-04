"""Cycle #159 (2026-05-19) — Real-collaboration charter + tag parser.

This module is the **textual protocol** for agent-team collaboration:
a Charter that every teammate gets in its prompt + a tolerant parser
that extracts the few control tags ([CLAIM], [QUESTION], [VOTE-CONVERGED],
[BLOCKED], [REFER]) we need to measure progress objectively.

Why textual not RPC: agent-teams Mailbox already gives us reliable
message delivery. What was missing was a CONVENTION the agents could
follow to make their reasoning *measurable* — otherwise a watcher can
only count bytes, not whether the team converged.

Cycle 159 design choice (B1 self-challenged): we resist building a
``Coordinator`` / ``Decomposer`` class. The Charter + tag parser is
~100 LoC, the model does the rest. Any heavier orchestration belongs
on the lead-Claude side via the native ``SendMessage`` tool.
"""
from __future__ import annotations

import re
from collections import defaultdict

# All recognised tag names — kept lowercase, hyphen-separated.
TAG_NAMES: tuple[str, ...] = (
    "claim",
    "question",
    "vote-converged",
    "blocked",
    "refer",
)

# Charter handed to each teammate. The text is deliberately compact and
# anti-confab heavy — the cycle #157 memory shows teammates degrade
# fast when prompts are vague. Aurelio's regole v2 (A1/A2/A3) baked in.
CHARTER_TEMPLATE: str = """\
# Real-Collaboration Charter (cycle 159)

You are part of an agent team coordinated through a shared Mailbox. Your
goal is **not** to ship a deliverable alone but to converge with your
teammates on a verified answer. Follow these rules verbatim.

## Anti-confabulation contract
- Every factual claim you make MUST cite a file path + line number, a
  tool-call output, or an existing HippoAgent fact_id. No claim from
  memory without verification.
- If you don't know, say `[BLOCKED] need X to proceed` and stop. Do not
  speculate.
- Before asserting anything you "remember" about prior work, call
  `mcp__hippoagent__hippo_facts_search` or `hippo_recall` to confirm.

## Memory contract (HippoAgent)
- Cite prior decisions by their fact_id: `[REFER] fact_id=<id> topic=<t>`.
- When you discover something worth surviving the session, propose it
  with `[CLAIM]` so the harness mirrors it as a Fact on topic
  `lab/teams/<team>` automatically.

## Tag protocol (mandatory)
Every message MUST use the following tags so the harness can measure
the team's progress:

- `[CLAIM] <verified assertion>` — fact you have verified empirically.
- `[QUESTION] @<teammate> <ask>` — explicit disagreement or clarification.
- `[REFER] fact_id=<id>|episode_id=<id> topic=<t>` — link to memory.
- `[BLOCKED] <reason>` — you are stuck, name what you need.
- `[VOTE-CONVERGED] <one-line reasoning>` — emit only when (a) all
  open [QUESTION]s have been answered and (b) no [BLOCKED] is open.

Multiple tags per message are fine. Plain prose between tags is fine.

## Convergence rule
The harness declares the team converged when **strictly more than half**
of the active members have emitted at least one `[VOTE-CONVERGED]`.
Do not vote unless your honest read is that the work is done.

## Failure modes the harness will detect
- **Deadlock**: zero non-idle messages for >120 s. The supervisor will
  unblock by asking a `[QUESTION]` to the silent teammate.
- **Confabulation**: a `[CLAIM]` without citation. The supervisor will
  ask `[QUESTION] cite source of <claim>`.

Italian or English both fine. Keep messages under ~300 words.
"""


# Tag matcher: ``[TAG] body`` where body runs until the next `[TAG]` or EOF.
# We anchor on the bracketed tag at line start (with optional leading
# whitespace), so a literal `[CLAIM]` mentioned inside prose doesn't trip.
_TAG_RE = re.compile(
    r"(?:^|\n)\s*\[(?P<tag>[A-Za-z][A-Za-z\-]*)\]\s?(?P<body>.*?)"
    r"(?=\n\s*\[[A-Za-z][A-Za-z\-]*\]|\Z)",
    flags=re.DOTALL,
)


def parse_protocol_tags(text: str) -> dict[str, list[str]]:
    """Extract the cycle-159 control tags from one message.

    Returns a dict keyed by every name in :data:`TAG_NAMES` (lowercase),
    each mapping to the list of body strings found. Unknown tag names
    are dropped silently — the protocol is permissive so a teammate
    inventing `[NOTE]` doesn't break the parser.

    Idle-notification JSON envelopes are NOT this module's concern;
    the caller (``InboxMessage.is_idle_notification``) handles those.
    """
    out: dict[str, list[str]] = defaultdict(list)
    # Pre-populate so the schema is always complete.
    for name in TAG_NAMES:
        _ = out[name]

    if not text:
        return dict(out)

    for m in _TAG_RE.finditer(text):
        tag = m.group("tag").lower()
        if tag not in TAG_NAMES:
            continue
        body = m.group("body").strip()
        if body:
            out[tag].append(body)
    return dict(out)
