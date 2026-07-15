"""``verimem flow tail`` — the LIVE Engine Room as a terminal feed.

Tails ``events.jsonl`` (the cross-process bus every surface writes to since
flow events moved into the core) and prints one colored line per
``flow.write`` / ``flow.recall`` event: verdict, surface (sdk|mcp|gateway),
actor (``VERIMEM_ACTOR`` — the agent's label, any vendor), tenant when
present, topic/ids/scores. Flow METADATA only — never fact content.

Pure renderer (:func:`render_flow_line`) kept separate from the loop so it
is unit-testable without a terminal.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# plain ANSI (no rich dependency in the hot loop; CI-safe via NO_COLOR)
_GRN = "\x1b[32m"
_RED = "\x1b[31m"
_YEL = "\x1b[33m"
_DIM = "\x1b[2m"
_BLD = "\x1b[1m"
_RST = "\x1b[0m"


def _c(code: str, txt: str, *, color: bool) -> str:
    return f"{code}{txt}{_RST}" if color else txt


def render_flow_line(rec: dict[str, Any], *, color: bool = False) -> str | None:
    """One feed line for a flow event; ``None`` for anything else."""
    name = str(rec.get("name", ""))
    if not name.startswith("flow."):
        return None
    p = rec.get("payload") or {}
    ts = datetime.fromtimestamp(float(rec.get("ts") or 0.0))
    hh = ts.strftime("%H:%M:%S")

    who = str(p.get("surface", "?"))
    if p.get("actor"):
        who += f"/{p['actor']}"
    if p.get("tenant"):
        who += f" t={p['tenant']}"

    if name == "flow.write":
        quarantined = (not p.get("stored")) or p.get("status") == "quarantined"
        if quarantined:
            tag = _c(_RED + _BLD, str(p.get("status", "refused")).upper(),
                     color=color)
        else:
            tag = _c(_GRN + _BLD, "ADMITTED", color=color)
        detail = f"write · topic {p.get('topic', '—')}"
        if p.get("fact_id"):
            detail += f" · id {str(p['fact_id'])[:8]}"
        if not quarantined and p.get("status"):
            detail += f" · status {p['status']}"
    elif name == "flow.recall":
        if p.get("abstained"):
            tag = _c(_YEL + _BLD, "ABSTAIN", color=color)
        else:
            tag = _c(_GRN + _BLD, "ANSWER", color=color)
        detail = f"recall/{p.get('kind', '?')} · n={p.get('n', '?')}"
        if p.get("best") is not None:
            detail += f" · best {p['best']}"
    else:
        return None

    return f"{_c(_DIM, hh, color=color)} {tag} [{who}] {detail}"


def _read_flow(path: Path, after_pos: int) -> tuple[list[dict[str, Any]], int]:
    """New complete lines after byte offset ``after_pos`` → (records, new_pos)."""
    try:
        with path.open("r", encoding="utf-8") as f:
            f.seek(after_pos)
            chunk = f.read()
            pos = f.tell()
    except OSError:
        return [], after_pos
    recs: list[dict[str, Any]] = []
    for ln in chunk.splitlines():
        try:
            recs.append(json.loads(ln))
        except ValueError:
            continue
    return recs, pos


def tail_flow(*, replay: int = 20, follow: bool = True, color: bool = True,
              poll_s: float = 0.5, echo=print) -> None:
    """Print the last ``replay`` flow events, then (if ``follow``) keep
    following the jsonl. ``echo`` is injectable for tests."""
    from . import event_jsonl_log as _ejl
    path = _ejl.EVENT_LOG_PATH

    recs, pos = _read_flow(path, 0)
    shown = [render_flow_line(r, color=color) for r in recs]
    for line in [s for s in shown if s][-replay:]:
        echo(line)
    if not follow:
        return
    echo(_c(_DIM, f"— following {path} (Ctrl+C to stop) —", color=color))
    try:
        while True:
            time.sleep(poll_s)
            recs, pos = _read_flow(path, pos)
            for r in recs:
                line = render_flow_line(r, color=color)
                if line:
                    echo(line)
    except KeyboardInterrupt:
        pass
