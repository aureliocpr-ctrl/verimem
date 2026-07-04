"""Promozione Tier C -> corpus accettato (engram.transcript_promote).

Il ponte ESPLICITO e gated dal grezzo (Tier C, confidence~0) al fatto accettato
(semantic.db), con PROVENANCE che punta al turno verbatim. Invarianti:
  - il fatto promosso porta provenance 'transcript:<session>:<turn_id>';
  - default status = model_claim: il grezzo NON diventa verita verificata;
  - ANTI-LAUNDERING: tentare status='verified' senza ref file/commit -> il gate
    di SemanticMemory.store lo DEMOTA a model_claim (no laundering della chat);
  - la promozione NON cancella il turno dal Tier C (resta consultabile).

Hermetic: DB temporanei, zero ~/.engram.
"""
from __future__ import annotations

import sqlite3

import pytest

from engram.semantic import SemanticMemory
from engram.transcript_index import TranscriptIndex, Turn
from engram.transcript_promote import promote_turn_to_fact

_P2 = 'ghp_'


def test_promote_creates_model_claim_with_provenance(tmp_path):
    idx = TranscriptIndex(db_path=tmp_path / "t.db")
    idx.store(Turn(
        text="la decisione architetturale e5-base e stata presa il 3 giugno",
        session_id="S9", role="assistant", id="trn1",
    ))
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    fact = promote_turn_to_fact(idx, "trn1", sm, topic="conversational/promoted")

    assert fact.status == "model_claim", "default: claim, NON verita verificata"
    assert any("trn1" in s and "S9" in s for s in fact.source_episodes), \
        "provenance al turno verbatim mancante"
    # e' nel corpus accettato (query diretta, robusta ai filtri di recall)
    with sqlite3.connect(tmp_path / "s.db") as c:
        row = c.execute(
            "SELECT proposition, status FROM facts WHERE id = ?", (fact.id,)
        ).fetchone()
    assert row is not None and row[1] == "model_claim"
    assert "e5-base" in row[0]


def test_promote_cannot_launder_to_verified_without_evidence(tmp_path):
    idx = TranscriptIndex(db_path=tmp_path / "t.db")
    idx.store(Turn(text="frase grezza spacciata per verificata senza prove",
                   session_id="S", id="trn2"))
    sm = SemanticMemory(db_path=tmp_path / "s.db")  # repo_root=None -> verified demoted
    fact = promote_turn_to_fact(idx, "trn2", sm, status="verified")
    assert fact.status == "model_claim", \
        "il grezzo NON puo diventare 'verified' senza evidenza (anti-laundering)"


def test_promote_keeps_turn_in_tier_c(tmp_path):
    idx = TranscriptIndex(db_path=tmp_path / "t.db")
    idx.store(Turn(text="questo turno resta nel tier C dopo la promozione",
                   session_id="S", id="trn3"))
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    promote_turn_to_fact(idx, "trn3", sm)
    assert idx.get("trn3") is not None, "la promozione NON cancella il grezzo"


def test_promote_unknown_turn_raises(tmp_path):
    idx = TranscriptIndex(db_path=tmp_path / "t.db")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    with pytest.raises(ValueError):
        promote_turn_to_fact(idx, "does-not-exist", sm)


def test_promote_redacts_secret_in_proposition(tmp_path):
    """La promozione maschera i segreti PRIMA di immettere nel corpus accettato
    (no laundering di credenziali dal grezzo al corpus + banner)."""
    idx = TranscriptIndex(db_path=tmp_path / "t.db")
    idx.store(Turn(
        text="ho incollato per errore il token " + _P2 + "ABCDEFGHIJ1234567890abcdefXY nella chat",
        session_id="S", id="sek1",
    ))
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    fact = promote_turn_to_fact(idx, "sek1", sm)
    assert "" + _P2 + "ABCDEFGHIJ1234567890abcdefXY" not in fact.proposition
    assert "REDACTED" in fact.proposition
