"""Backpressure on the review queue (P0 ciclo 2, punto 4).

The gate holds borderline writes "for review". Nothing counted them. A queue
nobody measures is a queue nobody drains, and "held for review" quietly turns
into "silently dropped" — the fact was neither admitted nor honestly refused,
which is the one outcome a memory sold on honest abstention cannot afford.

So the depth is measured and reported on the write that is ADDING to the
queue: the moment the operator is actually reading a receipt. Clean writes are
never annotated — pressure on a page that has nothing to do with it is noise,
and noise is how a signal gets ignored.

DECLARED LIMIT: there is no persisted per-fact quarantine reason (see
``Memory.restore_fact``, which says so about its own re-screen), so the depth
counts the WHOLE quarantined backlog rather than the L4-review class alone.
Measuring the real thing coarsely beats measuring a precise thing that does not
exist. A ``quarantine_reason`` column is the complete fix; it is not this
cycle, and pretending otherwise here would be the confabulation this file is
supposed to help prevent.

Cost: one COUNT per time window per store, not per write — a count on every
quarantining write is a tax that grows with the corpus, and one read per window
is enough to notice a backlog.
"""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Any

__all__ = ["DEFAULT_MAX", "depth", "pressure", "reset_cache", "threshold"]

#: Deliberately generous: this is a "nobody is draining this" alarm, not a
#: quota. A deployment that reviews in batches must not be nagged.
DEFAULT_MAX = 500

#: How long a depth reading stays good enough to reuse.
_TTL_S = 60.0

_cache: dict[str, tuple[float, int]] = {}


def reset_cache() -> None:
    """Drop memoised depths (tests, and any caller that just drained)."""
    _cache.clear()


def threshold() -> int:
    """``ENGRAM_REVIEW_QUEUE_MAX`` — 0 disables the signal deliberately.

    A malformed or negative value falls back to the default: a typo must not
    silently switch an alarm off. Only an explicit ``0`` does that.
    """
    raw = os.environ.get("ENGRAM_REVIEW_QUEUE_MAX", "").strip()
    if not raw:
        return DEFAULT_MAX
    try:
        val = int(raw)
    except ValueError:
        return DEFAULT_MAX
    if val == 0:
        return 0
    return val if val > 0 else DEFAULT_MAX


def _count(db_path: Path | str) -> int:
    """Quarantined, not superseded — a superseded row left the queue: a newer
    fact already answered it. Unreadable store → 0: never crash a write over a
    telemetry read, and never invent a number."""
    try:
        conn = sqlite3.connect(f"file:{Path(db_path)}?mode=ro", uri=True,
                               timeout=2.0)
    except sqlite3.Error:
        return 0
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE status = 'quarantined' "
            "AND superseded_by IS NULL").fetchone()
        return int(row[0]) if row else 0
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


#: Quanto indietro guarda il conteggio del FLUSSO. Sette giorni perche' e'
#: l'orizzonte in cui un operatore ricorda cosa ha scritto, non una soglia di
#: decisione: nessun allarme dipende da questo numero, che serve solo a
#: raccontare lo stock.
_GIORNI_RECENTI = 7.0


def recenti(db_path: Path | str, *, giorni: float = _GIORNI_RECENTI) -> int:
    """Quanti del backlog sono ENTRATI negli ultimi ``giorni``.

    Una profondita' non dice se la coda sta crescendo. Misurato sul corpus
    vivo il 2026-08-01: 528 quarantinati contro soglia 500 — l'allarme suona —
    ma 415 sono di maggio e 20 degli ultimi sette giorni. Un allarme sempre
    acceso e' un allarme spento: «il gate sta quarantinando adesso» e «c'e' un
    deposito che nessuno ha mai drenato» chiedono due azioni diverse.

    `created_at` E' UN EPOCH, e la trappola e' costata una misura sbagliata lo
    stesso giorno: scritto come per una data — ``created_at >= date('now',
    '-7 day')`` — il confronto e' fra un numero e una stringa e restituisce
    **0 sempre**, in silenzio. L'allarme direbbe «nessun arrivo recente» su
    qualunque corpus, che e' peggio del difetto che sta curando.

    Store illeggibile → 0, come `_count`: mai far cadere una scrittura per una
    lettura di telemetria, e mai inventare un numero.
    """
    da = time.time() - max(0.0, float(giorni)) * 86400.0
    try:
        conn = sqlite3.connect(f"file:{Path(db_path)}?mode=ro", uri=True,
                               timeout=2.0)
    except sqlite3.Error:
        return 0
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE status = 'quarantined' "
            "AND superseded_by IS NULL AND created_at >= ?", (da,)).fetchone()
        return int(row[0]) if row else 0
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


def depth(db_path: Path | str, *, max_age_s: float = 0.0) -> int:
    """Current queue depth. ``max_age_s > 0`` accepts a memoised reading that
    recent — the write path uses it; a caller that wants the truth right now
    passes nothing."""
    key = str(db_path)
    if max_age_s > 0:
        hit = _cache.get(key)
        if hit and (time.monotonic() - hit[0]) <= max_age_s:
            return hit[1]
    val = _count(db_path)
    _cache[key] = (time.monotonic(), val)
    return val


def note_enqueued(db_path: Path | str) -> None:
    """Count one write into the memoised depth.

    Without this the window works against the signal: a burst that fills the
    queue right after a reading would go unreported until the next COUNT — the
    exact moment an operator most needs to hear about it. Counting the rows we
    ourselves enqueue keeps the cached number honest between reads, at the cost
    of nothing. It can only UNDER-report (another process's writes are invisible
    until the window turns), which is the safe direction for an alarm.
    """
    key = str(db_path)
    hit = _cache.get(key)
    if hit is not None:
        _cache[key] = (hit[0], hit[1] + 1)


def pressure(db_path: Path | str, *, cached: bool = False) -> dict[str, Any]:
    """``{depth, threshold, over}``. ``over`` is False whenever the signal is
    disabled (threshold 0) or the store cannot be read."""
    limit = threshold()
    d = depth(db_path, max_age_s=_TTL_S if cached else 0.0)
    return {"depth": d, "threshold": limit, "over": bool(limit) and d >= limit}


def backpressure_warning(db_path: Path | str) -> dict[str, str] | None:
    """The receipt entry for a write that is adding to an over-full queue, or
    None. Never raises: a telemetry read must not break the write."""
    try:
        p = pressure(db_path, cached=True)
        note_enqueued(db_path)   # this write is IN the queue as of now
    except Exception:  # noqa: BLE001 — telemetry must never break a write
        return None
    if not p["over"]:
        return None
    # Quanto di quel numero e' ARRIVATO di recente: senza, «528 in coda» non
    # distingue un gate che sta quarantinando adesso da un deposito fermo da
    # mesi, e sono due azioni diverse. Il conteggio non decide niente — la
    # soglia continua a guardare lo stock — ma dice all'operatore quale delle
    # due cose sta leggendo. Illeggibile → si tace, non si inventa.
    try:
        n_recenti = recenti(db_path)
    except Exception:  # noqa: BLE001 — la telemetria non rompe una scrittura
        n_recenti = None
    quando = ("" if n_recenti is None else
              f", {n_recenti} of them in the last {int(_GIORNI_RECENTI)} days")
    return {
        "layer": "REVIEW_BACKPRESSURE",
        "reason": (f"{p['depth']} facts are waiting in the quarantine/review "
                   f"backlog (threshold {p['threshold']}){quando} — this "
                   f"write joins them"),
        "advice": ("drain the backlog (review and restore or forget) — a "
                   "queue nobody drains turns 'held for review' into "
                   "'silently dropped'; tune or disable with "
                   "ENGRAM_REVIEW_QUEUE_MAX (0 = off)"),
    }
