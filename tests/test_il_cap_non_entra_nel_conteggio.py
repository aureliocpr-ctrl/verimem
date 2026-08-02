"""Il dashboard diceva «test: 50» perché 50 era il limite, non il numero.

`recommend_actions` raggruppa le skill per azione consigliata, ordina ogni
gruppo e lo TRONCA a `top_k_per_group`. Il sommario contava la lista già
tagliata:

    groups[action_name] = items[:top_k_per_group]   # taglia
    n = len(groups.get(action_name, []))            # conta il tagliato

Con il default 50 il dashboard diceva «test: 50» dove le skill che vogliono un
test erano **254**. E lo schema MCP cappa `top_k_per_group` a **200**, quindi
da quel canale il numero vero non era nemmeno RAGGIUNGIBILE: misurato 50→50,
200→200, 10000→254.

Un conteggio che coincide sempre col limite è un conteggio che non conta
niente. Il cap serve a limitare l'ELENCO mostrato, non a cambiare il totale
dichiarato.

Trovato dall'altra istanza.
"""
from __future__ import annotations

import pytest

from verimem.recommend_actions import recommend_actions


def _skill(n: int):
    """Molte più skill del limite, tutte nello stesso stato: così il gruppo è
    grande e il taglio si vede."""
    from verimem.skill import Skill
    return [Skill(id=f"s{i:04d}", name=f"skill {i}", trigger="t",
                  status="candidate") for i in range(n)]


@pytest.fixture()
def libreria():
    return _skill(120)


def test_il_sommario_dice_il_totale_non_il_limite(libreria):
    """Il test che FALSIFICA: guarda il SOMMARIO, non `n_by_action`.

    La prima stesura controllava solo il campo nuovo, che è popolato prima del
    taglio in entrambe le versioni del codice: passava anche rimettendo la
    riga difettosa, cioè non provava niente. Il difetto viveva nella FRASE, e
    lì va cercato.
    """
    rep = recommend_actions(libreria, top_k_per_group=10)
    assert sum(rep["n_by_action"].values()) == 120, rep["n_by_action"]
    for azione, quante in rep["n_by_action"].items():
        if quante > 10:
            assert f"{azione}: {quante}" in rep["summary"], (
                f"il sommario dice il limite invece del totale "
                f"({azione} sono {quante}): {rep['summary']}")
            assert "(showing 10)" in rep["summary"], rep["summary"]


def test_il_totale_non_dipende_dal_limite(libreria):
    """Il criterio: cambiare il cap cambia quante se ne VEDONO, non quante ce
    ne SONO. È il difetto in una riga."""
    a = recommend_actions(libreria, top_k_per_group=5)
    b = recommend_actions(libreria, top_k_per_group=50)
    assert a["n_by_action"] == b["n_by_action"], (
        f"il totale cambia col limite: {a['n_by_action']} vs {b['n_by_action']}")


def test_l_elenco_invece_dipende_dal_limite(libreria):
    """Controprova: se non cambiasse, il cap non starebbe tagliando nulla e i
    test sopra passerebbero senza dire niente."""
    a = recommend_actions(libreria, top_k_per_group=5)
    b = recommend_actions(libreria, top_k_per_group=50)
    la = sum(len(v) for v in a["actions"].values())
    lb = sum(len(v) for v in b["actions"].values())
    assert la < lb, f"il cap non taglia: {la} vs {lb}"


def test_quando_non_taglia_il_sommario_non_lo_dice(libreria):
    """Nessun «(showing N)» dove non c'è stato taglio: un'annotazione che
    compare sempre smette di segnalare qualcosa."""
    rep = recommend_actions(_skill(3), top_k_per_group=50)
    assert "showing" not in rep["summary"], rep["summary"]
