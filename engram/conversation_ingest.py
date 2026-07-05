"""Conversation ingestion — the product API for "give me a conversation, I
extract the memories" (iter 34, 2026-07-05).

Why this exists: the atomic-extraction win (HaluMem F1 0.6499 -> 0.71-0.74,
benchmark/halumem_extraction_f1.py) lived only in the benchmark harness, while
the product path (transcript_promote) promotes single turns VERBATIM by hand.
mem0/Zep ship "add(messages) -> memories" as their core. This module ships it
with what they don't have:

  * the WINNING atomic granularity — ``ATOMIC_EXTRACT_SYSTEM`` is the single
    source of truth, imported by the benchmark, so a bench win IS a product win;
  * every extracted fact enters through ``SemanticMemory.store`` = the full
    anti-confab gate (status stays ``model_claim`` — claims, never laundered
    truth), secret redaction, and reconcile-on-write when enabled;
  * per-conversation PROVENANCE on every fact (``conversation:<id>``) and a
    dedicated ``writer_role`` (never a trusted hook — no gate bypass).

The LLM is INJECTED (anything with ``.complete(system, messages, **kw)``):
provider-agnostic, hermetic in tests, hosted-sampling-friendly in MCP.
"""
from __future__ import annotations

from typing import Any

#: The extraction prompt that won the granularity A/B (iter 19-22): HaluMem gold
#: points are atomic, subject-named and exhaustive; compound facts match at most
#: one gold at the e5 threshold and a small output cap truncates dense sessions.
ATOMIC_EXTRACT_SYSTEM = (
    "Extract EVERY durable memory fact a personal assistant should store from this "
    "conversation — identity, relationships, preferences (likes AND dislikes), events, "
    "plans, health, work, reasons. Rules:\n"
    "- ATOMIC: exactly ONE attribute or fact per line; if a sentence carries several "
    "(a preference + its reason + a date), split them into separate lines.\n"
    "- Start every line with the user's full name (never a pronoun).\n"
    "- Be EXHAUSTIVE: list every stable fact the dialogue states, including minor ones.\n"
    "- Only facts the dialogue actually states — never invent or infer beyond it.\n"
    "One fact per line, no numbering, no preamble.")

#: writer_role of ingested facts: NOT a trusted hook -> the full gate runs.
INGEST_WRITER_ROLE = "conversational_ingest"


def conversation_provenance_ref(conversation_id: str) -> str:
    """Stable, namespaced provenance ref for facts born from a conversation."""
    return f"conversation:{conversation_id}"


def parse_extracted_lines(text: str) -> list[str]:
    """One fact per non-empty line, bullets/numbering stripped (same parsing the
    benchmark validated)."""
    out: list[str] = []
    for line in (text or "").splitlines():
        s = line.strip().lstrip("-*•0123456789. ").strip()
        if len(s) > 4:
            out.append(s)
    return out


def render_conversation(messages: list[dict], *, cap_chars: int = 12000) -> str:
    """``role: content`` lines, capped (mirrors the benchmark's session_text)."""
    lines = []
    for m in messages or []:
        c = (m.get("content") or "").strip()
        if c:
            lines.append(f"{m.get('role', '?')}: {c}")
    return "\n".join(lines)[:cap_chars]


def ingest_conversation(
    semantic_memory,
    messages: list[dict],
    *,
    llm: Any,
    conversation_id: str,
    topic: str = "conversational/ingested",
    confidence: float = 0.5,
    max_out_tokens: int = 1200,
    embed: str | None = None,
) -> dict:
    """Extract ATOMIC facts from ``messages`` and store each through the gate.

    Returns ``{"stored", "rejected", "fact_ids", "extracted", "error"}``.
    Fail-safe end to end: an LLM error reports instead of raising; a fact the
    store gate rejects is counted, never re-tried blindly.
    """
    from .redaction import redact_secrets
    from .semantic import Fact

    res: dict = {"stored": 0, "rejected": 0, "fact_ids": [],
                 "extracted": 0, "error": None}
    dialogue = render_conversation(messages)
    if not dialogue:
        return res
    try:
        r = llm.complete(
            ATOMIC_EXTRACT_SYSTEM,
            [{"role": "user",
              "content": f"Conversation:\n{dialogue}\n\nFacts:"}],
            max_tokens=max_out_tokens)
        raw = (getattr(r, "text", "") or "")
    except Exception as exc:  # noqa: BLE001 — ingest must never crash the caller
        res["error"] = f"extraction llm error: {exc!s:.120}"
        return res

    lines = parse_extracted_lines(raw)
    res["extracted"] = len(lines)
    prov = conversation_provenance_ref(conversation_id)
    for prop in lines:
        prop, _ = redact_secrets(prop)
        fact = Fact(
            proposition=prop,
            topic=topic,
            confidence=confidence,
            status="model_claim",          # a claim, never laundered truth
            source_episodes=[prov],
            writer_role=INGEST_WRITER_ROLE,
        )
        try:
            if embed is not None:
                semantic_memory.store(fact, embed=embed)
            else:
                semantic_memory.store(fact)
            res["stored"] += 1
            res["fact_ids"].append(fact.id)
        except Exception:  # noqa: BLE001 — one rejected fact must not stop the rest
            res["rejected"] += 1
    return res


__all__ = [
    "ATOMIC_EXTRACT_SYSTEM", "INGEST_WRITER_ROLE", "conversation_provenance_ref",
    "parse_extracted_lines", "render_conversation", "ingest_conversation",
]
