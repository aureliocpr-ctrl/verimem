"""Il pannello consigliava di testare 253 skill morte.

`skill_health` applica una policy a cascata e la parola `retired` non compariva
nel modulo. Una skill ritirata con zero trials cadeva nel primo ramo:

    if trials == 0:
        return ("test", "no trials yet — run the skill on real tasks…")

Sul corpus vivo sono **315 skill su 325** a essere retired, e il dashboard
consigliava «test» a 253 di loro. Un pannello di curatela in cui otto consigli
su dieci riguardano cose che nessuno eseguirà più non aiuta a decidere dove
guardare: è la superficie che serve esattamente a quello.

PRECISAZIONE MISURATA. La prima diagnosi diceva che la policy SCRIVE, via
`apply_recommendations` → `curate_pipeline`. Verificato leggendo la mappa:
`_ACTION_TO_STATUS` copre solo `promote` e `retire`, e `curate_pipeline`
passa `actions=["promote","retire"]` — «test» non tocca lo status di nessuno.
Il danno era il RUMORE, non una scrittura sbagliata, e vale la pena dirlo con
precisione perché le due cose si curano in modo diverso.

Trovato dall'altra istanza.
"""
from __future__ import annotations

import pytest

from verimem.recommend_actions import recommend_actions
from verimem.skill import Skill
from verimem.skill_health import skill_health


def _skill(**kw):
    base = {"id": "s1", "name": "una skill", "trigger": "t",
            "status": "candidate", "trials": 0, "successes": 0}
    base.update(kw)
    return Skill(**base)


def test_una_ritirata_non_riceve_test():
    h = skill_health(_skill(status="retired"))
    assert h["suggested_action"] != "test", h


def test_e_dice_che_e_ritirata():
    """Non basta non dire «test»: chi legge deve sapere PERCHÉ non c'è
    nulla da fare, altrimenti la riga sembra un errore del pannello."""
    h = skill_health(_skill(status="retired"))
    assert h["suggested_action"] == "retired", h
    assert "retired" in h["reasoning"].lower(), h["reasoning"]


def test_una_candidata_a_zero_trials_continua_a_volere_un_test():
    """Il ramo che c'era prima resta: è il caso per cui era stato scritto."""
    h = skill_health(_skill(status="candidate", trials=0))
    assert h["suggested_action"] == "test", h


@pytest.mark.parametrize("stato", ["candidate", "promoted"])
def test_gli_altri_stati_non_si_spostano(stato):
    h = skill_health(_skill(status=stato, trials=12, successes=11))
    assert h["suggested_action"] != "retired", h


def test_il_sommario_non_tace_la_voce_piu_numerosa():
    """`retired` deve comparire nel sommario: su questo corpus è la voce più
    grande, e un pannello che la omette racconta una libreria che non
    esiste."""
    skills = ([_skill(id=f"r{i}", status="retired") for i in range(40)]
              + [_skill(id=f"c{i}", status="candidate") for i in range(3)])
    rep = recommend_actions(skills, top_k_per_group=100)
    assert "retired: 40" in rep["summary"], rep["summary"]
    assert rep["n_by_action"].get("retired") == 40, rep["n_by_action"]
