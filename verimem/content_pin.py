"""Content-bound receipts (D5 / task #44): pin WHAT was cited, not just where.

The provenance verifier answers *resolvability*: does ``file:<path>:<line>``
point at a file with at least that many lines? Nothing in the receipt records
what that line SAID, so a later read cannot tell whether the evidence still
supports the claim — the TOCTOU Kimi-K3 raised on the P0 design (2026-07-22):
pin the hash of the matched span, not the path and line.

A pin is a signal, never a verdict. Evidence that moved or changed does not
retroactively falsify a fact; it makes the receipt honest that what was read
then is not what is there now. `stale` is an orthogonal axis (D5), and
conflating it with truth would be its own confabulation.

Four outcomes, four different truths:

``ok``
    the cited line still reads the same;
``moved``
    the same text lives elsewhere in the file — an insertion above the
    citation is the ordinary case, and calling that a content change would
    make the signal useless within a day;
``changed``
    that line now says something else;
``unresolvable``
    the file or the line is gone, or there is no pin to compare — nothing can
    be said, and "nothing can be said" must never read as "verified".

Containment is the verifier's rule, unchanged: without a ``repo_root`` no path
is opened at all (CodeQL 2026-07-18 — a tenant-supplied absolute ref must not
probe arbitrary server files).
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

__all__ = ["PIN_PREFIX", "pin_for_ref", "verify_pin"]

PIN_PREFIX = "sha256:"

#: Same shape the provenance verifier accepts: ``file:<path>:<lineno>``.
_FILE_REF = re.compile(r"^file:(.+):(\d+)$", re.IGNORECASE)

#: Reading a whole file to hash one line is wasteful and, on a pathological
#: input, unbounded. Citations live near the top of sane files; past this we
#: decline to pin rather than stream a gigabyte.
_MAX_LINES = 200_000


def _normalise(line: str) -> str:
    """Trailing whitespace and the line ending are not content.

    A CRLF checkout must not read as a modified file — that would be an alarm
    every developer learns to ignore, which is worse than no alarm.
    """
    return line.rstrip("\r\n").rstrip()


def _digest(text: str) -> str:
    return PIN_PREFIX + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _resolve(path_str: str, repo_root: Path | str | None) -> Path | None:
    """Resolve a ref's path under the containment root, or None."""
    if repo_root is None:
        return None
    try:
        root = Path(repo_root).resolve()
    except OSError:
        return None
    p = Path(path_str)
    try:
        p = (p if p.is_absolute() else root / p).resolve()
    except OSError:
        return None
    try:
        p.relative_to(root)
    except ValueError:
        return None                      # symlink-out-of-root / traversal
    return p if (p.exists() and p.is_file()) else None


def _read_lines(path: Path) -> list[str] | None:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            out: list[str] = []
            for i, line in enumerate(f):
                if i >= _MAX_LINES:
                    return None
                out.append(line)
        return out
    except OSError:
        return None


def _cited_line(ref: str, repo_root: Path | str | None
                ) -> tuple[str | None, list[str] | None]:
    """(the cited line, all lines) — either may be None when unreadable."""
    m = _FILE_REF.match((ref or "").strip())
    if m is None:
        return None, None
    path_str, lineno_str = m.group(1), m.group(2)
    try:
        lineno = int(lineno_str)
    except ValueError:
        return None, None
    if lineno < 1:
        return None, None
    p = _resolve(path_str, repo_root)
    if p is None:
        return None, None
    lines = _read_lines(p)
    if lines is None or lineno > len(lines):
        return None, lines
    return lines[lineno - 1], lines


def pin_for_ref(ref: str, *, repo_root: Path | str | None) -> str | None:
    """``sha256:<hex>`` of the line ``ref`` cites — or None when it cannot be
    read (non-file ref, no containment root, path outside it, missing file,
    line past the end). None means "no claim", never "no change"."""
    line, _lines = _cited_line(ref, repo_root)
    return None if line is None else _digest(_normalise(line))


def verify_pin(ref: str, pin: str | None, *,
               repo_root: Path | str | None) -> str:
    """Compare a recorded pin against the evidence as it is NOW.

    Returns ``ok`` / ``moved`` / ``changed`` / ``unresolvable``. A receipt with
    no pin (written before pinning existed) is ``unresolvable`` — the honest
    answer, and the one that cannot be mistaken for a verification.
    """
    if not isinstance(pin, str) or not pin.strip():
        return "unresolvable"
    line, lines = _cited_line(ref, repo_root)
    if line is None:
        return "unresolvable"
    if _digest(_normalise(line)) == pin.strip():
        return "ok"
    if lines and any(_digest(_normalise(x)) == pin.strip() for x in lines):
        return "moved"
    return "changed"
