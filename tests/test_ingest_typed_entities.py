"""Tier-2 piggyback: entità tipizzate dall'LLM nella STESSA call di estrazione.

Opt-in (typed_entities=False default): il prompt di estrazione validato (F1
0.761) non cambia finché il bench-gate F1 non prova la non-regressione —
stesso standard applicato a user_name.

Il tier-1 regex ha arricchito il grafo (49→81) ma i fatti consolidati
nominano poco oltre utente+org (hub invariato, fact abac6de18ee5). Le entità
secondarie vivono nel DIALOGO: l'estrattore LLM le vede già — gli si chiede
UNA riga finale 'ENTITIES: type:Name; ...' (fuori dalla lista fatti, così il
consolidate non la tocca), a costo di zero call extra. Parse fail-safe: senza
riga ENTITIES il comportamento è byte-identico. Il link fatto↔entità è
deterministico (nome contenuto nella proposizione).
"""
from __future__ import annotations

import sqlite3

from engram.conversation_ingest import (
    ingest_conversation,
    split_entities_line,
)
from engram.entity_populate import entity_kg_path_for
from engram.semantic import SemanticMemory


class _StubLLM:
    """Ritorna sempre lo stesso testo di estrazione (formato reale)."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0

    def complete(self, system, messages, **kw):
        self.calls += 1

        class R:
            pass

        r = R()
        # il consolidate/gapfill ricevono la lista fatti: eco semplice
        if "cleaning a list" in system:
            r.text = messages[0]["content"].split("FACTS:")[-1] if "FACTS:" in messages[0]["content"] else messages[0]["content"]
        else:
            r.text = self.text
        r.total_tokens = 10
        return r


def test_split_entities_line_parses_and_strips():
    text = ("Emily visited Kyoto with the user\n"
            "The user enjoys pottery classes\n"
            "ENTITIES: person:Emily; place:Kyoto; activity:pottery classes")
    facts_text, ents = split_entities_line(text)
    assert "ENTITIES:" not in facts_text
    assert {"name": "Emily", "type": "person"} in ents
    assert {"name": "Kyoto", "type": "place"} in ents
    assert {"name": "pottery classes", "type": "activity"} in ents


def test_split_entities_line_failsafe_without_marker():
    text = "The user enjoys pottery\nThe user lives in Rome"
    facts_text, ents = split_entities_line(text)
    assert facts_text == text
    assert ents == []


def test_ingest_links_typed_entities_to_matching_facts(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "d.db")
    llm = _StubLLM(
        "Donald Brown visited Kyoto with Emily in 2025\n"
        "Donald Brown enjoys pottery classes\n"
        "ENTITIES: person:Emily; place:Kyoto; activity:pottery classes")
    res = ingest_conversation(
        sm, [{"role": "user", "content": "trip talk"}], llm=llm,
        conversation_id="t2", consolidate=False, embed="auto",
        typed_entities=True)
    assert res["stored"] == 2, "la riga ENTITIES non deve diventare un fatto"

    kg = sqlite3.connect(entity_kg_path_for(sm.db_path))
    names = {r[0] for r in kg.execute("select canonical_name from entities")}
    assert {"Emily", "Kyoto"} <= names
    # Emily è linkata SOLO al fatto che la nomina
    row = kg.execute(
        "select count(distinct ef.fact_id) from entity_facts ef "
        "join entities e on e.id = ef.entity_id where e.canonical_name = ?",
        ("Emily",)).fetchone()
    assert row[0] == 1


def test_ingest_without_entities_line_unchanged(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "d.db")
    llm = _StubLLM("Donald Brown enjoys pottery classes")
    res = ingest_conversation(
        sm, [{"role": "user", "content": "x"}], llm=llm,
        conversation_id="t3", consolidate=False, embed="auto")
    assert res["stored"] == 1
