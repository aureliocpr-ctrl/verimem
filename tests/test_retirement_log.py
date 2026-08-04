"""retirement_log — la finestra sui ritiri che nessuna API mostrava.

Misurato il 2026-08-04 (ws5, canale verimem-coord): dopo un ritiro, SETTE
superfici di lettura tacciono — count/get_all/quarantine_log/epistemic_health/
history/recall/search non dicono che un fatto è stato ritirato, né da chi né
perché. Le colonne esistono dallo schema v2 (superseded_by/at/reason + indice);
mancava la QUERY esposta. L'equivalente di ``quarantine_log`` per i ritiri.

E il conto dei «vivi» usa la metrica CANONICA della ritrattazione ws3 22:32:
un fatto sparisce in DUE modi (ritirato O quarantinato) — contare solo il primo
ha fatto sembrare chiusa una cura che spostava la perdita da un nome all'altro.
``survivability_counts`` espone il quartetto scritti/servibili/ritirati/
quarantinati INSIEME, per topic: il buco si vede solo così.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory
from verimem.retirement_log import retirement_log, survivability_counts

_MILAN = "the office headquarters are in Milan"
_ROME = "the office headquarters moved to Rome"
_TURIN = "the logistics warehouse operates in Turin"
_HYPE = "everything works perfectly and the deployment is fully verified"


@pytest.fixture()
def popolato(tmp_path):
    """Uno store con le quattro sorti possibili di un fatto:
    servibile (Turin) · ritirato (Milan, da Rome) · quarantinato (hype)."""
    m = Memory(tmp_path / "memory.db")
    a = m.add(_MILAN, topic="hq/sedi", verified_by=["hr-doc"])["id"]
    t = m.add(_TURIN, topic="wh/turin", verified_by=["ops-doc"])["id"]
    q = m.add(_HYPE, topic="hq/sedi")          # L1: self-claim -> quarantined
    r = m.add(_ROME, topic="hq/sedi", verified_by=["hr-doc"])["id"]
    m.semantic.supersede(a, r, principal="test:log", reason="sede spostata")
    return m, {"loser": a, "winner": r, "vivo": t,
               "quarantinato": q.get("id"), "q_status": q.get("status")}


# ---- la coppia, non il singolo ----------------------------------------------

def test_log_ritorna_la_coppia_con_topic_e_reversibilita(popolato):
    m, ids = popolato
    rows = retirement_log(m.semantic)
    assert len(rows) == 1
    r = rows[0]
    assert r["loser_id"] == ids["loser"]
    assert r["winner_id"] == ids["winner"]
    assert r["loser_topic"] == "hq/sedi" and r["winner_topic"] == "hq/sedi"
    assert r["reason"] == "sede spostata"
    assert r["superseded_at"] is not None
    assert r["reversible"] is True, (
        "col timone attivo ogni ritiro nuovo nasce annullabile")
    assert r["undo_op_id"], "la riga porta l'handle: ripristino a un click"


def test_niente_testi_di_default_with_text_li_include(popolato):
    m, _ = popolato
    senza = retirement_log(m.semantic)[0]
    assert "loser_text" not in senza and "winner_text" not in senza, (
        "metadati di default: il feed non porta contenuto")
    con = retirement_log(m.semantic, with_text=True)[0]
    assert con["loser_text"] == _MILAN
    assert con["winner_text"] == _ROME


def test_filtri_topic_e_reason(popolato):
    m, _ = popolato
    assert len(retirement_log(m.semantic, topic="hq")) == 1
    assert len(retirement_log(m.semantic, topic="wh")) == 0
    assert len(retirement_log(m.semantic, reason="sede spostata")) == 1
    assert len(retirement_log(m.semantic, reason="altro")) == 0


# ---- il quartetto: i tre modi di sparire, scontati insieme -------------------

def test_survivability_counts_quartetto_canonico(popolato):
    m, ids = popolato
    tot = survivability_counts(m.semantic)
    # written = servable + retired + quarantined(non-ritirati): la somma
    # torna per costruzione, e il test l'ancora ai numeri dello store.
    assert tot["written"] == tot["servable"] + tot["retired"] + tot["quarantined"]
    assert tot["retired"] == 1
    if ids["q_status"] == "quarantined":       # il gate ha quarantinato l'hype
        assert tot["quarantined"] >= 1
    per_topic = survivability_counts(m.semantic, topic="hq/sedi")
    assert per_topic["retired"] == 1
    assert per_topic["written"] >= 2
