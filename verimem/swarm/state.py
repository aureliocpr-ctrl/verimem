"""Cycle #148.3 (2026-05-18 sera) — parse Claude bg session state.

The Claude supervisor process writes ``~/.claude/jobs/<short_id>/state.json``
for every background session. Schema verified empirically Fase 0 against
real session d3ffcf29 (smoke test). The keys we care about for the
swarm orchestrator are surfaced on :class:`SessionState`; everything
else passes through ``extra="allow"`` so a CLI upgrade adding new
fields doesn't break us.

API:
    read_state(short_id, *, jobs_dir=None) -> SessionState | None
    find_state_dir(short_id, *, jobs_dir=None) -> Path | None

Default ``jobs_dir`` is ``~/.claude/jobs/`` (resolved at call time so
``HOME``/userprofile tweaks via env work transparently).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _default_jobs_dir() -> Path:
    return Path.home() / ".claude" / "jobs"


class SessionState(BaseModel):
    """Subset of fields we read from ``state.json``.

    All optional because:
      • Older Claude versions may not emit every field
      • ``state.json`` is updated incrementally — fields appear over time
      • ``extra="allow"`` keeps forward compat on new keys
    """

    model_config = ConfigDict(extra="allow")

    state: str = ""
    tempo: str = ""
    detail: str | None = None
    intent: str | None = None
    daemon_short: str | None = Field(default=None, alias="daemonShort")
    session_id: str | None = Field(default=None, alias="sessionId")
    output_result: str | None = None  # populated from output.result below
    in_flight_tasks: int = 0
    jsonl_path: str | None = Field(default=None, alias="linkScanPath")
    backend: str | None = None
    cli_version: str | None = Field(default=None, alias="cliVersion")
    created_at: str | None = Field(default=None, alias="createdAt")
    updated_at: str | None = Field(default=None, alias="updatedAt")
    cwd: str | None = None

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> SessionState:
        """Build from the raw JSON dict, flattening ``output.result`` +
        ``inFlight.tasks``.
        """
        # Flatten nested keys we want at top level.
        flat = dict(raw)
        output = raw.get("output") or {}
        if isinstance(output, dict) and "result" in output:
            flat["output_result"] = output["result"]
        in_flight = raw.get("inFlight") or {}
        if isinstance(in_flight, dict):
            flat["in_flight_tasks"] = int(in_flight.get("tasks", 0))
        return cls.model_validate(flat)


def find_state_dir(
    short_id: str, *, jobs_dir: Path | None = None,
) -> Path | None:
    """Locate ``<jobs_dir>/<short_id>/`` if it exists."""
    base = jobs_dir or _default_jobs_dir()
    p = base / short_id
    return p if p.is_dir() else None


def read_state(
    short_id: str, *, jobs_dir: Path | None = None,
) -> SessionState | None:
    """Read + parse the session state. Returns ``None`` if absent."""
    sd = find_state_dir(short_id, jobs_dir=jobs_dir)
    if sd is None:
        return None
    sj = sd / "state.json"
    if not sj.is_file():
        return None
    try:
        raw = json.loads(sj.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    return SessionState.from_raw(raw)
