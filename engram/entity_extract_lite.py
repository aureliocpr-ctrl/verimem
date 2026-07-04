"""Deterministic, zero-API entity extraction (entity-live tier 1).

WHY: the entity-KG + PPR engine (entity_kg.py) was built-not-live — the
only extractor (openie.py) needs an LLM, nothing populates the graph
from the real corpus, so entity retrieval returned 0 hits on real data
(the README said so honestly). This module is the LLM-free tier: regex
extraction tuned for THIS corpus (technical facts: code identifiers,
file paths, commit SHAs, acronyms, proper nouns), so the graph becomes
real today at zero API cost. The LLM tier (openie.py) stays as the
higher-quality opt-in on top.

Design constraints:
  * deterministic + pure (same text -> same entities), trivially testable;
  * conservative: prefer missing a borderline entity over flooding the
    graph with noise (stoplist, sentence-initial guard, per-text cap);
  * type tags are coarse on purpose: code | path | module | commit |
    acronym | proper | tech.
"""
from __future__ import annotations

import re

#: per-text cap — bounds the co-occurrence clique downstream (n*(n-1)/2).
MAX_ENTITIES_PER_TEXT = 16

# Italian + English function words that slip through Capitalized matching.
_STOPWORDS = {
    "il", "lo", "la", "le", "gli", "un", "una", "uno", "per", "con", "del",
    "della", "dei", "delle", "nel", "nella", "sul", "sulla", "questo",
    "questa", "questi", "queste", "quando", "dove", "come", "anche", "dopo",
    "prima", "senza", "sopra", "sotto", "the", "this", "that", "these",
    "those", "with", "from", "into", "over", "under", "when", "where",
    "while", "after", "before", "and", "but", "for", "not", "its", "his",
    "her", "our", "their", "are", "was", "were", "has", "have", "had",
    "all", "any", "each", "more", "most", "other", "some", "such", "only",
    "own", "same", "than", "then", "too", "very",
}

# Ordered patterns: first match wins per span (path before module before
# snake_case so "engram/semantic.py" doesn't shatter into pieces).
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # file path with extension: engram/semantic.py, benchmark\x.py
    ("path", re.compile(r"\b[\w.-]+[/\\][\w/\\.-]*\.\w{1,6}\b")),
    # dotted module: engram.provider_registry (>=2 dotted lowercase parts)
    ("module", re.compile(r"\b[a-z_][\w]*(?:\.[a-z_][\w]+)+\b")),
    # snake_case identifier (>=2 segments): community_detector
    ("code", re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")),
    # CamelCase: SemanticMemory, LongMemEval, McNemar
    ("code_camel", re.compile(r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+\b")),
    # commit-ish hex, 7-12 chars, not a pure number
    ("commit", re.compile(r"\b(?=[0-9a-f]*[a-f])[0-9a-f]{7,12}\b")),
    # acronym / all-caps tag, 2-6 letters: MCP, PPR, TDD, CI, MRR
    ("acronym", re.compile(r"\b[A-Z]{2,6}\b")),
    # tech token with digits: mem0, gpt4o, qwen3 (len >= 3, starts alpha)
    ("tech", re.compile(r"\b[a-z]{2,}[0-9][a-z0-9]*\b")),
    # Capitalized proper noun runs: Claude Code, Aurelio, Engram
    ("proper", re.compile(
        r"\b[A-Z][a-zà-ÿ]+(?:\s+[A-Z][a-zà-ÿ]+){0,3}\b")),
]

_SENTENCE_START = re.compile(r"(?:^|[.!?:;]\s+|\n\s*)$")


def _is_sentence_initial(text: str, start: int) -> bool:
    """True when the match begins a sentence (Capitalized-by-grammar)."""
    return bool(_SENTENCE_START.search(text[:start]))


def extract_entities_lite(text: str) -> list[dict[str, str]]:
    """Extract entities from `text`. Returns [{"name", "type"}, ...].

    Deterministic, never raises, [] on empty input. Conservative by
    design — see module docstring for the noise/recall trade-off.
    """
    if not text or not text.strip():
        return []

    taken: list[tuple[int, int]] = []  # claimed spans, first-match-wins
    out: list[dict[str, str]] = []
    seen_lower: set[str] = set()

    def _claim(start: int, end: int) -> bool:
        for s, e in taken:
            if start < e and end > s:
                return False
        taken.append((start, end))
        return True

    for etype, pat in _PATTERNS:
        for m in pat.finditer(text):
            name = m.group(0).strip().strip(".,;:()[]{}\"'")
            if not name or len(name) < 2:
                continue
            low = name.lower()
            if low in _STOPWORDS or low in seen_lower:
                continue
            if name.isdigit():
                continue
            if etype == "proper":
                # single Capitalized word at sentence start = grammar, not
                # entity — unless the same word also appears mid-sentence.
                if " " not in name and _is_sentence_initial(text, m.start()):
                    mid = re.search(
                        r"(?<![.!?:;]\s)(?<!^)\b" + re.escape(name) + r"\b",
                        text[m.end():],
                    )
                    if not mid:
                        continue
                first_word = name.split()[0].lower()
                if first_word in _STOPWORDS:
                    continue
            if not _claim(m.start(), m.end()):
                continue
            seen_lower.add(low)
            out.append({"name": name, "type": etype})
            if len(out) >= MAX_ENTITIES_PER_TEXT:
                return out
    return out


__all__ = ["extract_entities_lite", "MAX_ENTITIES_PER_TEXT"]
