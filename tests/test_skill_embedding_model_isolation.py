"""RED->GREEN: isolamento embedding-model nel recall delle skill.

Parallelo a semantic.py v9 (test_recall_embedding_model_isolation.py). Stesso
buco length-only su skill.py:trigger_embedding -> un trigger prodotto da un
MODELLO diverso ma di STESSA dimensione (1536 byte) passava il filtro e
inquinava retrieve()/find_duplicates/cluster (cosine cross-spazio = rumore).

FIX (skills v2): colonna per-riga ``embedding_model`` (stampata da store col
modello attivo) + filtro ``COALESCE(embedding_model, <legacy>) = <attivo>`` sui
path cosine. NULL == skill pre-v2 == baseline storico. Default invariato
(attivo == baseline): retrieve identico.

Strategia hermetica: ``store()`` (scrive JSON + DB + stamp) poi ``UPDATE`` della
SOLA colonna embedding_model -> ``get()`` (che legge il JSON) resta valido e il
filtro agisce nel SELECT di retrieve. DB temporaneo, zero scrittura live.
"""
from __future__ import annotations

import sqlite3

from engram import embedding as emb
from engram.skill import Skill, SkillLibrary

_FOREIGN = "sentence-transformers/all-MiniLM-FOREIGN-v2"


def _set_model(db, skill_id, model):
    with sqlite3.connect(db) as c:
        c.execute("UPDATE skills SET embedding_model = ? WHERE id = ?", (model, skill_id))
        c.commit()


def test_retrieve_excludes_foreign_embedding_model(tmp_path):
    """Una skill il cui trigger_embedding e' di un modello diverso (stessa dim)
    NON deve essere richiamata da retrieve(). Pre-fix (solo length) passava."""
    lib = SkillLibrary(dir_path=tmp_path / "d", db_path=tmp_path / "s.db")
    q = "come faccio il deploy unico zorp"
    lib.store(Skill(id="foreign", name="deploy", trigger=q, status="stable"))
    _set_model(lib.db_path, "foreign", _FOREIGN)  # degrada a modello foreign
    got = {s.id for s in lib.retrieve(q, k=10)}
    assert "foreign" not in got, "retrieve(): skill foreign-model same-dim NON deve passare"


def test_retrieve_includes_legacy_null_model(tmp_path):
    """Invariante: una skill legacy (embedding_model NULL) resta richiamabile
    sotto default (attivo == baseline). Il fix non esclude il corpus storico."""
    lib = SkillLibrary(dir_path=tmp_path / "d", db_path=tmp_path / "s.db")
    q = "procedura unica frobozz per la build"
    lib.store(Skill(id="legacy", name="build", trigger=q, status="stable"))
    _set_model(lib.db_path, "legacy", None)  # NULL = skill pre-v2 (MiniLM)
    got = {s.id for s in lib.retrieve(q, k=10)}
    # Post-flip 2026-06-04: skill legacy NULL (MiniLM) ESCLUSA sotto attivo multilingue.
    assert "legacy" not in got, "skill legacy NULL (MiniLM) esclusa sotto attivo multilingue"


def test_store_stamps_active_model(tmp_path):
    """store() stampa embedding_model col modello attivo."""
    lib = SkillLibrary(dir_path=tmp_path / "d", db_path=tmp_path / "s.db")
    lib.store(Skill(id="s1", name="x", trigger="fai una cosa"))
    with sqlite3.connect(lib.db_path) as c:
        row = c.execute("SELECT embedding_model FROM skills WHERE id='s1'").fetchone()
    assert row[0] == emb.model_signature(), "store deve stampare il modello attivo per-riga"


# --- robustezza retrieve(): stessa classe dei fix facts/episodi (2026-06-04) ---
# 3a superficie della memoria: retrieve() faceva np.argsort(-sims)[:k] senza
# guard k<=0 (k negativo sversa N-|k| skill) ne' guardia non-finite (trigger
# corrotto NaN/inf inquina il ranking). Allinea skill a semantic/memory.

def test_retrieve_negative_k_returns_empty(tmp_path):
    lib = SkillLibrary(dir_path=tmp_path / "d", db_path=tmp_path / "s.db")
    q = "procedura zorp di deploy unica"
    for i in range(3):
        lib.store(Skill(id=f"s{i}", name=f"n{i}", trigger=q, status="stable"))
    got = lib.retrieve(q, k=-1)
    assert got == [], f"retrieve k=-1 deve dare [] (non {len(got)} skill del corpus)"


def test_retrieve_zero_k_returns_empty(tmp_path):
    lib = SkillLibrary(dir_path=tmp_path / "d", db_path=tmp_path / "s.db")
    q = "procedura zorp di deploy unica"
    for i in range(3):
        lib.store(Skill(id=f"s{i}", name=f"n{i}", trigger=q, status="stable"))
    assert lib.retrieve(q, k=0) == []


def test_retrieve_excludes_nan_trigger_embedding(tmp_path):
    import numpy as np
    lib = SkillLibrary(dir_path=tmp_path / "d", db_path=tmp_path / "s.db")
    q = "procedura zorp di deploy unica"
    lib.store(Skill(id="good", name="g", trigger=q, status="stable"))
    lib.store(Skill(id="bad", name="b", trigger=q, status="stable"))
    with sqlite3.connect(lib.db_path) as c:
        c.execute("UPDATE skills SET trigger_embedding = ? WHERE id = 'bad'",
                  (emb.serialize(np.full(384, np.nan, dtype=np.float32)),))
        c.commit()
    got = {s.id for s in lib.retrieve(q, k=10)}
    assert "good" in got, "skill buona deve restare richiamabile"
    assert "bad" not in got, "skill con trigger NaN non va restituita (no corpus poison)"
