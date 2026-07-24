"""Pins on the adjudication receipt — inside the chain, without breaking it.

A pin that is not hash-chained is a pin an editor can rewrite: recording WHAT
was cited only helps if the record itself is tamper-evident. So `pins` joins
the chained payload — and that is exactly where the compatibility problem
lives, because every row already written computed its hash over a payload
WITHOUT the field. Adding it unconditionally would make `verify()` reject the
entire existing log: a false tamper alarm on intact data, the worst possible
failure for an integrity signal.

Same shape as the step-2 anchor receipt: a payload with nothing to say emits
byte-identically to v1, and only a row that actually carries pins hashes them.
"""
from __future__ import annotations

import json
import sqlite3

from verimem.adjudication_log import AdjudicationLog, _chain_payload

_BASE = dict(id="a1", ts=1.0, topic="t", disposition="admitted",
             proposition="p", fact_id=None, evidence_class=None, judge=None,
             score=None, threshold=None, reason="", layers_json="[]")


# --- the chained payload --------------------------------------------------

def test_payload_without_pins_is_byte_identical_to_v1():
    legacy = _chain_payload(**_BASE)
    assert "pins" not in legacy
    assert _chain_payload(**_BASE, pins_json="") == legacy
    assert _chain_payload(**_BASE, pins_json="{}") == legacy


def test_payload_with_pins_hashes_them():
    withpins = _chain_payload(**_BASE, pins_json='{"file:a.py:1":"sha256:x"}')
    assert withpins != _chain_payload(**_BASE)
    assert withpins["pins"] == '{"file:a.py:1":"sha256:x"}'


# --- persistence ----------------------------------------------------------

def test_pins_round_trip(tmp_path):
    log = AdjudicationLog(tmp_path / "adj.db")
    pins = {"file:src/mod.py:2": "sha256:abc"}
    rid = log.record(disposition="admitted", topic="t", proposition="p",
                     pins=pins)
    assert log.get(rid).pins == pins


def test_row_without_pins_reads_back_empty(tmp_path):
    log = AdjudicationLog(tmp_path / "adj.db")
    rid = log.record(disposition="admitted", topic="t", proposition="p")
    assert log.get(rid).pins == {}


def test_chain_still_verifies_with_and_without_pins(tmp_path):
    log = AdjudicationLog(tmp_path / "adj.db")
    log.record(disposition="admitted", topic="t", proposition="one")
    log.record(disposition="quarantined", topic="t", proposition="two",
               pins={"file:a.py:1": "sha256:aaa"})
    log.record(disposition="admitted", topic="t", proposition="three")
    assert log.verify() is None


def test_editing_a_pin_breaks_the_chain(tmp_path):
    """The point of chaining them: a rewritten pin is a detected pin."""
    log = AdjudicationLog(tmp_path / "adj.db")
    rid = log.record(disposition="admitted", topic="t", proposition="p",
                     pins={"file:a.py:1": "sha256:aaa"})
    with sqlite3.connect(log.db_path) as c:
        c.execute("UPDATE adjudications SET pins = ? WHERE id = ?",
                  (json.dumps({"file:a.py:1": "sha256:bbb"}), rid))
    assert log.verify() is not None


def test_pre_pin_database_migrates(tmp_path):
    """An audit DB created before the column exists gains it, and its rows
    keep verifying — they were hashed without pins and still are."""
    db = tmp_path / "old.db"
    with sqlite3.connect(db) as c:
        c.execute("""CREATE TABLE adjudications (
            id TEXT PRIMARY KEY, ts REAL NOT NULL, topic TEXT NOT NULL,
            disposition TEXT NOT NULL, proposition TEXT NOT NULL,
            fact_id TEXT, evidence_class TEXT, judge TEXT, score REAL,
            threshold REAL, reason TEXT NOT NULL DEFAULT '',
            layers TEXT NOT NULL DEFAULT '[]', entry_hash TEXT)""")
    log = AdjudicationLog(db)
    with sqlite3.connect(db) as c:
        cols = {r[1] for r in c.execute("PRAGMA table_info(adjudications)")}
    assert "pins" in cols
    log.record(disposition="admitted", topic="t", proposition="p")
    assert log.verify() is None
