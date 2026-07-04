"""Audit#2 2026-06-08 A-8: backfill_pending_embeddings SELECTed (id, proposition)
of deferred rows, encoded the proposition, then UPDATE ... WHERE id=? AND
length(embedding)=0. If a concurrent writer EDITED the proposition (leaving the
embedding still deferred) between the SELECT and the UPDATE, the stale embedding
(of the OLD text) was written onto the NEW proposition — a vector in a different
semantic position than its text = silent recall poisoning. Fix: gate the UPDATE
on `AND proposition = ?` (the exact text we embedded) so a changed row is left
for the next pass, and only count rows that actually updated.
"""
from __future__ import annotations

from engram import embedding
from engram.semantic import Fact, SemanticMemory


def test_backfill_skips_row_whose_proposition_changed_under_it(tmp_path, monkeypatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    f = Fact(proposition="original text", topic="t", status="model_claim",
             source_episodes=["e"])
    sm.store(f, embed="defer")  # length-0 embedding sentinel
    with sm._connect() as c:
        fid = c.execute(
            "SELECT id FROM facts WHERE proposition = ?", ("original text",)
        ).fetchone()[0]

    orig_encode = embedding.encode

    def encode_then_concurrent_edit(text):
        # A concurrent edit landing AFTER the SELECT but BEFORE the UPDATE:
        # rewrite the proposition, leaving the embedding still deferred.
        with sm._connect() as conn:
            conn.execute(
                "UPDATE facts SET proposition = ? WHERE id = ?",
                ("EDITED text", fid),
            )
        return orig_encode(text)

    monkeypatch.setattr(embedding, "encode", encode_then_concurrent_edit)
    sm.backfill_pending_embeddings()

    with sm._connect() as c:
        row = c.execute(
            "SELECT proposition, length(embedding) AS L FROM facts WHERE id = ?",
            (fid,),
        ).fetchone()
    assert row["proposition"] == "EDITED text"
    assert row["L"] == 0, (
        "stale embedding written over a concurrently-edited proposition (A-8)"
    )
