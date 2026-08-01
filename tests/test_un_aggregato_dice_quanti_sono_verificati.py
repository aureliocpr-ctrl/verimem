"""Un aggregato non porta il payload per fatto: dice quanti ne ha di verificati.

`facts_cluster_by_topic` raggruppa i fatti per topic e per ogni gruppo stampa
`avg_confidence`. La confidenza NON e' una misura di verifica: sul corpus vivo
e' un default per-canale che il moat non riscrive, quindi un cluster di fatti
giudicati 100 e uno di fatti mai guardati mostrano lo stesso numero — e chi
legge lo prende per una misura di affidabilita'.

Il censimento del 2026-07-30 l'ha trovato fra le superfici senza verdetto, ma
chiedergli il payload per fatto sarebbe stato copiare la cura sbagliata: questo
e' un aggregato, e la domanda giusta per un aggregato non e' «porti il campo»
ma «quanti di quelli che riassumi sono stati verificati».
"""
from __future__ import annotations

from verimem.facts_cluster_by_topic import facts_cluster_by_topic
from verimem.semantic import Fact


def _corpus():
    return [
        Fact(proposition="a", topic="t1", confidence=0.9, grounding_score=99.0),
        Fact(proposition="b", topic="t1", confidence=0.9, grounding_score=81.0),
        Fact(proposition="c", topic="t1", confidence=0.9),
        Fact(proposition="d", topic="t2", confidence=0.9),
    ]


def _cluster(out, topic):
    return next(c for c in out["clusters"] if c["topic"] == topic)


def test_dice_quanti_sono_stati_giudicati():
    c = _cluster(facts_cluster_by_topic(_corpus()), "t1")
    assert c["n_judged"] == 2, c


def test_la_media_e_sui_soli_giudicati():
    """Contare i non giudicati come zero inventerebbe una bocciatura: «mai
    misurato» non e' «misurato male»."""
    c = _cluster(facts_cluster_by_topic(_corpus()), "t1")
    assert c["avg_grounding"] == 90.0, c


def test_un_cluster_senza_nessun_giudicato_non_finge_uno_zero():
    c = _cluster(facts_cluster_by_topic(_corpus()), "t2")
    assert c["n_judged"] == 0
    assert c["avg_grounding"] is None, (
        "con nessun fatto giudicato la media non esiste, e 0.0 si leggerebbe "
        "come «tutti bocciati»")


def test_la_confidenza_resta_dov_era():
    """Si affianca, non sostituisce: chi leggeva avg_confidence continua a
    trovarla."""
    c = _cluster(facts_cluster_by_topic(_corpus()), "t1")
    assert abs(c["avg_confidence"] - 0.9) < 1e-9
    assert c["count"] == 3
