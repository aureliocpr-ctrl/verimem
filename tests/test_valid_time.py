"""Valid-time bi-temporale (competitor-gap step 4, 2026-06-14).

``valid_until`` da' a ogni fatto un limite SUPERIORE di validita': oltre quell'
istante il fatto non e' piu' vero (es. "il deploy e' in corso", "l'incident
review e' aperta", "il flag X e' ON fino al rollout") e il recall lo esclude
con un hard-expire, a prescindere dall'eta/half-life (≠ last_verified_at, che
e' decadimento graduale). None == nessuna scadenza (default: recall identico).

Differenziatore vs Mem0/Zep, che fanno invalidation ma senza un valid-time
esplicito per-fatto. Additiva, nullable: zero regressione sui fatti esistenti.

Copre i DUE path di recall (entrambi devono escludere lo stesso insieme,
lezione SCAN-68 sulle asimmetrie cache-vs-legacy):
  * cache hot-path  -> maschera numpy vettoriale (view_vu > now)
  * legacy SQL path -> _fact_is_stale(valid_until=...) per-riga
"""
from __future__ import annotations

import sqlite3
import time

from verimem.semantic import Fact, SemanticMemory, _fact_is_stale, _migrate_v9_to_v10


def test_fact_is_stale_hard_expire_unit():
    """La logica condivisa dai due path per-riga: valid_until <= now => stantio,
    indipendente dall'eta. None / futuro => comportamento invariato."""
    now = 1_000_000.0
    # last_verified_at fresco (== now) in tutti i casi: isola il valid-time.
    assert _fact_is_stale(now, now, now, valid_until=now - 1) is True, \
        "valid_until nel passato -> stantio subito (hard-expire)"
    assert _fact_is_stale(now, now, now, valid_until=now) is True, \
        "valid_until == now -> gia' scaduto (<=)"
    assert _fact_is_stale(now, now, now, valid_until=now + 1000) is False, \
        "valid_until nel futuro -> ancora valido"
    assert _fact_is_stale(now, now, now, valid_until=None) is False, \
        "None -> nessuna scadenza -> comportamento pre-v10 invariato"


def test_valid_until_roundtrips_through_store(tmp_path):
    """valid_until sopravvive a store() -> _row() (persistenza della colonna)."""
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    vu = time.time() + 86400.0  # domani
    f = Fact(proposition="feature flag beta is ON until the rollout completes",
             topic="t", valid_until=vu)
    sm.store(f, embed="sync")
    got = sm.get(f.id)
    assert got is not None
    assert got.valid_until == vu, "valid_until deve roundtrippare store -> _row"


def test_valid_until_default_none_is_no_expiry(tmp_path):
    """Un Fact costruito senza valid_until ha None -> nessuna scadenza (default
    backward-compatible: i fatti esistenti non scadono)."""
    f = Fact(proposition="x", topic="t")
    assert f.valid_until is None


def test_migration_v9_to_v10_adds_column_idempotent(tmp_path):
    """La migrazione aggiunge valid_until ed e' idempotente (duplicate column
    ignorata) -> rieseguibile senza rompere un DB gia' migrato."""
    db = tmp_path / "m.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE facts (id TEXT, proposition TEXT, created_at REAL)")
    con.commit()
    _migrate_v9_to_v10(con)
    cols = {r[1] for r in con.execute("PRAGMA table_info(facts)")}
    assert "valid_until" in cols, "la migrazione deve aggiungere la colonna"
    _migrate_v9_to_v10(con)  # idempotente: non solleva
    con.close()


def test_recall_excludes_expired_cache_hotpath(tmp_path):
    """Cache hot-path (topic=None -> maschera numpy vettoriale): un fatto con
    valid_until nel passato e' fuori dal top-k; uno senza scadenza resta."""
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    now = time.time()
    expired = Fact(proposition="the alpha_x deployment is currently in progress",
                   topic="t/ops", valid_until=now - 3600.0)
    sm.store(expired, embed="sync")
    live = Fact(proposition="the alpha_x deployment finished and is stable now",
                topic="t/ops", valid_until=None)
    sm.store(live, embed="sync")

    ids = {f.id for f, _ in sm.recall("alpha_x deployment", k=5)}
    assert expired.id not in ids, \
        "hard-expire: un fatto con valid_until passato e' escluso dal recall"
    assert live.id in ids, "un fatto senza scadenza (None) resta recall-abile"


def test_recall_keeps_future_valid_until_cache_hotpath(tmp_path):
    """valid_until nel futuro -> ancora valido -> recall-abile (hot-path)."""
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    f = Fact(proposition="the zeta incident review is open for triage",
             topic="t/inc", valid_until=time.time() + 3600.0)
    sm.store(f, embed="sync")
    ids = {x.id for x, _ in sm.recall("zeta incident review", k=5)}
    assert f.id in ids, "valid_until nel futuro non deve escludere il fatto"


def test_recall_excludes_expired_legacy_path(tmp_path):
    """Legacy SQL path (topic!=None -> NON cache-eligible -> _fact_is_stale
    per-riga con valid_until): stesso esito del hot-path (no asimmetria)."""
    sm = SemanticMemory(db_path=tmp_path / "semantic" / "semantic.db")
    now = time.time()
    expired = Fact(proposition="batch job gamma is running right now",
                   topic="t/jobs", valid_until=now - 3600.0)
    sm.store(expired, embed="sync")
    live = Fact(proposition="batch job gamma cron schedule configuration",
                topic="t/jobs", valid_until=None)
    sm.store(live, embed="sync")

    # topic non-None -> legacy path (la cache fast-path richiede topic=None).
    ids = {f.id for f, _ in sm.recall("batch job gamma", topic="t/jobs", k=5)}
    assert expired.id not in ids, "legacy path: hard-expire deve escludere lo scaduto"
    assert live.id in ids, "legacy path: il fatto senza scadenza resta"
