"""NaN-guard del recall Tier C (verimem.transcript_index).

Un embedding di lunghezza CORRETTA (passa il length-guard) ma con valori
non-finiti (NaN/inf) NON deve crashare il recall ne inquinare il ranking con
score non-finiti: la riga sporca viene scartata, il recall degrada con grazia.
Classe-fratello dell'incidente cycle-171 (embedding=b'') ma piu' subdolo:
lunghezza giusta, contenuto corrotto.

Hermetic: DB temporaneo.
"""
from __future__ import annotations

import sqlite3

import numpy as np

from verimem import embedding as E
from verimem.transcript_index import TranscriptIndex, Turn


def test_recall_drops_nan_embedding_no_crash_no_pollution(tmp_path):
    idx = TranscriptIndex(db_path=tmp_path / "t.db")
    idx.store(Turn(text="un turno valido e pulito sul recall semantico", session_id="S", id="ok1"))

    # inietta una riga con embedding di lunghezza CORRETTA ma tutto NaN
    dim_bytes = E.expected_embedding_bytes()
    n_floats = dim_bytes // 4
    nan_vec = np.full(n_floats, np.nan, dtype=np.float32)
    blob = E.serialize(nan_vec)
    assert len(blob) == dim_bytes, "il blob NaN deve passare il length-guard (stessa dim)"
    with sqlite3.connect(idx.db_path) as c:
        c.execute(
            "INSERT INTO turns (id, session_id, ts, role, text, embedding,"
            " embedding_model, source_path, source_offset, confidence, source_type)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("nan1", "S", 0.0, "user", "riga corrotta con vettore NaN", blob,
             E.model_signature(), "", 0, 0.0, "conversational_raw"),
        )

    hits = idx.recall("recall semantico pulito", k=10)  # non deve sollevare
    ids = [t.id for t, _s in hits]
    assert "nan1" not in ids, "una riga con embedding NaN non deve entrare nel ranking"
    assert all(np.isfinite(s) for _t, s in hits), "score non-finiti nel risultato (pollution)"
    assert "ok1" in ids, "il turno valido deve restare recuperabile"
