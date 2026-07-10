"""Pure-function tests for the MSC F1 harness (task #22, corpus #2).

Model-free logic only: turn flattening, answer-substring gold, normalization.
The end-to-end path is verified by the sanity run (needs the embedder).
"""
from __future__ import annotations

from benchmark.external_f1_msc import _norm, flatten_turns, gold_turn_ids


def _item():
    return {
        "previous_dialogs": [
            {"time_back": "7 days ago", "dialog": [
                {"id": "Speaker 1", "text": "I love Taylor Swift, honestly."},
                {"id": "Speaker 2", "text": "Nice! I prefer jazz."},
            ]},
            {"time_back": "2 days ago", "dialog": [
                {"id": "Speaker 1", "text": "My dog is named Rex."},
                {"id": "Speaker 2", "text": ""},  # empty → dropped
            ]},
        ],
        "self_instruct": {"B": "What artist did I mention?", "A": "Taylor Swift!"},
    }


def test_flatten_turns_ids_sessions_and_drops_empty():
    turns = flatten_turns(_item())
    assert [t["tid"] for t in turns] == ["0:0", "0:1", "1:0"]
    assert turns[0]["speaker"] == "Speaker 1"
    assert turns[0]["time_back"] == "7 days ago"
    assert turns[2]["session"] == 1


def test_norm_strips_punctuation_and_case():
    assert _norm("Taylor Swift!") == "taylor swift"
    assert _norm("  A,  B.  ") == "a  b"


def test_gold_matches_answer_substring():
    turns = flatten_turns(_item())
    assert gold_turn_ids(turns, "Taylor Swift!") == ["0:0"]


def test_gold_empty_when_answer_absent_or_blank():
    turns = flatten_turns(_item())
    assert gold_turn_ids(turns, "Beethoven") == []
    assert gold_turn_ids(turns, "") == []
    assert gold_turn_ids(turns, "  !! ") == []
