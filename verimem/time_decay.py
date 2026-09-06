"""R7: Time-decay on facts confidence.

Memory should age. A CVE noted 6 months ago is likely patched. A
config decision from 2 years ago may have been superseded.

Exponential decay with parametrizable half-life (default 90 days).
After 1 half-life → confidence halved.
After 2 half-lives → quartered.
etc.

Levels:
  - fresh  : age < 0.5 * half-life
  - stale  : 0.5 * half-life <= age < 3 * half-life
  - expired: age >= 3 * half-life
"""
from __future__ import annotations

import time
from typing import Any

_DAY_SEC = 86400.0


def decay_confidence(
    fact: Any,
    *,
    now: float | None = None,
    half_life_days: float = 90.0,
) -> float:
    """Return decayed confidence based on age."""
    if now is None:
        now = time.time()
    created = float(getattr(fact, "created_at", now))
    age_days = max(0.0, (now - created) / _DAY_SEC)
    original = float(getattr(fact, "confidence", 0.0) or 0.0)
    # exp decay: c(t) = c0 * (0.5) ** (t / half-life)
    decay_factor = 0.5 ** (age_days / half_life_days) if half_life_days > 0 else 1.0
    return round(original * decay_factor, 4)


def assess_freshness(
    fact: Any,
    *,
    now: float | None = None,
    half_life_days: float = 90.0,
) -> dict[str, Any]:
    """Return {status, decayed_confidence, age_days, original_confidence}."""
    if now is None:
        now = time.time()
    created = float(getattr(fact, "created_at", now))
    age_days = max(0.0, (now - created) / _DAY_SEC)
    original = float(getattr(fact, "confidence", 0.0) or 0.0)
    decayed = decay_confidence(fact, now=now, half_life_days=half_life_days)

    # ⚠️ LA SCADENZA DECIDE PRIMA DELL'ETA', e per una ragione misurata: il recall
    # TOGLIE un fatto oltre `valid_until` («⚠ 1 fatto/i esclusi perche' SCADUTI»)
    # mentre questa funzione, che guardava solo l'eta', rispondeva `fresh` sullo
    # STESSO fatto nello STESSO istante. Due porte, due verdetti opposti:
    #
    #     fatto 103a30c7a651 · valid_until 1788571647.5 · adesso 1788659283.3
    #     recall            -> non lo serve, «esclusi perche' SCADUTI»
    #     assess_freshness  -> {'status': 'fresh', 'age_days': 0.0}
    #
    # `valid_until` non compariva mai in questo file (0 occorrenze; controllo
    # positivo: `created_at`/`confidence` 16), quindi non era una scelta
    # dichiarata da qualche parte: era una dimensione che non c'era.
    #
    # ⚖️ E `expired_reason` ESISTE perche' `expired` significava gia' un'altra
    # cosa — «piu' vecchio di 3 emivite» — e usare la stessa parola per due
    # grandezze e' il difetto che il resto del prodotto difende esplicitamente
    # («un solo segnale per due significati»). Lo status dice se il fatto vale;
    # il motivo dice perche', e resta leggibile chi era prima.
    _oltre_validita = False
    _vu = getattr(fact, "valid_until", None)
    if _vu is not None:
        try:
            _oltre_validita = float(_vu) <= now
        except (TypeError, ValueError):
            # Una scadenza illeggibile non cambia il verdetto e non fa cadere
            # niente: si comporta come un fatto senza scadenza. Stessa scelta di
            # `client.py` («una data illeggibile non fa cadere nulla»).
            _oltre_validita = False

    expired_reason: str | None = None
    if _oltre_validita:
        status = "expired"
        expired_reason = "valid_until"
    elif age_days < 0.5 * half_life_days:
        status = "fresh"
    elif age_days < 3 * half_life_days:
        status = "stale"
    else:
        status = "expired"
        expired_reason = "age"

    return {
        "status": status,
        "expired_reason": expired_reason,
        "decayed_confidence": decayed,
        "original_confidence": original,
        "age_days": round(age_days, 1),
        "half_life_days": half_life_days,
    }


def find_stale_facts(
    facts: list[Any],
    *,
    now: float | None = None,
    threshold_days: float = 90.0,
    top_k: int = 100,
) -> dict[str, Any]:
    """List facts older than threshold_days OR past their `valid_until`.

    ⚠️ La seconda meta' del criterio e' nuova, e la ragione e' la stessa di
    `assess_freshness`: chi fa manutenzione guarda questa lista, e un fatto
    scaduto IERI ma scritto OGGI non compariva da nessuna parte — ne' qui
    (troppo giovane) ne' fra i freschi (il recall lo toglie). Restava invisibile
    proprio a chi lo cercava.
    `reason` dice quale delle due cause ha acceso la riga: senza, la lista
    mescolerebbe «vecchio» e «oltre la sua validita'» in un solo segnale, che e'
    il difetto che il prodotto difende altrove.
    """
    if now is None:
        now = time.time()
    stale: list[dict[str, Any]] = []
    for f in facts:
        created = float(getattr(f, "created_at", now))
        age = (now - created) / _DAY_SEC
        _oltre_validita = False
        _vu = getattr(f, "valid_until", None)
        if _vu is not None:
            try:
                _oltre_validita = float(_vu) <= now
            except (TypeError, ValueError):
                _oltre_validita = False      # illeggibile: si comporta come assente
        if age >= threshold_days or _oltre_validita:
            stale.append({
                "id": getattr(f, "id", ""),
                "topic": getattr(f, "topic", ""),
                "proposition": getattr(f, "proposition", "")[:120],
                "age_days": round(age, 1),
                "reason": "valid_until" if _oltre_validita else "age",
                "original_confidence": float(getattr(f, "confidence", 0.0) or 0.0),
                "decayed_confidence": decay_confidence(
                    f, now=now, half_life_days=threshold_days,
                ),
            })
    stale.sort(key=lambda x: -x["age_days"])
    return {
        "stale_facts": stale[:top_k],
        "n_total_scanned": len(facts),
        "n_stale": len(stale),
        "threshold_days": threshold_days,
    }


__all__ = [
    "decay_confidence",
    "assess_freshness",
    "find_stale_facts",
]
