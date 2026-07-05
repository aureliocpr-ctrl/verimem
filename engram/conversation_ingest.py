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

#: Consolidation pass (iter 35, mandate "beat them on every axis"): raw atomic
#: extraction over-produces (~37 facts vs ~20 gold on HaluMem -> precision 0.65
#: is the F1 bottleneck). This pass merges near-duplicates and drops
#: non-durable trivia while KEEPING every distinct durable fact.
CONSOLIDATE_SYSTEM = (
    "You are cleaning a list of extracted memory facts. Rules:\n"
    "- MERGE lines that state the same fact in different words into ONE line "
    "(keep the most complete phrasing).\n"
    "- DROP lines that are not durable memories: greetings, meta-talk about the "
    "conversation itself, restatements of the assistant's replies, transient "
    "chit-chat with no future value.\n"
    "- KEEP every distinct durable fact — do NOT summarize several facts into "
    "one, do NOT drop minor but durable details (dates, names, reasons).\n"
    "- Keep each line ATOMIC (one attribute per line) and starting with the "
    "person's full name.\n"
    "Return the cleaned list, one fact per line, no numbering, no preamble.")

#: Gap-fill / completeness pass (iter 36, mandate "beat them on EVERY axis" —
#: MemOS extraction is 79.7 and consolidation trades ~2pp recall for precision,
#: so recall is the other half of the climb toward F1 > 0.80). Given the
#: dialogue AND the facts already extracted, name ONLY the durable facts that
#: are stated but MISSING — a targeted second look, not a blind re-extract.
GAPFILL_SYSTEM = (
    "You are given a conversation and a list of memory facts ALREADY extracted "
    "from it. Your job: find durable memory facts the conversation STATES but "
    "that are MISSING from the list. Rules:\n"
    "- Output ONLY facts that are missing — never repeat a fact already listed.\n"
    "- Only facts the dialogue actually states — never invent or infer beyond it.\n"
    "- ATOMIC: one attribute per line, starting with the person's full name.\n"
    "- If nothing durable is missing, return an empty response.\n"
    "One missing fact per line, no numbering, no preamble.")

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
    consolidate: bool = True,
    completeness: bool = False,
    embed: str | None = None,
) -> dict:
    """Extract ATOMIC facts from ``messages`` and store each through the gate.

    ``completeness`` (opt-in, recall lever): a gap-fill LLM pass names durable
    facts the dialogue states but the first extraction missed, run BEFORE
    consolidation (extract -> gap-fill -> consolidate). Off by default until the
    A/B proves the recall gain is worth the extra pass.

    ``consolidate`` (default ON, quality-first): a 2nd LLM pass merges
    near-duplicates and drops trivia, lifting precision +8pp / F1 +3.3pp
    (measured u5s6 2026-07-05). Set ``consolidate=False`` for a single-pass /
    lower-latency ingest.

    Returns ``{"stored", "rejected", "fact_ids", "extracted", "gapfilled",
    "consolidated", "error"}``. Fail-safe end to end: an LLM error reports
    instead of raising; a fact the store gate rejects is counted, never
    re-tried blindly.
    """
    from .redaction import redact_secrets
    from .semantic import Fact

    res: dict = {"stored": 0, "rejected": 0, "fact_ids": [],
                 "extracted": 0, "gapfilled": 0, "consolidated": 0,
                 "error": None}
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
    if completeness and lines:
        extra = gapfill_facts(dialogue, lines, llm=llm,
                              max_out_tokens=max_out_tokens)
        lines = lines + extra
        res["gapfilled"] = len(extra)
    if consolidate and lines:
        lines = consolidate_facts(lines, llm=llm, max_out_tokens=max_out_tokens)
        res["consolidated"] = len(lines)
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


def gapfill_facts(dialogue: str, facts: list[str], *, llm: Any,
                  max_out_tokens: int = 1200) -> list[str]:
    """Return durable facts the ``dialogue`` STATES but ``facts`` missed (the
    recall pass). Additive-only and fail-safe: on any LLM error, or nothing new,
    returns ``[]`` — a gap-fill can only ADD, never lose the base extraction.
    Deduplicated against ``facts`` by normalized text so the pass never
    re-emits what we already have."""
    if not dialogue:
        return []
    have = {f.strip().casefold() for f in facts}
    try:
        r = llm.complete(
            GAPFILL_SYSTEM,
            [{"role": "user",
              "content": f"Conversation:\n{dialogue}\n\nAlready extracted:\n"
                         + "\n".join(facts) + "\n\nMissing facts:"}],
            max_tokens=max_out_tokens)
        found = parse_extracted_lines(getattr(r, "text", "") or "")
    except Exception:  # noqa: BLE001 — a gap-fill must never crash the ingest
        return []
    out, seen = [], set(have)
    for f in found:
        k = f.strip().casefold()
        if k and k not in seen:
            seen.add(k)
            out.append(f)
    return out


def consolidate_facts(facts: list[str], *, llm: Any,
                      max_out_tokens: int = 1200) -> list[str]:
    """Merge near-duplicates and drop non-durable trivia from an extracted fact
    list (the precision pass). Fail-safe: on any LLM error, or if the pass
    returns nothing, the ORIGINAL list is returned unchanged — consolidation can
    only refine, never lose everything."""
    if not facts:
        return []
    try:
        r = llm.complete(
            CONSOLIDATE_SYSTEM,
            [{"role": "user",
              "content": "Facts:\n" + "\n".join(facts) + "\n\nCleaned:"}],
            max_tokens=max_out_tokens)
        cleaned = parse_extracted_lines(getattr(r, "text", "") or "")
    except Exception:  # noqa: BLE001 — the pass must never lose the extraction
        return facts
    return cleaned if cleaned else facts


__all__ = [
    "ATOMIC_EXTRACT_SYSTEM", "CONSOLIDATE_SYSTEM", "GAPFILL_SYSTEM",
    "INGEST_WRITER_ROLE", "conversation_provenance_ref",
    "parse_extracted_lines", "render_conversation", "ingest_conversation",
    "consolidate_facts", "gapfill_facts",
]
