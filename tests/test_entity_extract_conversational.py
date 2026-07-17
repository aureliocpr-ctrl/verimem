"""Tier-1 conversational entity extraction (design CONVERSATIONAL_ENTITY_DESIGN.md).

Gap misurato (2026-07-08): l'extractor lite è tarato per testo TECNICO — su
un corpus conversazionale di 1.261 fatti produce 49 entità e il grafo è una
stella intorno all'utente (PPR piatto). I pattern conversazionali catturano
persone/luoghi/organizzazioni/eventi/attività dai fatti dichiarativi
HaluMem-style, con la precisione garantita dagli ancoraggi relazionali
(preposizione/verbo prima del nome — mai a inizio frase per grammatica).
"""
from __future__ import annotations

from verimem.entity_extract_lite import MAX_ENTITIES_PER_TEXT, extract_entities_lite


def _by_type(text: str) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for e in extract_entities_lite(text):
        out.setdefault(e["type"], set()).add(e["name"])
    return out


def test_person_after_relational_preposition():
    got = _by_type("Johnson Joseph visited Kyoto with Emily in March 2025")
    assert "Emily" in got.get("person", set())
    assert "Kyoto" in got.get("place", set())
    # un mese dopo "in" NON è un luogo
    assert "March" not in got.get("place", set())


def test_org_with_business_suffix():
    got = _by_type("Johnson introduced personalized tours at Albi B&B")
    assert any("Albi" in n for n in got.get("org", set())), (
        "'Albi B&B' (suffisso business) deve essere org"
    )


def test_event_closed_list():
    got = _by_type(
        "Johnson Joseph's monthly income increased after the promotion "
        "on Dec 21, 2025")
    assert "promotion" in {n.lower() for n in got.get("event", set())}
    got2 = _by_type("After the layoff, he focused on the B&B expansion")
    assert "layoff" in {n.lower() for n in got2.get("event", set())}


def test_activity_after_offer_verbs():
    got = _by_type("Johnson introduced personalized tours at Albi B&B")
    acts = {n.lower() for n in got.get("activity", set())}
    assert "personalized tours" in acts


def test_lowercase_nouns_after_with_are_not_persons():
    got = _by_type(
        "Johnson Joseph actively engaged with local businesses to grow")
    assert not got.get("person"), (
        "'with local businesses' (minuscolo) non è una persona"
    )


def test_technical_patterns_unchanged():
    got = _by_type("recall hang fixed in engram/semantic.py at deadbeef1234")
    assert "engram/semantic.py" in got.get("path", set())
    assert "deadbeef1234" in got.get("commit", set())


def test_cap_still_respected():
    text = " ".join(f"He traveled with Person{chr(65+i)} to City{chr(65+i)}"
                    for i in range(20))
    assert len(extract_entities_lite(text)) <= MAX_ENTITIES_PER_TEXT
