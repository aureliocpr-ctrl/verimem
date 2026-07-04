"""TDD — mattone DECAY / temporal-validity (FASE 4, buco #3 della falsificazione).

Lo schema `facts` non ha `last_verified_at`/`expires_at`: un capability-claim
`verified` non scade mai (caso A2A "prima funzionava"). Questa primitiva PURA
calcola un fattore di decadimento half-life per decidere quando un fatto va
"riverificato". NON wirata (additiva, zero-rischio): mattone per FASE 4.
"""
from __future__ import annotations

from engram.freshness import decay_factor, is_stale


def test_fresh_fact_not_stale():
    assert decay_factor(age_days=0, half_life_days=30) == 1.0
    assert is_stale(age_days=0, half_life_days=30) is False


def test_half_life_point():
    # a un'emivita esatta il fattore e' 0.5
    assert abs(decay_factor(age_days=30, half_life_days=30) - 0.5) < 1e-9


def test_old_fact_is_stale():
    # 2 emivite -> 0.25 < floor 0.5 -> stale
    assert is_stale(age_days=60, half_life_days=30, floor=0.5) is True


def test_monotonic_decay():
    assert decay_factor(age_days=10, half_life_days=30) > decay_factor(age_days=20, half_life_days=30)


def test_guards_no_spurious_decay():
    # half_life invalido o eta' negativa -> nessun decadimento (factor 1.0), niente crash
    assert decay_factor(age_days=100, half_life_days=0) == 1.0
    assert decay_factor(age_days=-5, half_life_days=30) == 1.0
    assert is_stale(age_days=100, half_life_days=0) is False
