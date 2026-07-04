"""Cycle 217 (2026-05-23) — skill_drafter.

Closes the cycle 213 → cycle 217 pipeline:

  Louvain community + topic purity + cohesion  (cycle 213)
    ↓
  Normalised topic family key                    (cycle 214/215)
    ↓
  ALGORITHMIC skill DRAFT (LLM-free)             ← here
    ↓
  Optional LLM call: refine into adopted skill    (deferred)

The drafter consumes one community entry produced by
``detect_emerging_skills`` plus the semantic.db and emits a TEXT
DRAFT plus structured metadata (trigger keywords, fact ids,
evidence).

Why LLM-free
------------
SOTA 2026 (MemOS, MemMachine) demonstrates that skill discovery
should not require LLM calls. This module materialises that
principle for HippoAgent: every emergent skill carries enough
deterministic structure (top facts + ranked keywords + evidence
block) that a downstream LLM call is OPTIONAL polish, not the
discovery itself.

Defensive
---------
* Missing DB → empty stub, no crash.
* Missing fact_ids → skipped.
* Empty community → minimal stub (caller may still log it).
"""
from __future__ import annotations

import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

#: Built-in English stop list.  Intentionally minimal to avoid
#: bloating the import; callers can post-filter further.
_STOPWORDS_EN: frozenset[str] = frozenset({
    "the", "a", "an", "and", "or", "but", "of", "for", "to", "in",
    "on", "at", "by", "is", "are", "was", "were", "be", "been",
    "being", "with", "as", "that", "this", "it", "from", "into",
    "than", "then", "so", "such", "if", "while", "when", "where",
    "use", "uses", "used", "using", "via", "per",
    "have", "has", "had", "do", "does", "did", "can", "may",
    "not", "no", "yes", "all", "any", "some", "more", "most", "less",
    "least", "very", "much", "many", "few", "each", "every", "other",
    "only", "also", "even", "just", "still", "yet",
})
#: Cycle 220 — Italian stop list.  HippoAgent's real corpus is heavily
#: Italian; cycle 217's empirical run surfaced particles like "non",
#: "con", "del" in the trigger_keywords. Filter them here so the
#: keyword set carries domain signal, not function words.
_STOPWORDS_IT: frozenset[str] = frozenset({
    "il", "lo", "la", "i", "gli", "le", "un", "una", "uno",
    "di", "del", "della", "dello", "dei", "degli", "delle",
    "da", "dal", "dalla", "dallo", "dai", "dagli", "dalle",
    "a", "al", "alla", "allo", "ai", "agli", "alle",
    "in", "nel", "nella", "nello", "nei", "negli", "nelle",
    "con", "col", "coi", "su", "sul", "sulla", "sullo", "sui",
    "sugli", "sulle", "per", "tra", "fra",
    "che", "chi", "cui", "non", "no", "sì", "si", "se", "ma",
    "e", "ed", "o", "od", "ne", "ci", "vi", "mi", "ti",
    "sono", "è", "era", "erano", "essere", "stato", "stata",
    "ho", "ha", "hai", "abbiamo", "avete", "hanno", "avere",
    "fa", "fai", "fanno", "fare", "faccio",
    "anche", "ancora", "molto", "poco", "più", "meno",
    "questo", "questa", "questi", "queste", "quel", "quella",
    "quelli", "quelle", "quale", "quali",
    "come", "dove", "quando", "perché", "poi", "ora", "già",
    "solo", "tutti", "tutto", "tutta", "tutte", "ogni",
})
#: Combined set used by ``_extract_keywords``.  Frozenset union is
#: cheap and immutable — built once at module import.
_STOPWORDS: frozenset[str] = _STOPWORDS_EN | _STOPWORDS_IT

#: Token pattern: alphanumeric ≥ 3 chars (filters single letters
#: and pure-numeric noise).
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}")


def _fetch_propositions(
    db_path: Path, ids: list[str],
) -> dict[str, str]:
    """Return ``{fact_id: proposition}`` for IDs found; missing IDs absent."""
    if not ids:
        return {}
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            placeholders = ",".join(["?"] * len(ids))
            rows = conn.execute(
                f"SELECT id, proposition FROM facts "  # noqa: S608
                f"WHERE id IN ({placeholders})",
                tuple(ids),
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return {}
    return {str(fid): str(prop or "") for fid, prop in rows}


def _extract_keywords(
    propositions: list[str], *, max_n: int = 12,
) -> list[str]:
    """Frequency-rank tokens across propositions; filter stopwords + short."""
    if not propositions:
        return []
    counter: Counter[str] = Counter()
    for prop in propositions:
        if not prop:
            continue
        for tok in _TOKEN_RE.findall(prop.lower()):
            if tok in _STOPWORDS:
                continue
            if len(tok) < 3:
                continue
            counter[tok] += 1
    # Only keep tokens that appear in ≥2 propositions (signal not noise).
    # Falls back to top-frequency if everything is unique.
    multi = [w for w, c in counter.most_common() if c >= 2]
    if multi:
        return multi[: int(max_n)]
    return [w for w, _ in counter.most_common(int(max_n))]


def _truncate(text: str, *, limit: int = 200) -> str:
    """Cut text to <= limit chars, append ellipsis if cut."""
    s = (text or "").strip()
    if len(s) <= limit:
        return s
    return s[: max(0, limit - 3)] + "..."


def draft_skill_from_community(
    semantic_db: Path | str,
    community: dict[str, Any],
    *,
    max_facts_in_text: int = 10,
    max_proposition_chars: int = 200,
) -> dict[str, Any]:
    """Produce a deterministic text DRAFT of an emergent skill candidate.

    Args:
        semantic_db: path to ``semantic.db`` (the live fact corpus).
        community: one dict as returned by
            ``detect_emerging_skills``. Required keys: ``fact_ids``,
            ``suggested_skill_name``, ``dominant_topic``,
            ``topic_purity``, ``cohesion``, ``size``,
            ``emergence_score``.
        max_facts_in_text: cap on how many fact propositions to
            embed in the draft text (longer drafts are harder to
            review).
        max_proposition_chars: per-fact truncation for embedded
            propositions.

    Returns:
        Dict with keys:
          - ``skill_name``: copy of ``suggested_skill_name``
          - ``draft_text``: human-readable Markdown body
          - ``trigger_keywords``: list[str] (frequency-ranked,
            stopwords-filtered)
          - ``fact_ids``: list of IDs that survived DB lookup
          - ``evidence``: nested dict (size/purity/cohesion/etc.)
    """
    p = Path(semantic_db)
    skill_name = str(community.get("suggested_skill_name") or "")
    dominant_topic = str(community.get("dominant_topic") or "")
    raw_ids = [str(fid) for fid in community.get("fact_ids", [])]
    size = int(community.get("size", 0) or 0)
    purity = float(community.get("topic_purity", 0.0) or 0.0)
    cohesion = float(community.get("cohesion", 0.0) or 0.0)
    score = float(community.get("emergence_score", 0.0) or 0.0)
    community_id = str(community.get("community_id") or "")

    propositions_map: dict[str, str] = {}
    if p.exists() and raw_ids:
        propositions_map = _fetch_propositions(p, raw_ids)
    # Preserve original ordering, keep only ids we actually fetched.
    fact_ids = [fid for fid in raw_ids if fid in propositions_map]

    propositions_in_order = [propositions_map[fid] for fid in fact_ids]
    keywords = _extract_keywords(propositions_in_order)

    # Build the Markdown draft body.
    lines: list[str] = []
    lines.append(f"# {skill_name or 'emerging_skill_unknown'} (DRAFT)")
    lines.append("")
    lines.append("## Evidence")
    lines.append(f"- size={size} facts (community_id: {community_id})")
    lines.append(f"- dominant_topic: {dominant_topic}")
    lines.append(
        f"- topic_purity: {purity:.2f}    cohesion: {cohesion:.2f}    "
        f"emergence_score: {score:.2f}",
    )
    lines.append("")
    lines.append(f"## Trigger keywords ({len(keywords)})")
    if keywords:
        lines.append(", ".join(keywords))
    else:
        lines.append("(none extracted — propositions too sparse)")
    lines.append("")
    lines.append(
        f"## Member facts (showing up to {max_facts_in_text})",
    )
    if fact_ids:
        for fid in fact_ids[: int(max_facts_in_text)]:
            prop_t = _truncate(
                propositions_map.get(fid, ""),
                limit=int(max_proposition_chars),
            )
            lines.append(f"- [{fid}] {prop_t}")
    else:
        lines.append("(no facts found in DB for this community)")
    lines.append("")
    lines.append(
        "Status: DRAFT (auto-discovered via cycle-213 emergence + "
        "cycle-214 topic normalisation + cycle-217 drafter; pending "
        "human/LLM review before adoption).",
    )

    draft_text = "\n".join(lines)

    return {
        "skill_name": skill_name,
        "draft_text": draft_text,
        "trigger_keywords": keywords,
        "fact_ids": fact_ids,
        "evidence": {
            "community_id": community_id,
            "size": size,
            "dominant_topic": dominant_topic,
            "topic_purity": purity,
            "cohesion": cohesion,
            "emergence_score": score,
        },
    }


__all__ = ["draft_skill_from_community"]
