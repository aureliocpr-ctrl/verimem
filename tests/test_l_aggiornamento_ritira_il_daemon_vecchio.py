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

NESSUN MODELLO: un server con encoder finto su una porta locale; l'ultima cella
usa due processi veri, sempre con l'encoder finto, in una home di sabbia.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from verimem import encode_service as svc

RADICE = Path(__file__).resolve().parents[1]

#: Il daemon di PRIMA dell'aggiornamento: il codice di oggi con i percorsi di
#: allora (un file e due lock unici nella home). Il passo indietro non e' cambiato.
DAEMON_VECCHIO = r'''
from verimem import encode_service as es, embedding
embedding._encode_local = lambda testo: [0.0, 0.0]
es._prepara_la_finestra = lambda: None
es._SUPERFLUOUS_IDLE_S = 2.0
cartella = es.LEGACY_DISCOVERY_PATH.parent
es.DISCOVERY_PATH = es.LEGACY_DISCOVERY_PATH
es.DAEMON_LOCK_PATH = cartella / "encode_service.daemon.lock"
es._SPAWN_LOCK_PATH = cartella / "encode_service.spawn.lock"
es.main()
'''

DAEMON_NUOVO = r'''
from verimem import encode_service as es, embedding
embedding._encode_local = lambda testo: [0.0, 0.0]
es._prepara_la_finestra = lambda: None
es.main()
'''


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


def _ambiente(sabbia: Path) -> dict:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("HIPPO_", "ENGRAM_", "VERIMEM_"))}
    dati = sabbia / "dati"
    env.update({
        "USERPROFILE": str(sabbia / "home"), "HOME": str(sabbia / "home"),
        "HIPPO_DATA_DIR": str(dati), "ENGRAM_DATA_DIR": str(dati), "VERIMEM_DATA_DIR": str(dati),
        "ENGRAM_EVENT_LOG": str(sabbia / "eventi.jsonl"),
        "HIPPO_EMBEDDING_MODEL": "modello/a", "HIPPO_EMBEDDING_DIM": "2",
        "ENGRAM_ENCODE_SERVICE": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
        "PYTHONPATH": str(RADICE), "PYTHONIOENCODING": "utf-8",
    })
    return env


def _pid_annunciato(percorso: Path) -> int:
    try:
        return int(json.loads(percorso.read_text(encoding="utf-8")).get("pid") or 0)
    except (OSError, ValueError):
        return 0


def _aspetta(condizione, secondi: float) -> bool:
    fine = time.monotonic() + secondi
    while time.monotonic() < fine:
        if condizione():
            return True
        time.sleep(0.5)
    return False


def test_il_daemon_vecchio_dello_stesso_modello_fa_il_passo_indietro(tmp_path):
    """Processi veri, stesso modello: il daemon di prima annunciato nel file
    vecchio, poi quello nuovo. RED senza il passaggio: il vecchio resta vivo,
    e la memoria del modello resta doppia fino all'inattivita'."""
    (tmp_path / "home" / ".engram").mkdir(parents=True)
    (tmp_path / "dati").mkdir()
    file_vecchio = tmp_path / "home" / ".engram" / "encode_service.json"
    avviati = []
    try:
        vecchio = subprocess.Popen([sys.executable, "-c", DAEMON_VECCHIO], cwd=str(RADICE),
                                   env=_ambiente(tmp_path),
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        avviati.append(vecchio)
        assert _aspetta(lambda: _pid_annunciato(file_vecchio) == vecchio.pid, 60), (
            "il daemon di prima non si e' mai annunciato nel file vecchio")

        nuovo = subprocess.Popen([sys.executable, "-c", DAEMON_NUOVO], cwd=str(RADICE),
                                 env=_ambiente(tmp_path),
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        avviati.append(nuovo)
        uscito = _aspetta(lambda: vecchio.poll() is not None, 30)
        codice_del_vecchio = vecchio.returncode    # uscito da solo: il passo indietro
        ancora_vivo = nuovo.poll() is None
        annunciato = _pid_annunciato(file_vecchio)
    finally:
        for processo in avviati:
            processo.kill()
            processo.wait(timeout=30)

    assert uscito, (
        f"il daemon di prima e' ancora vivo 30 s dopo l'avvio del nuovo; il file "
        f"vecchio annuncia il pid {annunciato} (vecchio {vecchio.pid}, nuovo {nuovo.pid})")
    assert codice_del_vecchio == 0, (
        f"il daemon di prima e' uscito con {codice_del_vecchio}: e' caduto, non ha "
        "fatto il passo indietro")
    assert ancora_vivo, "il daemon nuovo e' uscito insieme al vecchio"
    assert annunciato == nuovo.pid
