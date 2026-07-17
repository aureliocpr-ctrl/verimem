"""SkillLibrary.store must not persist a wrong-dim learned_embedding under the
active model_signature (save/recall hunt #4, 2026-06-14).

A skill JSON carries a persistent learned_embedding that survives a model flip.
store() reused it verbatim but stamped the ACTIVE model_signature(); after a
dim-changing flip the row's byte length no longer matched the active dim, and
retrieve()'s `length(trigger_embedding) = ?` filter silently dropped it forever.
Fix: reuse only when the dim matches the active model, else re-encode.
"""
from __future__ import annotations

import sqlite3

from verimem import embedding
from verimem.skill import Skill, SkillLibrary


def _emb_bytes(db, sid):
    con = sqlite3.connect(db)
    blob = con.execute(
        "SELECT trigger_embedding FROM skills WHERE id=?", (sid,)
    ).fetchone()[0]
    con.close()
    return len(blob)


def test_wrong_dim_learned_embedding_is_reencoded(tmp_path):
    db = tmp_path / "skills.db"
    lib = SkillLibrary(db_path=db)
    exp = embedding.expected_embedding_bytes()

    s = Skill(name="alpha skill", trigger="do the alpha thing")
    s.learned_embedding = [0.1] * 5  # WRONG dim (5 floats), e.g. a stale pre-flip vec
    lib.store(s)

    assert _emb_bytes(db, s.id) == exp, (
        "a wrong-dim learned_embedding must be re-encoded to the active dim, "
        "not stored at the stale length under the active model_signature"
    )


def test_correct_dim_learned_embedding_is_reused(tmp_path):
    db = tmp_path / "skills.db"
    lib = SkillLibrary(db_path=db)
    exp = embedding.expected_embedding_bytes()

    s = Skill(name="beta skill", trigger="do the beta thing")
    # a correctly-sized learned_embedding (active dim) must be accepted as-is
    s.learned_embedding = [0.0] * (exp // 4)
    lib.store(s)
    assert _emb_bytes(db, s.id) == exp
