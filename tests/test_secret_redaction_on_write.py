"""P1 (audit 2026-06-07): secrets/credentials were stored verbatim on the
primary curated write paths (hippo_remember -> SemanticMemory.store, episodes
-> EpisodicMemory.store) and recalled back into context. redact_secrets was
wired ONLY on the transcript path. This wires it on every write: API keys /
tokens / private keys are masked before persistence. Conservative — high-
confidence secret patterns only, never generic PII. Default ON;
ENGRAM_REDACT_SECRETS=0 escape hatch.

Hermetic: tmp DB, embed='defer' (no model), monkeypatched env.
"""
from __future__ import annotations

import sqlite3

from engram.episode import Episode
from engram.memory import EpisodicMemory
from engram.semantic import Fact, SemanticMemory


def _prop(db, like):
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        r = c.execute(
            "SELECT proposition FROM facts WHERE proposition LIKE ?", (like,)
        ).fetchone()
        return r[0] if r else None
    finally:
        c.close()


def test_fact_secret_redacted_on_store(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_REDACT_SECRETS", raising=False)  # default ON
    db = tmp_path / "s.db"
    sm = SemanticMemory(db_path=db)
    sm.store(
        Fact(
            proposition="my anthropic key is sk-ant-abc123def456ghi789jkl012mno345",
            topic="sec", status="model_claim", source_episodes=["ep1"],
        ),
        embed="defer",
    )
    stored = _prop(db, "my anthropic key%")
    assert stored is not None
    assert "sk-ant-abc123" not in stored, "secret stored VERBATIM"
    assert "REDACTED" in stored


def test_clean_fact_not_redacted(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_REDACT_SECRETS", raising=False)
    db = tmp_path / "s.db"
    sm = SemanticMemory(db_path=db)
    sm.store(
        Fact(proposition="user prefers dark roast coffee", topic="prefs",
             status="model_claim", source_episodes=["ep1"]),
        embed="defer",
    )
    assert _prop(db, "user prefers%") == "user prefers dark roast coffee"


def test_episode_secret_redacted_on_store(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_REDACT_SECRETS", raising=False)
    monkeypatch.delenv("ENGRAM_INJECTION_SCREEN", raising=False)
    em = EpisodicMemory(db_path=tmp_path / "ep.db")
    ep = Episode(
        task_text="deploy the service", outcome="success",
        final_answer="the github token is ghp_abcdefghij0123456789abcdefghijABCDEF",
    )
    em.store(ep, embed="defer")
    got = em.get(ep.id)
    assert "ghp_abcdefghij" not in got.final_answer, "secret stored VERBATIM in episode"
    assert "REDACTED" in got.final_answer


def test_escape_hatch_disables_redaction(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_REDACT_SECRETS", "0")
    db = tmp_path / "s.db"
    sm = SemanticMemory(db_path=db)
    sm.store(
        Fact(proposition="key is sk-ant-zzz111yyy222www333vvv444uuu555",
             topic="sec", status="model_claim", source_episodes=["ep1"]),
        embed="defer",
    )
    assert "sk-ant-zzz111" in _prop(db, "key is%")  # redaction OFF -> verbatim
