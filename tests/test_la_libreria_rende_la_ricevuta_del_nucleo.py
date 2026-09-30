"""La libreria rende la Ricevuta del nucleo, da TUTTE le sue uscite.

`Memory.add()` non ha un punto di uscita: ne ha QUATTRO, e tre sono i casi
scomodi — la scrittura vuota, quella rifiutata, quella instradata alla
telemetria. Curare solo il ritorno principale avrebbe lasciato il vecchio
schema proprio dove la ricevuta serve di piu': quando qualcosa NON e' andato
come il chiamante si aspettava.

⚠️ QUATTRO VARIABILI, PERCHE' QUI SI E' IN-PROCESS. La regola non e' «tre o
quattro», e' DOVE si mette l'ambiente: in un sottoprocesso le tre bastano
perche' il giornale si fissa all'import e il figlio nasce gia' puntato; qui
`verimem` e' gia' importato quando il banco gira, quindi lo store si sposta e
il giornale NO — serve anche `ENGRAM_EVENT_LOG`. Misurato da un pari il 19/09,
dopo che due scritture erano finite nello store vero.

⚠️ E IL CONTROLLO POSITIVO E' CHIEDERE AL PROCESSO DOVE HA SCRITTO, non
crederci: ogni cella legge `store` dalla ricevuta e pretende che sia la cartella
usa-e-getta. «Credo di aver isolato» non e' una misura.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from verimem.core import CHIAVI


@pytest.fixture
def memoria(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Una memoria su uno store usa-e-getta, con il giornale che la segue."""
    deposito = tmp_path / "store"
    for nome in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(nome, str(deposito))
    monkeypatch.setenv("ENGRAM_EVENT_LOG", str(deposito / "eventi.jsonl"))
    from verimem import Memory
    return Memory(), tmp_path


#: La cartella di casa: quella che nessun banco deve toccare.
CASA = Path.home() / ".engram"


def _fuori_dallo_store_vero(ricevuta: dict) -> bool:
    """Il processo ha scritto FUORI dallo store vero? Lo dice la ricevuta.

    ⚠️ LA PRIMA STESURA CHIEDEVA «ha scritto in tmp_path?» ED E' CADUTA, e la
    caduta e' stata utile: lo store reale era
    `pytest-of-aurel/.../hippo_test_data0`, perche' il `conftest` del repo
    dirotta la cartella dati PRIMA che le variabili di questo banco contino.
    Isolato lo era — ma non dove avevo dichiarato io, e un controllo che
    pretende il posto SBAGLIATO fallisce anche quando tutto va bene.
    La domanda giusta non e' «ha scritto dove ho detto», e' «ha scritto nello
    store VERO?»: quella e' la cosa che fa danno.
    """
    scritto = str(ricevuta.get("store") or "")
    return bool(scritto) and str(CASA) not in scritto


def test_la_scrittura_normale_rende_le_chiavi_del_nucleo(memoria):
    m, _ = memoria
    r = m.add("Un fatto qualunque per il caso normale.", topic="prova/1b2")
    assert _fuori_dallo_store_vero(r), f"scritto nello store VERO: {r.get('store')!r}"
    mancanti = sorted(set(CHIAVI) - set(r))
    assert not mancanti, f"la libreria non rende: {mancanti}"


def test_le_chiavi_non_dipendono_dall_INGRESSO(memoria):
    """Con e senza `source` l'insieme deve essere lo stesso.

    Sulla porta CLI, prima della cura, erano 11 con la source e 10 senza: un
    contratto che cambia col comando non e' un contratto. Qui si pretende che
    le 14 ci siano in entrambi i casi, anche vuote.
    """
    m, _ = memoria
    senza = m.add("Un fatto senza fonte.", topic="prova/1b2")
    con = m.add("Un fatto con la sua fonte.", topic="prova/1b2",
                source="Un fatto con la sua fonte, scritto nella fonte.")
    assert set(CHIAVI) <= set(senza)
    assert set(CHIAVI) <= set(con)


def test_una_scrittura_VUOTA_rende_la_ricevuta_e_non_dice_rifiutato(memoria):
    """La prima delle tre uscite scomode (`client.py:755`).

    Una scrittura senza contenuto non e' un rifiuto: chiamarla «rifiutata»
    sarebbe un esito FALSO, cioe' la giuntura che la ricevuta esiste per
    togliere. La tabella dell'esito le da' una riga sua con la sua ragione.
    """
    m, _ = memoria
    r = m.add("", topic="prova/1b2")
    mancanti = sorted(set(CHIAVI) - set(r))
    assert not mancanti, f"l'uscita VUOTA non rende: {mancanti}"
    assert r["esito"] in ("rifiutato", "fermato")
    assert r["fermato_da"], "una scrittura non entrata senza dire perche'"


def test_ogni_uscita_porta_i_campi_dello_store(memoria):
    """Nessuna delle quattro uscite puo' tacere su DOVE ha scritto.

    Il 14/09 tre variabili puntavano a uno store di prova e la scrittura e'
    finita in quello vero: se la ricevuta non lo dice, chi credeva di aver
    isolato non ha modo di accorgersene.
    """
    m, radice = memoria
    for testo in ("Un fatto normale.", ""):
        r = m.add(testo, topic="prova/1b2")
        assert r["store"], f"store vuoto per {testo!r}"
        assert r["store_decided_by"], f"store_decided_by vuoto per {testo!r}"


def test_il_margine_lo_calcola_la_ricevuta_anche_qui(memoria):
    """Se c'e' un punteggio, ci sono la sua scala e il suo margine.

    L'implicazione, non la disponibilita' del giudice: se il punteggio manca
    devono mancare anche scala, soglia e margine — una scala senza numero e'
    un'etichetta su niente.
    """
    m, _ = memoria
    r = m.add("Il totale della fattura e' 500 euro.", topic="prova/1b2",
              source="Il documento riporta un totale di 300 euro.")
    if r["punteggio"] is None:
        assert r["scala"] is None and r["soglia"] is None
        assert r["margine"] is None
        return
    assert r["scala"] and r["modello"]
    assert r["margine"] == pytest.approx(r["punteggio"] - r["soglia"])


def test_le_vecchie_chiavi_restano_finche_dura_il_debito(memoria):
    """L'unione, con la sua scadenza.

    Quattordici file di prodotto leggono `stored` o `warnings`: toglierle oggi
    romperebbe loro. Restano finche' 1b.4 non le rimuove — e questa cella e' il
    promemoria che il debito e' VOLUTO, non dimenticato.
    """
    m, _ = memoria
    r = m.add("Un fatto per il debito.", topic="prova/1b2")
    for vecchia in ("stored", "status", "warnings"):
        assert vecchia in r, f"la vecchia chiave {vecchia!r} e' sparita troppo presto"
