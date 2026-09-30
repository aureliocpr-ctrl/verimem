"""Cycle 168 (2026-05-22) — LLM-augmented trigger_keywords extraction.

Pure function that delegates *concept-level* keyword extraction to an
*injected* LLM callable. The cycle-162 rule-based populator produced
shallow, wordy tags (``"stress,test,worker,write"``); this primitive
bumps quality by structuring an LLM prompt that returns deduplicated,
lowercase, hyphen-separated *concepts*
(``"write-concurrency,ci-pipeline,regression-testing"``).

Subscription-only contract (CLAUDE.md O4)
-----------------------------------------
The ``llm_callable`` injection point keeps this module **provider-
agnostic and key-free**. In production wire it to:
  * ``mcp__engram-bridge__ask_claude`` (host's Claude Code session,
    subscription-only) -- recommended default;
  * an in-process sampling helper (MCP host pattern) when running
    inside the MCP server;
  * a deterministic stub for unit tests / replay.

Do NOT instantiate ``anthropic.Anthropic`` or ``openai.OpenAI`` clients
inside this module -- those paths would require an external API key
and violate the subscription-only invariant.

Failure-mode contract
---------------------
This function is meant to be batched over the 277 facts with empty
``trigger_keywords`` (corpus audit 2026-05-22) and the 1388 with
shallow rule-based output. *One bad LLM call must not abort the loop.*
Every failure path returns ``[]`` and silently swallows the cause:

  * empty / whitespace-only ``text`` -- no LLM call, ``[]``;
  * LLM raises -- ``[]`` (caller may log, this module stays mute);
  * malformed JSON -- ``[]``;
  * missing / non-list ``keywords`` field -- ``[]``.

Output normalisation
--------------------
Each keyword is lowercased, stripped, and whitespace runs are
collapsed into a single hyphen (``" regression  testing "`` ->
``"regression-testing"``). Duplicates are removed case-insensitively
**after** normalisation, so the LLM can mix cases without
introducing noise.
"""
from __future__ import annotations

import json
from collections.abc import Callable

#: Prompt template. Keep the JSON-only output instruction explicit --
#: in pilot runs the model occasionally wraps the payload in markdown
#: fences, which json.loads can't parse. The "Output JSON only" line
#: in combination with "JSON:" suffix proved to suppress that in
#: the rule-based bench (see fact b0ac1291108f for empirical context).
_PROMPT_TEMPLATE = """You are a knowledge engineer. Extract {n_min}-{n_max} \
concept-level trigger keywords from the text below. Output STRICT JSON:
{{"keywords": ["kw1", "kw2", ...]}}

Rules:
- Each keyword: lowercase, hyphen-separated (e.g. "regression-testing"),
  NO spaces inside a keyword.
- Concept-level: abstract topic tags, NOT verbatim words from the text.
- Deduplicate. Avoid stopwords ("the", "a", "and", ...).
- Output JSON only -- NO prose, NO markdown fences, NO code blocks.

Text to extract from:
\"\"\"
{text}
\"\"\"

JSON:"""


def _normalise(raw: str) -> str:
    """Collapse whitespace runs to single hyphen, lowercase, strip."""
    parts = raw.strip().lower().split()
    return "-".join(parts)


def _strip_markdown_fences(raw: str) -> str:
    r"""Strip leading / trailing markdown code fences.

    Empirical observation 2026-05-22 (ask_claude haiku low-effort):
    despite the prompt forbidding markdown, the model wraps the JSON
    payload in ``​\`\`\`json ... ​\`\`\``` fences. ``json.loads`` chokes on
    them, so the smoke test on fact ``a232e5c15c76`` returned ``[]``.
    This helper makes the parser tolerant: a one-line markdown wrapper
    around valid JSON is reduced to the JSON body.

    The strip is intentionally narrow -- only fences at start/end --
    so any in-text backticks (e.g. inline ``​\`code\`​``) are preserved
    and do not corrupt the payload.
    """
    s = raw.strip()
    if s.startswith("```"):
        # Drop the opening fence + optional language tag up to first newline.
        first_newline = s.find("\n")
        s = s[first_newline + 1:] if first_newline > 0 else s[3:]
    if s.endswith("```"):
        s = s[:-3]
    return s.strip()


def extract_keywords(
    text: str,
    *,
    llm_callable: Callable[[str], str],
    n_min: int = 5,
    n_max: int = 10,
) -> list[str]:
    """Return up to ``n_max`` concept-level trigger keywords for ``text``.

    Args:
        text: the proposition / fact body to extract keywords from.
            Empty or whitespace-only input short-circuits to ``[]``
            without invoking the LLM (cost-control on batch runs).
        llm_callable: ``(prompt: str) -> str`` returning the LLM's
            raw response. Production wires this to a subscription-only
            channel (see module docstring); tests inject a mock.
        n_min: hint for the LLM minimum (NOT enforced -- if the model
            returns fewer items we use what we got, no fabrication).
        n_max: hard cap on the returned list length.

    Returns:
        ``list[str]`` of normalised keywords (lowercase, hyphenated,
        deduplicated case-insensitively). Empty list on any failure
        mode -- never raises.
    """
    if not text or not text.strip():
        return []
    prompt = _PROMPT_TEMPLATE.format(
        n_min=int(n_min), n_max=int(n_max), text=text,
    )
    try:
        raw = llm_callable(prompt)
    except Exception:
        return []
    try:
        payload = json.loads(_strip_markdown_fences(raw))
    except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
        return []
    if not isinstance(payload, dict):
        return []
    kws_raw = payload.get("keywords")
    if not isinstance(kws_raw, list):
        return []
    seen: set[str] = set()
    out: list[str] = []
    for k in kws_raw:
        if not isinstance(k, str):
            continue
        norm = _normalise(k)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
        if len(out) >= int(n_max):
            break
    return out


__all__ = ["extract_keywords"]
