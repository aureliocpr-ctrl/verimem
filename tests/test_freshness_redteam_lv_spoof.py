"""REGRESSION-GUARD vettore #3 (validita temporale) — 2026-06-03.

Storia: questi test nacquero RED (sorella red-team) per documentare il buco
"future last_verified_at -> fact immortale" + "store si fida del caller senza
clamp". Il fix #3 di C ha CHIUSO il buco: ``_fact_is_stale`` tratta un
``last_verified_at`` nel futuro come STANTIO (fail-closed), quindi il fatto e'
escluso dal recall a prescindere dal timestamp fornito dal caller.

Invertiti (2026-06-03) ad asserire il comportamento CORRETTO post-fix:
sono ora regression-guard verdi.

Hermetic: SemanticMemory su DB tmp + lettura SQL diretta (niente embedding/
recall per non dipendere dal modello). Zero side-effect sul DB reale.
"""
from __future__ import annotations

import sqlite3
import time

from verimem.semantic import Fact, SemanticMemory, _fact_is_stale

_TEN_YEARS = 10 * 365 * 86400
_ANCIENT = 5000 * 86400  # ~13.7 anni


def test_fact_is_stale_future_lv_is_treated_stale():
    """Unit deterministico: un ``last_verified_at`` nel futuro e' trattato
    come STANTIO (fail-closed). Chiude l'immortalita da timestamp futuro."""
    now = 1_000_000_000.0
    ancient_created = now - _ANCIENT
    future_lv = now + _TEN_YEARS
    # Solo created_at antico (lv=None -> fallback created_at) -> stantio.
    assert _fact_is_stale(None, ancient_created, now) is True
    # last_verified_at nel futuro -> stantio (NON piu immortale).
    assert _fact_is_stale(future_lv, ancient_created, now) is True


def test_store_future_timestamp_results_stale_excluded(tmp_path):
    """store NON si fida di un timestamp futuro del caller: il fatto risulta
    stantio (fail-closed) e quindi escluso dal cutoff del recall."""
    m = SemanticMemory(db_path=tmp_path / "s.db")
    now = time.time()
    future = now + _TEN_YEARS
    f = Fact(
        id="immortal", proposition="auth module works in prod",
        topic="cap/auth", confidence=0.9, status="verified",
        created_at=now - _ANCIENT, last_verified_at=future,
    )
    m.store(f)

    conn = sqlite3.connect(str(m.db_path))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT last_verified_at, created_at FROM facts WHERE id='immortal'"
    ).fetchone()
    conn.close()
    stored_lv = row["last_verified_at"]

    # Comportamento corretto post-fix: il last_verified_at futuro e' trattato
    # come stantio dal recall -> il capability-claim NON e' immortale.
    assert _fact_is_stale(stored_lv, row["created_at"], now) is True, (
        "il fix #3 deve trattare il last_verified_at futuro come stantio "
        f"(fail-closed); stored_lv={stored_lv}, now={now:.0f}"
    )


def test_fresh_verified_fact_is_not_excluded(tmp_path):
    """P1 cutoff-per-eta (verde col fix): il cutoff colpisce per ETA, non per
    status. Un fact verified FRESCO non e' escluso; uno vecchio si (by design)."""
    now = time.time()
    # verified appena verificato -> non stale.
    assert _fact_is_stale(now - 10 * 86400, now - 200 * 86400, now) is False
    # verified vecchio (oltre 90gg dall'ultima verifica) -> stale (per design).
    assert _fact_is_stale(now - 200 * 86400, now - 400 * 86400, now) is True
