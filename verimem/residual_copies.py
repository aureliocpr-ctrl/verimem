"""Where a deleted fact is STILL readable — the honest half of "forgotten".

Measured on a real machine (2026-08-05): the Auto-Dream worker copies
the whole ``semantic.db`` into ``dreams/auto-<ts>/`` about every 35 minutes
and keeps 3; MANUAL dream dirs (``dream_<ts>``) are never rotated — the one
from May 12 still holds 60 facts the live store no longer has. ``forget``
does its job on every live table (the entity graph included), so the data is
gone from the product — and still on disk, for hours in the rotating copies
and forever in the manual ones.

That is not a backup bug. It is the same class this codebase keeps paying
for: **the action succeeds, the effect is partial, and no surface says so.**
This module says so. It changes no behaviour — it reports.

Design notes:
- it CHECKS, it does not estimate: one primary-key lookup per copy is
  microseconds, and a guessed answer about deleted personal data is worse
  than no answer;
- it distinguishes rotating copies from permanent ones, because "for a
  couple of hours" and "forever" are different promises to a user;
- every failure degrades to "no copies reported" and NEVER raises into the
  deletion path: an observability layer must not be able to block a GDPR
  erasure.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

__all__ = ["residual_copies_for", "dreams_root_for", "forget_with_report"]


def forget_with_report(semantic, fact_id: str, *,
                       principal: str = "sdk") -> dict:
    """Cancella un fatto E dice dove resta leggibile. UNA definizione.

    Stava solo dentro ``Memory.forget_with_report``: quando ho aperto la
    porta MCP, il primo tentativo ne ha RISCRITTO il corpo nell'handler —
    cioè la prima delle tre classi di difetto che questo prodotto ripete
    (una copia invece della superficie unica), commessa mentre curavo la
    terza (una capacità raggiungibile da un canale solo). Ora il corpo sta
    qui e lo chiamano tutte le porte.

    Il referto non blocca MAI la cancellazione: se la scansione delle
    copie fallisce, l'elenco esce vuoto e l'atto avviene lo stesso.
    """
    try:
        copie = residual_copies_for(semantic.db_path, fact_id)
    except Exception:  # noqa: BLE001 — l'osservabilita' non blocca l'atto
        copie = []
    rimosso = bool(semantic.delete(fact_id, principal=principal,
                                   action="forget"))
    return {"removed": rimosso, "fact_id": fact_id,
            "residual_copies": copie}

#: Copies whose name starts with this are managed by the auto-worker's
#: retention (``_prune_old_dreams`` keeps the newest few). Anything else in
#: the dreams directory was created by hand and is never pruned.
_AUTO_PREFIX = "auto-"


def dreams_root_for(live_db: str | Path) -> Path:
    """The ``dreams/`` directory next to a live store.

    The live DB is ``<data_dir>/semantic/semantic.db``; the copies live in
    ``<data_dir>/dreams/<name>/semantic.db``.
    """
    p = Path(live_db).resolve()
    return p.parent.parent / "dreams"


def residual_copies_for(live_db: str | Path, fact_id: str,
                        *, limit: int = 50) -> list[dict[str, Any]]:
    """Copies that still contain ``fact_id``, newest first.

    Each entry: ``{name, path, kind, rotates, contains}`` where ``kind`` is
    ``"auto"`` (subject to retention) or ``"manual"`` (kept forever), and
    ``rotates`` is the same fact stated as the boolean a caller acts on.
    Only copies that ACTUALLY contain the row are returned — a warning that
    cries wolf gets ignored, which is how a real one gets missed.

    Never raises: an unreadable or locked copy is skipped.
    """
    out: list[dict[str, Any]] = []
    root = dreams_root_for(live_db)
    try:
        if not root.is_dir():
            return out
        dirs = sorted((d for d in root.iterdir() if d.is_dir()),
                      key=lambda d: d.name, reverse=True)[:limit]
    except OSError:
        return out
    for d in dirs:
        db = d / "semantic.db"
        try:
            if not db.is_file():
                continue
            # read-only URI: opening a copy must never create files nor
            # take a write lock on someone else's snapshot
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=1.0)
            try:
                row = con.execute(
                    "SELECT 1 FROM facts WHERE id = ? LIMIT 1",
                    (fact_id,)).fetchone()
            finally:
                con.close()
        except (sqlite3.Error, OSError):
            continue          # unreadable copy: skip, never raise
        if not row:
            continue
        is_auto = d.name.startswith(_AUTO_PREFIX)
        out.append({
            "name": d.name,
            "path": str(db),
            "kind": "auto" if is_auto else "manual",
            "rotates": is_auto,
            "contains": True,
        })
    return out
