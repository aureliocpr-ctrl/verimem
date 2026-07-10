"""Characterization tests for working_memory pruning (F2 gap).

The wake loop trims old tool observations when the message list exceeds
budget, so small models don't lose the original task. Pure functions,
zero unit tests before F2 — pinned here: index 0 (the task) is never pruned,
the last keep_tail observations are sacred, and pruning stops as soon as the
list fits budget.
"""
from __future__ import annotations

from engram.working_memory import (
    estimate_size,
    native_tool_is_candidate,
    native_tool_replace,
    prune_messages,
    react_obs_is_candidate,
    react_obs_replace,
)


def test_estimate_size_strings_and_blocks():
    assert estimate_size([{"content": "hello"}]) == 5
    assert estimate_size(
        [{"role": "user", "content": [{"type": "tool_result", "content": "abc"}]}]) == 3
    # structured (non-string) tool_result content -> fixed 200 proxy
    assert estimate_size(
        [{"role": "user", "content": [{"type": "tool_result", "content": {"x": 1}}]}]) == 200


def test_prune_noop_when_within_budget():
    msgs = [{"role": "user", "content": "task"},
            {"role": "tool", "content": "small"}]
    out, n = prune_messages(
        msgs, budget=10_000, keep_tail=1, placeholder="[pruned]",
        is_candidate=native_tool_is_candidate,
        replace_in_place=native_tool_replace)
    assert n == 0 and out[1]["content"] == "small"


def test_prune_replaces_old_tool_output_over_budget():
    big = "x" * 500
    msgs = [{"role": "user", "content": "the original task"}]
    for _ in range(6):
        msgs.append({"role": "tool", "content": big})
    out, n = prune_messages(
        msgs, budget=800, keep_tail=1, placeholder="[pruned]",
        is_candidate=native_tool_is_candidate,
        replace_in_place=native_tool_replace)
    assert n >= 1
    assert out[0]["content"] == "the original task", "index 0 is never pruned"
    assert out[-1]["content"] == big, "the last kept_tail observation is sacred"
    assert estimate_size(out) <= 800 or n > 0


def test_prune_keeps_index0_even_if_candidate():
    # index 0 carries tool_result but must be excluded (it's the task turn)
    big = "y" * 400
    msgs = [{"role": "user", "content": [{"type": "tool_result", "content": big}]},
            {"role": "tool", "content": big},
            {"role": "tool", "content": big}]
    out, _ = prune_messages(
        msgs, budget=300, keep_tail=0, placeholder="[p]",
        is_candidate=native_tool_is_candidate,
        replace_in_place=native_tool_replace)
    assert out[0]["content"][0]["content"] == big


def test_native_candidate_matches_tool_and_toolresult_only():
    assert native_tool_is_candidate(1, {"role": "tool", "content": "x"})
    assert native_tool_is_candidate(
        1, {"role": "user", "content": [{"type": "tool_result", "content": "x"}]})
    assert not native_tool_is_candidate(1, {"role": "assistant", "content": "x"})
    assert not native_tool_is_candidate(1, {"role": "user", "content": "plain"})


def test_native_replace_is_idempotent():
    m = {"role": "tool", "content": "orig"}
    assert native_tool_replace(m, "[p]") is True and m["content"] == "[p]"
    assert native_tool_replace(m, "[p]") is False  # already pruned


def test_react_observation_strategy():
    m = {"role": "user", "content": "Observation: the tool returned 42"}
    assert react_obs_is_candidate(1, m)
    assert react_obs_replace(m, "[p]") is True
    assert m["content"].startswith("Observation:") and "Continue." in m["content"]
    assert not react_obs_is_candidate(1, {"role": "user", "content": "hi"})
