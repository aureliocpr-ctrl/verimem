"""Concurrent `engram teams send` must not LOSE messages (TDD, 2026-06-05).

`send_cmd` did a read-modify-write on the inbox JSON with NO serialization:

    existing = read_json(inbox)      # both senders read the same array
    existing.append(my_message)      # each appends its own
    write_json(inbox, existing)      # LAST writer wins -> the other is LOST

That is the normal swarm case (many teammates messaging one coordinator).
A torn read (a reader hitting a half-written file) also silently reset the
inbox to []. Fix: a BOUNDED cross-platform file lock serializes the
read-modify-write + the write is atomic (temp + os.replace).

Falsification: `test_concurrent_appends_lose_no_message` is RED against the
unlocked core (atomic write ALONE does not prevent the lost update) and GREEN
once the lock wraps the read-modify-write — proving the lock is necessary.

Hermetic: only the filesystem under tmp_path. No DB, no network.
"""
from __future__ import annotations

import json
import os
import time as _time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from verimem.teams.cli import (
    _INBOX_LOCK_STALE_S,
    append_to_inbox,
)


def _messages(inbox: Path) -> list[dict]:
    return json.loads(inbox.read_text(encoding="utf-8"))


def test_sequential_appends_accumulate(tmp_path: Path) -> None:
    for i in range(5):
        append_to_inbox(tmp_path, "bob", "alice", f"msg{i}")
    inbox = tmp_path / "inboxes" / "bob.json"
    msgs = _messages(inbox)
    assert [m["text"] for m in msgs] == [f"msg{i}" for i in range(5)]
    assert all(m["from"] == "alice" and m["read"] is False for m in msgs)


def test_concurrent_appends_lose_no_message(tmp_path: Path) -> None:
    """60 concurrent sends to ONE inbox -> all 60 survive (the falsification).

    RED against the unlocked read-modify-write (messages lost); GREEN with the
    lock. High concurrency makes the race deterministic enough to not flake.
    """
    n = 60
    with ThreadPoolExecutor(max_workers=16) as ex:
        list(ex.map(
            lambda i: append_to_inbox(tmp_path, "bob", "alice", f"m{i:03d}"),
            range(n),
        ))
    inbox = tmp_path / "inboxes" / "bob.json"
    msgs = _messages(inbox)
    texts = sorted(m["text"] for m in msgs)
    assert len(msgs) == n, f"LOST {n - len(msgs)} messages to the race (got {len(msgs)})"
    assert texts == [f"m{i:03d}" for i in range(n)], "missing or duplicate messages"


def test_corrupt_inbox_recovers_without_raising(tmp_path: Path) -> None:
    inbox = tmp_path / "inboxes" / "bob.json"
    inbox.parent.mkdir(parents=True)
    inbox.write_text("{ this is not valid json", encoding="utf-8")
    append_to_inbox(tmp_path, "bob", "alice", "recovered")  # must not raise
    msgs = _messages(inbox)
    assert len(msgs) == 1 and msgs[0]["text"] == "recovered"


def test_lock_is_bounded_when_stale(tmp_path: Path) -> None:
    """A stale lock file (crashed holder) is stolen, never waited on forever."""
    inbox = tmp_path / "inboxes" / "bob.json"
    inbox.parent.mkdir(parents=True)
    stale_lock = inbox.with_name(inbox.name + ".lock")
    stale_lock.write_text("", encoding="utf-8")
    old = _time.time() - (_INBOX_LOCK_STALE_S + 90)
    os.utime(stale_lock, (old, old))
    t0 = _time.monotonic()
    append_to_inbox(tmp_path, "bob", "alice", "after-stale")
    elapsed = _time.monotonic() - t0
    assert elapsed < 2.0, f"stale lock not stolen — waited {elapsed:.1f}s (hang risk)"
    assert len(_messages(inbox)) == 1
