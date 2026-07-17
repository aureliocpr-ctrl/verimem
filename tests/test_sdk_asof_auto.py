"""SDK: as_of="auto" — il routing temporale della query esposto sul prodotto.

Micro-bench validato (routed_asof_ab.json): 10/31 wrong→correct, Boundary
21/21. L'SDK espone il cablaggio: search(query, as_of="auto") estrae l'àncora
retrospettiva dalla domanda (extract_as_of) e va in time-travel solo quando
c'è; senza àncora resta il recall live, byte-identico.
"""
from __future__ import annotations

from datetime import datetime, timezone

from verimem.client import Memory


def _epoch(y, m, d):
    return datetime(y, m, d, tzinfo=timezone.utc).timestamp()


def _mem_with_transition(tmp_path):
    mem = Memory(tmp_path / "m.db")
    old = mem.add("the monthly income is 3500 USD",
                  verified_by=["payroll:2025-09"], asserted_at=_epoch(2025, 9, 5))
    new = mem.add("the monthly income is 4500 USD",
                  verified_by=["payroll:2026-06"], asserted_at=_epoch(2026, 6, 1))
    mem.semantic.supersede(old["id"], new["id"], reason="raise")
    return mem


def test_search_asof_auto_routes_anchored_question(tmp_path):
    mem = _mem_with_transition(tmp_path)
    hits = mem.search("what was the monthly income as of 2025-10-01?",
                      as_of="auto")
    texts = " | ".join(h["text"] for h in hits)
    assert "3500" in texts, "l'àncora retrospettiva deve attivare il time-travel"
    assert "4500" not in texts, "il valore futuro non deve apparire"


def test_search_asof_auto_is_noop_without_anchor(tmp_path):
    mem = _mem_with_transition(tmp_path)
    auto = mem.search("what is the monthly income?", as_of="auto")
    live = mem.search("what is the monthly income?")
    assert [h["text"] for h in auto] == [h["text"] for h in live], (
        "senza àncora, auto = recall live identico"
    )
    assert any("4500" in h["text"] for h in auto)
