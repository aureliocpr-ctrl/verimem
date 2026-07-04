"""Cycle #146 (2026-05-18 sera) — Lab Live dashboard for multi-agent chat.

Aurelio richiede: durante esperimenti multi-agent (cycle 145+ in poi),
vedere LIVE in CLI le interazioni degli agent che si coordinano via
fact su topic comune. Cycle 146 = `engram lab live <topic>` che polla
SQLite ogni N sec e mostra chat fact in cronologico ASC, color-coded
per ruolo estratto dal prefisso ``[ROLE @HH:MM:SS]``.

API:
    fetch_chat_since(sm, topic, since_ts=0.0) -> list[dict]
        SQL select facts WHERE topic=? AND created_at > since_ts
        ORDER BY created_at ASC. Returns rows as dicts.

    parse_role(proposition) -> str
        Regex extract role tag from ``[ROLE @T] msg`` prefix.
        Returns "Unknown" on no match / empty.

    run_live(sm, topic, refresh_sec=2.0, max_seconds=None) -> None
        Rich Live loop. Polls fetch_chat_since incrementally, updates
        a coloured table in-place. Ctrl-C exit clean.

CLI:
    engram lab live [--topic <t>] [--refresh-sec 2] [--max-sec N]
"""
from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .semantic import SemanticMemory


# Regex matches the chat-prefix tag set by the agent protocol.
_ROLE_RE = re.compile(r"^\[([A-Za-z][\w\-]*)\s*@")

# Rich color per role — extensible. Unknown falls back to white.
ROLE_COLORS: dict[str, str] = {
    "ORCHESTRATOR": "magenta",
    "Python-Eng": "cyan",
    "Code-Reviewer": "green",
    "QA-Eng": "yellow",
    "Unknown": "white",
}


def parse_role(proposition: str) -> str:
    """Return the ``ROLE`` tag from ``[ROLE @HH:MM:SS] msg``.

    ``"Unknown"`` if the proposition does not start with the tag.
    """
    if not proposition:
        return "Unknown"
    m = _ROLE_RE.match(proposition)
    return m.group(1) if m else "Unknown"


def fetch_chat_since(
    sm: SemanticMemory, topic: str, since_ts: float = 0.0,
) -> list[dict]:
    """Return chat facts on ``topic`` with ``created_at > since_ts``.

    Ordered ascending by ``created_at`` so the live feed reads natural
    cronologico. Strictly greater than ``since_ts`` so the same row is
    not surfaced twice across polls.
    """
    with sm._connect() as conn:  # noqa: SLF001
        rows = conn.execute(
            "SELECT id, proposition, topic, confidence, created_at, "
            "       status, verified_by "
            "FROM facts "
            "WHERE topic = ? AND created_at > ? "
            "  AND superseded_by IS NULL "
            "ORDER BY created_at ASC",
            (topic, float(since_ts)),
        ).fetchall()
    out: list[dict] = []
    for r in rows:
        out.append({
            "id": r["id"],
            "proposition": r["proposition"] or "",
            "topic": r["topic"],
            "confidence": float(r["confidence"]),
            "created_at": float(r["created_at"]),
            "status": r["status"] or "",
            "verified_by": r["verified_by"] or "",
        })
    return out


# ======================================================================
# Live dashboard (Rich)
# ======================================================================
def _fmt_ts(ts: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts))


def _build_table(rows: list[dict], topic: str) -> object:
    """Compose a Rich Table snapshot. Imports Rich lazily so the module
    keeps importable even if Rich is not installed (it is, per pyproject).
    """
    from rich.table import Table
    table = Table(
        title=f"HippoAgent Lab Live — topic: {topic}",
        title_style="bold",
        expand=True,
        show_lines=False,
    )
    table.add_column("time", style="dim", width=10, no_wrap=True)
    table.add_column("role", width=14, no_wrap=True)
    table.add_column("proposition", overflow="fold")
    for r in rows[-30:]:  # last 30 to keep terminal happy
        role = parse_role(r["proposition"])
        colour = ROLE_COLORS.get(role, "white")
        ts = _fmt_ts(r["created_at"])
        # Strip the role-prefix from the displayed text so the role
        # column doesn't repeat the bracket.
        body = _ROLE_RE.sub("", r["proposition"], count=1).lstrip()
        # Mark quarantined fact in dim red.
        if r.get("status") == "quarantined":
            body = f"[red][quarantined][/red] {body}"
        table.add_row(ts, f"[{colour}]{role}[/{colour}]", body)
    return table


def run_live(
    sm: SemanticMemory, topic: str, *,
    refresh_sec: float = 2.0,
    max_seconds: float | None = None,
) -> None:
    """Live polling loop. Exits cleanly on Ctrl-C or max_seconds reached.

    Implementation: keep a ``since_ts`` watermark to fetch only deltas
    between polls. Rich Live updates the table in-place.
    """
    from rich.console import Console
    from rich.live import Live

    console = Console()
    since_ts = 0.0
    cumulative: list[dict] = []
    deadline = time.time() + max_seconds if max_seconds else None

    # Seed with all existing rows so the first frame shows the full
    # history (the operator may join mid-experiment).
    initial = fetch_chat_since(sm, topic, since_ts=0.0)
    cumulative.extend(initial)
    if initial:
        since_ts = max(r["created_at"] for r in initial)

    try:
        with Live(
            _build_table(cumulative, topic),
            console=console, refresh_per_second=4, screen=False,
        ) as live:
            while True:
                if deadline is not None and time.time() >= deadline:
                    break
                time.sleep(refresh_sec)
                new = fetch_chat_since(sm, topic, since_ts=since_ts)
                if new:
                    cumulative.extend(new)
                    since_ts = max(r["created_at"] for r in new)
                live.update(_build_table(cumulative, topic))
    except KeyboardInterrupt:
        # Clean exit — Rich Live restores terminal state automatically.
        console.print("[dim]exit (Ctrl-C)[/dim]")
