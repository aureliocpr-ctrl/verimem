"""TDD anti-spoof — buco #3b (stessa classe del buco #1 writer_role):
`last_verified_at` e' un campo che GOVERNA la freschezza e store() si fida del
valore del CALLER (semantic.py store: lv_at = fact.last_verified_at se settato).

EXPLOIT: un client salva un Fact con last_verified_at NEL FUTURO. Allora
`age_days = (now - last_verified_at) / 86400` e' NEGATIVO; freshness.decay_factor
(freshness.py:22) con `age_days <= 0` ritorna 1.0 -> is_stale sempre False ->
il fatto NON SCADE MAI -> il cutoff freshness (#3) e' aggirato.

Principio (verbatim Aurelio): un campo che governa freschezza/fiducia non deve
MAI fidarsi del valore del caller. Un timestamp di verifica nel FUTURO e'
impossibile -> e' un segnale di manomissione -> fail-closed = stale/escluso.

Questo test FALLISCE oggi (pre-fix): il fatto spoof con lv nel futuro viene
ritornato dal recall. Diventa GREEN col fail-closed su `base > now` in
_fact_is_stale (legacy path) + nella maschera numpy (cache path).

HERMETIC: SemanticMemory su tmp_path, MAI il DB reale.
"""
from __future__ import annotations

import time

from engram.semantic import Fact, SemanticMemory

_TEN_YEARS_S = 10 * 365 * 24 * 3600
_TOPIC = "capability/test"  # fuori dalla telemetry-denylist.
_QUERY = "does capability X still work via the /foo endpoint"


def _seed(sm: SemanticMemory) -> tuple[str, str]:
    now = time.time()
    fresh = Fact(
        id="fresh01",
        proposition="Capability X works: the /foo endpoint returns 200 OK.",
        topic=_TOPIC,
        created_at=now,
    )
    # SPOOF: il caller mette last_verified_at nel FUTURO per restare "fresco
    # per sempre" e bypassare il decadimento temporale del buco #3.
    spoof = Fact(
        id="spoof01",
        proposition="Capability X works: the /foo endpoint returns 200 OK.",
        topic=_TOPIC,
        created_at=now,
        last_verified_at=now + _TEN_YEARS_S,
    )
    sm.store(fresh)
    sm.store(spoof)
    return fresh.id, spoof.id


def test_cache_path_rejects_future_last_verified_at(tmp_path) -> None:
    """Cache fast-path (topic=None)."""
    sm = SemanticMemory(db_path=tmp_path / "sem.db")
    fresh_id, spoof_id = _seed(sm)

    ids = [f.id for f, _sim in sm.recall(_QUERY, k=5)]

    assert fresh_id in ids, f"setup rotto: fresco assente (ids={ids})"
    assert spoof_id not in ids, (
        f"spoof #3b: recall ha ritornato un fatto con last_verified_at nel "
        f"futuro (id={spoof_id}) -> freschezza falsificata dal caller. ids={ids}"
    )


def test_legacy_path_rejects_future_last_verified_at(tmp_path) -> None:
    """Legacy SQL path (topic esplicito)."""
    sm = SemanticMemory(db_path=tmp_path / "sem.db")
    fresh_id, spoof_id = _seed(sm)

    ids = [f.id for f, _sim in sm.recall(_QUERY, k=5, topic=_TOPIC)]

    assert fresh_id in ids, f"setup rotto: fresco assente legacy (ids={ids})"
    assert spoof_id not in ids, (
        f"spoof #3b (legacy path): recall ha ritornato un fatto con "
        f"last_verified_at nel futuro (id={spoof_id}). ids={ids}"
    )
