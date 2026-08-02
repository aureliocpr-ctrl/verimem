"""`n_quarantined` contava anche i quarantinati GIA' RITIRATI.

Il pannello di salute affianca `n_quarantined` a `n_live`, e il commento del
modulo prescrive proprio quella lettura: «Reporting it next to n_recallable
makes the headline honest: n_live (= total - superseded) counts quarantined
too, so a corpus that is 44% quarantined would look "mostly live/ready"
without this split».

Ma `n_live` ESCLUDE i superseduti e la query di `n_quarantined` NO. I due
numeri stanno nella stessa risposta e contano popolazioni diverse, quindi il
confronto che il commento raccomanda mette a rapporto insiemi non
confrontabili. Misurato sul corpus di Aurelio il 2026-08-02:

    n_total      6942
    n_superseded 1792
    n_live       5150   (= total - superseded)

    n_quarantined COSI COM E   1810  -> letto contro n_live: 35.1%
    n_quarantined FRA I VIVI    570  -> 11.1%

    dei 1810 dichiarati, 1240 NON stanno in n_live: sono gia' ritirati

Il pannello dichiara che oltre un terzo del corpus vivo e' trattenuto dal
gate, quando e' un ottavo. E manda a drenare una coda di 1240 fatti che la
coda l'hanno gia' lasciata — un fatto piu' nuovo ha gia' risposto per loro.

CINQUE SUPERFICI SU SEI ERANO GIA' D'ACCORDO fra loro e in disaccordo con
questa: `cli.py:205`, `client.py:1449`, `mcp_server.py:13011` e le due di
`review_queue.py` filtrano tutte `AND superseded_by IS NULL`, e il docstring
di `review_queue._count` spiega perche': «a superseded row left the queue: a
newer fact already answered it». Non c'e' una semantica da scegliere, c'e'
una superficie che si era persa la riga.
"""
from __future__ import annotations

import time

import pytest

from verimem.corpus_health_metrics import corpus_health_metrics
from verimem.semantic import Fact, SemanticMemory


@pytest.fixture()
def mem(tmp_path):
    return SemanticMemory(db_path=tmp_path / "semantic.db")


def _fatto(mem, fid: str, testo: str, *, status: str = "verified") -> None:
    mem.store(Fact(id=fid, proposition=testo, topic="t", status=status,
                   created_at=time.time()))


def test_un_quarantinato_ritirato_non_e_piu_in_coda(mem):
    """Il caso in una riga: due quarantinati, uno gia' sostituito."""
    _fatto(mem, "q-vecchio", "Il piano costa 100 euro.", status="quarantined")
    _fatto(mem, "q-vivo", "La quota annuale non e' nota.", status="quarantined")
    _fatto(mem, "nuovo", "Il piano costa 200 euro.")
    mem.supersede("q-vecchio", "nuovo", principal="test")

    m = corpus_health_metrics(mem)
    assert m["n_quarantined"] == 1, (
        f"n_quarantined={m['n_quarantined']}: conta anche il ritirato, che la "
        f"coda l'ha gia' lasciata — un fatto piu' nuovo ha risposto per lui")


def test_il_numero_e_confrontabile_con_n_live(mem):
    """Il difetto vero non e' il conteggio, e' il CONFRONTO che il modulo
    stesso raccomanda: `n_quarantined` non puo' eccedere `n_live` se deve
    essere letto come «quanta parte del vivo e' trattenuta»."""
    for i in range(4):
        _fatto(mem, f"q{i}", f"Una claim non verificata numero {i}.",
               status="quarantined")
    _fatto(mem, "sostituto", "Il fatto che li rimpiazza.")
    for i in range(3):
        mem.supersede(f"q{i}", "sostituto", principal="test")

    m = corpus_health_metrics(mem)
    assert m["n_quarantined"] <= m["n_live"], (
        f"n_quarantined={m['n_quarantined']} > n_live={m['n_live']}: due "
        f"popolazioni diverse affiancate nella stessa risposta")
    assert m["n_quarantined"] == 1, m


def test_senza_supersessioni_il_numero_non_cambia(mem):
    """Controprova: la cura non deve spostare il caso normale."""
    for i in range(3):
        _fatto(mem, f"q{i}", f"Una claim non verificata numero {i}.",
               status="quarantined")
    _fatto(mem, "sano", "Un fatto verificato qualunque.")
    m = corpus_health_metrics(mem)
    assert m["n_quarantined"] == 3, m
    assert m["n_live"] == 4, m


def test_le_sei_superfici_contano_la_stessa_cosa(mem):
    """Il criterio operativo, non il numero: qualunque superficie dichiari
    «quanti sono in quarantena» deve dare la risposta di `review_queue`, che
    e' quella documentata («a superseded row left the queue»).

    Se un giorno nasce una settima superficie con la sua query, questo test
    non se ne accorge — ma le sei che c'erano restano d'accordo, ed e' il
    disaccordo fra loro ad aver prodotto il difetto.
    """
    from verimem.review_queue import depth

    _fatto(mem, "q-vecchio", "Una claim ritirata.", status="quarantined")
    _fatto(mem, "q-vivo", "Una claim ancora in coda.", status="quarantined")
    _fatto(mem, "nuovo", "Il fatto che l'ha sostituita.")
    mem.supersede("q-vecchio", "nuovo", principal="test")

    assert corpus_health_metrics(mem)["n_quarantined"] == depth(mem.db_path)
