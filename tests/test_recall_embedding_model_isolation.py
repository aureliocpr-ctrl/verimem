"""RED->GREEN (buco BLOCCANTE segnalato da Sorella C, 2026-06-03):
isolamento dello spazio di embedding per-modello nel recall.

CONTESTO. La tabella ``facts`` ha ``embedding BLOB`` e il recall pre-fix
filtrava SOLO per ``length(embedding) = 1536`` (384 dim x 4 byte float32).
Quel filtro blocca i blob malformati e i modelli di dimensione DIVERSA, ma
NON un modello DIVERSO della STESSA dimensione (es. un altro MiniLM, o lo
stesso modello ricaricato in una config diversa). Due vettori da modelli
diversi vivono in spazi non comparabili: il loro cosine e' rumore. Mischiarli
nel corpus live = ``silent cross-space poisoning`` (config.py:96-99 ammette il
gap; embedding.py:160-173 lo marca come lavoro futuro).

FIX (v9). Colonna per-riga ``embedding_model`` (stampata da store col modello
attivo) + filtro recall ``COALESCE(embedding_model, <legacy>) = <attivo>`` su
ENTRAMBI i path (cache fast-path E legacy SQL). NULL == riga legacy pre-v9 ==
modello storico all-MiniLM-L6-v2. Con default invariato (attivo == legacy) le
righe NULL e quelle stampate passano entrambe -> recall IDENTICO (invariante
di b145c2d preservata).

Hermetic: SemanticMemory su DB temporaneo. ZERO scrittura sul corpus live.
"""
from __future__ import annotations

import sqlite3
import time

import numpy as np

from verimem import embedding as emb
from verimem.semantic import Fact, SemanticMemory

# Colonne minime per un INSERT diretto che simula un vettore arrivato nel DB
# da un re-embed/daemon di un altro modello (il vero vettore di poisoning).
_COLS = (
    "id, proposition, topic, confidence, source_episodes, created_at, "
    "embedding, verified_by, status, writer_role, meta_narrative, "
    "last_verified_at, embedding_model"
)


def _raw_insert(db, *, fid, blob, model, now):
    with sqlite3.connect(db) as c:
        c.execute(
            f"INSERT INTO facts ({_COLS}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (fid, f"poison {fid}", "t", 0.9, "", now, blob, "[]",
             "model_claim", "agent_inference", 0, now, model),
        )
        c.commit()


def test_recall_excludes_foreign_embedding_model(tmp_path):
    """Un vettore STESSA-DIM (1536 byte) ma di un MODELLO diverso deve essere
    ESCLUSO dal recall anche a cosine 1.0. Pre-fix (solo filtro length) la riga
    foreign veniva restituita = poisoning silenzioso."""
    db = tmp_path / "s.db"
    sm = SemanticMemory(db_path=db)
    # fatto legittimo (stampato col modello attivo da store)
    sm.store(Fact(id="legit", proposition="il gatto dorme sul tappeto", topic="t"))

    q = "parola chiave unica xyzzy zork"
    qvec = emb.encode(q)            # stesso encoder -> stessa dim 384
    foreign_blob = emb.serialize(qvec)
    assert len(foreign_blob) == 384 * 4, "il blob foreign deve avere la STESSA dim (passa il filtro length)"
    # cosine col query = 1.0 -> sarebbe il top hit se non filtrato per modello
    _raw_insert(db, fid="foreign", blob=foreign_blob,
                model="sentence-transformers/all-MiniLM-FOREIGN-v2", now=time.time())

    cache_ids = {f.id for f, *_ in sm.recall(q, k=10)}                       # fast-path (cache)
    legacy_ids = {f.id for f, *_ in sm.recall(q, k=10, include_orphaned=True)}  # legacy SQL path
    assert "foreign" not in cache_ids, "cache path: vettore foreign-model NON deve passare il recall"
    assert "foreign" not in legacy_ids, "legacy path: vettore foreign-model NON deve passare il recall"


def test_legacy_null_rows_excluded_under_switched_default(tmp_path):
    """Post-flip 2026-06-04 (default multilingue != legacy MiniLM): una riga
    legacy (embedding_model NULL = MiniLM storico) ha un vettore di SPAZIO
    DIVERSO dal modello attivo -> ESCLUSA dal recall (anti cross-space poisoning).
    Per restare visibile va RE-EMBEDDATA (lo fa il flip per le eligible); sotto un
    modello attivo == MiniLM (env) tornerebbe visibile via COALESCE."""
    db = tmp_path / "s.db"
    sm = SemanticMemory(db_path=db)
    q = "frase di prova unica wibble quux"
    blob = emb.serialize(emb.encode(q))
    now = time.time()
    with sqlite3.connect(db) as c:
        # embedding_model esplicitamente NULL = riga pre-v9 (legacy MiniLM)
        c.execute(
            f"INSERT INTO facts ({_COLS}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,NULL)",
            ("legacy", "wibble baseline storico", "t", 0.9, "", now, blob,
             "[]", "model_claim", "agent_inference", 0, now),
        )
        c.commit()
    ids = {f.id for f, *_ in sm.recall(q, k=10)}
    assert "legacy" not in ids, "riga legacy NULL (MiniLM) ESCLUSA sotto modello attivo multilingue (anti cross-space)"


def test_store_stamps_active_embedding_model(tmp_path):
    """store() stampa la colonna embedding_model col modello attivo, cosi'
    il recall puo' isolare lo spazio dopo un futuro switch."""
    db = tmp_path / "s.db"
    sm = SemanticMemory(db_path=db)
    sm.store(Fact(id="x", proposition="ciao mondo", topic="t"))
    with sqlite3.connect(db) as c:
        row = c.execute("SELECT embedding_model FROM facts WHERE id='x'").fetchone()
    assert row[0] == emb.model_signature(), "store deve stampare il modello attivo per-riga"


def test_legacy_baseline_decoupled_from_active_default():
    """Post-flip 2026-06-04: _LEGACY (cosa SONO le righe NULL = MiniLM storico) e'
    DECOUPLED dal default ATTIVO (multilingue). Conflarli includerebbe i vettori
    legacy cross-spazio nel recall (poisoning). _LEGACY resta single-sourced da
    config (no literal duplicato) ma FROZEN a MiniLM != default attivo."""
    import os

    from verimem.config import _DEFAULT_EMBEDDING_MODEL
    from verimem.config import _LEGACY_EMBEDDING_MODEL as _CFG_LEGACY
    from verimem.semantic import _LEGACY_EMBEDDING_MODEL

    assert _LEGACY_EMBEDDING_MODEL == _CFG_LEGACY == "sentence-transformers/all-MiniLM-L6-v2", (
        "il baseline legacy deve essere single-sourced da config e FROZEN a MiniLM"
    )
    assert _LEGACY_EMBEDDING_MODEL != _DEFAULT_EMBEDDING_MODEL, (
        "legacy e default ATTIVO devono essere DECOUPLED dopo lo switch (anti cross-space)"
    )
    if not os.environ.get("HIPPO_EMBEDDING_MODEL"):
        assert emb.model_signature() == _DEFAULT_EMBEDDING_MODEL
