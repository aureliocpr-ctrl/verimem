"""LLM-refined atomic extraction from narration (verimem.narration_llm).

The rule-based ``verimem.narration.extract_atomic_candidates`` only keeps clauses
that already carry a verifiable anchor (commit SHA / PR# / file:line). This RAISES
recall by asking an LLM to pull the atomic, verifiable factual claims out of a
session narrative — with the same anti-confabulation discipline as
``verimem.openie``: a JSON-only contract, ONE retry on a malformed parse, and an
empty list on a second failure. A bad model response NEVER crashes and NEVER
yields a fabricated parse.

The ``llm`` is any object exposing ``complete(system, messages, …) -> resp`` (with
``resp.text`` the model output) — i.e. ``verimem.llm.get_llm()``, which in HOSTED
MODE routes via MCP sampling to the active subscription (zero external API cost).
Pure given the llm; testable with a fake.
"""
from __future__ import annotations

import json
from typing import Any

ATOMIC_EXTRACT_SYSTEM = (
    "You extract ATOMIC, VERIFIABLE factual claims from a session narrative.\n"
    'Output MUST be a single JSON object: {"claims": [str, ...]}.\n'
    "Rules:\n"
    "1. Output ONLY valid JSON. No prose, no markdown fences, no code blocks.\n"
    "2. Each claim is ONE self-contained, checkable fact — PREFER ones that cite "
    "concrete evidence: a commit SHA, a PR number, a file:line, a measured number.\n"
    "3. DROP vague plans ('PROSSIMO: …', 'next'), opinions, and time-bound framing "
    "('stasera', 'oggi', 'this session') — keep the durable, atemporal fact.\n"
    "4. Do NOT invent anything not present in the narrative. If unsure, omit it.\n"
    '5. If there is nothing atomic and verifiable, return {"claims": []}.'
)


def _parse_claims(text: str | None) -> list[str] | None:
    """Strict JSON parse → list of non-empty claim strings, or None if malformed."""
    try:
        data = json.loads((text or "").strip())
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    claims = data.get("claims")
    if not isinstance(claims, list):
        return None
    return [c.strip() for c in claims if isinstance(c, str) and c.strip()]


def extract_atomic_facts(
    narration: str | None, llm: Any, *, max_claims: int = 12,
) -> list[str]:
    """Ask ``llm`` to extract atomic verifiable claims from ``narration``.

    Anti-confab (mirrors ``verimem.openie``): JSON-only contract, ONE retry on a
    malformed parse ('fix the JSON'), and ``[]`` on a second failure — a broken
    model response degrades to empty, never a crash or a fabricated parse.
    Returns de-duplicated (case-folded) claims capped at ``max_claims``. Safe on
    empty input or a missing llm.
    """
    text = (narration or "").strip()
    if not text or llm is None:
        return []
    messages = [{"role": "user", "content": text}]
    try:
        resp = llm.complete(system=ATOMIC_EXTRACT_SYSTEM, messages=messages)
        claims = _parse_claims(getattr(resp, "text", None))
        if claims is None:
            resp = llm.complete(
                system=ATOMIC_EXTRACT_SYSTEM,
                messages=messages + [
                    {"role": "assistant", "content": getattr(resp, "text", "") or ""},
                    {"role": "user",
                     "content": "Fix the JSON syntax. Output ONLY the JSON object."},
                ],
            )
            claims = _parse_claims(getattr(resp, "text", None))
    except Exception:  # noqa: BLE001 — a broken LLM call must degrade to []
        return []
    if not claims:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for c in claims:
        key = c.lower()
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out[:max_claims]


__all__ = ["extract_atomic_facts", "ATOMIC_EXTRACT_SYSTEM"]
