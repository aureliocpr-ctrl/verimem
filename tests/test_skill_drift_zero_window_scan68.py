"""TDD — skill_drift: una finestra a 0 usi NON e' un drift (scan 68-Opus P2).
Bug: il guard `h_uses + r_uses < min_uses` usa la SOMMA -> uno skill con storia
ma 0 usi recenti (o viceversa) passa, e il rate della finestra vuota viene
fabbricato a 0.0 -> drift |0.0 - hist| spesso >= soglia -> falso 'degrading'
(o 'improving' per uno skill nuovo). Un 0/0 NON e' un success_rate dello 0%."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from engram.skill_drift import detect_skill_drift


@dataclass
class _Ep:
    id: str
    outcome: str
    skills_used: list = field(default_factory=list)
    created_at: float = 0.0


def test_skill_unused_recently_is_not_degrading():
    now = time.time()
    eps = [_Ep(f"h{i}", "success", ["dormant"], created_at=now - 86400 * 60)
           for i in range(10)]  # 10 storici, 0 recenti
    out = detect_skill_drift(eps, now=now, recent_window_days=14,
                             history_window_days=120, min_uses=3)
    assert "dormant" not in [d["skill_id"] for d in out["drifts"]], (
        "skill con 0 usi nella finestra recente non e' 'degrading', e' non-usato")


def test_new_skill_no_history_is_not_drift():
    now = time.time()
    eps = [_Ep(f"r{i}", "success", ["fresh"], created_at=now - 86400 * 3)
           for i in range(10)]  # 10 recenti, 0 storici
    out = detect_skill_drift(eps, now=now, recent_window_days=14,
                             history_window_days=120, min_uses=3)
    assert "fresh" not in [d["skill_id"] for d in out["drifts"]], (
        "skill nuovo senza baseline storico non ha un drift misurabile")
