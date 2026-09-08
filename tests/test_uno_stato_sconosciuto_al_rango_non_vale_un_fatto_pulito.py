"""Uno stato che la tabella dei ranghi non conosce NON deve valere quanto un
fatto pulito quando si decide se RITIRARE un fatto vecchio.

`anti_confab_gate._route_evolutions` decide le supersessioni confrontando i
ranghi, e legge il rango così (main 7b9e8ca1, righe 746, 791, 2257, 2406):

    _STATUS_RANK.get(status or "model_claim", 2)

Il default `2` è il rango di `model_claim`. Quindi un fatto il cui stato la
tabella non conosce viene trattato come un fatto pulito, e la condizione
`rango_vecchio <= rango_nuovo` lo rende RITIRABILE da una scrittura ordinaria.

Non è un rischio del futuro stato «review»: è attivo oggi. Misurato sullo store
di casa il 08/09 in sola lettura (banco ws3-quanti-fatti-hanno-uno-stato-che-il-
rango-non-conosce): **2.541 fatti vivi su 15.661 (16,2%)** hanno uno stato che
`_STATUS_RANK` non conosce — `user_manual` 2.494, `bootstrap_rule` 24,
`bootstrap_lesson` 14, `diary`, `lesson_manual`, `bench_manual`, `pending`.

Il prodotto sa già dire «non lo conosco»: `semantic._rango_di_fiducia` (dal
07/08) torna `None` invece di zero, e il suo docstring porta la stessa misura
di agosto (2.540 su 6.982). La usano `contradiction.py` e `doctor.py`. Il gate
no. Questa cella fissa la differenza PRIMA di aggiungere uno stato nuovo: se il
rango non sa rispondere, la supersessione non parte.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from verimem.anti_confab_gate import _route_evolutions
from verimem.semantic import _STATUS_RANK, _rango_di_fiducia

STATO_IGNOTO = "user_manual"  # 2.494 fatti vivi nello store di casa, 08/09


def test_CONTROLLO_il_rango_non_conosce_questo_stato_e_il_prodotto_lo_sa_dire():
    assert STATO_IGNOTO not in _STATUS_RANK
    assert _rango_di_fiducia(STATO_IGNOTO) is None, "il prodotto sa dire «non lo conosco»"
    assert _rango_di_fiducia("model_claim") == 2


def test_CONTROLLO_il_default_del_gate_lo_promuove_a_fatto_pulito():
    # è la riga che il gate usa quattro volte: il default vale model_claim
    assert _STATUS_RANK.get(STATO_IGNOTO, 2) == _STATUS_RANK["model_claim"]


class _Store:
    """Lo store minimo che `_route_evolutions` interroga: `get(id)` -> fatto."""

    def __init__(self, vecchio):
        self._vecchio = vecchio

    def get(self, _id):
        return self._vecchio


def _vecchio(status: str):
    return SimpleNamespace(
        id="vecchio", proposition="Il canone del capannone 12 è 5100 euro.",
        status=status, agent="ws3", verified_by=[], asserted_at=1.0,
        source_signature="firma", topic="prova/rango", valid_from=1.0,
    )


def _chiama(status_vecchio: str, status_nuovo: str = "model_claim") -> list[str]:
    """Ritorna la lista `supersede_ids` dopo la chiamata: se contiene «vecchio»,
    quel fatto viene RITIRATO dalla scrittura nuova."""
    agent = SimpleNamespace(semantic=_Store(_vecchio(status_vecchio)),
                            store=_Store(_vecchio(status_vecchio)))
    supersede_ids: list[str] = []
    _route_evolutions(agent, [], 2.0, ["vecchio"], supersede_ids,
                      new_status=status_nuovo, claimant="ws3",
                      proposition="Il canone del capannone 12 è 5900 euro.",
                      cand_ha_source=True)
    return supersede_ids


def test_CONTROLLO_il_confronto_dei_ranghi_e_VIVO_e_distingue():
    """Il controllo che rende leggibile il rosso: un fatto `verified` (rango 3,
    più forte del `model_claim` che scrive) NON viene ritirato — quindi la
    funzione arriva davvero al confronto dei ranghi, e un rosso lì sotto è del
    confronto, non di una chiamata che si ferma prima (sonda 08/09 19:41:
    verified → conflicts, tutti gli altri → supersede)."""
    assert _chiama("verified") == [], "un fatto più forte non si ritira"


def test_CONTROLLO_uno_stato_noto_e_piu_debole_resta_ritirabile():
    """`quarantined` (rango −1) sotto una scrittura `model_claim` (2): la
    supersessione È il comportamento voluto e la cura non deve toglierlo."""
    assert _chiama("quarantined") == ["vecchio"]


def test_ERA_ROSSO_uno_stato_ignoto_non_rende_il_vecchio_ritirabile():
    """Il rosso di questa cella, ora verde con `_rango_per_supersessione`.

    FALSIFICAZIONE, con la sonda `ws3-sonda-il-confronto-dei-ranghi-e-vivo.py`
    eseguita prima e dopo la cura (senza toccare l'albero condiviso)::

        19:41 (prima)  user_manual -> supersede_ids=['vecchio']  conflicts=[]
        20:08 (dopo)   user_manual -> supersede_ids=[]           conflicts=['vecchio']
        e nelle due esecuzioni  model_claim e quarantined restano ritirabili,
        verified no: la cura sposta SOLO la classe che doveva spostare.
    """
    assert "vecchio" not in _chiama(STATO_IGNOTO)


def test_uno_stato_ignoto_NON_si_comporta_piu_come_un_fatto_pulito():
    """La forma positiva del reperto: prima della cura i due erano identici
    (`['vecchio'] == ['vecchio']`), ora no. Se un domani tornassero uguali,
    questo test lo dice."""
    assert _chiama("model_claim") == ["vecchio"]
    assert _chiama(STATO_IGNOTO) != _chiama("model_claim")


def test_una_scrittura_SENZA_stato_resta_un_model_claim():
    """L'altro caso che il vecchio `.get(x, 2)` teneva insieme al primo, e che
    la cura deve conservare: chi scrive senza dichiarare uno stato è
    `model_claim`, e ritira un `model_claim` più vecchio come prima."""
    assert _chiama("model_claim", status_nuovo=None) == ["vecchio"]


def test_una_scrittura_con_stato_IGNOTO_non_ritira_nessuno():
    """Il lato speculare, che nessuno aveva guardato: se è la scrittura NUOVA a
    portare uno stato che la tabella non conosce, il confronto non si può fare
    e non si ritira niente."""
    assert _chiama("model_claim", status_nuovo=STATO_IGNOTO) == []
