"""P1 — `validate_claim`: anti-confabulazione deterministica.

Spec: docs/specs/p1-hippo-validate-claim.md (commit ce67839).

Tool chiamato PRIMA che Claude affermi un fatto verificabile (es. "X
è nato nel Y", "Z ha detto W"). Cerca evidenza in memoria semantica e
restituisce verdict + advice. Zero LLM call: NER super-light
(Capitalized + anni) + token overlap + contradiction-by-different-year.

Origine: pattern di confabulazione pescati live (sessione 2026-05-14):
Tonegawa Nobel 1987→2014, Anthropic Skills 2025→2026, LightRAG
HKUDS→HKUST. La meccanica è puramente lessicale — non sostituisce
ragionamento, ma intercetta i casi più frequenti di "ho cambiato un
numero/data/attribuzione".
"""
from __future__ import annotations

import re
from typing import Any, Protocol

# Numeric-quantity contradiction primitives — shared with the batch corpus
# scanner (facts_conflict) so write-time and retroactive detection use
# IDENTICAL semantics. Aliased to the historical private names below.
from .quantity_match import (
    YEAR_RE as _YEAR_RE,
)
from .quantity_match import (
    content_tokens as _content_tokens,
)
from .quantity_match import (
    contrasting_attrs as _contrasting_attrs,
)
from .quantity_match import (
    extract_quantities as _extract_quantities,
)
from .quantity_match import (
    norm_unit as _norm_unit,
)

_CAPS_RE = re.compile(r"\b([A-Z][a-zA-Z]{2,})\b")

# Parole capitalized che non sono nomi propri — sono inizio frase /
# pronomi / determiners / verbi modali / congiunzioni / preposizioni.
# Lista corta volutamente: si può espandere se emergono falsi positivi.
_CAPS_STOPWORDS = {
    "The", "And", "But", "Or", "If", "When", "While", "Although",
    "From", "With", "Was", "Were", "Are", "Has", "Have", "Had",
    "This", "That", "These", "Those", "Such", "Some", "Any",
    "Will", "Would", "Could", "Should", "May", "Might", "Must",
    "His", "Her", "Their", "Its", "Our", "Your", "Whose",
    "Who", "What", "Where", "Why", "How",
    "Not", "Yes", "Maybe",
}


class _FactLike(Protocol):
    id: str
    proposition: str
    topic: str
    confidence: float
    source_episodes: list[str]


class _SemanticLike(Protocol):
    def search_facts(
        self, query: str, *, limit: int = 20, topic: str | None = None,
    ) -> list[_FactLike]: ...


class _AgentLike(Protocol):
    semantic: _SemanticLike


def _extract_salients(text: str) -> tuple[set[str], set[str]]:
    """Estrae (capitalized_names, years) dalla stringa.

    NER super-light: nessuna libreria, nessun modello. Filtra
    capitalized stopwords (inizi frase, pronomi). Anni 1500-2099.
    """
    caps_raw = _CAPS_RE.findall(text or "")
    caps = {w for w in caps_raw if w not in _CAPS_STOPWORDS}
    years = set(_YEAR_RE.findall(text or ""))
    return caps, years


def _subj_overlap(claim_caps: set[str], fact_text: str) -> float:
    """Frazione di nomi-claim presenti nel testo del fact (case-insensitive).

    Riproduce il match "i nomi della claim appaiono nel fact". Lavora
    su stringa-lower per gestire eventuali normalizzazioni (es. "Tonegawa"
    in claim, "tonegawa" in proposition).
    """
    if not claim_caps:
        return 0.0
    fact_lower = (fact_text or "").lower()
    hits = sum(1 for t in claim_caps if t.lower() in fact_lower)
    return hits / len(claim_caps)


def validate_claim(
    agent: _AgentLike,
    claim: str,
    topic_hint: str | None = None,
    threshold: float = 0.6,
) -> dict[str, Any]:
    """Valida una claim factual contro la memoria semantica dell'agente.

    Args:
        agent: oggetto con `.semantic.search_facts(query, *, limit, topic)`.
        claim: stringa con asserzione verificabile (es. "X è nato nel Y").
        topic_hint: filtra i fact a un topic specifico (es.
            "science/biology/nobel").
        threshold: soglia minima di subject-overlap per considerare un
            fact "soggettivamente rilevante" per la claim. Default 0.6.

    Returns:
        dict con chiavi:
          - verdict ∈ {"supported", "contradicted", "unknown"}
          - confidence: float in [0, 1]
          - evidence_facts: list[str] di fact_id
          - evidence_episodes: list[str] di episode_id
          - advice: stringa breve in italiano per Claude

    Verdict logic:
      1. Estrai (caps, years) dalla claim. Se totale < 2 ⇒ "unknown"
         (claim troppo generica per validazione lessicale).
      2. Cerca fact correlati via `semantic.search_facts`. Se vuoto
         ⇒ "unknown".
      3. Per ogni fact con subj_overlap ≥ threshold:
         - se claim_years ∧ fact_years sono disgiunti ⇒ contradicting
         - altrimenti ⇒ supporting
      4. Se contradicting ⇒ "contradicted". Altrimenti se supporting
         ⇒ "supported". Altrimenti ⇒ "unknown".
    """
    claim_caps, claim_years = _extract_salients(claim)
    salient_count = len(claim_caps) + len(claim_years)

    # Numeric-quantity path (sibling of the year-disjoint rule). A claim
    # that states a measurable quantity ("45 minutes", "1024 entries") can
    # contradict a stored fact even with ZERO capitalized names — exactly
    # the subtle confab the keyword L1 detectors miss. Years are excluded
    # from quantities (handled by the year path) so the two never collide.
    claim_quants = _extract_quantities(claim)
    claim_units = {u for (u, _v) in claim_quants if u}
    claim_content = _content_tokens(claim)
    # Distinctive (non-unit) content words drive retrieval + the precision
    # guard below. "minutes"/"entries" are the unit, not the subject.
    claim_distinct = {t for t in claim_content if _norm_unit(t) not in claim_units}
    numeric_viable = bool(claim_quants) and bool(claim_distinct)

    # Gate: claim troppo generica (un solo token saliente o nessuno).
    # Esempio: "Tonegawa is a researcher." ha solo {"Tonegawa"} →
    # NON è verificabile lessicalmente, meglio dichiarare unknown.
    # Il path numerico ha la sua viabilità (quantità + ≥1 parola di
    # contesto) e NON va bloccato dal gate caps/anni.
    if salient_count < 2 and not numeric_viable:
        return {
            "verdict": "unknown",
            "confidence": 0.0,
            "evidence_facts": [],
            "evidence_episodes": [],
            "advice": (
                "Claim troppo generica per validazione lessicale "
                "(servono ≥ 2 token salienti: nomi capitalized + "
                "anno)."
            ),
        }

    # Backend `SemanticMemory.search_facts` (engram/semantic.py:225) usa
    # SQL `LOWER(proposition) LIKE '%<full_query>%'`: passare la claim
    # INTERA fa praticamente sempre miss (la claim verbatim non è
    # sottostringa del fact corretto, perché il fact contiene altre
    # parole intorno). Bug pescato dal critic-orchestrator counterexample
    # worker (cycle #70 review): il fake del test era troppo generoso
    # (token-overlap) e nascondeva il problema reale in produzione.
    #
    # Fix: tokenizzare la claim ed emettere una query per ogni nome
    # capitalized (discriminanti informativi: "Tonegawa", "Newton").
    # Dedup per id. Skippiamo gli anni come chiave di ricerca: "1987"
    # da solo è troppo rumoroso (match cross-topic).
    try:
        hits: list[_FactLike] = []
        seen: set[str] = set()
        search_tokens = list(sorted(claim_caps))
        if claim_quants:
            # Numeric claims often have no caps → also retrieve by the
            # distinctive content words so the related fact is found
            # (longest first: more discriminating).
            search_tokens += sorted(
                claim_distinct, key=lambda t: (-len(t), t),
            )[:8]
        for token in search_tokens:
            for f in agent.semantic.search_facts(
                token, limit=10, topic=topic_hint,
            ):
                if f.id in seen:
                    continue
                seen.add(f.id)
                hits.append(f)
            if len(hits) >= 30:
                break
    except Exception as exc:  # pragma: no cover — difensivo
        return {
            "verdict": "unknown",
            "confidence": 0.0,
            "evidence_facts": [],
            "evidence_episodes": [],
            "advice": f"Errore in semantic.search_facts: {exc}",
        }

    if not hits:
        return {
            "verdict": "unknown",
            "confidence": 0.0,
            "evidence_facts": [],
            "evidence_episodes": [],
            "advice": "Nessun fatto correlato trovato in memoria.",
        }

    contradicting: list[_FactLike] = []
    supporting: list[_FactLike] = []
    for f in hits:
        fact_caps, fact_years = _extract_salients(f.proposition)
        overlap = _subj_overlap(claim_caps, f.proposition)
        if overlap < threshold:
            continue
        # Anni disgiunti ⇒ contraddizione.
        if claim_years and fact_years and not (claim_years & fact_years):
            contradicting.append(f)
        else:
            supporting.append(f)

    # NUMERIC-QUANTITY contradiction pass — independent of the caps-overlap
    # gate above (which is ~0 for number-only claims). Fires only when the
    # hit shares a DISTINCTIVE (non-unit) content word with the claim AND
    # states a different value for the SAME normalised unit. The shared-word
    # guard is what stops "ring buffer 256 entries" from contradicting
    # "cache 1024 entries" (coincidental unit, unrelated subject).
    numeric_contra: list[_FactLike] = []
    numeric_advice = ""
    numeric_agree = False
    if claim_quants:
        _year_ids = {f.id for f in contradicting}
        for f in hits:
            if f.id in _year_ids:
                continue
            f_quants = _extract_quantities(f.proposition)
            if not f_quants:
                continue
            f_content = _content_tokens(f.proposition)
            f_distinct = {
                t for t in f_content if _norm_unit(t) not in claim_units
            }
            if not (claim_distinct & f_distinct):
                continue  # unrelated subject → never a contradiction
            if _contrasting_attrs(claim_content, f_content):
                continue  # different attribute (read/write, …) → not a conflict
            f_conflict: tuple[str, float, float] | None = None
            for (cu, cv) in claim_quants:
                if not cu:
                    continue  # bare unitless number → too ambiguous
                for (fu, fv) in f_quants:
                    if cu != fu:
                        continue
                    if cv == fv:
                        numeric_agree = True  # same unit & value → confirmed
                    else:
                        f_conflict = (cu, cv, fv)
            if f_conflict:
                numeric_contra.append(f)
                if not numeric_advice:
                    cu, cv, fv = f_conflict
                    numeric_advice = (
                        f"in memoria: {fv:g} {cu} (fact {f.id}), "
                        f"NON {cv:g} {cu} — controlla prima di affermare."
                    )

    if contradicting or numeric_contra:
        contra: list[_FactLike] = list(contradicting)
        _seen_c = {f.id for f in contra}
        for f in numeric_contra:
            if f.id not in _seen_c:
                contra.append(f)
                _seen_c.add(f.id)
        episodes = sorted(
            {eid for f in contra for eid in f.source_episodes}
        )
        f0 = contra[0]
        f0_years = sorted(_extract_salients(f0.proposition)[1])
        claim_years_sorted = sorted(claim_years)
        if contradicting and f0_years and claim_years_sorted:
            advice = (
                f"in memoria: {', '.join(f0_years)} (fact {f0.id}), "
                f"NON {', '.join(claim_years_sorted)} — controlla "
                "prima di affermare."
            )
        elif numeric_advice:
            advice = numeric_advice
        else:
            advice = (
                "Evidenza contraria in memoria — controlla "
                "prima di affermare."
            )
        return {
            "verdict": "contradicted",
            "confidence": min(float(f0.confidence), 0.95),
            "evidence_facts": [f.id for f in contra],
            "evidence_episodes": episodes,
            "advice": advice,
        }

    # A claim that makes a SPECIFIC numeric assertion we could not confirm
    # against a same-subject fact must NOT be promoted to "supported" on
    # name-overlap alone — that would be false reassurance (a confab-adjacent
    # failure). Suppress support in that case → honest "unknown".
    suppress_support = bool(claim_quants) and not numeric_agree
    if supporting and not suppress_support:
        episodes = sorted(
            {eid for f in supporting for eid in f.source_episodes}
        )
        f0 = supporting[0]
        return {
            "verdict": "supported",
            "confidence": min(float(f0.confidence), 0.95),
            "evidence_facts": [f.id for f in supporting],
            "evidence_episodes": episodes,
            "advice": "Claim coerente con la memoria.",
        }

    if suppress_support and supporting:
        return {
            "verdict": "unknown",
            "confidence": 0.0,
            "evidence_facts": [f.id for f in supporting],
            "evidence_episodes": [],
            "advice": (
                "Soggetto presente in memoria ma la quantità numerica "
                "della claim non è confermata da alcun fatto — verifica "
                "prima di affermare il valore."
            ),
        }

    return {
        "verdict": "unknown",
        "confidence": 0.0,
        "evidence_facts": [],
        "evidence_episodes": [],
        "advice": "Evidenza insufficiente: nessun fact ha subject overlap "
                  f"≥ threshold {threshold}.",
    }
