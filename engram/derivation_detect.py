"""Precision-first auto-detection of TYPED logical-derivation edges (R27 hybrid step 2).

When a fact is written with a grounding ``source``, we may infer which EXISTING facts its
truth DERIVES FROM and auto-populate ``derives_from`` (the ATMS edge propagate cascades on).

The non-negotiable design constraint (Aurelio: "se sei sicuro e preciso"): HIGH PRECISION,
low recall. A FALSE derivation edge causes a FALSE transitive retraction — the exact failure
R26 found when the narrative ``lineage_to`` was mistaken for a logical edge. So we link ONLY
on STRONG, near-unambiguous evidence and NEVER on fuzzy semantic similarity:

  1. EXPLICIT id-mention — the source text cites an existing fact's 12-hex id.
  2. EXACT proposition-containment (OPT-IN, ``use_containment=True``) — an existing fact's
     full proposition (>= min_chars, normalised) appears verbatim in the source.

EMPIRICAL CALIBRATION (R27 step 2, measured on the real 4312-fact corpus — the reason
auto-detect is OFF by default and the authoritative path stays the explicit ``derives_from``
param):
  * EXACT-containment over-links **38% (19/50)**: many facts share long boilerplate prefixes
    (PRE-COMPACT/MASTER-FACT templates) so one fact's source matches several others whose
    full proposition is a substring. Therefore containment is OPT-IN, default OFF — it fails
    the precision bar on a boilerplate-heavy corpus.
  * id-mention is unambiguous as a CITATION, but **37.9%** of facts cite another fact's id and
    a hand-read shows these are mostly NARRATIVE references (handoffs, "building on session
    X"), not truth-dependencies — i.e. citation != logical derivation, the same category
    error as ``lineage_to`` (R26). So even id-mention is a HEURISTIC, not a proof of
    derivation: ship it env-gated, never as the default, and keep the explicit param the
    source of truth.

No embeddings, no cosine, no paraphrase matching. Superseded facts are excluded as parents
(a new fact should not be justified by an already-retracted belief). Pure + deterministic.
"""
from __future__ import annotations

import re

_ID_RE = re.compile(r"\b[0-9a-f]{12}\b")
_WS_RE = re.compile(r"\s+")
DEFAULT_MIN_CHARS = 40


def _norm(s: str) -> str:
    return _WS_RE.sub(" ", (s or "").strip().lower())


def _attr(fact: object, name: str, default: object = None) -> object:
    if isinstance(fact, dict):
        return fact.get(name, default)
    return getattr(fact, name, default)


def detect_derivations(source: str, facts: object, *, exclude_id: str | None = None,
                       use_containment: bool = False,
                       min_proposition_chars: int = DEFAULT_MIN_CHARS) -> list[str]:
    """Return ids of EXISTING facts the ``source`` cites as parents (high precision).

    ``facts`` = the candidate corpus (live facts). Default: link only on explicit id-mention
    (rule 1). ``use_containment=True`` additionally links on exact full-proposition containment
    (rule 2) — OFF by default because it over-links 38% on the real corpus (see module doc).
    Superseded parents and ``exclude_id`` (the new fact itself) are never linked."""
    if not source:
        return []
    norm_source = _norm(source) if use_containment else ""
    ids_in_source = set(_ID_RE.findall(source))
    linked: set[str] = set()
    for f in facts:
        fid = str(_attr(f, "id", "") or "")
        if not fid or fid == exclude_id or _attr(f, "superseded_by"):
            continue
        if fid in ids_in_source:                       # (1) explicit id-mention (default)
            linked.add(fid)
            continue
        if use_containment:                            # (2) exact containment (opt-in, imprecise)
            prop = _norm(str(_attr(f, "proposition", "") or ""))
            if len(prop) >= min_proposition_chars and prop in norm_source:
                linked.add(fid)
    return sorted(linked)


__all__ = ["detect_derivations", "DEFAULT_MIN_CHARS"]
