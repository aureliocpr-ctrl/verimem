"""`L4.3` deve arrivare alla PORTA, non solo esistere come funzione.

`verimem/soggetto_valore.py` copre lo **scambio di attribuzione**: un claim che
riporta un valore che la fonte contiene davvero, ma **riferito a un'altra
entità**. Ha 21 test suoi, tutti verdi, e restituisce già un dizionario nella
forma dell'avviso (`layer`/`reason`/`advice`/`matched_text`) — cioè era scritto
per essere agganciato al gate. **Dal 28/08 non lo chiama nessuno**: è il 39°
modulo irraggiungibile che fa fallire
`test_nessun_modulo_nasce_irraggiungibile`.

Il buco che copre è misurato due volte, per vie indipendenti:

- il suo docstring: su 12 scambi `L4.1` parla **0 volte** (confronta insiemi di
  valori, non predicati), e la protezione del giudice **si sgretola con la
  lunghezza della fonte** — 7/12 ammessi a 453 caratteri, 10/12 a 930;
- ws1, il 02/09: **9 frasi su 10** che cambiano *solo di chi si parla* passano
  il giudice con gli stessi punteggi delle vere.

⚠️ QUESTO TEST NON CHIEDE UN VETO. Chiede che il layer **dichiari**, come fanno
`L4.2` e `L4-negazione`: la forma scelta in casa per un layer nuovo, e per la
ragione scritta a `anti_confab_gate.py:2928` — *«una cura che rompe un presidio
verde scritto da un altro non si consegna»*. Il passaggio a veto resta una
decisione collegiale, come lo fu il declassamento di `L1.20`.
"""
import os
import tempfile

import pytest

CONTRATTO = (
    "Art. 3 - La penale per il ritardo nella consegna e' pari al 2% dell'importo "
    "contrattuale per ogni settimana di ritardo. "
    "Art. 4 - La penale per difformita' qualitativa e' pari al 5% dell'importo "
    "contrattuale. "
    "Art. 7 - L'importo contrattuale e' di 148000 euro. "
    "Art. 8 - La cauzione definitiva e' pari a 22000 euro."
)


@pytest.fixture()
def store_isolato(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="test_l43_porta_")
    monkeypatch.setenv("HIPPO_DATA_DIR", tmp)
    monkeypatch.setenv("ENGRAM_DATA_DIR", tmp)
    monkeypatch.delenv("VERIMEM_DATA_DIR", raising=False)
    return tmp


def _strati(ricevuta) -> set[str]:
    return {str(w.get("layer", "")) for w in (ricevuta.get("warnings") or [])}


def test_lo_scambio_di_soggetto_arriva_nella_ricevuta(store_isolato):
    """Il claim dice che la CAUZIONE vale 148000: quella cifra nella fonte c'è,
    ma è l'IMPORTO CONTRATTUALE. `L4.1` tace per costruzione — il numero c'è."""
    from verimem import Memory

    m = Memory()
    r = m.add("La cauzione definitiva e' pari a 148000 euro.",
              topic="test/l43-porta", source=CONTRATTO)
    strati = _strati(r)
    assert "L4.3" in strati, (
        f"lo scambio di attribuzione non arriva alla porta: strati visti {sorted(strati)}. "
        f"Il modulo esiste (verimem/soggetto_valore.py, 21 test verdi) ma nessuno "
        f"lo chiama — e' il 39esimo modulo irraggiungibile"
    )


def test_il_layer_non_parla_su_un_claim_fedele(store_isolato):
    """Controllo POSITIVO al rovescio: senza questo, un layer che grida sempre
    passerebbe il test qui sopra e non misurerebbe nulla."""
    from verimem import Memory

    m = Memory()
    r = m.add("L'importo contrattuale e' di 148000 euro.",
              topic="test/l43-fedele", source=CONTRATTO)
    assert "L4.3" not in _strati(r), (
        "il layer segnala un claim FEDELE alla fonte: se parla sempre, il test "
        "sullo scambio non dimostra che sappia distinguere"
    )
