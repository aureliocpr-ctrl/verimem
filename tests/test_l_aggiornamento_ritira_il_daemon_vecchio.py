"""Aggiornamento dal file di scoperta unico a uno per configurazione.

Fino al 28/09 c'era un solo file, `~/.engram/encode_service.json`. Dopo
l'aggiornamento i client cercano il file della loro configurazione, e un daemon
di prima resta nel file vecchio senza che nessun client nuovo lo cerchi: sulla
macchina di sviluppo quel daemon impegna circa 6 GB, e morirebbe solo dopo
l'inattivita' (8 ore), accanto al nuovo. E un server MCP partito prima
dell'aggiornamento (codice vecchio in memoria) cerca ancora il file vecchio.

La regola: il daemon nuovo scrive i propri dati anche nel file vecchio, salvo
che questo annunci un daemon VIVO di un altro modello o di un'altra dimensione.
Il daemon vecchio dello stesso modello vede la scoperta presa da un altro vivo
e fa il passo indietro che sa gia' fare; i client vecchi trovano il nuovo.

NESSUN MODELLO: un server con encoder finto su una porta locale.
"""
from __future__ import annotations

import json
import os

import pytest

from verimem import encode_service as svc


@pytest.fixture
def server(monkeypatch, tmp_path):
    vecchio = tmp_path / "vecchio" / "encode_service.json"
    vecchio.parent.mkdir()
    monkeypatch.setattr(svc, "LEGACY_DISCOVERY_PATH", vecchio, raising=False)
    s = svc.EncodeServer(encode_fn=lambda t: [0.0, 0.0], model_name="modello/a",
                         model_dim=2, discovery_path=tmp_path / "nuovo" / "scoperta.json")
    yield s, vecchio
    s.stop()


def _scrivi(percorso, **campi):
    percorso.write_text(json.dumps({"port": 1, "host": "127.0.0.1", **campi}),
                        encoding="utf-8")


def _annuncia(percorso):
    return json.loads(percorso.read_text(encoding="utf-8"))


def test_il_file_vecchio_di_un_daemon_vivo_dello_stesso_modello_passa_al_nuovo(server):
    """RED sul tronco: il file vecchio resta del daemon vecchio."""
    s, vecchio = server
    _scrivi(vecchio, pid=os.getppid(), model="modello/a", dim=2)

    s.start()

    assert _annuncia(vecchio)["pid"] == os.getpid(), (
        "il daemon vecchio dello stesso modello resta annunciato: i client vecchi "
        "continuano a usarlo e lui non fa mai il passo indietro")


def test_senza_file_vecchio_i_client_vecchi_trovano_il_nuovo(server):
    """Un server MCP partito prima dell'aggiornamento cerca il file vecchio."""
    s, vecchio = server

    s.start()

    assert vecchio.exists() and _annuncia(vecchio)["pid"] == os.getpid()


def test_il_file_vecchio_di_un_daemon_morto_passa_al_nuovo(server):
    s, vecchio = server
    _scrivi(vecchio, pid=2 ** 22 + 7, model="modello/a", dim=2)

    s.start()

    assert _annuncia(vecchio)["pid"] == os.getpid()


def test_allo_stop_il_file_vecchio_non_resta_a_nome_di_un_morto(server):
    """Lo stop toglie il file per configurazione che nomina il daemon: il file
    vecchio preso da lui deve seguire la stessa regola."""
    s, vecchio = server
    s.start()

    s.stop()

    assert not vecchio.exists(), _annuncia(vecchio)


def test_il_file_vecchio_di_un_altro_modello_vivo_non_si_tocca(server):
    """GUARDIA: serve un'altra configurazione, e non la si sfratta."""
    s, vecchio = server
    _scrivi(vecchio, pid=os.getppid(), model="modello/b", dim=2)

    s.start()

    assert _annuncia(vecchio)["pid"] == os.getppid()
    assert _annuncia(vecchio)["model"] == "modello/b"
