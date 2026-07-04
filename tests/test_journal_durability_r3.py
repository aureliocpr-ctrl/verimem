"""Audit 3-round R1 #5 (durability): the crash-journal replay must force the
replayed writes to disk BEFORE it unlinks the journal.

_replay_pending_facts did `memory.store(...)` then `claim.unlink()` with no
checkpoint in between. With `synchronous=NORMAL` (WAL), a store is not
guaranteed durable until a checkpoint — so a power-cut in the unlink gap loses
BOTH the replayed write and the journal that recorded it. Fix:
`_durable_checkpoint(db_path)` (wal_checkpoint(FULL)+fsync) runs before the
unlink whenever the claim replayed anything.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import engram.semantic as semantic_mod
from engram.semantic import Fact, SemanticMemory


def test_checkpoint_runs_before_journal_unlink(tmp_path, monkeypatch) -> None:
    db = tmp_path / "semantic" / "semantic.db"
    db.parent.mkdir(parents=True)
    SemanticMemory(db_path=db)  # create schema, then close

    orphan = Fact(proposition="durable before the journal dies", topic="t/dur")
    jpath = semantic_mod._journal_path_for(db)
    jpath.write_text(
        json.dumps({"kind": "fact", "fact": asdict(orphan),
                    "store_kwargs": {"embed": "sync"}}) + "\n",
        encoding="utf-8",
    )

    # The durability barrier must exist (introduced by the fix).
    real_ckpt = getattr(semantic_mod, "_durable_checkpoint", None)
    assert real_ckpt is not None, (
        "manca _durable_checkpoint: il replay deve forzare la durabilita' "
        "prima di rimuovere il journal"
    )

    events: list[str] = []

    def spy_ckpt(p):
        events.append("checkpoint")
        return real_ckpt(p)

    monkeypatch.setattr(semantic_mod, "_durable_checkpoint", spy_ckpt)

    real_unlink = Path.unlink

    def spy_unlink(self, *a, **k):
        if self.suffix == ".jsonl" or "replay-" in self.name:
            events.append("unlink")
        return real_unlink(self, *a, **k)

    monkeypatch.setattr(Path, "unlink", spy_unlink)

    sm = SemanticMemory(db_path=db)  # __init__ replays the orphan
    assert sm.get(orphan.id) is not None, "il replay deve persistere l'orphan"
    assert "checkpoint" in events, "la barriera di durabilita' deve girare"
    assert "unlink" in events, "il journal deve essere rimosso dopo il replay"
    assert events.index("checkpoint") < events.index("unlink"), \
        "il checkpoint durabile deve precedere l'unlink del journal"
