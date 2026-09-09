"""Batch portable export of facts (semantic memory backup).

FORGIA pezzo #230 — Wave 29.
"""
from __future__ import annotations

from typing import Any

from .fact_contract import fact_payload

_SCHEMA_VERSION = 1


def export_all_facts(
    facts: list[Any],
    *,
    topic: str | None = None,
    n_in_store: int | None = None,
    cap: int | None = None,
) -> dict[str, Any]:
    """Return all facts as portable JSON dicts.

    Args:
      - `facts`: iterable of fact-likes.
      - `topic`: optional filter (exact match on `f.topic`).
      - `n_in_store`: quanti fatti esistono davvero nella popolazione da cui
        `facts` è stato preso (`SemanticMemory.count(topic=...)`). Serve a
        rendere LEGGIBILE un export parziale; `None` quando il chiamante non
        lo sa, e allora i campi che ne dipendono valgono `None` (la
        convenzione delle porte gemelle: `null` = «non dichiarato», mai un
        numero inventato).
      - `cap`: il tetto che il chiamante ha applicato leggendo lo store.

    Returns: `{schema_version, n_total, n_in_store, cap, capped, facts}`.

    ⚠️ `n_total` è, e resta, **il numero delle righe esportate** — non il
    totale del corpus. Il nome è infelice e cambiarlo romperebbe chi lo
    consuma; il totale vero sta in `n_in_store` (2026-09-09).

    📌 2026-09-09: questa funzione dichiara il taglio, non lo evita. Chi legge
    lo store deve passare il `topic` a `list_facts` — altrimenti il tetto cade
    PRIMA del filtro qui sotto e un topic vecchio esce vuoto.
    """
    rows: list[dict[str, Any]] = []
    for f in facts:
        if topic is not None and getattr(f, "topic", "") != topic:
            continue
        # 2026-07-30: un export che lascia indietro meta' del fatto e' una
        # perdita di dati silenziosa — chi migra il corpus si porta via le
        # proposizioni e non il verdetto del moat, il tier del giudice, chi
        # l'ha scritto, ne' se e' stato superato. Qui il fatto esce INTERO,
        # tramite il contratto unico (Fact.as_payload).
        rows.append(fact_payload(f))
    return {
        "schema_version": _SCHEMA_VERSION,
        "n_total": len(rows),
        "n_in_store": n_in_store,
        "cap": cap,
        "capped": (None if n_in_store is None or cap is None
                   else n_in_store > cap),
        "facts": rows,
    }


__all__ = ["export_all_facts"]
