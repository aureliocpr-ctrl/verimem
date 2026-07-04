"""TDD RED — buco #3 (validita temporale): recall NON deve ritornare un fatto
stantio (capability-claim scaduto per eta, SENZA successore che lo supersede).

Stato OGGI (2026-06-03, verificato leggendo engram/semantic.py):
  * `recall` rankizza per solo coseno: cache fast-path semantic.py:991-992,
    legacy path semantic.py:1052-1053. NESSUNA chiamata a freshness.is_stale.
  * `engram/freshness.py` (decay_factor:15, is_stale:27) e' PRONTO ma NON wired.
  * L'unica invalidazione esistente e' EVENT-based (superseded_by, set da
    supersede() semantic.py:1481 / auto_supersede_on_contradiction): copre solo
    il caso "rimpiazzato da un nuovo fatto", NON il caso "scaduto per eta".

Quindi un capability-claim vecchio (es. "X funziona", verificato 100 anni fa,
mai smentito) resta LIVE nel recall -> caso A2A "prima funzionava"
(freshness.py:3-5). Questo test lo dimostra e FALLISCE oggi.

Diventa GREEN quando is_stale viene wired in recall (design sorella C):
last_verified_at default=created_at + is_stale(now-last_verified_at, half_life)
come cutoff, su ENTRAMBI i path (cache ~991 + legacy ~1052; l'asimmetria
cache-vs-legacy e' la lezione SCAN-68 semantic.py:1023-1028).

HERMETIC: SemanticMemory su tmp_path, MAI il DB reale ~/.engram. Encode reale
(384-dim) come il resto della suite — niente mock dell'embedding.

NON edita semantic.py/freshness.py: il wiring lo fa la sorella A. Qui SOLO il
test che falsifica.
"""
from __future__ import annotations

import time

from engram.semantic import Fact, SemanticMemory

# Eta abbastanza estrema da rendere il fatto stantio per QUALSIASI half-life
# positivo ragionevole che A scegliera' (robusto al parametro ignoto).
_ONE_HUNDRED_YEARS_S = 100 * 365 * 24 * 3600

_TOPIC = "capability/test"  # fuori dalla telemetry-denylist (semantic.py:240).
_QUERY = "does capability X still work via the /foo endpoint"


def _seed(sm: SemanticMemory) -> tuple[str, str]:
    """Inserisce un fatto FRESCO (controllo) e uno STANTIO. Stessa topic e
    proposizione quasi identica: entrambi matchano la query, cosi' il test
    isola la FRESCHEZZA, non un miss di recall semantico."""
    now = time.time()
    fresh = Fact(
        id="fresh01",
        proposition="Capability X works: the /foo endpoint returns 200 OK.",
        topic=_TOPIC,
        created_at=now,  # appena verificato
    )
    stale = Fact(
        id="stale01",
        proposition="Capability X works: the /foo endpoint returns 200 OK.",
        topic=_TOPIC,
        created_at=now - _ONE_HUNDRED_YEARS_S,  # verificato 100 anni fa
    )
    sm.store(fresh)
    sm.store(stale)
    return fresh.id, stale.id


def test_recall_cache_path_excludes_stale_fact(tmp_path) -> None:
    """Cache fast-path (topic=None -> semantic.py:962-1000)."""
    sm = SemanticMemory(db_path=tmp_path / "sem.db")
    fresh_id, stale_id = _seed(sm)

    hits = sm.recall(_QUERY, k=5)  # topic=None -> cache path
    ids = [f.id for f, _sim in hits]

    # Guard anti falso-verde: il fatto fresco DEVE comparire (se sparisse tutto,
    # un assert sullo stantio passerebbe per il motivo sbagliato).
    assert fresh_id in ids, (
        f"setup rotto: il fatto fresco non e' nel recall (ids={ids})"
    )
    # CUORE: lo stantio NON deve essere ritornato. OGGI fallisce (recall non
    # chiama is_stale) -> RED. GREEN quando is_stale e' wired al cache path.
    assert stale_id not in ids, (
        f"buco #3: recall ha ritornato un fatto stantio (id={stale_id}, "
        f"verificato 100 anni fa, mai superseded). ids={ids}"
    )


def test_recall_legacy_path_excludes_stale_fact(tmp_path) -> None:
    """Legacy SQL path (topic esplicito -> semantic.py:1004-1054). Esercitato
    a parte per catturare l'asimmetria cache-vs-legacy (SCAN-68)."""
    sm = SemanticMemory(db_path=tmp_path / "sem.db")
    fresh_id, stale_id = _seed(sm)

    hits = sm.recall(_QUERY, k=5, topic=_TOPIC)  # topic set -> legacy path
    ids = [f.id for f, _sim in hits]

    assert fresh_id in ids, (
        f"setup rotto: il fatto fresco non e' nel recall legacy (ids={ids})"
    )
    assert stale_id not in ids, (
        f"buco #3 (legacy path): recall ha ritornato un fatto stantio "
        f"(id={stale_id}). ids={ids}"
    )
