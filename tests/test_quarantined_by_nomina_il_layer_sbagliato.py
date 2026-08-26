"""`quarantined_by` nomina il PRIMO layer che parla, non quello che ha deciso.

Misurato il 2026-08-26 alle 21:40, `ee5a439f`, fuori da pytest, store isolato.

Un fatto trattenuto con due layer sulla ricevuta:

    quarantined  g=43.59
      quarantined_by = 'L3-coexistence'
      layer che hanno parlato = ['L3-coexistence', 'L4-review']

`L3-coexistence` dichiara nel proprio messaggio di NON trattenere:

    «a contradiction was found but both facts are kept … both stay servable and
     recall returns them together»

A trattenere e' `L4-review`: «borderline grounding (44) in the CE review band
[40, 80) — held for review, **not admitted**».

Il controllo che isola la causa: una coppia dove parla un solo gruppo di layer
riceve l'etichetta giusta —

    quarantined  g=1.87   quarantined_by='moat'   layer=['L4-negazione','L4-grounding']  ok

⇒ Il difetto compare quando piu' layer parlano: l'etichetta prende il primo.

PERCHE' CONTA, e non e' cosmesi: chi indaga un rifiuto legge `quarantined_by`,
va a leggere il messaggio di quel layer, e trova scritto che il fatto **resta
servibile** — l'opposto di cio' che e' successo. La diagnosi diventa impossibile,
o peggio si conclude che il fatto e' servito quando non lo e'.

Si aggancia a due cose gia' in casa: l'aperto «il perche' di un rifiuto non e'
persistito» (`quarantined_by` popolato nel 3,8% dei casi) — non e' solo poco
popolato, quando c'e' puo' nominare il layer sbagliato — e la riga del 20/08
«un'etichetta FALSA e' peggio di una mancante».
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from verimem.client import Memory

FONTE = "    2 passed     NO\n    1 xfailed    NO\n    2 test       NO\n    passati      NO"
PRIMO = "Nella source troncata 2 passed non compare."
SECONDO = "Nella source troncata 1 xfailed non compare."


def _coppia() -> dict:
    """Scrive le due proposizioni in sequenza e restituisce la ricevuta della seconda."""
    mem = Memory(str(Path(tempfile.mkdtemp()) / "qb.db"))
    mem.add(PRIMO, topic="t/qb", source=FONTE, validate="full")
    return mem.add(SECONDO, topic="t/qb", source=FONTE, validate="full")


def test_CONTROLLO_la_seconda_scrittura_e_trattenuta_da_piu_di_un_layer():
    """Il righello. Se non e' trattenuta, o parla un layer solo, il test sotto
    non misura il difetto: lo dice fallendo, non saltando."""
    ric = _coppia()
    layer = [str(w.get("layer")) for w in (ric.get("warnings") or [])]
    assert str(ric.get("status")) == "quarantined", (
        f"non e' trattenuta ({ric.get('status')}, g={ric.get('grounding_score')}): "
        "il banco non riproduce piu' il caso, rimisurare"
    )
    assert len(layer) >= 2, f"parla un layer solo ({layer}): il difetto non si presenta"


@pytest.mark.xfail(
    strict=True,
    reason="quarantined_by prende il PRIMO layer che parla invece del decisore: "
    "nomina L3-coexistence, che dichiara «both stay servable», mentre a "
    "trattenere e' L4-review (26/08)",
)
def test_quarantined_by_dovrebbe_nominare_chi_ha_deciso():
    ric = _coppia()
    etichetta = str(ric.get("quarantined_by"))
    assert etichetta != "L3-coexistence", (
        f"l'etichetta e' {etichetta!r}, ma quel layer dichiara di NON trattenere; "
        f"i layer sulla ricevuta sono "
        f"{[str(w.get('layer')) for w in (ric.get('warnings') or [])]}"
    )


def test_CONTROLLO_dove_parla_un_gruppo_solo_l_etichetta_e_giusta():
    """L'altra popolazione: il campo non e' rotto sempre, e va detto."""
    fonte = "    40 pezzi     NO\n    12 colli     NO\n    3 bolle      NO"
    mem = Memory(str(Path(tempfile.mkdtemp()) / "qc.db"))
    ric = mem.add(
        "Nel referto abbreviato 40 pezzi non compare.",
        topic="t/qc",
        source=fonte,
        validate="full",
    )
    if str(ric.get("status")) != "quarantined":
        pytest.fail(
            f"il caso di controllo non e' piu' trattenuto ({ric.get('status')}): "
            "rimisurare, il confronto fra i due casi non regge"
        )
    assert str(ric.get("quarantined_by")) == "moat", (
        f"anche il caso a un gruppo solo ha l'etichetta sbagliata "
        f"({ric.get('quarantined_by')!r}): il difetto e' piu' esteso di quanto "
        "questo banco dichiari"
    )
