"""L'indice di cluster batte i fatti che indicizza, e li batte perché li copia.

`auto_consolidate` crea per ogni cluster di topic un nodo MASTER additivo — un
INDICE, non un'affermazione — la cui proposition finisce con:

    Top representative atomi: <primi 60 char del fatto 1> | <fatto 2> | <fatto 3>

Concatenando frammenti di N fatti, l'indice contiene le parole chiave di TUTTI e
vince il ranking semantico contro ognuno di essi. Misurato sul corpus vivo
2026-07-30, 40 query «cosa so di <topic>» sui topic che hanno un indice:

    indice nei primi tre : 22/40  (55%)
    indice al PRIMO posto: 11/40  (28%)

Con k=3, un indice nei primi tre è un fatto vero in meno. E ciò che offre al suo
posto sono spezzoni tagliati a metà parola: «il verbo del giocatore (play |».

Non è confabulazione — l'assemblaggio è deterministico e senza LLM (lezione
2026-06-29, verificata sul codice) — ed è la ragione per cui la cura è nel TESTO
e non nel read path: togliere i frammenti fa perdere all'indice la sua rendita di
posizione senza toccare il ranking, e non perde informazione perché un frammento
troncato non informa nessuno. Quante e quali sono le sub-facts resta scritto, e
i `key_facts` restano nel dict per gli edge.
"""
from __future__ import annotations

import tempfile
from pathlib import Path


def _cluster_master(props: list[str]) -> dict:
    """Il master che il consolidamento costruirebbe per questi fatti."""
    import sqlite3

    from verimem.consolidation import propose_master_node
    from verimem.semantic import Fact, SemanticMemory

    sm = SemanticMemory(db_path=Path(tempfile.mkdtemp()) / "s.db")
    ids = []
    for i, p in enumerate(props):
        f = Fact(proposition=p, topic="prova/cluster", source_episodes=[])
        sm.store(f, embed="defer")
        ids.append(f.id)
    del sqlite3
    return propose_master_node(sm, {"topic_prefix": "prova/cluster",
                                   "fact_ids": ids})


FATTI = [
    "Il servizio di fatturazione ascolta sulla porta 8443 dietro nginx.",
    "Il database di produzione e PostgreSQL 16 su db-prod-01.",
    "Il rilascio della versione 0.8.0 e previsto per settembre.",
]


def test_the_index_does_not_carry_fragments_of_the_facts():
    """La rendita di posizione: le keyword dei figli dentro il padre."""
    master = _cluster_master(FATTI)
    prop = master["proposition"]
    for f in FATTI:
        assert f[:40] not in prop, (
            f"l'indice contiene un frammento del fatto che indicizza:\n{prop}"
        )


def test_the_index_still_says_what_it_indexes():
    """Togliere i frammenti non deve renderlo muto: quante sub-facts e quale
    prefisso restano l'informazione utile di un indice."""
    master = _cluster_master(FATTI)
    prop = master["proposition"]
    assert "prova/cluster" in prop, prop
    assert "3" in prop, f"non dice quante sub-facts indicizza: {prop}"


def test_key_facts_are_still_available_to_the_caller():
    """Non spariscono: servono agli edge causali, solo non al testo indicizzato."""
    master = _cluster_master(FATTI)
    assert len(master.get("key_facts") or []) >= 1


def test_no_fragment_is_truncated_mid_word_anywhere():
    """Il sintomo visibile che ha fatto scoprire il caso — «(play |» — non deve
    poter ricomparire in nessuna forma."""
    master = _cluster_master(FATTI)
    assert " | " not in master["proposition"], master["proposition"]
