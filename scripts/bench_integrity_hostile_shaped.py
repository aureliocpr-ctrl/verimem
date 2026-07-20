"""Measure the integrity screening on hostile-SHAPED legitimate content.

Closes the limit we declared ourselves in the 0.7.0 CHANGELOG ("0 content
false positives on 500 knowledge texts — honest limit: that corpus is not
hostile-shaped-legitimate"). Runs the REAL write path (SemanticMemory.store
through the injection screen + admission gate), not the detectors in
isolation, so what is measured is what a customer actually gets.

Reports, per label:
  legit  -> false-positive rate (blocked/quarantined legitimate knowledge)
  attack -> catch rate (the defense still has to work)

Usage: python scripts/bench_integrity_hostile_shaped.py [--json]
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from benchmark.hostile_shaped_corpus import CASES  # noqa: E402
from verimem.semantic import Fact, SemanticMemory  # noqa: E402


def _status_of(db, fact_id: str) -> str | None:
    con = sqlite3.connect(db)
    try:
        row = con.execute(
            "SELECT status FROM facts WHERE id = ?", (fact_id,)).fetchone()
        return row[0] if row else None
    finally:
        con.close()


def _in_telemetry(db, fact_id: str) -> bool:
    con = sqlite3.connect(db)
    try:
        return con.execute(
            "SELECT 1 FROM telemetry WHERE id = ?", (fact_id,)).fetchone() \
            is not None
    except sqlite3.OperationalError:
        return False
    finally:
        con.close()


def run(writer_role: str = "agent_inference") -> dict:
    """Store every case through the REAL write path and report outcomes.

    ``writer_role`` is the arm under test: the default (an agent asserting
    the text itself) versus ``external_content`` — the escape the store's
    own log advertises ("if this text was ingested from a document or user,
    set writer_role='external_content' to route it to the document policy").
    A customer whose knowledge QUOTES attacks is exactly that case, so the
    two arms answer: is a hostile-shaped false positive a detector problem
    or a default/DX problem?
    """
    tmp = Path(tempfile.mkdtemp(prefix="verimem_hostile_bench_"))
    db = tmp / "bench.db"
    sm = SemanticMemory(db_path=db)

    rows = []
    for cid, topic, text, label in CASES:
        f = Fact(id=cid, proposition=text, topic=topic,
                 status="model_claim", source_episodes=["bench-src"],
                 writer_role=writer_role)
        sm.store(f, embed="defer")
        status = _status_of(db, cid)
        routed = _in_telemetry(db, cid)
        blocked = (status in (None, "quarantined")) or routed
        rows.append({
            "id": cid, "label": label, "topic": topic[:48],
            "status": status, "routed_telemetry": routed, "blocked": blocked,
        })

    legit = [r for r in rows if r["label"] == "legit"]
    atk = [r for r in rows if r["label"] == "attack"]
    fp = [r for r in legit if r["blocked"]]
    fn = [r for r in atk if not r["blocked"]]

    return {
        "n_legit": len(legit), "n_attack": len(atk),
        "false_positives": len(fp),
        "false_positive_rate": round(len(fp) / len(legit), 3) if legit else None,
        "false_positive_ids": [r["id"] for r in fp],
        "attacks_caught": len(atk) - len(fn),
        "catch_rate": round((len(atk) - len(fn)) / len(atk), 3) if atk else None,
        "missed_attack_ids": [r["id"] for r in fn],
        "rows": rows,
    }


def _report(name: str, res: dict) -> None:
    print(f"--- arm: {name}")
    print(f"legit n={res['n_legit']}  FALSE POSITIVES={res['false_positives']}"
          f"  rate={res['false_positive_rate']}")
    for i in res["false_positive_ids"]:
        print(f"   FP: {i}")
    print(f"attack n={res['n_attack']}  caught={res['attacks_caught']}"
          f"  rate={res['catch_rate']}")
    for i in res["missed_attack_ids"]:
        print(f"   MISSED: {i}")


if __name__ == "__main__":
    arms = {
        "default (agent_inference)": run("agent_inference"),
        "external_content (the advertised escape)": run("external_content"),
    }
    if "--json" in sys.argv:
        print(json.dumps(arms, indent=2, ensure_ascii=False))
    else:
        for name, res in arms.items():
            _report(name, res)
