"""T93 — un avviso RITIRATO da una guardia si vede nella ricevuta e non decide.

IL DIFETTO, misurato il 16 e il 18/09. Due guardie tolgono avvisi dopo averli
prodotti — il discorso riportato con disclaimer (`_is_honest_reported`) e la
smentita (`_e_una_smentita`) — e per chi legge la ricevuta un avviso **ritirato**
e un avviso **mai nato** sono la stessa cosa: niente. Le due guardie sono giuste
e questo banco NON chiede di toglierle: chiede che il ritiro sia DETTO.

PERCHE' NON E' UN CAMPO NUOVO. `client.py:493` dice che la superficie unica
della convenzione e' `_is_advisory_layer`: un livello che si vede e non decide
esiste gia' (`-observe`, `-graded`). `-withdrawn` si aggiunge li', in una riga.

LE FRASI NON SONO SCELTE A CASO, ed e' la parte che mi e' costata un errore:
- la frase C inglese («The system does NOT work in production») **non accende
  nessun detector**, quindi non c'e' niente da ritirare e il banco misurerebbe
  il vuoto. La frase che accende e' quella ITALIANA, ed e' la stessa che il
  commento del gate cita da se' a riga 1704.
- e la guardia non si interroga sul proprio effetto: chiamare
  `_e_una_smentita` sul warning GIA' marcato rende `False`, perche' il layer
  rinominato non sta piu' in `_NEGABILI`. Qui si guarda l'USCITA, non la guardia.
"""
from __future__ import annotations

import pytest

from verimem.anti_confab_gate import _is_advisory_layer, _l1_warnings

SENZA_GUARDIE = "The system works perfectly and has been verified in production."
RIPORTATA = ("The vendor claims the system works perfectly in production, "
             "but we have NOT verified it.")
SMENTITA = "Il modulo NON funziona in produzione."
INNOCUA = "La coda ha 500 elementi."


def _strati(testo: str) -> list[dict]:
    return _l1_warnings(testo, None)


def test_CONTROLLO_POSITIVO_senza_guardie_gli_avvisi_decidono():
    """Senza questa cella le tre sotto passerebbero anche a detector spenti."""
    avvisi = _strati(SENZA_GUARDIE)
    decidono = [w["layer"] for w in avvisi if not _is_advisory_layer(w["layer"])]
    assert decidono, (
        "CONTROLLO POSITIVO SPENTO: la frase di vanto non accende nessun "
        "avviso che decide, quindi le celle sul ritiro non misurano niente.\n"
        f"  avvisi = {[w.get('layer') for w in avvisi]}")
    assert not any(w.get("ritirato_da") for w in avvisi), (
        "una frase senza disclaimer e senza negazione non deve produrre ritiri")


@pytest.mark.parametrize(("testo", "ragione"), [
    (RIPORTATA, "reported-speech-with-disclaimer"),
    (SMENTITA, "denial-not-claim"),
])
def test_un_avviso_ritirato_SI_VEDE_e_NON_decide(testo: str, ragione: str):
    """Il cuore: oggi questa lista e' VUOTA, ed e' il rosso."""
    avvisi = _strati(testo)
    ritirati = [w for w in avvisi if w.get("ritirato_da")]
    assert ritirati, (
        "la guardia ha tolto un avviso e la ricevuta non lo dice: per chi "
        "legge, un avviso ritirato e uno mai nato sono la stessa cosa.\n"
        f"  testo   = {testo!r}\n"
        f"  avvisi  = {[w.get('layer') for w in avvisi]}\n"
        "  atteso  = almeno un avviso con `ritirato_da` e un layer -withdrawn")
    assert all(w["ritirato_da"] == ragione for w in ritirati), (
        f"la ragione del ritiro non e' quella attesa: "
        f"{[w.get('ritirato_da') for w in ritirati]} invece di {ragione!r}")
    assert all(_is_advisory_layer(w["layer"]) for w in ritirati), (
        "un avviso ritirato DECIDE ancora: la cura lo ha reso un veto, che e' "
        "il contrario di quello che serve.\n"
        f"  {[w['layer'] for w in ritirati]}")


def test_CONTROLLO_NEGATIVO_la_cura_non_fabbrica_ritiri():
    """Una frase innocua non deve guadagnare un ritiro: senza questa cella,
    marcare tutto passerebbe."""
    avvisi = _strati(INNOCUA)
    assert not [w for w in avvisi if w.get("ritirato_da")], (
        "la cura ha marcato come ritirato un avviso di una frase che non "
        f"attiva nessuna guardia: {[w.get('layer') for w in avvisi]}")


def test_AL_LIVELLO_DELLA_PORTA_un_ritiro_non_trattiene_la_scrittura(tmp_path):
    """IL RILIEVO DEL PARI, e aveva ragione: le celle sopra chiedono a
    `_is_advisory_layer` — la funzione che questa cura MODIFICA — se la modifica
    ha funzionato. E' interrogare la guardia sul proprio effetto.

    Questa cella misura dove il difetto si vedeva davvero: alla PORTA. Il 19/09
    la marcatura, senza la cura al contatore, faceva diventare `quarantined` una
    scrittura che prima era ammessa — e nessuna delle celle sopra se ne
    accorgeva, perche' guardavano tutte il layer e nessuna il VERDETTO.
    """
    from verimem.client import Memory

    r = Memory(tmp_path / "m.db").add(RIPORTATA, topic="prova/t93")
    strati = [w.get("layer") for w in (r.get("warnings") or [])]

    assert r.get("status") != "quarantined", (
        "una claim attribuita CON il suo disclaimer viene trattenuta: il "
        "ritiro e' diventato un veto.\n"
        f"  status = {r.get('status')}\n  strati = {strati}")
    assert any(str(s).endswith("-withdrawn") for s in strati), (
        "il banco non sta misurando il ritiro: senza un avviso marcato qui, "
        f"la cella sopra passerebbe anche a cura spenta. strati = {strati}")
