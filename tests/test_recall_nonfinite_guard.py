"""recall robusto a embedding corrotti (NaN/inf): nessuno score non-finito,
la riga corrotta NON viene restituita (e non scavalca le buone).

``cosine_matrix(q, corpus) = corpus @ q`` assume righe L2-normalizzate; una riga
NaN/inf (corruzione DB o encode degenere) propaga NaN/inf nello score di recall.
Finora SOLO transcript_index aveva la guardia; il path facts (semantic.recall,
cache + legacy) no. Fix: escludere le righe non-finite dai risultati.

Hermetic: DB temp, gate-independent.
"""
from __future__ import annotations

import sqlite3

import numpy as np
import pytest

from engram import embedding as emb
from engram.semantic import Fact, SemanticMemory

_DIM = 384


@pytest.fixture(autouse=True)
def _gate_off(monkeypatch):
    monkeypatch.delenv("ENGRAM_ADMISSION_GATE", raising=False)


def _corrupt(db, fact_id: str, vec: np.ndarray) -> None:
    with sqlite3.connect(db) as c:
        c.execute("UPDATE facts SET embedding = ? WHERE id = ?",
                  (emb.serialize(vec), fact_id))
        c.commit()


def test_recall_cache_path_excludes_nan_embedding(tmp_path):
    db = tmp_path / "s.db"
    sm = SemanticMemory(db_path=db)
    sm.store(Fact(id="good", proposition="procedura zorp di deploy buona",
                  topic="t", source_episodes=["e"]))
    sm.store(Fact(id="bad", proposition="procedura zorp di deploy guasta",
                  topic="t", source_episodes=["e"]))
    _corrupt(db, "bad", np.full(_DIM, np.nan, dtype=np.float32))
    res = SemanticMemory(db_path=db).recall("procedura zorp deploy", k=5)
    scores = [s for _, s in res]
    assert scores, "recall non deve svuotarsi/crashare per una riga NaN"
    assert all(np.isfinite(s) for s in scores), f"score non-finito nel recall: {scores}"
    ids = {f.id for f, _ in res}
    assert "good" in ids, "il fatto buono deve restare richiamabile"
    assert "bad" not in ids, "la riga con embedding NaN non va restituita"


def test_recall_cache_path_excludes_inf_embedding(tmp_path):
    db = tmp_path / "s.db"
    sm = SemanticMemory(db_path=db)
    sm.store(Fact(id="good", proposition="alfa beta gamma delta", topic="t", source_episodes=["e"]))
    sm.store(Fact(id="bad", proposition="alfa beta gamma epsilon", topic="t", source_episodes=["e"]))
    _corrupt(db, "bad", np.full(_DIM, np.inf, dtype=np.float32))
    res = SemanticMemory(db_path=db).recall("alfa beta gamma", k=5)
    scores = [s for _, s in res]
    assert all(np.isfinite(s) for s in scores), f"score non-finito (inf): {scores}"
    assert "bad" not in {f.id for f, _ in res}


def test_recall_legacy_path_excludes_nan_embedding(tmp_path):
    # include_superseded=True forza il LEGACY SQL path (non la cache).
    db = tmp_path / "s.db"
    sm = SemanticMemory(db_path=db)
    sm.store(Fact(id="good", proposition="lezione importante sul recall robusto",
                  topic="lessons/x", source_episodes=["e"]))
    sm.store(Fact(id="bad", proposition="lezione importante sul recall guasto",
                  topic="lessons/x", source_episodes=["e"]))
    _corrupt(db, "bad", np.full(_DIM, np.nan, dtype=np.float32))
    res = SemanticMemory(db_path=db).recall(
        "lezione importante recall", k=5, include_superseded=True)
    scores = [s for _, s in res]
    assert all(np.isfinite(s) for s in scores), f"legacy path score non-finito: {scores}"
    assert "bad" not in {f.id for f, _ in res}
