"""I soli documenti non fanno partire la matrice della ci (2026-09-08).

Aurelio, 08/09: «se fate 190 commit in un giorno potete mai lanciare 190 ci?».
Misurato quel giorno: 190 commit su main dalla 0.7.6 in quattro giorni, e il
candidato 7b9e8ca1 (due file .md) ha comprato 9 job e ~55 minuti di matrice
per una riga di README. Il presidio tiene ferma la regola: un push che tocca
SOLO .md o docs/ non fa partire la matrice; il verdetto sul candidato si
CHIEDE con workflow_dispatch sull'ultimo sha (quel run porta anche i presidi
del README e costruisce il wheel per lo smoke).

RED falsificato il 08/09 con la modifica stashata (ci.yml di main senza
paths-ignore): 1 failed; GREEN con la modifica: 2 passed.
"""
from __future__ import annotations

from pathlib import Path

import yaml

_CI = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"


def _push_trigger() -> dict:
    doc = yaml.safe_load(_CI.read_text(encoding="utf-8"))
    on = doc.get("on", doc.get(True))
    assert isinstance(on, dict) and "push" in on, "ci.yml: il trigger push manca"
    return on["push"]


def test_un_push_di_soli_documenti_non_fa_partire_la_matrice():
    ignorati = set(_push_trigger().get("paths-ignore") or [])
    for atteso in ("docs/**", "**/*.md"):
        assert atteso in ignorati, (
            f"ci.yml: push senza paths-ignore per {atteso!r}: un push di soli "
            "documenti fa partire 9 job e ~55 min di matrice per una riga di README"
        )


def test_il_verdetto_si_puo_ancora_chiedere_sull_ultimo_sha():
    doc = yaml.safe_load(_CI.read_text(encoding="utf-8"))
    on = doc.get("on", doc.get(True))
    assert "workflow_dispatch" in on, (
        "ci.yml: senza workflow_dispatch un candidato di soli documenti non "
        "avrebbe MAI un run completo, e il cancello del publish non leggerebbe niente"
    )
