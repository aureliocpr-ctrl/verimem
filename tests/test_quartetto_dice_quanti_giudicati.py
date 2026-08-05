"""Il contatore dice anche quanti dei fatti serviti sono stati GIUDICATI.

Il quartetto rispondeva a «quanti ne restano» (scritti/servibili/ritirati/
quarantinati) e non a «di quelli che servo, quanti sono verificati» — che è
la domanda su cui questo prodotto è venduto. Misurato sul corpus reale il
2026-08-05:

    scritti 8113 · servibili 5631 · di cui giudicati 1360 (24,2%)
    => il prodotto SERVE 4271 fatti che il moat non ha mai giudicato

Il numero esisteva (`verimem doctor` lo riporta, e ws4 l'aveva misurato al
19,3% su una fotografia precedente) ma non era nel contatore che la cabina
mostra accanto agli altri, quindi nessuna vista lo metteva vicino ai
servibili — dove significa qualcosa.

`judged` conta sui SERVIBILI e non su tutti: un fatto ritirato o
quarantinato non viene servito a nessuno, e includerlo gonfierebbe il
denominatore proprio nel senso che fa comodo.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory
from verimem.retirement_log import survivability_counts

_FONTE = "Company handbook: our head office is located in Milan, Italy."


@pytest.fixture()
def misto(tmp_path):
    """Uno store con le tre sorti che contano: giudicato, mai giudicato,
    e uno ritirato (che non deve entrare nel conto dei serviti)."""
    m = Memory(tmp_path / "memory.db")
    a = m.add("the office headquarters are in Milan", topic="hq",
              source=_FONTE)                       # giudicato
    b = m.add("the warehouse is in Turin", topic="wh",
              verified_by=["doc"])                 # MAI giudicato
    c = m.add("the branch is in Rome", topic="br", verified_by=["doc"])
    m.semantic.supersede(c["id"], b["id"], principal="t", reason="banco")
    return m, a, b


def test_il_contatore_dice_quanti_sono_giudicati(misto):
    m, a, _b = misto
    q = m.survivability()
    assert a["grounding_score"] is not None
    assert q["judged"] == 1, q
    assert q["servable"] == 2, q


def test_judged_conta_sui_SERVIBILI_non_su_tutti(misto):
    """Un ritirato non lo serve nessuno: entrarci gonfierebbe il
    denominatore proprio nel senso che fa comodo."""
    m, _a, _b = misto
    q = m.survivability()
    assert q["judged"] <= q["servable"] < q["written"], q


def test_la_formula_del_giudicato_e_dichiarata(misto):
    """Un numero senza la sua definizione è il difetto che questo ramo cura:
    chi legge deve sapere che `null` vuol dire mai giudicato, non bocciato."""
    m, _a, _b = misto
    q = m.survivability()
    assert "judged" in q["formula"], q["formula"]
    assert "grounding_score" in q["formula"], q["formula"]


def test_arriva_su_ogni_porta(misto):
    """Come per il resto del quartetto: una sola sorgente, stesse chiavi."""
    m, _a, _b = misto
    assert survivability_counts(m.semantic)["judged"] == m.survivability()["judged"]
