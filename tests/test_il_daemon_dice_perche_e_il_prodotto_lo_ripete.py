"""Quando il daemon dice PERCHÉ ha rifiutato, il prodotto lo ripete.

MISURATO IL 06/09, sulla macchina di casa. Il daemon di encode era vivo (pid
28776, porta 55587, connessione provata: ACCETTA), riceveva la richiesta, e
rispondeva:

    {'ok': False, 'error': "AcceleratorError: CUDA error: unknown error ..."}

cioè aveva una diagnosi precisa e la consegnava. Il prodotto la scartava —
`_encode_via_service` guarda solo `resp.get("ok")` e `"vec" in resp` — e
l'utente leggeva:

    encode daemon unavailable and in-process cold-load is disabled
    (HIPPO_ENCODE_DELEGATE_ONLY=1) — caller must degrade

    store: encode delegate unavailable → il fatto viene scritto SENZA
    embedding (recall keyword finché il daemon non torna)

«finché il daemon non torna», mentre il daemon non se n'era mai andato. La
diagnosi manda a cercare un processo morto, e intanto i fatti si scrivono senza
vettore e `semantic.recall` poi li rende `0 hit`. A me è costata mezz'ora su
una falsa pista, durante una release.

⚠️ L'ERRORE È NEL CONTRATTO, non è un extra da inventare: `test_encode_service.
py:73` fa `assert "text" in resp["error"]`, cioè il protocollo PREVEDE che il
daemon spieghi il rifiuto. Degli otto file di test che nominano il delegate,
nessuno verificava che quella spiegazione arrivasse al chiamante: il daemon fa
la sua parte, il consumatore la butta, e nessuna cella se ne accorge. È la
giuntura, non il componente.

Qui si presidia il lato che mancava.
"""
from __future__ import annotations

import pytest

from verimem import embedding as E


class _ConnFinta:
    """Una connessione che non parla con nessuno: la risposta la decide il test."""

    def __init__(self) -> None:
        self.chiusa = False

    def settimeout(self, _s) -> None:
        pass

    def close(self) -> None:
        self.chiusa = True


@pytest.fixture()
def daemon_che_rifiuta(monkeypatch):
    """Il daemon c'È, risponde, e dice perché rifiuta — il caso misurato."""
    from verimem import encode_service as svc

    monkeypatch.setattr(svc, "read_discovery",
                        lambda: {"host": "127.0.0.1", "port": 55587,
                                 "model": E.CONFIG.embedding_model,
                                 "token": "x"})
    monkeypatch.setattr(E, "_service_enabled", lambda: True)
    import socket as _s
    monkeypatch.setattr(_s, "create_connection", lambda *a, **k: _ConnFinta())
    monkeypatch.setattr(svc, "send_msg", lambda *a, **k: None)
    monkeypatch.setattr(
        svc, "recv_msg",
        lambda *a, **k: {"ok": False,
                         "error": "AcceleratorError: CUDA error: unknown error"})
    return "AcceleratorError: CUDA error: unknown error"


def test_controllo_positivo_un_daemon_che_risponde_bene_serve_il_vettore(
        monkeypatch) -> None:
    """Se cade, il finto daemon non è agganciato e il resto non misura nulla."""
    import numpy as np

    from verimem import encode_service as svc

    monkeypatch.setattr(svc, "read_discovery",
                        lambda: {"host": "127.0.0.1", "port": 1,
                                 "model": E.CONFIG.embedding_model})
    monkeypatch.setattr(E, "_service_enabled", lambda: True)
    import socket as _s
    monkeypatch.setattr(_s, "create_connection", lambda *a, **k: _ConnFinta())
    monkeypatch.setattr(svc, "send_msg", lambda *a, **k: None)
    monkeypatch.setattr(svc, "recv_msg",
                        lambda *a, **k: {"ok": True, "vec": [0.1, 0.2, 0.3]})
    vec = E._encode_via_service("prova")
    assert vec is not None, "il finto daemon non è agganciato: banco cieco"
    assert isinstance(vec, np.ndarray)


def test_il_motivo_del_rifiuto_non_si_perde(daemon_che_rifiuta) -> None:
    """⚠️ RED: oggi la spiegazione del daemon finisce nel nulla.

    Non si chiede che `_encode_via_service` renda un vettore — non ce l'ha. Si
    chiede che il motivo NON venga buttato: chi non torna con un vettore deve
    lasciare detto perché, o chi legge non ha modo di saperlo.
    """
    motivo = E.ultimo_rifiuto_del_servizio()
    assert motivo is None, (
        "il banco parte con la memoria del rifiuto già sporca: azzerala")

    vec = E._encode_via_service("prova")
    assert vec is None, "con `ok: False` non c'è vettore, e va bene così"

    motivo = E.ultimo_rifiuto_del_servizio()
    assert motivo is not None, (
        "il daemon ha detto PERCHÉ e il prodotto l'ha buttato: chi legge "
        "riceve «unavailable» e va a cercare un processo morto che è vivo")
    assert "CUDA" in motivo, (
        f"il motivo conservato non è quello del daemon: {motivo!r}")


def test_il_messaggio_all_utente_riporta_il_motivo(daemon_che_rifiuta,
                                                  monkeypatch) -> None:
    """⚠️ RED: «unavailable» è una diagnosi, e su questo caso è sbagliata.

    La frase che l'utente legge deve contenere ciò che il daemon ha detto.
    Senza, il prodotto sostituisce una causa vera con una inventata — la classe
    di difetto che questo prodotto cura ovunque, applicata al proprio canale
    di scrittura.

    ⚠️ LE DUE PRECONDIZIONI SI FISSANO, NON SI ASSUMONO. Il ramo che solleva
    vive dietro `_delegate_only() and not is_loaded()`: la prima dipende da una
    variabile d'ambiente EREDITABILE, la seconda da quanto ha già fatto la
    suite prima di questa cella. Lasciarle al caso significa una cella che
    passa o cade per ragioni che non c'entrano — la prima stesura di questo
    test è caduta con `DID NOT RAISE` per esattamente quello.
    """
    monkeypatch.setattr(E, "_delegate_only", lambda: True)
    monkeypatch.setattr(E, "is_loaded", lambda: False)
    with pytest.raises(E.EncodeDelegateUnavailable) as caduta:
        E._encode_one("prova")
    testo = str(caduta.value)
    assert "CUDA" in testo, (
        f"il messaggio non riporta il motivo del daemon: {testo!r}")


def test_un_daemon_zitto_non_inventa_un_motivo(monkeypatch) -> None:
    """CONTROLLO: se il daemon NON dice niente, non si deve fabbricare nulla.

    Un campo «motivo» che si riempie da solo sarebbe peggio del silenzio: chi
    legge crederebbe di avere una diagnosi. Qui il daemon è davvero
    irraggiungibile, e «unavailable» è la parola giusta.
    """
    from verimem import encode_service as svc

    monkeypatch.setattr(svc, "read_discovery", lambda: None)
    monkeypatch.setattr(E, "_service_enabled", lambda: True)
    assert E._encode_via_service("prova") is None
    assert E.ultimo_rifiuto_del_servizio() is None, (
        "nessuno ha detto niente: non si inventa un motivo")
