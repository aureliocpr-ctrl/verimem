"""Episodi: recall robusto a summary/context embedding corrotti (NaN/inf).

Stessa classe del fix facts (semantic.recall): una riga embedding NaN/inf
propaga NaN nello score. recall() passa per _rerank_and_finalise (floor
min_similarity puo' gia' scartare NaN>=0=False) MENTRE recall_by_context NO.
Il test e' EMPIRICO: dice quali path perdono davvero, si fixa solo quelli.
"""
from __future__ import annotations

import sqlite3

import numpy as np
import pytest

from engram import embedding as emb
from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory

_DIM = 384


@pytest.fixture(autouse=True)
def _gate_off(monkeypatch):
    monkeypatch.delenv("ENGRAM_ADMISSION_GATE", raising=False)


def _ep(eid, text):
    return Episode(id=eid, task_id=eid, task_text=text, outcome="success",
                   final_answer="x",
                   traces=[Trace(step=1, thought="t", action="a", action_input="{}", observation="o")],
                   tokens_used=1)


def _corrupt(db, col, eid, vec):
    with sqlite3.connect(db) as c:
        c.execute(f"UPDATE episodes SET {col} = ? WHERE id = ?", (emb.serialize(vec), eid))
        c.commit()


def test_episode_recall_summary_no_nan_score(tmp_path):
    db = tmp_path / "e.db"
    em = EpisodicMemory(db)
    em.store(_ep("good", "procedura zorp di deploy buona"))
    em.store(_ep("bad", "procedura zorp di deploy guasta"))
    _corrupt(db, "summary_embedding", "bad", np.full(_DIM, np.nan, dtype=np.float32))
    res = EpisodicMemory(db).recall("procedura zorp deploy", k=5)
    scores = [s for _, s in res]
    assert all(np.isfinite(s) for s in scores), f"score non-finito nel recall episodi: {scores}"
    assert "good" in {e.id for e, _ in res}


def test_recall_by_context_no_nan_score(tmp_path):
    db = tmp_path / "e.db"
    em = EpisodicMemory(db)
    ctx = emb.encode("contesto cognitivo zorp deploy")
    em.store(_ep("good", "procedura zorp"), context_emb=ctx)
    em.store(_ep("bad", "procedura zorp due"), context_emb=ctx)
    _corrupt(db, "context_embedding", "bad", np.full(_DIM, np.nan, dtype=np.float32))
    res = EpisodicMemory(db).recall_by_context(ctx, k=5)
    scores = [s for _, s in res]
    assert all(np.isfinite(s) for s in scores), f"recall_by_context score non-finito: {scores}"
    assert "bad" not in {e.id for e, _ in res}
