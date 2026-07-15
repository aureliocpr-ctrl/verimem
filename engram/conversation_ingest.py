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
    "DIFFERENT facts (a preference + its reason), split them into separate lines.\n"
    "- An ENUMERATION of values of the SAME attribute is ONE fact — keep the whole "
    "list on one line ('dislikes snakes and cats'), never split it across lines.\n"
    "- Keep each fact's own date or qualifier ON the same line as the fact "
    "('switched to classical music on 2043-07-10') — a date split onto its own "
    "line is an orphan that answers nothing.\n"
    "- Start every line with the speaker's full name AS STATED IN THE CONVERSATION "
    "TEXT (never a pronoun). If the conversation never states a name, write "
    "'The user'. NEVER use a name that does not appear in the conversation itself "
    "— a name known from outside this text is contamination, not memory.\n"
    "- Be EXHAUSTIVE: list every stable fact the dialogue states, including minor ones.\n"
    "- Only facts the dialogue actually states — never invent or infer beyond it.\n"
    "One fact per line, no numbering, no preamble.")


#: Tier-2 piggyback (2026-07-08, CONVERSATIONAL_ENTITY_DESIGN.md): typed
#: entities asked for in the SAME extraction call — zero extra LLM cost. One
#: final line OUTSIDE the fact list, so the consolidate pass (which only sees
#: fact lines) can never eat it. The regex tier stays as the floor; these are
#: additive and idempotent at populate time.
_TYPED_ENTITIES_INSTRUCTION = (
    "\n- After ALL fact lines, add exactly ONE final line starting with "
    "'ENTITIES: ' listing the people, places, organizations, activities and "
    "life events EXPLICITLY mentioned in the conversation, as 'type:Name' "
    "pairs separated by '; ' (types: person, place, org, activity, event). "
    "Only entities the conversation text actually names — never infer. "
    "Example: ENTITIES: person:Emily; place:Kyoto; event:promotion")

_ENTITY_TYPES = {"person", "place", "org", "organization", "activity", "event"}


#: Giro 2 (2026-07-16): origin tag for the anti-sycophancy write path. When
#: ``tag_beliefs`` is on, the extractor prefixes an UNVERIFIED FACTUAL ASSERTION
#: with this marker; the store loop maps that one line to status="user_belief"
#: (ranked below model_claim, hidden from default recall) instead of laundering
#: it as a model_claim. Preferences/opinions/identity/grounded-facts are never
#: tagged — the split is biased toward KEEPING personalization in recall.
_BELIEF_MARKER = "BELIEF:"

_BELIEF_EXTRACT_INSTRUCTION = (
    "\n- ORIGIN TAG: prefix a line with 'BELIEF: ' ONLY when it is an UNVERIFIED "
    "FACTUAL ASSERTION — a checkable claim about the external world (e.g. 'X is "
    "faster than Y', 'the deploy is green', 'their API is the best') that the "
    "conversation does NOT substantiate. NEVER tag preferences, opinions, "
    "identity, relationships, plans, or facts the dialogue itself grounds — those "
    "are stored normally. When unsure, do NOT tag.")

_BELIEF_CONSOLIDATE_INSTRUCTION = (
    "\n- Keep the 'BELIEF: ' prefix on every line that already starts with it "
    "(and add it to no other line).")


def split_entities_line(text: str) -> tuple[str, list[dict[str, str]]]:
    """Separa la riga finale ``ENTITIES: type:Name; ...`` dal testo fatti.

    Fail-safe: nessuna riga ENTITIES → ``(testo invariato, [])``. Tipi fuori
    dal vocabolario scartati; 'organization' normalizzato a 'org'."""
    if not text:
        return text or "", []
    lines = text.splitlines()
    ents: list[dict[str, str]] = []
    kept: list[str] = []
    for line in lines:
        s = line.strip().lstrip("-*• ").strip()
        if s.upper().startswith("ENTITIES:"):
            body = s[len("ENTITIES:"):].strip()
            for pair in body.split(";"):
                if ":" not in pair:
                    continue
                etype, _, name = pair.partition(":")
                etype = etype.strip().lower()
                name = name.strip().strip(".,;:()[]{}\"'")
                if etype == "organization":
                    etype = "org"
                if etype in _ENTITY_TYPES and len(name) >= 2:
                    ents.append({"name": name, "type": etype})
            continue
        kept.append(line)
    return "\n".join(kept), ents


def extraction_system_for(user_name: str | None,
                          *, typed_entities: bool = False,
                          tag_beliefs: bool = False) -> str:
    """The extraction system prompt, optionally extended with the app-provided
    user name (identity fix, diag 2026-07-07).

    Dialogues almost never state the user's own name, so extracted facts said
    'The user ...' while questions ask by name — a structural query/store
    mismatch that cripples retrieval. When the APPLICATION knows the user's name
    (legitimate metadata, exactly what competitors consume), passing it here
    makes facts retrieval-ready. The source is DECLARED in the prompt; the
    in-text anti-contamination rule stays for every other name. No ``user_name``
    -> byte-identical base prompt. ``typed_entities`` appends the tier-2
    ENTITIES-line instruction (default False: existing callers unchanged)."""
    base = ATOMIC_EXTRACT_SYSTEM
    if (user_name or "").strip():
        base = (base +
                f"\n- The user's name is '{user_name.strip()}' (provided by the "
                "application, not by this conversation). Use it as the subject of "
                "facts about the user instead of 'The user'. This exception applies "
                "ONLY to this one name; every other name must still appear in the "
                "conversation text.")
    if typed_entities:
        base = base + _TYPED_ENTITIES_INSTRUCTION
    if tag_beliefs:
        base = base + _BELIEF_EXTRACT_INSTRUCTION
    return base

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
    "person's name exactly as it appears in the list (do NOT introduce any "
    "name that is not already there).\n"
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


def strip_belief_marker(line: str) -> tuple[str, bool]:
    """``(clean_proposition, is_belief)``. A line the extractor tagged with a
    leading ``BELIEF:`` marker (Giro 2) is an unverified factual assertion ->
    stored as status ``user_belief`` instead of ``model_claim``. Case-insensitive,
    prefix-only (a mid-line 'BELIEF:' never counts). Fail-safe: no marker ->
    ``(line unchanged, False)``."""
    s = (line or "").lstrip()
    if s[:len(_BELIEF_MARKER)].upper() == _BELIEF_MARKER:
        return s[len(_BELIEF_MARKER):].strip(), True
    return line, False


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
    asserted_at: float | None = None,
    embed: str | None = None,
    user_name: str | None = None,
    typed_entities: bool = False,
    tag_beliefs: bool = False,
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
            extraction_system_for(user_name, typed_entities=typed_entities,
                                  tag_beliefs=tag_beliefs),
            [{"role": "user",
              "content": f"Conversation:\n{dialogue}\n\nFacts:"}],
            max_tokens=max_out_tokens)
        raw = (getattr(r, "text", "") or "")
    except Exception as exc:  # noqa: BLE001 — ingest must never crash the caller
        res["error"] = f"extraction llm error: {exc!s:.120}"
        return res

    # tier-2: la riga ENTITIES (se presente) esce dal flusso fatti PRIMA del
    # parse — fail-safe totale: senza riga, tutto identico.
    raw, session_entities = split_entities_line(raw)
    res["typed_entities"] = len(session_entities)
    lines = parse_extracted_lines(raw)
    res["extracted"] = len(lines)
    if completeness and lines:
        extra = gapfill_facts(dialogue, lines, llm=llm,
                              max_out_tokens=max_out_tokens)
        lines = lines + extra
        res["gapfilled"] = len(extra)
    if consolidate and lines:
        lines = consolidate_facts(lines, llm=llm, max_out_tokens=max_out_tokens,
                                  tag_beliefs=tag_beliefs)
        res["consolidated"] = len(lines)
    prov = conversation_provenance_ref(conversation_id)
    # Bi-temporal (v13): asserted_at = EVENT time (when the conversation
    # happened) — drives the reconcile age-gap and answer-with-history.
    # created_at stays TRANSACTION time (now): stuffing the event time into
    # created_at made the staleness half-life hide backdated facts and the
    # anti-spoof guard hide future ones (83% of a timestamped store invisible
    # to recall — root-caused 2026-07-05).
    stamp = {"asserted_at": float(asserted_at)} if asserted_at is not None else {}
    kg = None
    if session_entities:
        try:
            from .entity_kg import EntityStore
            from .entity_populate import entity_kg_path_for
            kg = EntityStore(db_path=entity_kg_path_for(
                semantic_memory.db_path))
        except Exception:  # noqa: BLE001 — graph enrichment must never block ingest
            kg = None
    for prop in lines:
        # Giro 2: a BELIEF:-tagged line is an unverified user assertion ->
        # user_belief (hidden from default recall), else model_claim as always.
        # The marker is only interpreted when we asked for it (flag on).
        is_belief = False
        if tag_beliefs:
            prop, is_belief = strip_belief_marker(prop)
        prop, _ = redact_secrets(prop)
        fact = Fact(
            proposition=prop,
            topic=topic,
            confidence=confidence,
            status="user_belief" if is_belief else "model_claim",
            source_episodes=[prov],
            writer_role=INGEST_WRITER_ROLE,
            **stamp,
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
            continue
        # tier-2 link additivo: le entità LLM della sessione i cui nomi
        # compaiono nel fatto — idempotente sopra il populate regex del
        # hook store() (dedup name_norm, PK link). Best-effort.
        if kg is not None:
            low = prop.lower()
            match = [e for e in session_entities if e["name"].lower() in low]
            if match:
                try:
                    from .entity_populate import populate_entities_for_fact
                    populate_entities_for_fact(fact.id, prop, kg,
                                               entities=match)
                except Exception:  # noqa: BLE001 — never break the ingest
                    pass
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
                      max_out_tokens: int = 1200,
                      tag_beliefs: bool = False) -> list[str]:
    """Merge near-duplicates and drop non-durable trivia from an extracted fact
    list (the precision pass). Fail-safe: on any LLM error, or if the pass
    returns nothing, the ORIGINAL list is returned unchanged — consolidation can
    only refine, never lose everything.

    ``tag_beliefs`` (Giro 2): append the instruction to PRESERVE a leading
    ``BELIEF:`` marker so the origin tag survives the rewrite. Default off ->
    ``CONSOLIDATE_SYSTEM`` unchanged (the bench constant is never mutated)."""
    if not facts:
        return []
    system = CONSOLIDATE_SYSTEM + (_BELIEF_CONSOLIDATE_INSTRUCTION if tag_beliefs else "")
    try:
        r = llm.complete(
            system,
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
    "extraction_system_for", "parse_extracted_lines", "render_conversation",
    "ingest_conversation", "consolidate_facts", "gapfill_facts",
    "strip_belief_marker",
]
