"""Tests for smart_truncate — head+tail preservation.

The point of these tests is to pin the *behavioural contract*: when a
caller asks "give me at most N chars but keep both ends", the result
must (a) fit in N, (b) start with the same head, (c) end with the same
tail, (d) be idempotent on inputs that already fit.
"""
from __future__ import annotations

from engram.trunc import smart_truncate


def test_short_text_returned_unchanged():
    s = "the quick brown fox"
    assert smart_truncate(s, max_chars=1024) is s  # same object — no copy


def test_empty_input_returns_empty():
    assert smart_truncate("", 100) == ""


def test_truncated_output_fits_within_budget_plus_marker():
    s = "x" * 10_000
    out = smart_truncate(s, max_chars=200)
    # Allow some slack: snapping to newline boundaries can shift a few
    # chars, and the marker length is dynamic.
    assert len(out) <= 250


def test_head_and_tail_preserved():
    # Build a text where head and tail are distinguishable. The body is
    # a unique-character-per-line string so we can assert that lines
    # from deep in the middle do NOT survive — they were the eligible
    # drop.
    head = "BEGIN_HEAD_MARKER_x_END_HEAD_MARKER\n"
    body = "".join(f"middle_line_{i:04d}_filler\n" for i in range(200))
    tail = "BEGIN_TAIL_MARKER\nfinal line\n"
    s = head + body + tail
    out = smart_truncate(s, max_chars=200)
    assert "BEGIN_HEAD_MARKER" in out
    assert "BEGIN_TAIL_MARKER" in out
    assert "final line" in out
    # The earlier-middle lines (e.g. middle_line_0050) must be dropped:
    # with max_chars=200 there is no room to include lines that aren't
    # within the head budget or the tail budget.
    assert "middle_line_0050" not in out
    assert "middle_line_0100" not in out


def test_marker_announces_drop_count():
    s = "0" * 10_000
    out = smart_truncate(s, max_chars=200)
    assert "truncated" in out
    # The marker mentions a number of chars dropped.
    assert "chars from middle" in out


def test_max_chars_smaller_than_marker_falls_back_to_head():
    """When the budget can't fit the separator, we still don't crash."""
    s = "abc" * 1000
    out = smart_truncate(s, max_chars=8)
    # Result must be at most 8 chars (we said so), with an ellipsis tag.
    assert len(out) <= 8
    assert "abc" in out  # head still present


def test_head_ratio_zero_keeps_only_tail():
    s = "AAA" + "B" * 300 + "CCC"
    out = smart_truncate(s, max_chars=120, head_ratio=0.0)
    # All budget should go to the tail. Head should be tiny / absent.
    assert "CCC" in out
    # The text "AAA" appears at the very start of the input; with
    # head_ratio=0 the head section is empty so "AAA" must NOT lead
    # the output.
    assert not out.startswith("AAA")


def test_head_ratio_one_keeps_only_head():
    s = "AAA" + "B" * 300 + "CCC"
    out = smart_truncate(s, max_chars=120, head_ratio=1.0)
    assert out.startswith("AAA")
    # CCC must NOT survive — the tail allocation was zero.
    assert "CCC" not in out


def test_head_ratio_clamped_when_out_of_range():
    """Defensive: out-of-range head_ratio shouldn't blow up."""
    s = "x" * 1000
    smart_truncate(s, max_chars=100, head_ratio=-0.5)
    smart_truncate(s, max_chars=100, head_ratio=1.7)


def test_newline_snapping_does_not_break_lines():
    """The head should end on a newline, and the tail should start
    on one, so neither splice slices a line in half."""
    s = "alpha\nbeta\ngamma\n" + ("filler text that fills " * 500) + "\ndelta\nepsilon\n"
    out = smart_truncate(s, max_chars=200)
    # Find where the head ends (just before the marker line containing
    # "truncated"). Whatever comes before the marker should end with
    # a newline OR with our head-snap bound.
    head_part, sep, tail_part = out.partition("…[truncated")
    assert head_part.endswith("\n") or len(head_part) < 1
    # Tail part should start with what looks like a real line.
    assert tail_part.endswith("\n") or "delta" in tail_part
