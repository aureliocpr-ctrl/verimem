"""La guardia «c'e' un giudice?» elencava tre vie, e il daemon e' la quarta.

`anti_confab_gate` decideva se far girare il moat con tre criteri — un llm
iniettato, il backend dichiarato `local`, il modello CE su disco — **tutti e tre
sguardi IN CASA**. Ma `try_local_score` chiede al daemon condiviso PER PRIMO, e
il docstring di `_gate_via_daemon` dice perche': *«e' cio' che rende giudicata
la PRIMA scrittura invece di ammetterla al buio»*.

MISURATO il 2026-08-30 alle 22:33, modello locale ASSENTE (cartella vuota) e
daemon VIVO, processi freschi::

    i tre criteri                       False
    try_local_score, stesso processo    0.5561     <- il daemon RISPONDE
    Memory().add(..., source=...)       gs=None    <- il write esce al buio

⚖️ E LA CURA NON E' TOGLIERE IL PREDICATO — questa e' la parte che la misura ha
deciso, contro la mia prima intenzione. Nello stesso banco::

    write con la guardia, nessun giudice      351 ms   (non tenta)
    tentativo di giudizio, processo fresco 15.453 ms   (tenta e fallisce)

⇒ Un predicato che risparmia quindici secondi si tiene. Gli si aggiunge **la via
che gli manca**, con lo stesso costo delle altre: `local_ce_available` e' un
`os.path`, `daemon_del_giudice_annunciato` e' una lettura di file.

🔑 LA CONDIZIONE DI FALSIFICAZIONE SCRITTA PRIMA E' SERVITA A QUESTO: *«se il
write senza giudice pagasse secondi invece di millisecondi, la guardia
guadagnerebbe cio' che costa e la cura andrebbe pensata come quarta via
economica invece che come rimozione del predicato»*. E' scattata, e ha cambiato
la cura.

⚠️ UN ANNUNCIO NON E' UNA GARANZIA, ed e' dichiarato nella funzione: il daemon
puo' morire fra l'annuncio e la chiamata. Serve a NON ESCLUDERE una strada che
esiste; chi la percorre degrada gia' da solo (`_gate_via_daemon` -> None ->
warm in background -> `L4-skipped`).
"""

from __future__ import annotations

import pytest

from verimem import local_grounding as lg


@pytest.fixture
def senza_interruttore(monkeypatch):
    monkeypatch.delenv("ENGRAM_ENCODE_SERVICE", raising=False)


def test_un_daemon_annunciato_e_una_via_al_giudizio(monkeypatch, senza_interruttore):
    """IL CUORE: e' il caso in cui il write usciva al buio."""
    monkeypatch.setattr(lg, "encode_service", None, raising=False)
    import verimem.encode_service as svc
    monkeypatch.setattr(svc, "read_discovery",
                        lambda: {"host": "127.0.0.1", "port": 61574})
    assert lg.daemon_del_giudice_annunciato() is True


def test_senza_annuncio_non_si_inventa_un_giudice(monkeypatch, senza_interruttore):
    """⚠️ LA POPOLAZIONE OPPOSTA: se rispondesse sempre True, il gate crederebbe
    di avere un giudice ovunque e il fail-open dichiarato smetterebbe di essere
    leggibile — cioe' il difetto opposto, piu' grave."""
    import verimem.encode_service as svc
    monkeypatch.setattr(svc, "read_discovery", lambda: None)
    assert lg.daemon_del_giudice_annunciato() is False
    monkeypatch.setattr(svc, "read_discovery", lambda: {"host": "127.0.0.1"})
    assert lg.daemon_del_giudice_annunciato() is False


def test_l_interruttore_di_ambiente_ha_l_ultima_parola(monkeypatch):
    """Chi spegne il servizio con `ENGRAM_ENCODE_SERVICE=0` non deve vedersi
    contare il daemon come giudice: e' lo stesso interruttore che
    `_gate_via_daemon` legge alla sua prima riga, e due letture della stessa
    politica devono dare lo stesso esito."""
    import verimem.encode_service as svc
    monkeypatch.setattr(svc, "read_discovery",
                        lambda: {"host": "127.0.0.1", "port": 61574})
    for spento in ("0", "false", "no", "off", "OFF"):
        monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", spento)
        assert lg.daemon_del_giudice_annunciato() is False, spento


def test_un_guasto_nella_sonda_non_rompe_una_scrittura(monkeypatch,
                                                       senza_interruttore):
    """⚠️ E' un PREDICATO sul percorso caldo: se esplode, esplode una scrittura.
    Un guasto vale «non lo so» e si degrada verso il comportamento di prima."""
    import verimem.encode_service as svc

    def _esplode():
        raise OSError("disco che non risponde")

    monkeypatch.setattr(svc, "read_discovery", _esplode)
    assert lg.daemon_del_giudice_annunciato() is False


def test_la_guardia_del_gate_conosce_la_quarta_via():
    """Il presidio strutturale: la funzione dev'essere DENTRO `_have_judge`, o
    la cura vive nel modulo e non nel punto che decide."""
    import inspect

    from verimem import anti_confab_gate as gate
    sorgente = inspect.getsource(gate)
    i = sorgente.find("_have_judge = (")
    assert i > 0, "la riga `_have_judge` non si trova piu': parser da rivedere"
    blocco = sorgente[i:i + 400]
    assert "daemon_del_giudice_annunciato" in blocco, blocco[:200]
