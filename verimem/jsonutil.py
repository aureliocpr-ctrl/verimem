"""Shared JSON parsing helpers — single source of truth.

Until FORGIA pezzo #28/#31 every module that needed to parse a JSON
object from an LLM response had its own ad-hoc `_extract_json`. The
local copies drifted: some forgot the `isinstance(parsed, dict)` guard,
producing the `'int' is not iterable` crash class. This module is the
canonical implementation; new callers should import from here.

Existing local copies in `sleep.py` and `compilation.py` remain (with
the fix applied) for backward-compatibility — they delegate to this
helper or duplicate its body. New code should use `extract_json_object`.
"""
from __future__ import annotations

import json
import re
from typing import Any


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Extract a JSON OBJECT (dict) from a possibly-wrapped LLM response.

    Accepts:
      - bare JSON object  ``{"k": "v"}``
      - object inside ``\\n``json fences``\\n``
      - object embedded in surrounding prose (regex first ``{...}``)

    Rejects (returns None) any of:
      - JSON scalar (``"4"``, ``"hello"``, ``true``, ``null``)
      - JSON array (``[1, 2, 3]``)
      - non-JSON garbage

    The dict-only contract is what every caller actually wants;
    returning a scalar to a caller doing ``"key" in data`` crashes
    with ``TypeError: argument of type 'int' is not iterable``.

    Args:
      text: raw LLM output (whitespace tolerated, fences stripped).

    Returns:
      A ``dict[str, Any]`` on success, ``None`` otherwise.
    """
    if not isinstance(text, str):
        return None
    s = text.strip()
    # Strip ```json fences if present.
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    try:
        parsed = json.loads(s)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", s, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                return None
    return None
