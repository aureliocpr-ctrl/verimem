"""Un numero CITATO dentro il testo servito non deve smentire il campo
vivo che gli sta di fianco nello stesso payload.

Il difetto, letto il 30/08 chiamando il prodotto da utente
(``hippo_retirement_log breakdown=true`` sul corpus di casa)::

    "by_scope": {"same_topic": 698, "cross_topic": 1538}
    "scope_means": "... The same-topic 266 are where supersession is a
                    real editorial act ..."

698 accanto a 266, nella stessa risposta. Nessuno dei due e' sbagliato:
1463 e 1538 vengono da un EVENTO congelato (il collasso del 2026-07-02) e
sono esatti ancora oggi, mentre 266 e' un FLUSSO che da allora e'
cresciuto. Il testo li mette in fila senza distinguerli, e il lettore
confronta l'ultimo col campo di fianco.

La cura del 2026-08-07 (``measured_at``, ``since``, le ``formula``) aveva
gia' affrontato questo: dare l'istante ai numeri. Ha coperto i numeri
VIVI e ha lasciato scoperti quelli citati DENTRO il testo — la stessa
forma del difetto che curava.

Qui il numero non si data: si DERIVA. Un valore calcolato tre righe
sopra non puo' divergere da se stesso.
"""
from __future__ import annotations

import re

import pytest

from verimem.client import Memory
from verimem.retirement_log import retirement_breakdown


@pytest.fixture()
def mem_con_same_topic(tmp_path):
    """Due ritiri DENTRO lo stesso topic: e' il caso che la fixture del
    banco gemello (``test_housekeeping_non_vuol_dire_senza_perdita``) non
    produce, perche' li' ``same_topic`` vale 0 e il confronto non si vede."""
    m = Memory(tmp_path / "m.db")
    a = m.add("the depot holds 10 crates", topic="log/a")["id"]
    b = m.add("the depot holds 20 crates", topic="log/a")["id"]
    c = m.add("the depot holds 30 crates", topic="log/a")["id"]
    m.semantic.supersede(a, b, principal="test", reason="banco")
    m.semantic.supersede(b, c, principal="test", reason="banco")
    return m


def test_il_numero_citato_nel_testo_NON_deve_smentire_il_campo_vivo(
        mem_con_same_topic):
    bd = retirement_breakdown(mem_con_same_topic.semantic)
    vivo = bd["by_scope"]["same_topic"]
    assert vivo == 2, bd["by_scope"]
    citato = re.search(r"same-topic\s+([\d,]+)", bd["scope_means"])
    assert citato is not None, bd["scope_means"]
    assert int(citato.group(1).replace(",", "")) == vivo, (
        f"il testo dice {citato.group(1)}, il campo accanto dice {vivo}")


def test_i_numeri_dell_EVENTO_restano_letterali_e_datati(mem_con_same_topic):
    """Il rovescio: 1463 e 1538 NON vanno derivati. Sono la misura di un
    evento del passato, dichiarata con la sua data, e su un banco da tre
    fatti diventerebbero 0 — cioe' si perderebbe l'informazione."""
    nota = retirement_breakdown(mem_con_same_topic.semantic)["scope_means"]
    assert "1463" in nota and "1538" in nota, nota
    assert "2026-08-07" in nota, nota
