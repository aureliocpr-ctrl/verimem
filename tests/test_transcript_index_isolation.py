"""Tier C — conversational-raw transcript index (engram/transcript_index.py).

Terzo strato di memoria: un INDICE low-trust del transcript grezzo (cosa è
stato detto e come, verbatim), ISOLATO dal corpus accettato (semantic.db).

Invarianti che questi test bloccano (TDD-enforced):
  1. roundtrip: store + recall semantico funziona (pull-only API dedicata).
  2. ogni riga è stampata confidence=0.0 + source_type='conversational_raw'
     + embedding_model (lezione v9: evita poisoning same-dim).
  3. ISOLAMENTO: lo store di default è un DB SEPARATO da CONFIG.semantic_db, e
     un turn del Tier C non affiora MAI in SemanticMemory.recall (corpus
     accettato). È la rete portante anti-inquinamento.
  4. recall esclude righe con embedding_model estraneo (stessa-dim) — come v9.

Hermetic: DB temporaneo, zero scrittura su ~/.engram.
"""
from __future__ import annotations

import sqlite3

from engram import embedding as emb
from engram.semantic import Fact, SemanticMemory
from engram.transcript_index import TranscriptIndex, Turn, default_db_path


def test_store_and_recall_roundtrip(tmp_path):
    idx = TranscriptIndex(db_path=tmp_path / "t.db")
    idx.store(Turn(text="abbiamo deciso di usare e5-base per il recall", session_id="s1", role="assistant"))
    idx.store(Turn(text="il gatto dorme sul divano in salotto", session_id="s1", role="user"))
    out = idx.recall("quale modello di embedding abbiamo scelto", k=2)
    assert out, "recall deve ritornare hit"
    assert "e5-base" in out[0][0].text, "il turn più rilevante deve uscire primo"


def test_store_stamps_confidence_zero_source_type_and_model(tmp_path):
    db = tmp_path / "t.db"
    TranscriptIndex(db_path=db).store(Turn(text="ciao mondo conversazionale", session_id="s1"))
    with sqlite3.connect(db) as c:
        row = c.execute(
            "SELECT confidence, source_type, embedding_model FROM turns"
        ).fetchone()
    assert row[0] == 0.0, "confidence deve essere 0.0 (fonte debole)"
    assert row[1] == "conversational_raw", "source_type tag obbligatorio"
    assert row[2] == emb.model_signature(), "embedding_model va stampato (lezione v9)"


def test_default_db_is_separate_from_semantic():
    from engram.config import CONFIG
    p = default_db_path()
    assert p != CONFIG.semantic_db, "Tier C NON deve coincidere col corpus accettato"
    assert "conversational" in str(p).lower(), "store dedicato 'conversational'"


def test_isolation_tier_c_never_in_semantic_recall(tmp_path):
    marker = "procedura zorplax di deploy verbatim unica"
    idx = TranscriptIndex(db_path=tmp_path / "t.db")
    idx.store(Turn(text=marker, session_id="s1"))
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(id="f1", proposition="il cielo di solito appare blu", topic="t"))
    hits = sm.recall(marker, k=10)
    assert all(marker not in f.proposition for f, _ in hits), (
        "il verbatim del Tier C non deve MAI affiorare nel recall del corpus accettato"
    )
    tc = idx.recall(marker, k=5)
    assert tc and marker in tc[0][0].text, "ma è recuperabile via il pull-only dedicato"


def test_recall_excludes_foreign_embedding_model(tmp_path):
    db = tmp_path / "t.db"
    idx = TranscriptIndex(db_path=db)
    idx.store(Turn(text="frase conversazionale unica wibble quux", session_id="s1", id="foreign"))
    idx.store(Turn(text="frase conversazionale unica wibble quux", session_id="s1", id="active"))
    with sqlite3.connect(db) as c:
        c.execute("UPDATE turns SET embedding_model = ? WHERE id = ?",
                  ("sentence-transformers/all-MiniLM-FOREIGN-v2", "foreign"))
        c.commit()
    got = {t.id for t, _ in TranscriptIndex(db_path=db).recall("wibble quux", k=10)}
    assert "foreign" not in got, "turn con modello estraneo (stessa dim) deve essere ESCLUSO"
    assert "active" in got, "turn col modello attivo deve restare"


def test_recall_excludes_corrupt_length_embedding(tmp_path):
    """Difesa in profondità (parità con semantic.py): un embedding di lunghezza
    ERRATA (blob corrotto/troncato, classe incidente cycle-171 `embedding=b''`)
    NON deve far crashare recall() con ValueError 'inhomogeneous shape' — deve
    essere ESCLUSO dal filtro length(embedding)=expected_bytes, degradando con
    grazia. Lo stesso embedding_model attivo non basta a salvarlo: serve il
    length-guard SQL-side."""
    db = tmp_path / "t.db"
    idx = TranscriptIndex(db_path=db)
    idx.store(Turn(text="frase conversazionale normale e abbastanza lunga", session_id="S", id="good"))
    idx.store(Turn(text="altra frase conversazionale normale lunga", session_id="S", id="bad"))
    # corrompi l'embedding di 'bad' a lunghezza errata (model_signature resta valido)
    with sqlite3.connect(db) as c:
        c.execute("UPDATE turns SET embedding = ? WHERE id = 'bad'", (b"\x00\x00\x00\x00",))
        c.commit()
    got = {t.id for t, _ in TranscriptIndex(db_path=db).recall("frase normale", k=10)}
    assert "good" in got, "il turno con embedding valido deve restare"
    assert "bad" not in got, "embedding di lunghezza errata deve essere ESCLUSO (no crash)"


def test_recall_excludes_legacy_null_model_under_switched_default(tmp_path):
    """BUCO-2 / flip 2026-06-04 (4a superficie dopo facts/episodi/skill): una riga
    legacy con ``embedding_model`` NULL È storicamente MiniLM. Sotto un default
    ATTIVO diverso (multilingue, post-flip) NON deve affiorare: il suo vettore sta
    in uno spazio embedding diverso (stessa dim -> passa il length-guard, ma cosine
    non comparabile = poisoning silenzioso). Pre-fix ``_LEGACY_EMBEDDING_MODEL =
    _DEFAULT_EMBEDDING_MODEL`` (coupled) faceva COALESCE(NULL)->attivo -> INCLUSA a
    torto. Post-fix: ``_LEGACY`` frozen=MiniLM, DECOUPLED -> COALESCE(NULL)->MiniLM
    != attivo -> esclusa. (Allineato a semantic/memory/skill v9.)"""
    db = tmp_path / "t.db"
    idx = TranscriptIndex(db_path=db)
    idx.store(Turn(text="frase legacy unica wibble quux", session_id="s1", id="legacy"))
    idx.store(Turn(text="frase legacy unica wibble quux", session_id="s1", id="active"))
    # 'legacy' = riga pre-stamp: embedding_model NULL (= MiniLM storico via COALESCE)
    with sqlite3.connect(db) as c:
        c.execute("UPDATE turns SET embedding_model = NULL WHERE id = 'legacy'")
        c.commit()
    got = {t.id for t, _ in TranscriptIndex(db_path=db).recall("wibble quux", k=10)}
    assert "legacy" not in got, "turn legacy NULL (MiniLM) ESCLUSO sotto attivo multilingue (anti-poisoning)"
    assert "active" in got, "turn col modello attivo deve restare richiamabile"
