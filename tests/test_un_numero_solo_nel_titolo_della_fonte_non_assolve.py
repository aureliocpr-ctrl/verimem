"""La fonte non assolve un valore che porta SOLO dentro il titolo di un file.

Questa cella è il FALSIFICATORE della strada scartata. Il rovescio di una cura
precedente — i nomi di file tolti anche dalla fonte, che così perdeva
un'evidenza — si poteva chiudere in due modi:

  (a) smettere di togliere i nomi di file dalla FONTE;
  (b) riconoscere che `00-ESAME` e `00-ESAME.md` sono lo stesso nome.

Le due strade sono indistinguibili sui casi del difetto, e (a) è una riga in
meno contro le trenta di (b). Questa cella è ciò che le separa: con (a) il
valore `400`, che la fonte porta solo dentro `400-piani.md`, viene PERDONATO —
la fonte assolve un numero che nessuno ha affermato lì. Con (b) resta accusato.

Misurato il 2026-09-22: sul corpus il caso ha raggio ZERO (nessuna delle 8874
coppie con fonte conservata ci cade). È scritto qui perché un raggio zero non è
una ragione per lasciare un buco: è la ragione per cui il buco non si vedrebbe.
"""
from __future__ import annotations

import pytest

from verimem.valore_non_nella_fonte import valori_non_nella_fonte

_CLAIM = "Il capannone misura 400 metri."
_FONTE_SOLO_NEL_TITOLO = "Vedi 400-piani.md per i dettagli."


def _accusati(claim: str, fonte: str) -> list[float]:
    return sorted(v.valore for v in valori_non_nella_fonte(claim, fonte))


def test_un_valore_che_la_fonte_porta_solo_nel_titolo_resta_accusato():
    """Il cuore della cella: qui (a) direbbe `[]` e sarebbe un falso perdono."""
    assert _accusati(_CLAIM, _FONTE_SOLO_NEL_TITOLO) == [400.0], (
        "la fonte porta 400 solo dentro un nome di file: non lo afferma, "
        "quindi non può assolverlo")


@pytest.mark.parametrize("claim,fonte,attesi", [
    # lo stesso nome nelle due grafie: il claim non viene accusato del numero
    # del documento che entrambi nominano
    ("Il registro 00-ESAME ha 215 celle.",
     "Il registro 00-ESAME.md ha 215 celle.", []),
    # e la direzione opposta, perché la normalizzazione è simmetrica
    ("Ho aperto 03-cose-spente.md e ho contato 7 voci.",
     "In 03-cose-spente ci sono 7 voci.", []),
])
def test_le_due_grafie_dello_stesso_nome_sono_lo_stesso_nome(claim, fonte, attesi):
    assert _accusati(claim, fonte) == attesi


def test_il_controllo_negativo_il_modulo_accusa_ancora():
    """Senza questa cella le due sopra diventerebbero verdi anche spegnendo il
    confronto, e nessuno se ne accorgerebbe."""
    assert _accusati("Il capannone misura 400 metri.",
                     "Il capannone misura 250 metri.") == [400.0]
