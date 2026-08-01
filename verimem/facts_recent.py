"""Last N facts by created_at.

FORGIA pezzo #269 — Wave 68.
"""
from __future__ import annotations

from typing import Any

from .fact_contract import fact_payload


def facts_recent(
    facts: list[Any],
    *,
    top_k: int = 20,
) -> dict[str, Any]:
    """Return last N facts, newest-first."""
    sorted_facts = sorted(
        facts,
        key=lambda f: -float(getattr(f, "created_at", 0.0) or 0.0),
    )
    # 2026-07-30: il contratto unico (Fact.as_payload) con l'anteprima corta
    # che questa vista aveva gia'. Prima usciva la sola confidenza, che sul
    # corpus vivo e' ANTI-correlata con l'essere stati verificati: e' un
    # default per-canale che il moat non riscrive, quindi un fatto giudicato
    # 100 e uno mai guardato mostravano lo stesso 0.5.
    records = [
        {**fact_payload(f),
         "proposition": (getattr(f, "proposition", "") or "")[:160]}
        for f in sorted_facts[:top_k]
    ]
    return {"n_total": len(facts), "facts": records}


__all__ = ["facts_recent"]
