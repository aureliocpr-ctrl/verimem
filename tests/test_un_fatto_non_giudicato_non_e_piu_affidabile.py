"""Un fatto scritto SENZA il gate non può dichiararsi più affidabile di uno giudicato.

`consolidation._persist_master` costruisce a mano `Fact(..., confidence=0.85)` e
chiama `sm.store(f)` — **non** `Memory.add()`. Non passa quindi né dal moat né
dallo screen lessicale: nessuno ha confrontato quel testo con una fonte.

Misurato sul corpus di casa il 02/09:

    i 144 auto-consolidati   confidence 0.85   grounding_score NULL
    i fatti passati dal gate confidence 0.5    (10532 fatti)

⇒ **La scala di fiducia è invertita rispetto alla verifica**: chi non è stato
giudicato si attribuisce quasi il doppio della fiducia di chi lo è stato, con una
fonte, e ha passato. La `confidence` entra nel ranking del recall, quindi non è
un'etichetta decorativa: un aggregato mai verificato scavalca i fatti verificati.

L'invariante che questo test presidia è **relativo**, non un valore fisso: non
dice quanto debba valere la confidence del master, dice che **non può superare**
quella di un fatto ammesso dal gate con una fonte che lo sostiene.
"""
import os
import tempfile

import pytest


@pytest.fixture()
def store_isolato(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="test_confidenza_")
    monkeypatch.setenv("HIPPO_DATA_DIR", tmp)
    monkeypatch.setenv("ENGRAM_DATA_DIR", tmp)
    monkeypatch.delenv("VERIMEM_DATA_DIR", raising=False)
    return tmp


def test_il_master_non_supera_la_confidenza_di_un_fatto_giudicato(store_isolato):
    from verimem import Memory
    from verimem.consolidation import _persist_master
    from verimem.memory import EpisodicMemory

    m = Memory()
    # `Memory` non espone lo store episodico (`m.episodic` NON esiste: il primo
    # giro di questo test falliva li', e sembrava un RED sull'invariante mentre
    # era un sensore scollegato). `_persist_master` lo vuole come argomento.
    episodico = EpisodicMemory()

    # ── il metro: un fatto che HA passato il gate, con una fonte che lo sostiene
    r = m.add(
        "I bancali ricevuti dal magazzino sono tre.",
        topic="test/metro",
        source="Il magazzino ha ricevuto tre bancali il 9 giugno.",
    )
    assert r.get("grounding_score") is not None, (
        "il fatto di riferimento dev'essere stato GIUDICATO, altrimenti il "
        "confronto non misura nulla: senza fonte il gate non assegna un punteggio"
    )
    giudicato = m.semantic.get(r["id"])
    confidenza_giudicata = float(giudicato.confidence)

    # ── il caso: un master scritto dal consolidamento, che il gate non vede
    ep_id, fact_id, _edges = _persist_master(
        m.semantic,
        episodico,
        {"topic_prefix": "test/metro", "fact_count": 1, "fact_ids": [r["id"]]},
        {"topic": "test/metro/auto-MASTER",
         "proposition": "AUTO-CLUSTER-MASTER test/metro — auto-consolidated entry point organizing 1 sub-facts"},
    )
    master = m.semantic.get(fact_id)
    assert master is not None, "il master dev'essere stato scritto"
    assert master.grounding_score is None, (
        "controllo positivo dell'ipotesi: il master NON dev'essere stato "
        "giudicato — se qui avesse un punteggio, il difetto sarebbe un altro"
    )

    assert float(master.confidence) <= confidenza_giudicata, (
        f"un fatto scritto senza passare dal gate (grounding_score NULL) dichiara "
        f"confidence {float(master.confidence):.2f}, mentre un fatto GIUDICATO con "
        f"una fonte che lo sostiene ne dichiara {confidenza_giudicata:.2f}: la scala "
        f"di fiducia e' invertita rispetto alla verifica, e la confidence pesa sul "
        f"ranking del recall."
    )


def test_il_ripiego_scatta_se_il_cluster_punta_a_fatti_spariti(store_isolato):
    """Il ramo di ripiego: nessuna confidenza da ereditare.

    ⚠️ Il caso «un figlio con `confidence` NULL» **non può prodursi**: la colonna
    ha un vincolo `NOT NULL` e un UPDATE a NULL solleva `IntegrityError`
    (verificato: `NOT NULL constraint failed: facts.confidence`). Il ramo `else`
    resta però raggiungibile per un'altra strada, e questa è reale: il cluster
    porta `fact_ids` che al momento della persistenza **non esistono più** —
    cancellati fra il rilevamento e la scrittura. Allora la query non torna
    righe, la lista è vuota, e il master deve valere il default di classe (0.5),
    non un numero inventato e non un errore.
    """
    from verimem import Memory
    from verimem.consolidation import _persist_master
    from verimem.memory import EpisodicMemory
    from verimem.semantic import Fact

    m = Memory()
    _ep, fact_id, _e = _persist_master(
        m.semantic,
        EpisodicMemory(),
        # id che non esistono: il cluster e' stato rilevato e poi svuotato
        {"topic_prefix": "test/ripiego", "fact_count": 2,
         "fact_ids": ["ffffffffffff", "eeeeeeeeeeee"]},
        {"topic": "test/ripiego/auto-MASTER",
         "proposition": "AUTO-CLUSTER-MASTER test/ripiego — auto-consolidated entry point organizing 2 sub-facts"},
    )
    master = m.semantic.get(fact_id)
    assert master is not None, "il master dev'essere scritto anche senza figli leggibili"
    assert float(master.confidence) == float(Fact.confidence), (
        f"senza confidenze da ereditare il master deve valere il default di classe "
        f"({Fact.confidence}), non {master.confidence}"
    )
    assert float(Fact.confidence) == 0.5, (
        "controllo del controllo: se il default di classe cambiasse, l'assert "
        "sopra confronterebbe un valore con se stesso e non misurerebbe piu' nulla"
    )


def test_la_colonna_confidenza_non_ammette_il_nulla(store_isolato):
    """Perche' il caso «figlio con confidenza NULL» non e' nel test qui sopra."""
    import sqlite3

    from verimem import Memory

    m = Memory()
    r = m.add("I bancali ricevuti sono tre.", topic="test/vincolo",
              source="Il magazzino ha ricevuto tre bancali.")
    con = sqlite3.connect(str(m.semantic.db_path))
    try:
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("UPDATE facts SET confidence = NULL WHERE id = ?", (r["id"],))
            con.commit()
    finally:
        con.close()
