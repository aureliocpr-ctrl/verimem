"""Quando il gate dice all'utente COME riparare, quel rimedio deve funzionare.

Gli `advice` del gate non sono tutti uguali. Alcuni danno un consiglio generico
(«correggi il valore, oppure passa la fonte che lo contiene»); due contengono
invece una **promessa verificabile**, cioè indicano un gesto preciso e
affermano cosa succede dopo::

    L4.1-ambiguo   «riscrivi il numero senza separatori (45000)
                    PER FARLO VERIFICARE»
    L4-negazione   «passa una fonte che ENUNCI l'assenza […]
                    SU QUELLA FORMA IL GIUDIZIO TORNA AFFIDABILE»

⇒ Sono promesse del prodotto quanto una riga del README, e nessun test le
teneva. Misurate alla porta il 16/08 — funzionano entrambe::

    claim «45.000 euro»              layers ['L4.1-ambiguo']
    il rimedio «45000 euro»          layers []            g 99.829
    fonte che lascia DEDURRE         quarantined          g  0.159
    il rimedio: fonte che ENUNCIA    model_claim          g 99.815

⚠️ Perché serve un presidio: se una cura futura rompesse uno dei due percorsi,
il gate continuerebbe a **stampare l'istruzione** — e l'utente farebbe il gesto
giusto ottenendo lo stesso rifiuto, senza capire perché. Un rimedio che non
ripara è peggio di nessun rimedio: manda a sbattere chi si fida.

📌 Il censimento degli advice è PARZIALE (5 coppie layer/advice trovate con un
regex sul sorgente, e il gate ne ha altre): qui stanno le due che promettono un
esito. Le altre tre dicono «correggi» o «verifica», che non è falsificabile.
"""
from __future__ import annotations

import pytest

from verimem import Memory


def _ricevuta(claim: str, fonte: str) -> dict:
    r = Memory().add(claim, topic="prova/rimedi", source=fonte)
    return r if isinstance(r, dict) else getattr(r, "__dict__", {})


def _layers(d: dict) -> list[str]:
    return [w.get("layer") for w in (d.get("warnings") or [])]


# --------------------------------------------------------- L4.1-ambiguo -----
FONTE_EURO = "Il contratto vale 45000 euro e scade a dicembre."


def test_il_numero_col_punto_viene_dichiarato_non_verificato():
    """La premessa: senza questa, il test sotto passerebbe per il motivo
    sbagliato — non c'è nessun rimedio da provare se non c'è l'avviso."""
    d = _ricevuta("Il contratto vale 45.000 euro.", FONTE_EURO)
    assert "L4.1-ambiguo" in _layers(d), (
        f"l'avviso che il rimedio dovrebbe risolvere non compare: {_layers(d)}")


def test_togliere_il_separatore_LO_FA_VERIFICARE_come_promesso():
    d = _ricevuta("Il contratto vale 45000 euro.", FONTE_EURO)
    assert "L4.1-ambiguo" not in _layers(d), (
        "l'advice dice «riscrivi il numero senza separatori PER FARLO "
        f"VERIFICARE», ma riscritto così l'avviso resta: {_layers(d)}. "
        "L'utente farebbe il gesto giusto e otterrebbe lo stesso esito")


# ---------------------------------------------------------- L4-negazione ----
CLAIM_NEG = "Il fornitore Verdi non ha consegnato pallet al magazzino."
FONTE_DEDOTTA = (
    "Il magazzino contiene 480 pallet di farina, 210 di zucchero e 65 di "
    "sale, consegnati dai fornitori Rossi e Bianchi.")
FONTE_ENUNCIATA = (
    "Il magazzino contiene 480 pallet di farina, 210 di zucchero e 65 di "
    "sale. Il fornitore Verdi non ha consegnato nulla e non risulta fra i "
    "fornitori.")


@pytest.mark.slow
def test_una_fonte_che_ENUNCIA_l_assenza_rende_il_giudizio_affidabile():
    """Il cuore della promessa: il prodotto dichiara che su una fonte che
    enuncia l'assenza «il giudizio torna affidabile». È l'unica uscita che il
    gate offre per una negazione vera — se non funziona, quel layer trattiene
    fatti veri e indica una porta chiusa."""
    dedotta = _ricevuta(CLAIM_NEG, FONTE_DEDOTTA)
    assert dedotta.get("status") == "quarantined", (
        "la premessa non regge: la fonte che lascia dedurre l'assenza non "
        f"viene più trattenuta ({dedotta.get('status')}). Rileggere, non "
        "cancellare: il rimedio sotto non avrebbe più nulla da riparare")

    enunciata = _ricevuta(CLAIM_NEG, FONTE_ENUNCIATA)
    assert enunciata.get("status") != "quarantined", (
        "l'advice promette che con una fonte che ENUNCIA l'assenza «il "
        f"giudizio torna affidabile», e invece resta {enunciata.get('status')} "
        f"con {_layers(enunciata)}: l'unica uscita documentata è chiusa")
    assert "L4-negazione" not in _layers(enunciata), _layers(enunciata)
