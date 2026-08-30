"""L'anteprima del gate deve nominare lo status che la scrittura produce.

`verimem trust` e' la PROVA: si chiede al gate cosa farebbe, prima di
scrivere davvero. Il 30/08 diceva::

    FLAGGED ↓ (would store as provisional)

e la scrittura produce ``quarantined`` — `client.py` e altri sei punti.
Nessuna riga assegna piu' ``provisional`` per questa via: e' il
comportamento del gate che e' cambiato (lo status esiste ancora, lo store
lo riserva alle ipotesi con riferimento URL/arxiv, e `semantic.py` lo
legge — precisazione di ws3, che mi ha corretto un «e' morto» troppo
ampio). ⇒ Un utente prova il gate, legge una parola, scrive, e ne trova
un'altra: il prodotto si contraddice fra la prova e la scrittura.

E la tabella portava una voce per ``quarantine``, che ``GateAction`` non
dichiara: una riga che non puo' essere selezionata — e che diceva la cosa
GIUSTA («excluded from recall») mentre quella viva diceva la sbagliata.
"""
from __future__ import annotations

from typing import get_args

import pytest

from verimem.anti_confab_gate import GateAction
from verimem.cli import _VERDETTI, _verdetto_del_gate


def test_il_declassamento_nomina_quarantined_e_non_provisional():
    v = _verdetto_del_gate("downgrade", judged=True).lower()
    assert "quarantined" in v, v
    assert "provisional" not in v, v


def test_ogni_verdetto_nominato_e_un_azione_che_il_gate_PRODUCE():
    """Il presidio: una voce per un'azione inesistente non si vede mai."""
    dichiarate = set(get_args(GateAction))
    assert set(_VERDETTI) <= dichiarate, set(_VERDETTI) - dichiarate


@pytest.mark.parametrize("azione", sorted(get_args(GateAction)))
def test_ogni_azione_del_gate_ha_una_riga_e_non_stampa_il_nome_nudo(azione):
    """Il verso opposto: nessuna delle tre deve cadere nel fallback."""
    v = _verdetto_del_gate(azione, judged=True)
    assert v != f"[white]{azione}[/white]", v
