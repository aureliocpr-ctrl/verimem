"""Routing temporale della query → time-travel (cantiere attenzione, 2026-07-08).

Gap misurato (A/B attn_order_ab + ispezione contesto): su domande "as of
<data>" il recall porta fatti di TUTTA la timeline marcati [current] (anche
2033-2043 per una domanda sul 2025) → 6 fatti income contraddittori nel
contesto → l'answerer si astiene PUR AVENDO la risposta alla riga 2. Il
motore HA il time-travel (recall_as_of, bi-temporale v13): mancava il
cablaggio query→as_of. Qui: extract_as_of (parsing esplicito, None se la
domanda non àncora una data) + recall_with_history(as_of=...) che compone il
time-travel con l'enrichment, etichettando [as of <date>].
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from engram.semantic import Fact, SemanticMemory
from engram.temporal_context import extract_as_of, recall_with_history


def _epoch(y, m, d, hh=0, mm=0, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc).timestamp()


# ------------------------------------------------------------ extract_as_of

def test_extract_as_of_iso_date():
    t = extract_as_of("What is Johnson's major in Engineering as of 2025-09-04?")
    assert t is not None
    # fine giornata UTC: i fatti asserted QUEL giorno sono inclusi
    assert abs(t - _epoch(2025, 9, 4, 23, 59, 59)) < 2


def test_extract_as_of_verbose_date_forms():
    t1 = extract_as_of("What was the income on Dec 21, 2025?")
    assert t1 is not None and abs(t1 - _epoch(2025, 12, 21, 23, 59, 59)) < 2
    t2 = extract_as_of("Did the B&B host 5,000 guests by Jun 21, 2026?")
    assert t2 is not None and abs(t2 - _epoch(2026, 6, 21, 23, 59, 59)) < 2
    t3 = extract_as_of("What did he prefer as of February 27, 2041?")
    assert t3 is not None and abs(t3 - _epoch(2041, 2, 27, 23, 59, 59)) < 2


def test_extract_as_of_none_when_no_temporal_anchor():
    assert extract_as_of("What is Johnson Joseph's MBTI type?") is None
    assert extract_as_of("") is None
    assert extract_as_of(None) is None
    # "after <date>" = periodo APERTO successivo: il time-travel lo
    # taglierebbe — esplicitamente NON instradato
    assert extract_as_of("How did things change after Dec 21, 2025?") is None


# ---------------------------------------- recall_with_history(as_of=...)

def test_recall_with_history_as_of_hides_the_future(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "d.db")
    old = Fact(proposition="the monthly income is 3500 USD",
               topic="t", asserted_at=_epoch(2025, 9, 5))
    sm.store(old, embed="sync")
    new = Fact(proposition="the monthly income is 4500 USD",
               topic="t", asserted_at=_epoch(2026, 6, 1))
    sm.store(new, embed="sync")
    sm.supersede(old.id, new.id, reason="raise")

    # domanda ancorata a ottobre 2025: deve vedere il 3500, NON il 4500 futuro
    lines = recall_with_history(sm, "monthly income", k=5,
                                as_of=_epoch(2025, 10, 1))
    joined = "\n".join(lines)
    assert "3500" in joined, "il fatto corrente ALLA DATA deve esserci"
    assert "4500" not in joined, "un fatto asserted DOPO as_of non deve apparire"
    assert "as of" in joined, "le righe as-of dichiarano il punto temporale"

    # senza as_of: comportamento invariato (il corrente vince)
    live = "\n".join(recall_with_history(sm, "monthly income", k=5))
    assert "4500" in live
