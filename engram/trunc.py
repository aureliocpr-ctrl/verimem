"""Smart truncation utility — preserves head AND tail of long output.

Why this exists, in one line:
  When a Python script raises, the traceback is at the *bottom* of stderr.
  When a tool dumps 1 MB to stdout, naive head-truncation throws away the
  most diagnostic part. Splitting the budget between head and tail keeps
  both the prelude (what the script set out to do) and the resolution
  (what actually happened, including the error).

Public API:
  • `smart_truncate(text, max_chars, head_ratio=0.6) -> str`

Design choices:
  - Default head_ratio 0.6: tracebacks are typically a handful of frames
    + a single error line, so 40% of the budget for the tail is plenty.
    For pure-progress logs (training output etc.), head bias still
    captures the most informative prefix.
  - We render a clearly-marked separator so a downstream parser (or the
    LLM) can recognise that the middle was elided.
  - Idempotent: smart_truncate(s, max) where len(s) <= max returns s
    unchanged. No allocation, no copy.
  - Newline-aware: when possible we cut at a newline boundary so the
    head doesn't end mid-line. The tail starts at a newline boundary too.
"""
from __future__ import annotations

# Marker used between head and tail. Chosen for being recognisable by
# both humans and a downstream parser, and short enough to not eat the
# token budget the truncation is meant to preserve.
_DEFAULT_MARKER = "\n…[truncated {dropped} chars from middle]…\n"


def smart_truncate(
    text: str,
    max_chars: int,
    *,
    head_ratio: float = 0.6,
    marker: str = _DEFAULT_MARKER,
) -> str:
    """Return `text` capped to `max_chars`, preserving head AND tail.

    If `len(text) <= max_chars` the input is returned unchanged.

    The remaining budget is split between head (`head_ratio`) and tail
    (`1 - head_ratio`). When possible, both cuts snap to a newline so
    we don't slice mid-line.

    Edge cases handled:
      • max_chars <= len(marker)+2 → fall back to plain head-truncation
        (the marker would not fit; preserve as much head as possible).
      • head_ratio outside [0, 1] → clamped.
      • text shorter than max_chars → returned unchanged.
      • Empty text → empty string.
      • marker uses {dropped} placeholder; if you pass a marker with no
        placeholder we still substitute correctly (str.format ignores
        unknown fields).
    """
    if not text:
        return ""
    n = len(text)
    if n <= max_chars:
        return text

    # Clamp head_ratio to a sane range — defensive; bad inputs upstream
    # shouldn't crash a logging utility.
    head_ratio = max(0.0, min(1.0, head_ratio))

    # Render the separator with the placeholder filled. The exact length
    # depends on `dropped`, which we can compute now (we know the cut
    # boundaries below). To avoid a chicken-and-egg dependency we render
    # a one-shot estimate and trust it — small variation is acceptable.
    dropped_estimate = n - max_chars
    sep = marker.format(dropped=dropped_estimate)

    # If the marker alone eats more than the budget, no smart split is
    # possible. Fall back to plain head truncation with an inline tag.
    if len(sep) + 2 >= max_chars:
        return text[: max_chars - 1] + "…"

    available = max_chars - len(sep)
    head_len = int(available * head_ratio)
    tail_len = available - head_len

    head_end = head_len
    tail_start = n - tail_len

    # Snap head_end backward to the previous newline (preserve line
    # boundary) — but only if the snap stays within the same step (no
    # giving up more than 80 chars to a far-away newline).
    nl = text.rfind("\n", max(0, head_end - 80), head_end)
    if nl != -1:
        head_end = nl

    # Snap tail_start forward to the next newline.
    nl_t = text.find("\n", tail_start, min(n, tail_start + 80))
    if nl_t != -1:
        tail_start = nl_t + 1

    # Re-render the marker with the actual dropped count post-snap.
    dropped_final = max(0, tail_start - head_end)
    sep = marker.format(dropped=dropped_final)

    return text[:head_end] + sep + text[tail_start:]
