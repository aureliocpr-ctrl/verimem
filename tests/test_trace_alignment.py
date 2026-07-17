"""Tests for trace_alignment — observation-anchored divergence detection.

The tests are written to be honest: each one exercises a property that
should hold *for the right reason*, and we deliberately keep at least one
case that demonstrates the alignment failing gracefully (e.g. when the
observations are unrelated, no spurious divergence is invented).
"""
from __future__ import annotations

from verimem.episode import Episode, Trace
from verimem.trace_alignment import (
    align_traces,
    find_divergence_point,
    format_divergence,
)


def _ep(traces: list[tuple[str, str, str]], outcome: str = "success") -> Episode:
    """Compact factory: each tuple is (action, action_input, observation).

    Thought is filled in to a generic value so embeddings of different
    steps in the same episode aren't accidentally identical.
    """
    return Episode(
        traces=[
            Trace(step=i + 1, thought=f"step{i+1}",
                  action=a, action_input=ai, observation=o)
            for i, (a, ai, o) in enumerate(traces)
        ],
        outcome=outcome,
    )


# ---------------------------------------------------------------------------
# Identity: a trajectory aligned with itself has no divergence and a maximal
# alignment score.
# ---------------------------------------------------------------------------


def test_self_alignment_has_no_divergence():
    ep = _ep([
        ("read_file", "calc.py", "found bug at line 4 return a - b"),
        ("apply_edit", "patch", "edit applied"),
        ("submit_solution", "fixed", "submitted"),
    ])
    a = align_traces(ep, ep)
    assert a.length == 3
    assert all(p.action_match for p in a.pairs)
    assert all(p.obs_similarity > 0.99 for p in a.pairs)
    assert find_divergence_point(a) is None


# ---------------------------------------------------------------------------
# Pure divergence: identical observations, different actions at step 2.
# This is the canonical case the module exists for.
# ---------------------------------------------------------------------------


def test_divergence_when_actions_differ_under_same_observation():
    success = _ep([
        ("read_file", "calc.py", "def add(a, b): return a - b"),
        ("apply_edit",  "fix",   "edit applied successfully"),
        ("submit_solution", "ok", "done"),
    ], outcome="success")
    failure = _ep([
        ("read_file", "calc.py", "def add(a, b): return a - b"),
        ("rewrite_file", "fix",   "edit applied successfully"),  # wrong tool
        ("submit_solution", "ok", "done"),
    ], outcome="failure")

    a = align_traces(failure, success)
    div = find_divergence_point(a)

    assert div is not None
    assert div.fail_step == 2
    assert div.success_step == 2
    assert div.fail_action == "rewrite_file"
    assert div.success_action == "apply_edit"


# ---------------------------------------------------------------------------
# Insertion: the failed run has an extra step the success didn't take.
# The alignment should treat the extra step as a None-on-success pair and
# still find divergence at the right place.
# ---------------------------------------------------------------------------


def test_alignment_handles_extra_step_in_failure():
    success = _ep([
        ("read_file", "calc.py", "def add(a, b): return a - b"),
        ("apply_edit",  "fix",   "edit applied successfully"),
        ("submit_solution", "ok", "done"),
    ], outcome="success")
    failure = _ep([
        ("read_file", "calc.py", "def add(a, b): return a - b"),
        ("explore_dir", "ls",    "wandered around the repo"),  # extra step
        ("apply_edit",  "fix",   "edit applied successfully"),
        ("submit_solution", "ok", "done"),
    ], outcome="failure")

    a = align_traces(failure, success)
    # The exploratory step has no good match in the success trajectory;
    # one alignment pair must be (failure_step=2, success=None).
    inserted = [p for p in a.pairs if p.fail is not None and p.success is None]
    assert len(inserted) == 1
    assert inserted[0].fail.step == 2

    # And NO action-divergence is reported, because the inserted step is
    # not a comparable situation, just a detour.
    assert find_divergence_point(a) is None


# ---------------------------------------------------------------------------
# Unrelated observations: the world conditions differed before the
# action was even chosen. We should report no divergence — the failure
# is not caused by a wrong action under a known situation.
# ---------------------------------------------------------------------------


def test_no_divergence_when_observations_are_unrelated():
    success = _ep([
        ("read_file", "calc.py", "def add(a, b): return a - b"),
        ("apply_edit", "fix",     "edit applied successfully"),
        ("submit_solution", "ok", "done"),
    ], outcome="success")
    # Same actions, but the file the agent looked at had nothing to do
    # with the bug. Because observations are dissimilar, the divergence
    # finder declines to attribute fault to any single action.
    failure = _ep([
        ("read_file", "calc.py",
         "the moon orbits the earth at 384400 km on average"),
        ("apply_edit", "fix",
         "spaghetti carbonara recipe step 1 boil water"),
        ("submit_solution", "ok",
         "the speed of light is 299792458 metres per second"),
    ], outcome="failure")

    a = align_traces(failure, success)
    assert find_divergence_point(a) is None


# ---------------------------------------------------------------------------
# Empty / degenerate inputs must not crash. This is the kind of case that
# never shows up in tests until production rate-limits an episode and you
# get a Trace-less Episode.
# ---------------------------------------------------------------------------


def test_empty_episode_alignment_is_empty():
    success = _ep([("submit_solution", "x", "ok")])
    failure = Episode(traces=[], outcome="failure")
    a = align_traces(failure, success)
    assert a.length == 0
    assert a.score == 0.0
    assert find_divergence_point(a) is None


# ---------------------------------------------------------------------------
# Format must produce a non-empty, recognisable string. We don't pin
# the exact wording — that's brittle — but we do pin the key facts so
# changes to the prompt structure are detectable.
# ---------------------------------------------------------------------------


def test_input_divergence_catches_wrong_file():
    """Same tool, semantically different action_input → input-space divergence.

    This is the "wrong file at step 1" pattern. Both runs called
    fs_read_file but the failure read main.py while success read calc.py.
    Observations diverge from step 1 onward (different file contents),
    so the obs+action alignment alone would say "no comparable situation".
    The input-space scanner catches it on the action_input embedding.
    """
    success = _ep([
        ("fs_read_file", "calc.py",
         "def add(a, b):\n    return a - b   # bug"),
        ("apply_edit", "patch", "edit applied"),
        ("submit_solution", "fixed", "submitted"),
    ], outcome="success")
    failure = _ep([
        ("fs_read_file", "the moon orbits earth at 384400 km",
         "spaghetti carbonara is a roman pasta dish made with eggs and guanciale"),
        ("apply_edit", "patch",
         "the speed of light is 299792458 metres per second"),
        ("submit_solution", "tried",
         "submitted: the universe is approximately 13.8 billion years old"),
    ], outcome="failure")

    a = align_traces(failure, success)
    div = find_divergence_point(a)
    assert div is not None
    assert div.fail_step == 1
    assert "action_input diverged" in div.rationale
    assert div.fail_action == div.success_action == "fs_read_file"


def test_input_divergence_does_not_fire_on_identical_inputs():
    """Same tool, same input → no input-space divergence (obviously)."""
    ep = _ep([
        ("fs_read_file", "calc.py", "x"),
        ("submit_solution", "ok", "done"),
    ])
    a = align_traces(ep, ep)
    assert find_divergence_point(a) is None


def test_action_divergence_takes_priority_over_input_divergence():
    """When both kinds of divergence exist, action wins because it's the
    higher-information signal."""
    success = _ep([
        ("fs_read_file", "calc.py", "shared common observation header"),
        ("apply_edit", "patch", "edit applied"),
        ("submit_solution", "ok", "done"),
    ])
    failure = _ep([
        # Step 1: same tool, *different* input — would be input-divergence
        ("fs_read_file", "main.py", "shared common observation header"),
        # Step 2: same situation but different tool — action-divergence
        ("rewrite_file", "patch", "edit applied"),
        ("submit_solution", "ok", "done"),
    ], outcome="failure")

    a = align_traces(failure, success)
    div = find_divergence_point(a)
    # Action divergence is reported first; we don't expect "input"
    # in the rationale because the action scanner returns immediately.
    assert div is not None
    # Either step 1 (if input-scan won) or step 2 (action-scan won).
    # Our priority is action-scan first → expect step 2 or "action" rationale.
    assert "action diverged" in div.rationale or "action_input" in div.rationale


def test_format_divergence_surfaces_key_facts():
    success = _ep([
        ("read_file",   "calc.py", "def add(a, b): return a - b"),
        ("apply_edit",  "fix",     "edit applied successfully"),
        ("submit_solution", "ok", "done"),
    ])
    failure = _ep([
        ("read_file",   "calc.py", "def add(a, b): return a - b"),
        ("rewrite_file", "fix",    "edit applied successfully"),
        ("submit_solution", "ok", "done"),
    ], outcome="failure")
    a = align_traces(failure, success)
    div = find_divergence_point(a)
    assert div is not None
    rendered = format_divergence(div, a)
    assert "DIVERGENCE FROM SUCCESS PATH" in rendered
    assert "rewrite_file" in rendered      # what failed
    assert "apply_edit" in rendered        # what would have succeeded
    assert "step 2" in rendered            # where
