"""T152 — la riga di riepilogo di `save` accusa DUE schermi a nome fisso.

Reperto del 19/09: qualunque sia il layer che ha trattenuto la scrittura, la
CLI stampa sempre

    stored QUARANTINED — the injection/contradiction screens fired

«injection/contradiction» è una coppia scritta a mano, non un dato. Se a
fermare è `L4.1` (un numero che la fonte non contiene) o `L4-grounding` (il
giudice), la riga nomina due schermi che **non si sono accesi** — e due righe
più sotto la stessa ricevuta stampa i layer veri, che la contraddicono.

Non è cosmesi: è la prima riga che l'utente legge quando una scrittura viene
respinta, e lo manda a cercare un'iniezione o una contraddizione che non c'è.
È la classe di T77 e T150 — un nome di comodo al posto di chi ha deciso — sulla
terza superficie: dopo la colonna del database e l'etichetta, il testo.

⚠️ LE CELLE NON SCRIVONO NIENTE: la riga dipende solo dalla ricevuta, e farla
passare da una scrittura vera significherebbe misurare il giudice invece della
riga. È la lezione che ha reso fragile la cella di T150, arrivata qui prima di
costare un secondo rosso.
"""
from __future__ import annotations

from verimem.cli import riga_stored_quarantined

#: Le tre forme in cui una ricevuta arriva alla riga, copiate dalle misure di
#: oggi sul tronco e non ricostruite a mente:
#:   L4.1          il claim afferma un valore che la fonte non contiene
#:   L4-grounding  il giudice non trova sostegno (moat failed)
#:   L1.10         auto-affermazione, e nessuno dei due schermi citati
RICEVUTE = {
    "L4.1": {"status": "quarantined",
             "warnings": [{"layer": "L4.1", "advice": "…"}]},
    "L4-grounding": {"status": "quarantined",
                     "warnings": [{"layer": "L4-grounding", "advice": "…"}]},
    "L1.10": {"status": "quarantined",
              "warnings": [{"layer": "L1.10", "advice": "…"}]},
}


def test_la_riga_nomina_il_layer_che_ha_fermato():
    """Il RED di T152: oggi la riga è identica per tutti e tre."""
    for atteso, ricevuta in RICEVUTE.items():
        riga = riga_stored_quarantined(ricevuta)
        assert atteso in riga, (
            f"la riga non nomina {atteso!r}, che è il layer che ha fermato la "
            f"scrittura. Dice: {riga!r}"
        )


def test_la_riga_non_accusa_schermi_che_non_si_sono_accesi():
    """Il difetto vero non è l'assenza del nome: è la PRESENZA di due nomi falsi.

    Un utente che legge «injection/contradiction» su una scrittura fermata da
    `L4.1` va a cercare un'iniezione di prompt in una frase che conteneva solo
    un numero non presente nella fonte.
    """
    riga = riga_stored_quarantined(RICEVUTE["L4.1"])
    for bugia in ("injection", "contradiction"):
        assert bugia not in riga.lower(), (
            f"la riga accusa lo schermo {bugia!r} su una scrittura fermata da "
            f"L4.1, dove quello schermo non ha parlato. Dice: {riga!r}"
        )


def test_un_avviso_consultivo_non_viene_nominato():
    """Deve usare i layer che hanno AGITO, non tutti quelli che hanno parlato.

    `_blocking_layers` esclude gli `*-observe`; una riga che li nominasse
    darebbe il merito del blocco a chi ha solo avvisato — lo stesso difetto
    che `chi_ha_quarantinato` ha già chiuso sull'etichetta.
    """
    ricevuta = {"status": "quarantined",
                "warnings": [{"layer": "L3-semantic-observe", "advice": "…"},
                             {"layer": "L4.1", "advice": "…"}]}
    riga = riga_stored_quarantined(ricevuta)
    assert "L4.1" in riga, f"non nomina il layer che ha agito: {riga!r}"
    assert "observe" not in riga, (
        f"nomina un avviso consultivo fra i responsabili del blocco: {riga!r}"
    )


def test_CONTROLLO_la_riga_dice_gia_oggi_che_la_scrittura_e_trattenuta():
    """Il controllo positivo VERO: la metà che funziona e deve restare.

    ⚠️ Scritto DOPO aver visto il primo giro rosso su quattro celle su quattro.
    Avevo chiamato «CONTROLLO» la cella qui sotto, che è invece un altro caso
    del difetto: un banco tutto rosso non dice quale metà si sta misurando, ed
    è la riga che avevo appena scritto io nella consegna precedente. Questa
    cella passa PRIMA della cura e deve passare anche dopo: se si spegne, la
    cura ha tolto l'informazione che la riga già dava.
    """
    for ricevuta in list(RICEVUTE.values()) + [
            {"status": "quarantined", "warnings": []}]:
        riga = riga_stored_quarantined(ricevuta)
        assert "QUARANTINED" in riga, (
            f"la riga non dice più che la scrittura è trattenuta: {riga!r}"
        )
        assert "warnings" in riga, (
            f"la riga non rimanda più agli avvisi sotto: {riga!r}"
        )


def test_senza_layer_la_riga_non_inventa_un_colpevole():
    """Il ripiego, ed è la metà che protegge dal rimedio peggiore del male.

    Se nessun layer ha agito non c'è nessuno da nominare: la riga deve dire
    che è trattenuta e rimandare agli avvisi, senza accusare niente. Un nome
    inventato sarebbe peggio di un'assenza — è la riga del 20/08 che vale
    ancora.
    """
    riga = riga_stored_quarantined({"status": "quarantined", "warnings": []})
    assert "QUARANTINED" in riga, (
        f"la riga non dice più che la scrittura è trattenuta: {riga!r}"
    )
    for bugia in ("injection", "contradiction"):
        assert bugia not in riga.lower(), (
            f"senza layer la riga accusa comunque {bugia!r}: {riga!r}"
        )
