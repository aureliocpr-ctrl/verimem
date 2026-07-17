"""P2.c — OpenIE LLM-based entity & triple extraction.

Spec: docs/specs/p2c-openie-extraction.md (P2.c).

Pattern HippoRAG 2-step (NER → triple) ma con `json.loads` strict
e zero parser code-execution sull'output LLM. L'LLM riceve prompt
che richiedono response JSON-only; il client locale fa
`json.loads(...)` strict, retry una volta su ValueError con prompt
"fix the JSON syntax", e su secondo fail ritorna lista vuota.

Anti-pattern HippoRAG upstream: openie_openai.py usa eseguibili
parser sull'output LLM — equivale a fidarsi ciecamente del modello.
Noi NON lo facciamo: una stringa malformata o malevola produce
`[]`, mai una crash o un side-effect.

Funzioni esportate:
  - `_parse_ner_response(text) -> list[dict]`
  - `_parse_triple_response(text, known_entities) -> list[dict]`
  - `extract_entities(text, llm, mode, existing_entities) -> dict`
"""
from __future__ import annotations

import json
from typing import Any, Protocol

# Riusiamo la stessa normalizzazione Unicode-safe di entity_kg
# per consistenza di dedup case+form-insensitive.
from .entity_kg import _norm

# ---------- LLM protocol -----------------------------------------------


class _LLMProtocol(Protocol):
    """Subset minimale del contratto LLM (verimem.llm.AnthropicLLM/etc).

    Riceve system+messages, ritorna LLMResponse con `.text`.
    """

    def complete(  # noqa: D401
        self,
        system: str,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        stop_sequences: list[str] | None = None,
    ) -> Any: ...


# ---------- Prompts ----------------------------------------------------


NER_SYSTEM_PROMPT = (
    "You are a precise named-entity extractor. Your output MUST be "
    "a single JSON object with the exact schema:\n"
    '  {"entities": [{"name": str, "type": str, '
    '"aliases": [str, ...]}]}\n'
    "Rules:\n"
    "1. Output ONLY valid JSON. No prose, no markdown fences, no "
    "code blocks.\n"
    "2. Extract Capitalized proper nouns (people, places, "
    "organizations, papers, products, concepts).\n"
    "3. `type` is a short tag: person|org|place|paper|repo|product|"
    "concept|other.\n"
    "4. `aliases` is optional; include only obvious alternate forms.\n"
    "5. If `existing_entities` is provided in the user message, "
    "use those canonical forms when applicable.\n"
    "6. If no entities found, return {\"entities\": []}."
)


TRIPLE_SYSTEM_PROMPT = (
    "You are a precise (subject, predicate, object) triple "
    "extractor. Your output MUST be a single JSON object with the "
    "exact schema:\n"
    '  {"triples": [{"subject": str, "predicate": str, '
    '"object": str, "confidence": float}]}\n'
    "Rules:\n"
    "1. Output ONLY valid JSON. No prose, no markdown fences.\n"
    "2. `subject` and `object` MUST be entity names from the "
    "provided list — DO NOT invent new entities.\n"
    "3. `predicate` is a short snake_case verb phrase "
    "(works_at, discovered, founded_by, located_in, ...).\n"
    "4. `confidence` is a float in [0, 1].\n"
    "5. If no triples found, return {\"triples\": []}."
)


_RETRY_FIX_JSON_PROMPT = (
    "Your previous response was not valid JSON. Reply ONLY with "
    "the corrected JSON object, no prose."
)


# ---------- Parsers (strict json.loads, no code-execution) ------------


def _parse_ner_response(text: str) -> list[dict[str, Any]]:
    """Strict JSON parse of an NER response.

    Returns the `entities` list if the input is valid JSON with the
    expected schema. Returns `[]` otherwise (malformed JSON, missing
    key, wrong type) — never raises, never executes the input as
    code.
    """
    if not text or not text.strip():
        return []
    try:
        obj = json.loads(text)
    except (ValueError, TypeError):
        return []
    if not isinstance(obj, dict):
        return []
    entities = obj.get("entities")
    if not isinstance(entities, list):
        return []
    # Validate each entry has at least a `name` string field
    out: list[dict[str, Any]] = []
    for e in entities:
        if not isinstance(e, dict):
            continue
        name = e.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        item: dict[str, Any] = {"name": name.strip()}
        type_ = e.get("type")
        item["type"] = (
            type_.strip() if isinstance(type_, str) else ""
        )
        aliases = e.get("aliases")
        if isinstance(aliases, list):
            item["aliases"] = [
                a.strip() for a in aliases
                if isinstance(a, str) and a.strip()
            ]
        out.append(item)
    return out


def _parse_triple_response(
    text: str,
    known_entities: set[str],
) -> list[dict[str, Any]]:
    """Strict JSON parse + entity validation.

    Returns only triples whose subject AND object appear in
    `known_entities` (case-sensitive exact match — caller is
    responsible for normalization upstream). This prevents the LLM
    from confabulating new entities in the triple step.
    """
    if not text or not text.strip():
        return []
    try:
        obj = json.loads(text)
    except (ValueError, TypeError):
        return []
    if not isinstance(obj, dict):
        return []
    triples = obj.get("triples")
    if not isinstance(triples, list):
        return []
    out: list[dict[str, Any]] = []
    for t in triples:
        if not isinstance(t, dict):
            continue
        s = t.get("subject")
        p = t.get("predicate")
        o = t.get("object")
        if not all(
            isinstance(x, str) and x.strip()
            for x in (s, p, o)
        ):
            continue
        s, p, o = s.strip(), p.strip(), o.strip()
        if s not in known_entities or o not in known_entities:
            continue
        conf = t.get("confidence", 0.0)
        try:
            conf_f = float(conf)
        except (ValueError, TypeError):
            conf_f = 0.0
        conf_f = max(0.0, min(1.0, conf_f))
        out.append({
            "subject": s,
            "predicate": p,
            "object": o,
            "confidence": conf_f,
        })
    return out


# ---------- High-level extract_entities -------------------------------


def _call_llm_strict_json(
    llm: _LLMProtocol,
    system: str,
    user_content: str,
    *,
    max_retries: int = 1,
) -> str:
    """Invoca LLM con temperature=0, fai retry una volta se l'output
    non è JSON parseable. Ritorna la stringa text (anche se invalida)
    o `""` se l'LLM client solleva (timeout, rate limit, HTTP error,
    connection reset).

    Round-2 critic counterexample 0.78 fix: AnthropicLLM/OpenAICompat
    in produzione possono sollevare httpx.HTTPError / RuntimeError /
    altre eccezioni di rete; il modulo openie deve assorbire e
    ritornare empty per rispettare il contratto "never raises".
    """
    messages = [{"role": "user", "content": user_content}]
    try:
        response = llm.complete(
            system=system, messages=messages, temperature=0.0,
        )
    except Exception:  # noqa: BLE001 — defensive su LLM client errors
        return ""
    text = (getattr(response, "text", "") or "").strip()
    # Quick check: tenta parse, se fail e abbiamo retry, ri-chiedi
    try:
        json.loads(text)
        return text
    except (ValueError, TypeError):
        pass
    if max_retries <= 0:
        return text
    # Retry: messaggio di fix
    retry_messages = [
        {"role": "user", "content": user_content},
        {"role": "assistant", "content": text},
        {"role": "user", "content": _RETRY_FIX_JSON_PROMPT},
    ]
    try:
        response2 = llm.complete(
            system=system, messages=retry_messages,
            temperature=0.0,
        )
    except Exception:  # noqa: BLE001 — defensive idem
        return text  # ritorna il primo testo (malformed ma non vuoto)
    return (getattr(response2, "text", "") or "").strip()


def extract_entities(
    text: str,
    llm: _LLMProtocol,
    mode: str = "ner_only",
    existing_entities: list[str] | None = None,
) -> dict[str, Any]:
    """Extract entities (and optionally triples) from `text`.

    Args:
        text: free-form text to extract from.
        llm: any object with a `.complete(system, messages, ...)`
            method (verimem.llm.MockLLM, AnthropicLLM, etc.).
        mode: `"ner_only"` (1 LLM call) or `"ner+triple"` (2 calls).
        existing_entities: canonical names already in the KG; the
            output excludes entities that case+Unicode-normalize to
            any of these (dedup pre-merge).

    Returns:
        `{"entities": [{name, type, aliases?}], "triples":
        [{subject, predicate, object, confidence}]}`.
        Empty lists on LLM failure or malformed output (never raises).
    """
    if not text or not text.strip():
        return {"entities": [], "triples": []}

    valid_modes = {"ner_only", "ner+triple"}
    if mode not in valid_modes:
        raise ValueError(
            f"mode must be one of {valid_modes}, got {mode!r}"
        )

    existing_norm: set[str] = set()
    if existing_entities:
        existing_norm = {
            _norm(e) for e in existing_entities if e
        }

    # ---- Step 1: NER ----
    user_ner = text.strip()
    if existing_entities:
        user_ner += (
            "\n\nKnown entities (use canonical names when "
            f"applicable, do not duplicate):\n"
            f"{json.dumps(existing_entities)}"
        )
    ner_text = _call_llm_strict_json(
        llm, NER_SYSTEM_PROMPT, user_ner, max_retries=1,
    )
    raw_entities = _parse_ner_response(ner_text)

    # Dedup: filtra le entity già esistenti via _norm
    entities: list[dict[str, Any]] = []
    seen_norm: set[str] = set()
    for e in raw_entities:
        name_norm = _norm(e["name"])
        if not name_norm:
            continue
        if name_norm in existing_norm:
            continue
        if name_norm in seen_norm:
            continue
        seen_norm.add(name_norm)
        entities.append(e)

    if mode == "ner_only" or not entities:
        return {"entities": entities, "triples": []}

    # ---- Step 2: Triple ----
    entity_names = [e["name"] for e in entities]
    # NOTA: per il triple step passiamo TUTTI gli entity names (sia
    # quelli appena estratti che gli existing) come known_entities,
    # così l'LLM può creare triple X→Y dove uno dei due era
    # pre-esistente.
    all_known = set(entity_names) | set(existing_entities or [])
    user_triple = (
        f"Entities: {json.dumps(sorted(all_known))}\n\n"
        f"Text: {text.strip()}"
    )
    triple_text = _call_llm_strict_json(
        llm, TRIPLE_SYSTEM_PROMPT, user_triple, max_retries=1,
    )
    triples = _parse_triple_response(triple_text, all_known)

    return {"entities": entities, "triples": triples}
