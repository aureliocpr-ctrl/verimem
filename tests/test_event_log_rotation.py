"""Audit 2026-06-08 A7: events.jsonl was append-only with NO rotation
(log_size_bytes existed but never gated anything). Every emit() — including
every MCP tool call — appends a line forever, so a long-running server reached
hundreds of MB. append_event now rotates to a single `.1` backup past
ENGRAM_EVENT_LOG_MAX_BYTES (default 5MB), bounding total to ~2x the cap.
"""
from __future__ import annotations

from engram import event_jsonl_log as ev


def test_event_log_rotates_past_cap(tmp_path, monkeypatch):
    logp = tmp_path / "events.jsonl"
    monkeypatch.setattr(ev, "EVENT_LOG_PATH", logp)
    monkeypatch.setattr(ev, "_EVENT_LOG_MAX_BYTES", 200)  # tiny cap for the test
    for i in range(60):
        ev.append_event("evt", {"i": i, "pad": "x" * 40})
    # main file is bounded (rotation happened), and a .1 backup exists
    assert logp.exists()
    assert logp.stat().st_size <= 200 + 1024, "event log not bounded — no rotation"
    assert (tmp_path / "events.jsonl.1").exists(), "no rotated backup file"


def test_append_still_readable_after_rotation(tmp_path, monkeypatch):
    logp = tmp_path / "events.jsonl"
    monkeypatch.setattr(ev, "EVENT_LOG_PATH", logp)
    monkeypatch.setattr(ev, "_EVENT_LOG_MAX_BYTES", 200)
    for i in range(60):
        ev.append_event("evt", {"i": i})
    # the most recent events (post-rotation) are still tailable
    recent = ev.tail_events(since_ts=0.0, limit=1000)
    assert recent, "no events readable after rotation"
    assert all(r["name"] == "evt" for r in recent)
