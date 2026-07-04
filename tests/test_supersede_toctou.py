"""Audit 2026-06-08 A5: supersede() did SELECT(superseded_by IS NULL) -> branch
-> UNCONDITIONAL UPDATE. Two concurrent writers both pass the SELECT guard
(each sees NULL in its own snapshot), both UPDATE -> last-writer-wins, one
supersession lineage silently lost (the conflict guard is defeated). The real
deployment IS multi-process (CLI + MCP + auto_dream_worker + budget daemon all
write semantic.db). Fix: make the UPDATE a compare-and-set
(`WHERE id=? AND superseded_by IS NULL`) and treat rowcount==0 as a lost race
-> re-read the winner -> idempotent (same target) or SupersedeConflict.
"""
from __future__ import annotations

import threading

from engram.semantic import Fact, SemanticMemory, SupersedeConflict


def _store(sm, prop):
    f = Fact(proposition=prop, topic="x", status="model_claim", source_episodes=["e"])
    sm.store(f, embed="defer")
    with sm._connect() as c:
        return c.execute("SELECT id FROM facts WHERE proposition = ?", (prop,)).fetchone()[0]


def test_concurrent_supersede_has_exactly_one_winner(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    rounds = 40
    bad_rounds = 0
    for r in range(rounds):
        a = _store(sm, f"r{r}-A")
        b = _store(sm, f"r{r}-B")
        c = _store(sm, f"r{r}-C")
        results: dict[str, tuple] = {}
        barrier = threading.Barrier(2)

        def worker(new_id, tag, a=a, barrier=barrier, results=results):
            barrier.wait()  # release both threads together -> maximize the race
            try:
                res = sm.supersede(a, new_id, reason=tag)
                results[tag] = ("ok", bool(res.get("idempotent_noop")))
            except SupersedeConflict:
                results[tag] = ("conflict", False)
            except Exception as exc:  # noqa: BLE001
                results[tag] = ("error", repr(exc))

        t1 = threading.Thread(target=worker, args=(b, "B"))
        t2 = threading.Thread(target=worker, args=(c, "C"))
        t1.start(); t2.start(); t1.join(); t2.join()

        # exactly ONE real (non-idempotent) winner; the loser must NOT also
        # report a fresh success (that is the silent guard-defeat).
        winners = [k for k, (s, idem) in results.items() if s == "ok" and idem is False]
        if len(winners) != 1:
            bad_rounds += 1

    assert bad_rounds == 0, (
        f"{bad_rounds}/{rounds} rounds had != 1 winner — TOCTOU guard-defeat"
    )
