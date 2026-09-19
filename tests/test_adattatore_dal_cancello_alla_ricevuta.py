"""L'adattatore: dal dizionario del cancello alla `Ricevuta`, e niente altro.

Il banco della porta (`test_la_porta_cli_rende_la_ricevuta_del_nucleo`) misura
il prodotto ESEGUENDOLO, e per questo e' lento e dipende da cosa e' disponibile
sulla macchina — il giudice, lo store, il modello. Queste celle misurano la
TRADUZIONE e basta: nessun processo, nessun disco, nessun giudice. Servono a
sapere che cosa fa l'adattatore quando il dizionario e' fatto in un certo modo,
compresi i modi che alla porta non si riescono a provocare a comando.

⚠️ QUELLO CHE QUESTE CELLE POSSONO E LA PORTA NO: costruire un dizionario
ROTTO. Alla porta non si ottiene «fermato senza chi» — il cancello non lo
produce oggi. Qui si', e serve: il giorno che lo producesse, la ricevuta deve
dire «non dichiarato dal cancello» e non lasciare un buco muto.
"""
from __future__ import annotations

import pytest

from verimem.adattatore_ricevuta import GIUDICE_NON_DICHIARATO, ricevuta_dal_cancello
from verimem.core import CHIAVI

#: Il minimo che `client.py` mette sempre: dove ha scritto e chi l'ha deciso.
DAL_CANCELLO = {
    "moat": "passed", "stored": True, "id": "abc123", "status": "model_claim",
    "store": "/casa/semantic.db", "store_decided_by": "default",
}


def _con(**cambi):
    return ricevuta_dal_cancello({**DAL_CANCELLO, **cambi})


def test_una_scrittura_passata_diventa_ammessa():
    r = _con()
    assert r.esito == "ammesso"
    assert r.fermato_da is None
    assert tuple(r.come_dizionario()) == CHIAVI


def test_quarantined_by_diventa_fermato_da():
    """Il campo esiste nel cancello ma e' CONDIZIONALE, e nessuno lo portava
    in un nome stabile: e' il rosso che questa fetta cura."""
    r = _con(quarantined_by="moat", status="quarantined")
    assert r.esito == "fermato"
    assert r.fermato_da == "moat"


def test_fermata_SENZA_un_nome_dichiara_che_il_nome_non_c_e():
    """Il caso che alla porta non si sa provocare, e che qui si costruisce.

    Un `fermato` senza `fermato_da` il nucleo lo RIFIUTA, e ha ragione: chi
    ferma ha un nome. Se il cancello un giorno non lo desse, l'adattatore deve
    dirlo a parole invece di far esplodere la porta o, peggio, di rendere una
    ricevuta che tace su chi ha deciso.
    """
    r = _con(status="quarantined")          # nessun quarantined_by
    assert r.esito == "fermato"
    assert r.fermato_da and "non dichiarato" in r.fermato_da


def test_una_scrittura_non_entrata_e_rifiutata():
    r = _con(stored=False)
    assert r.esito == "rifiutato"
    assert r.fermato_da


def test_un_punteggio_senza_la_sua_soglia_non_passa_zoppo():
    """Meglio non portarlo che portarlo senza il margine.

    Il nucleo rifiuta un punteggio senza soglia; l'adattatore non aggira il
    rifiuto inventando una soglia, lo rispetta lasciando vuoti tutti e tre.
    """
    r = _con(grounding_score=99.5)          # nessuna adjudication, nessun threshold
    assert r.punteggio is None
    assert r.scala is None and r.soglia is None and r.margine is None


def test_i_tre_numeri_viaggiano_insieme_e_il_margine_lo_calcola_la_ricevuta():
    r = _con(grounding_score=99.5, adjudication={
        "threshold": 40.0, "judge": {"backend": "local", "model": "ce_v2"}})
    assert r.punteggio == pytest.approx(99.5)
    assert r.soglia == pytest.approx(40.0)
    assert r.margine == pytest.approx(59.5)
    assert r.scala and r.modello == "ce_v2" and r.giudice == "local"


def test_senza_giudice_dichiarato_si_scrive_che_non_e_dichiarato():
    assert _con().giudice == GIUDICE_NON_DICHIARATO


@pytest.mark.parametrize("mancante", ["store", "store_decided_by"])
def test_i_campi_dello_store_non_restano_mai_vuoti(mancante):
    """Se il cancello smettesse di dichiararli, chi legge deve trovare una
    RAGIONE e non una stringa vuota — che il nucleo rifiuterebbe comunque."""
    grezzo = {k: v for k, v in DAL_CANCELLO.items() if k != mancante}
    r = ricevuta_dal_cancello(grezzo)
    assert getattr(r, mancante), f"{mancante} vuoto"


def test_un_avviso_senza_livello_non_diventa_un_livello_anonimo():
    """`Livello(nome="")` il nucleo lo rifiuta. L'adattatore non gli passa
    avvisi senza nome invece di inventarne uno."""
    r = _con(warnings=[{"message": "qualcosa"}, {"layer": "L4", "reason": "R2"}])
    assert [liv.nome for liv in r.livelli] == ["L4"]
    assert r.livelli[0].ragione == "R2"


def test_uno_stato_di_livello_sconosciuto_non_fa_esplodere_la_porta():
    """Un valore fuori elenco diventa «eseguito», non una ValueError in faccia
    all'utente: l'adattatore e' un traduttore, non un secondo cancello."""
    r = _con(warnings=[{"layer": "L4", "stato": "boh", "reason": "R2"}])
    assert r.livelli[0].stato == "eseguito"
