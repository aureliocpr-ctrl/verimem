"""Isolamento embedding-model nel recall episodi (memory.py v6).

Terza superficie dopo facts (semantic v9) e skill (v2): stessa classe di buco
(filtro length-only su summary_embedding) -> un episodio prodotto da un modello
diverso ma stessa-dim inquinava il recall. Fix: colonna embedding_model per-riga
(migration v6) + filtro COALESCE su entrambi i path cosine (cache _ensure_recall_index
+ path SQL outcome-filtered).

Controllo isolante: due episodi con lo STESSO testo, uno stampato col modello
attivo e uno degradato a foreign -> se solo il foreign sparisce, la causa e' il
filtro per-modello (non la query / non altro). Hermetic, DB temporaneo.
"""
from __future__ import annotations

import sqlite3

from verimem import embedding as emb
from verimem.episode import Episode, Trace
from verimem.memory import EpisodicMemory


def _ep(eid: str, text: str) -> Episode:
    return Episode(
        id=eid, task_id=eid, task_text=text, outcome="success", final_answer="x",
        traces=[Trace(step=1, thought="t", action="a", action_input="{}", observation="o")],
        tokens_used=10,
    )


def test_recall_excludes_foreign_model_episode(tmp_path):
    db = tmp_path / "ep.db"
    mem = EpisodicMemory(db)
    mem.store(_ep("foreign", "procedura zorp di deploy unica"))
    mem.store(_ep("active", "procedura zorp di deploy unica"))  # STESSO testo
    # degrada SOLO 'foreign' a un modello diverso (stessa dim)
    with sqlite3.connect(db) as c:
        c.execute("UPDATE episodes SET embedding_model = ? WHERE id = ?",
                  ("sentence-transformers/all-MiniLM-FOREIGN-v2", "foreign"))
        c.commit()
    got = {e.id for e, _ in EpisodicMemory(db).recall("procedura zorp deploy", k=10)}
    assert "foreign" not in got, "episodio foreign-model (stessa dim) deve essere ESCLUSO"
    assert "active" in got, "episodio active-model con lo stesso testo deve RESTARE (isola la causa al modello)"


def test_recall_excludes_legacy_null_model_episode_under_switched_default(tmp_path):
    # Post-flip 2026-06-04: episodio legacy (embedding_model NULL = MiniLM storico)
    # ESCLUSO sotto modello attivo multilingue (vettore cross-spazio). Re-embed
    # (lo fa il flip) per tenerlo visibile.
    db = tmp_path / "ep.db"
    mem = EpisodicMemory(db)
    mem.store(_ep("legacy", "frase episodio unica wibble quux"))
    with sqlite3.connect(db) as c:
        c.execute("UPDATE episodes SET embedding_model = NULL WHERE id = 'legacy'")
        c.commit()
    got = {e.id for e, _ in EpisodicMemory(db).recall("episodio wibble quux", k=10)}
    assert "legacy" not in got, "episodio legacy NULL (MiniLM) ESCLUSO sotto attivo multilingue"


def test_store_stamps_active_model(tmp_path):
    db = tmp_path / "ep.db"
    mem = EpisodicMemory(db)
    mem.store(_ep("x", "ciao mondo episodio"))
    with sqlite3.connect(db) as c:
        row = c.execute("SELECT embedding_model FROM episodes WHERE id='x'").fetchone()
    assert row[0] == emb.model_signature()


def test_v6_migration_idempotent_on_existing_column(tmp_path):
    """La migration v6 deve essere IDEMPOTENTE come facts-v9/skills-v2: se
    `embedding_model` esiste già (DB fresco dal _SCHEMA corrente, o rollback
    del version-ledger senza drop colonna), ri-eseguirla NON deve crashare —
    deve inghiottire "duplicate column name". Regressione del bug dg_cabling
    (v6 era l'unica embedding_model-migration senza swallow)."""
    from verimem.memory import _migration_v6_embedding_model

    db = tmp_path / "ep.db"
    EpisodicMemory(db)  # crea lo schema corrente (embedding_model già presente)
    with sqlite3.connect(db) as c:
        _migration_v6_embedding_model(c)  # ri-esecuzione: NON deve sollevare
        cols = {r[1] for r in c.execute("PRAGMA table_info(episodes)")}
    assert "embedding_model" in cols


# --- dg/context recall paths: stessa classe di buco del summary (gap 2026-06-04) --
# La v6 isolava SOLO il path summary cosine (_ensure_recall_index + outcome-filtered
# summary). I path DG (_ensure_dg_index hot-path + recall dg outcome-filtered) e
# recall_by_context NON filtravano per embedding_model -> poisoning same-dim ancora
# possibile via quei due indici. Questi test pinnano la chiusura.

def test_recall_dg_excludes_foreign_model_episode(tmp_path):
    """Hot-path DG (use_dg=True, niente outcome_filter -> _ensure_dg_index)."""
    db = tmp_path / "ep.db"
    mem = EpisodicMemory(db)
    mem.store(_ep("foreign", "procedura zorp di deploy unica"))
    mem.store(_ep("active", "procedura zorp di deploy unica"))  # STESSO testo
    with sqlite3.connect(db) as c:
        c.execute("UPDATE episodes SET embedding_model = ? WHERE id = ?",
                  ("sentence-transformers/all-MiniLM-FOREIGN-v2", "foreign"))
        c.commit()
    got = {e.id for e, _ in EpisodicMemory(db).recall(
        "procedura zorp deploy", k=10, use_dg=True)}
    assert "foreign" not in got, "DG hot-path: episodio foreign-model (stessa dim) deve essere ESCLUSO"
    assert "active" in got, "DG hot-path: episodio active-model deve RESTARE (isola la causa al modello)"


def test_recall_dg_outcome_filtered_excludes_foreign_model_episode(tmp_path):
    """Path DG outcome-filtered (use_dg=True + outcome_filter -> query inline 1243)."""
    db = tmp_path / "ep.db"
    mem = EpisodicMemory(db)
    mem.store(_ep("foreign", "procedura zorp di deploy unica"))
    mem.store(_ep("active", "procedura zorp di deploy unica"))
    with sqlite3.connect(db) as c:
        c.execute("UPDATE episodes SET embedding_model = ? WHERE id = ?",
                  ("sentence-transformers/all-MiniLM-FOREIGN-v2", "foreign"))
        c.commit()
    got = {e.id for e, _ in EpisodicMemory(db).recall(
        "procedura zorp deploy", k=10, use_dg=True, outcome_filter="success")}
    assert "foreign" not in got, "DG outcome-filtered: foreign-model deve essere ESCLUSO"
    assert "active" in got


def test_recall_by_context_excludes_foreign_model_episode(tmp_path):
    """recall_by_context: ranking puro su context_embedding (query 1380)."""
    db = tmp_path / "ep.db"
    mem = EpisodicMemory(db)
    ctx = emb.encode("contesto cognitivo condiviso zorp deploy")
    mem.store(_ep("foreign", "procedura zorp"), context_emb=ctx)
    mem.store(_ep("active", "procedura zorp"), context_emb=ctx)
    with sqlite3.connect(db) as c:
        c.execute("UPDATE episodes SET embedding_model = ? WHERE id = ?",
                  ("sentence-transformers/all-MiniLM-FOREIGN-v2", "foreign"))
        c.commit()
    got = {e.id for e, _ in EpisodicMemory(db).recall_by_context(ctx, k=10)}
    assert "foreign" not in got, "context-path: episodio foreign-model deve essere ESCLUSO"
    assert "active" in got


def test_recall_dg_and_context_keep_legacy_null_model(tmp_path):
    """I legacy (embedding_model NULL) devono RESTARE richiamabili anche su dg/context
    (il COALESCE default li tiene dentro) — guard anti-regressione del fix."""
    db = tmp_path / "ep.db"
    mem = EpisodicMemory(db)
    ctx = emb.encode("contesto legacy wibble quux")
    mem.store(_ep("legacy", "frase episodio unica wibble quux"), context_emb=ctx)
    with sqlite3.connect(db) as c:
        c.execute("UPDATE episodes SET embedding_model = NULL WHERE id = 'legacy'")
        c.commit()
    m = EpisodicMemory(db)
    dg_got = {e.id for e, _ in m.recall("episodio wibble quux", k=10, use_dg=True)}
    ctx_got = {e.id for e, _ in m.recall_by_context(ctx, k=10)}
    # Post-flip: legacy NULL (MiniLM) ESCLUSO anche su dg/context sotto attivo multilingue.
    assert "legacy" not in dg_got, "DG: legacy NULL (MiniLM) escluso sotto attivo multilingue"
    assert "legacy" not in ctx_got, "context: legacy NULL (MiniLM) escluso sotto attivo multilingue"
