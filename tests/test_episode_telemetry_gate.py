"""Write-time episode telemetry separation (2026-06-14).

The gemello of SemanticMemory's fact telemetry routing: when the admission gate
is ON, cross-LLM call records ([agy-call …] / [gemini-call …], auto-saved by the
bridge — 22% of the live episode store) are routed at WRITE time to a separate
``episode_telemetry`` table, so the curated ``episodes`` corpus stays REAL tasks
and recall needs no filter. Non-lossy; OFF (default) = byte-identical legacy.
"""
from __future__ import annotations

import sqlite3

from verimem._call_telemetry import is_call_telemetry
from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory


def _ep(task_id, text, outcome="success", final="x"):
    return Episode(
        task_id=task_id, task_text=text, outcome=outcome, final_answer=final,
        traces=[Trace(step=1, thought="t", action="a", action_input="{}", observation="o")],
        tokens_used=10,
    )


def test_is_call_telemetry_detector():
    for t in ["[agy-call 2026-06-13] prompt=critic", "[gemini-call x]",
              "  [DEEPSEEK-call y]", "[kimi-call z]"]:
        assert is_call_telemetry(t) is True, t
    for t in ["fix the embedding recall bug", "call the API to fetch data",
              "[DECISION] cycle #53", None, ""]:
        assert is_call_telemetry(t) is False, t


def test_gate_on_routes_call_telemetry_to_separate_table(tmp_data_dir, monkeypatch):
    monkeypatch.setattr("verimem.admission_gate.gate_enabled", lambda: True)
    db = tmp_data_dir / "episodes" / "ep.db"
    m = EpisodicMemory(db)
    # final_answer carries the LLM's response — the most valuable payload; it
    # MUST survive the routing (the critic counterexample: it was being dropped).
    tel = _ep("t1", "[agy-call 2026-06-13] prompt=critic adversarial popperiano",
              final="VERDICT: HOLD — the claim survives falsification.")
    real = _ep("t2", "fix the embedding recall bug in the model")
    m.store(tel)
    m.store(real)
    # the curated episodes store holds ONLY the real task
    ids = {e.id for e in m.all()}
    assert real.id in ids
    assert tel.id not in ids, "call-telemetry must not pollute the curated episodes store"
    assert m.get(tel.id) is None
    # TRULY non-lossy: the FULL episode (task_text + final_answer + traces) is
    # preserved verbatim in episode_telemetry — routed out of recall, NOT deleted.
    con = sqlite3.connect(db)
    row = con.execute(
        "SELECT task_text, payload FROM episode_telemetry WHERE id=?", (tel.id,)
    ).fetchone()
    con.close()
    assert row is not None and row[0].startswith("[agy-call")
    import json
    payload = json.loads(row[1])
    assert payload["final_answer"] == "VERDICT: HOLD — the claim survives falsification.", (
        "final_answer (the LLM response) must NOT be dropped on routing"
    )
    assert payload["traces"] and payload["traces"][0]["action"] == "a", "traces must survive too"


def test_gate_off_keeps_legacy_behaviour(tmp_data_dir, monkeypatch):
    monkeypatch.setattr("verimem.admission_gate.gate_enabled", lambda: False)
    db = tmp_data_dir / "episodes" / "ep.db"
    m = EpisodicMemory(db)
    tel = _ep("t1", "[agy-call x] prompt=y")
    m.store(tel)
    # gate OFF -> the call record stays in episodes (byte-identical legacy path)
    assert m.get(tel.id) is not None, "with the gate OFF nothing is routed away"


def test_real_task_always_stays_in_episodes(tmp_data_dir, monkeypatch):
    monkeypatch.setattr("verimem.admission_gate.gate_enabled", lambda: True)
    db = tmp_data_dir / "episodes" / "ep.db"
    m = EpisodicMemory(db)
    real = _ep("t1", "implement the semantic correction detector")
    m.store(real)
    assert m.get(real.id) is not None
