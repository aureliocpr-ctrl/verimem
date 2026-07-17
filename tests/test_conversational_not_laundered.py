"""Anti-laundering 2026-06-03 (falla trovata dall'audit indipendente 4-sorelle).

Una promozione conversational a BASSO trust (writer_role='conversational_promotion',
status=model_claim) NON deve affiorare nel recall di DEFAULT ne nel banner
SessionStart come se fosse conoscenza curata/verificata. Resta accessibile:
  - on-demand via ``recall(..., include_conversational=True)``;
  - via il Tier C pull-only (``hippo_transcript_recall``).
E se poi viene VERIFICATA con evidenza reale (status='verified'), torna knowledge
piena (l'esclusione vale SOLO per le non-verificate).

Hermetic: DB temporanei, zero ~/.verimem.
"""
from __future__ import annotations

import importlib.util
import sqlite3
import time
from pathlib import Path

from verimem import embedding as E
from verimem.semantic import Fact, SemanticMemory
from verimem.transcript_index import TranscriptIndex, Turn
from verimem.transcript_promote import promote_turn_to_fact

_HOOK = Path(__file__).resolve().parent.parent / "hooks" / "hippo_session_start.py"


def _load_hook():
    spec = importlib.util.spec_from_file_location("hippo_session_start_undertest", _HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_default_recall_excludes_unverified_conversational_promotion(tmp_path):
    idx = TranscriptIndex(db_path=tmp_path / "t.db")
    idx.store(Turn(text="il fatturato Q3 e' 1.2M secondo quanto detto in chat",
                   session_id="S", id="rev1"))
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="report trimestrale aziendale ufficiale", topic="biz"))
    promote_turn_to_fact(idx, "rev1", sm, topic="conversational/promoted")

    hits = sm.recall("fatturato Q3 1.2M", k=10)
    assert not any("1.2M" in f.proposition for f, *_ in hits), \
        "LAUNDERING: il claim conversational affiora nel recall di default"


def test_optin_recall_surfaces_conversational_promotion(tmp_path):
    idx = TranscriptIndex(db_path=tmp_path / "t.db")
    idx.store(Turn(text="il fatturato Q3 e' 1.2M secondo quanto detto in chat",
                   session_id="S", id="rev1"))
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    promote_turn_to_fact(idx, "rev1", sm, topic="conversational/promoted")

    hits = sm.recall("fatturato Q3 1.2M", k=10, include_conversational=True)
    assert any("1.2M" in f.proposition for f, *_ in hits), \
        "la promozione DEVE restare accessibile on-demand (opt-in)"


def test_recall_filter_is_surgical_normal_model_claim_still_recalled(tmp_path):
    """Il filtro tocca SOLO conversational_promotion, non tutti i model_claim."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="fatto normale model_claim sul recall semantico", topic="x"))
    hits = sm.recall("recall semantico model_claim normale", k=10)
    assert any("fatto normale" in f.proposition for f, *_ in hits), \
        "regressione: il filtro ha escluso un model_claim NON-conversational"


def test_verified_former_promotion_is_recallable(tmp_path):
    """Una promozione poi VERIFICATA con evidenza (status=verified) torna
    knowledge piena: l'esclusione vale solo per le non-verificate."""
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="anchor fact", topic="x"))
    vec = E.serialize(E.encode("il dato sul fatturato annuale verificato con bilancio depositato"))
    now = time.time()
    with sqlite3.connect(sm.db_path) as c:
        c.execute(
            "INSERT INTO facts (id, proposition, topic, confidence, source_episodes,"
            " created_at, embedding, status, writer_role, embedding_model,"
            " last_verified_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("vcp1", "il dato sul fatturato annuale verificato con bilancio depositato",
             "conversational/promoted", 0.9, "", now, vec, "verified",
             "conversational_promotion", E.model_signature(), now),
        )
    hits = sm.recall("fatturato annuale verificato bilancio", k=10)
    assert any(f.id == "vcp1" for f, *_ in hits), \
        "una promozione VERIFICATA non deve essere esclusa dal recall di default"


def test_banner_query_excludes_unverified_conversational_promotion(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    sm.store(Fact(proposition="fatto curato normale sul progetto", topic="proj"))
    idx = TranscriptIndex(db_path=tmp_path / "t.db")
    idx.store(Turn(text="dato sensibile detto in chat fatturato 9.9M", session_id="S", id="b1"))
    promote_turn_to_fact(idx, "b1", sm, topic="conversational/promoted")

    hook = _load_hook()
    rows = hook._safe_recent_facts(sm.db_path, limit=20)
    props = [p for p, _t in rows]
    assert any("fatto curato normale" in p for p in props), "il banner deve mostrare i fatti curati"
    assert not any("9.9M" in p for p in props), \
        "LAUNDERING: il banner mostra una promozione conversational a basso-trust"


def test_banner_query_tolerates_legacy_schema_without_writer_role(tmp_path):
    """DB grezzo senza colonna writer_role/status: il banner NON deve crashare
    (fallback non-filtrato; i DB legacy non hanno promozioni conversational)."""
    db = tmp_path / "legacy.db"
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE facts (proposition TEXT, topic TEXT, created_at REAL)")
        c.execute("INSERT INTO facts VALUES (?,?,?)", ("fatto legacy", "t", time.time()))
    hook = _load_hook()
    rows = hook._safe_recent_facts(db, limit=8)
    assert any("fatto legacy" in p for p, _t in rows), "fallback legacy rotto (banner crasha?)"
