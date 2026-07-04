"""Tests for the shared `jsonutil.extract_json_object` helper.

Single source of truth for the dict-only JSON parsing pattern that has
bitten the codebase twice (FORGIA #28 sleep, #31 compilation/ide).
Future call-sites should import from here.

Six invariants:

  1. dict in → dict out (with whitespace normalised).
  2. JSON scalar (int, str, bool, null) → None.
  3. JSON array → None.
  4. Code-fence wrapped object → unwrapped dict.
  5. Prose-embedded object → first {...} block extracted.
  6. Non-string input → None (defensive).
"""
from __future__ import annotations

from engram.jsonutil import extract_json_object


def test_dict_input_returned_verbatim():
    assert extract_json_object('{"a": 1}') == {"a": 1}
    assert extract_json_object('   {"a": 1, "b": [1,2]}  ') == {
        "a": 1, "b": [1, 2],
    }


def test_scalar_inputs_return_none():
    assert extract_json_object("4") is None
    assert extract_json_object('"hello"') is None
    assert extract_json_object("true") is None
    assert extract_json_object("false") is None
    assert extract_json_object("null") is None


def test_array_input_returns_none():
    assert extract_json_object("[1, 2, 3]") is None
    assert extract_json_object('[{"a":1}]') is None


def test_code_fence_unwrapped():
    assert extract_json_object('```json\n{"k": "v"}\n```') == {"k": "v"}
    assert extract_json_object('```\n{"k": "v"}\n```') == {"k": "v"}


def test_prose_embedded_object():
    raw = 'Here is the JSON: {"x": 42}, hope it helps.'
    assert extract_json_object(raw) == {"x": 42}


def test_garbage_returns_none():
    assert extract_json_object("not json at all") is None
    assert extract_json_object("") is None
    assert extract_json_object("   ") is None


def test_non_string_input_returns_none():
    assert extract_json_object(None) is None  # type: ignore[arg-type]
    assert extract_json_object(42) is None  # type: ignore[arg-type]
    assert extract_json_object({"already": "dict"}) is None  # type: ignore[arg-type]
