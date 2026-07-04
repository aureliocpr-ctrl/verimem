"""TDD — auto-invalidate-on-contradiction (P0a memoria production-ready 2026-06-02).

Problema-radice (Aurelio: 'la memoria e quasi inutile se ci salviamo cose errate'):
quando un fatto NUOVO e piu affidabile contraddice un fatto VECCHIO, il vecchio
resta 'live' nel recall a inquinare. Il primitivo `supersede()` esiste gia ma
NESSUNO lo aggancia in automatico: il gate L3 riporta `contradicting_fact_ids`
e poi declassa solo il fatto NUOVO, senza toccare il vecchio.

Fix: `SemanticMemory.auto_supersede_on_contradiction(new_id, contradicting_ids)`
marca come superseded SOLO i vecchi con trust STRETTAMENTE inferiore al nuovo
(invalidate-not-delete: la riga resta in DB per lineage; sparisce dal recall di
default `WHERE superseded_by IS NULL`). Regola di sicurezza: un claim debole NON
puo invalidare uno piu affidabile.

HERMETIC: SemanticMemory su tmp_path, mai ~/.engram. Stub embedding via conftest
autouse. Statuses scelti (legacy_unverified=0 / model_claim=2) per NON innescare
l'hard-gate verified/provisional di store().
"""
from __future__ import annotations

from engram.semantic import Fact, SemanticMemory


def _mem(tmp_path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "semantic.db")


def _store(mem: SemanticMemory, *, fid: str, prop: str, topic: str, status: str) -> None:
    mem.store(Fact(id=fid, proposition=prop, topic=topic, status=status))


def test_auto_supersede_marks_lower_trust_contradicted(tmp_path):
    mem = _mem(tmp_path)
    _store(mem, fid="old1", prop="ai-eye pilota agy via WriteConsoleInputW",
           topic="lessons/tools/ai-eye", status="legacy_unverified")
    _store(mem, fid="new1", prop="ai-eye NON pilota agy (ConPTY): timeout verificato",
           topic="lessons/tools/ai-eye", status="model_claim")

    out = mem.auto_supersede_on_contradiction("new1", ["old1"])

    assert out["superseded"] == ["old1"]
    old = mem.get("old1")
    assert old is not None                 # riga preservata: invalidate, NON delete
    assert old.superseded_by == "new1"
    assert old.superseded_reason           # motivo non vuoto


def test_auto_supersede_skips_equal_or_higher_trust(tmp_path):
    mem = _mem(tmp_path)
    # vecchio FORTE (model_claim) + nuovo DEBOLE (legacy): NON invalidare il forte
    _store(mem, fid="strong", prop="X fa Y", topic="t", status="model_claim")
    _store(mem, fid="weak", prop="X non fa Y", topic="t", status="legacy_unverified")

    out = mem.auto_supersede_on_contradiction("weak", ["strong"])

    assert out["superseded"] == []
    assert "strong" in out["skipped"]
    assert mem.get("strong").superseded_by is None


def test_auto_supersede_handles_missing_and_self(tmp_path):
    mem = _mem(tmp_path)
    _store(mem, fid="n", prop="claim", topic="t", status="model_claim")

    out = mem.auto_supersede_on_contradiction("n", ["n", "ghost"])

    assert "n" not in out["superseded"]    # self-reference ignorato
    assert "ghost" in out["missing"]       # id inesistente classificato, no crash
