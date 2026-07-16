"""opus tenant-pass MED/HIGH-3: `/v1/events/flow` re-read the ENTIRE events.jsonl
(up to 5 MB) every 0.5s per connection — synchronous, inside an async endpoint —
so N concurrent SSE clients amplified to N×(full-file read + full JSON reparse)
every tick = a self-inflicted DoS. The fix is an incremental byte-offset reader:
each tick reads ONLY the bytes appended since the last one, handles rotation
(file shrank below the saved offset → restart), holds a trailing partial line for
the next tick, and caps how many lines it processes per tick (anti-burst).

These pin the reader's contract directly (pure fn, no SSE plumbing).
"""
from __future__ import annotations

import json

from engram.gateway import _read_flow_bytes


def _line(path, rec) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def _flow(ts: float, tenant: str = "t1", name: str = "flow.write") -> dict:
    return {"name": name, "ts": ts, "payload": {"tenant": tenant}}


def test_reads_only_new_bytes_not_whole_file(tmp_path):
    p = tmp_path / "events.jsonl"
    _line(p, _flow(1.0, name="flow.write"))
    recs, off1 = _read_flow_bytes(p, 0, "t1", False, 0)
    assert [r["name"] for r in recs] == ["flow.write"]
    assert off1 > 0

    # no new append → nothing, offset does NOT move (no re-read of old lines)
    recs2, off2 = _read_flow_bytes(p, off1, "t1", False, 1000)
    assert recs2 == []
    assert off2 == off1

    # append a second event → ONLY that one comes back (the first is not re-read)
    _line(p, _flow(2.0, name="flow.recall"))
    recs3, off3 = _read_flow_bytes(p, off1, "t1", False, 1000)
    assert [r["name"] for r in recs3] == ["flow.recall"]
    assert off3 > off1


def test_rotation_resets_offset(tmp_path):
    p = tmp_path / "events.jsonl"
    _line(p, _flow(1.0))
    _line(p, _flow(2.0))
    _, off = _read_flow_bytes(p, 0, "t1", False, 0)
    assert off > 0
    # rotation: file replaced by a smaller one (size < saved offset) → read from 0
    p.write_text(json.dumps(_flow(3.0)) + "\n", encoding="utf-8")
    recs, off2 = _read_flow_bytes(p, off, "t1", False, 1000)
    assert [r["ts"] for r in recs] == [3.0]
    assert off2 <= off  # restarted, not stuck past EOF


def test_partial_trailing_line_held_until_complete(tmp_path):
    p = tmp_path / "events.jsonl"
    # a write in progress: bytes present but no terminating newline yet
    full = json.dumps(_flow(1.0))
    with p.open("a", encoding="utf-8") as f:
        f.write(full[:10])  # partial, no "\n"
    recs, off = _read_flow_bytes(p, 0, "t1", False, 1000)
    assert recs == []
    assert off == 0  # nothing consumed — we must not emit or skip a partial line
    # the writer finishes the line
    with p.open("a", encoding="utf-8") as f:
        f.write(full[10:] + "\n")
    recs2, off2 = _read_flow_bytes(p, off, "t1", False, 1000)
    assert [r["ts"] for r in recs2] == [1.0]
    assert off2 > 0


def test_cap_bounds_lines_per_tick_and_resumes(tmp_path):
    p = tmp_path / "events.jsonl"
    for i in range(10):
        _line(p, _flow(float(i)))
    # cap=4 → at most 4 this tick, offset advances only over those 4
    recs, off = _read_flow_bytes(p, 0, "t1", False, 4)
    assert [r["ts"] for r in recs] == [0.0, 1.0, 2.0, 3.0]
    # next tick picks up exactly where we stopped — no loss, no dup
    recs2, off2 = _read_flow_bytes(p, off, "t1", False, 4)
    assert [r["ts"] for r in recs2] == [4.0, 5.0, 6.0, 7.0]
    recs3, _ = _read_flow_bytes(p, off2, "t1", False, 4)
    assert [r["ts"] for r in recs3] == [8.0, 9.0]


def test_tenant_filter_drops_others_but_offset_advances(tmp_path):
    p = tmp_path / "events.jsonl"
    _line(p, _flow(1.0, tenant="t1"))
    _line(p, _flow(2.0, tenant="t2"))          # other tenant → not emitted
    _line(p, _flow(3.0, tenant="t1"))
    recs, off = _read_flow_bytes(p, 0, "t1", False, 1000)
    assert [r["ts"] for r in recs] == [1.0, 3.0]
    # offset consumed ALL three complete lines (t2 not re-scanned next tick)
    recs2, _ = _read_flow_bytes(p, off, "t1", False, 1000)
    assert recs2 == []


def test_untenanted_seen_only_in_personal_mode(tmp_path):
    p = tmp_path / "events.jsonl"
    rec = {"name": "flow.write", "ts": 1.0, "payload": {}}  # tenant=None
    _line(p, rec)
    # multi-tenant: a None-tenant event is NOT visible to a real tenant
    recs, _ = _read_flow_bytes(p, 0, "t1", False, 1000)
    assert recs == []
    # personal mode (see_untenanted=True): the local operator sees it
    recs2, _ = _read_flow_bytes(p, 0, "operator", True, 1000)
    assert [r["ts"] for r in recs2] == [1.0]


def test_non_flow_lines_ignored_but_consumed(tmp_path):
    p = tmp_path / "events.jsonl"
    _line(p, {"name": "write", "ts": 1.0, "payload": {"tenant": "t1"}})  # not flow.*
    _line(p, _flow(2.0, tenant="t1"))
    recs, off = _read_flow_bytes(p, 0, "t1", False, 1000)
    assert [r["ts"] for r in recs] == [2.0]
    recs2, _ = _read_flow_bytes(p, off, "t1", False, 1000)
    assert recs2 == []
