"""Il discovery di un daemon VIVO non va cancellato.

Trovato guardando lo stato reale della macchina il 25/07, dopo aver curato il
lock: tre daemon vivi, uno dei quali (PID 40616) con **1385 MB residenti**,
cioe' il modello caricato, proprietario del lock — e NESSUN file di discovery.
Un daemon sano, con il modello in RAM, che nessun client poteva trovare, e che
sarebbe rimasto cosi' a occupare 1,4 GB fino all'idle-timeout di 8 ore.

La causa e' in ``ensure_running``: quando ``daemon_usable()`` risponde False il
file viene rimosso, con la motivazione — giusta — di non lasciare i client a
sbattere contro la porta di un daemon morto. Ma ``daemon_usable`` ha un probe
con timeout, quindi risponde False anche per un daemon VIVO che in quel momento
non ha risposto in tempo, e allora la rimozione rende invisibile un daemon sano.
E' la classe di difetto che due revisioni esterne avevano indicato per il furto
del lock (un probe impaziente che sbaglia sotto carico); li' l'obiezione non
reggeva, qui la conseguenza e' peggiore: il furto crea un secondo daemon, la
cancellazione ne nasconde uno funzionante.

Il file dichiara il ``pid`` di chi lo ha scritto, quindi la domanda si puo'
porre esattamente: si rimuove il discovery di un proprietario MORTO, non quello
di uno vivo.
"""
from __future__ import annotations

import json
import os

import pytest

from verimem import encode_service as svc


@pytest.fixture()
def discovery(tmp_path, monkeypatch):
    p = tmp_path / "encode_service.json"
    # Il conftest disabilita il servizio di encode per tutta la suite, e con
    # ENGRAM_ENCODE_SERVICE=0 ensure_running esce alla prima riga senza toccare
    # niente: i test qui sotto passerebbero tutti per il motivo sbagliato. Va
    # riabilitato per misurare il comportamento vero.
    monkeypatch.delenv("ENGRAM_ENCODE_SERVICE", raising=False)
    monkeypatch.setattr(svc, "DISCOVERY_PATH", p)
    monkeypatch.setattr(svc, "_SPAWN_LOCK_PATH", tmp_path / "spawn.lock")
    monkeypatch.setattr(svc, "_spawn_detached", lambda: None)   # niente processi
    monkeypatch.setattr(svc, "daemon_usable", lambda *a, **k: False)
    return p


def _scrivi(p, pid: int | None) -> None:
    info = {"port": 1234, "host": "127.0.0.1", "model": "m", "dim": 8}
    if pid is not None:
        info["pid"] = pid
    p.write_text(json.dumps(info), encoding="utf-8")


def test_a_live_owners_discovery_survives(discovery, monkeypatch):
    """Il caso misurato: il daemon e' vivo e ha il modello caricato, ha solo
    mancato un probe. Cancellargli il discovery lo rende irraggiungibile per
    tutti, e nessuno se ne accorge."""
    monkeypatch.setattr(svc, "_pid_alive", lambda pid: True)
    _scrivi(discovery, 4242)
    svc.ensure_running()
    assert discovery.exists(), (
        "il discovery di un daemon VIVO e' stato cancellato: un daemon sano con "
        "il modello in RAM diventa invisibile a tutti i client")


def test_a_dead_owners_discovery_is_removed(discovery, monkeypatch):
    """La ragione per cui la rimozione esiste, e che deve restare: senza,
    i client continuerebbero a fallire contro la porta di un daemon morto."""
    monkeypatch.setattr(svc, "_pid_alive", lambda pid: False)
    _scrivi(discovery, 4242)
    svc.ensure_running()
    assert not discovery.exists(), (
        "il discovery di un daemon MORTO non e' stato rimosso: i client "
        "continuano a sbattere contro una porta chiusa")


def test_a_discovery_without_a_pid_is_removed(discovery, monkeypatch):
    """Fail-safe: un file che non dice chi lo ha scritto — vecchio formato o
    scrittura troncata — non puo' essere difeso, quindi si rimuove come prima."""
    monkeypatch.setattr(svc, "_pid_alive", lambda pid: True)
    _scrivi(discovery, None)
    svc.ensure_running()
    assert not discovery.exists()


def test_an_unparseable_discovery_is_removed(discovery, monkeypatch):
    """Stessa ragione: se non si riesce a leggere chi lo possiede, non lo si
    puo' proteggere."""
    monkeypatch.setattr(svc, "_pid_alive", lambda pid: True)
    discovery.write_text("{non json", encoding="utf-8")
    svc.ensure_running()
    assert not discovery.exists()


def test_the_service_disabled_switch_still_short_circuits(discovery, monkeypatch):
    """ENGRAM_ENCODE_SERVICE=0 esce prima di toccare qualsiasi cosa. E' anche il
    controllo che il fixture qui sopra sia necessario: e' proprio questo
    cortocircuito che, lasciato attivo dal conftest, faceva passare gli altri
    test senza che eseguissero il codice in esame."""
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "0")
    monkeypatch.setattr(svc, "_pid_alive", lambda pid: False)
    _scrivi(discovery, 4242)
    assert svc.ensure_running() is False
    assert discovery.exists(), "con il servizio disabilitato non si tocca nulla"
