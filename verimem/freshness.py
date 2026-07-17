"""Temporal-validity / decay primitive (FASE 4 lab, buco #3 della falsificazione).

Un capability-claim `verified` oggi non scade mai (lo schema `facts` non ha
`last_verified_at`/`expires_at`) → caso A2A ("prima funzionava"). Questa
primitiva PURA calcola un fattore di decadimento half-life: il chiamante puo'
decidere quando un fatto va declassato a "da riverificare".

PURA e ISOLATA: non tocca schema/recall/gate (additiva, zero-rischio). Mattone
per FASE 4 (la calibrazione dei parametri half-life/floor per namespace e' una
decisione di design da informare con la ricerca).
"""
from __future__ import annotations


def decay_factor(age_days: float, half_life_days: float) -> float:
    """Fattore di freschezza in [0, 1] secondo decadimento half-life.

    1.0 = appena verificato. Scende del 50% ad ogni `half_life_days`.
    Guardie: ``half_life_days <= 0`` (decay disabilitato) o ``age_days <= 0``
    (appena verificato / futuro) → ritorna 1.0 (nessun decadimento spurio).
    """
    if half_life_days <= 0 or age_days <= 0:
        return 1.0
    return 0.5 ** (age_days / half_life_days)


def is_stale(age_days: float, half_life_days: float, floor: float = 0.5) -> bool:
    """True se la freschezza e' scesa sotto ``floor`` → il fatto va riverificato."""
    return decay_factor(age_days, half_life_days) < floor
