"""Un daemon VIVO ma che non serve non deve bloccare il daemon di encode.

Perche' questo file esiste (misurato sulla macchina reale il 25/07). Il PID
51776 — ``pythonw -m verimem.encode_service``, avviato alle 15:56, 322 MB di
RAM, cioe' il modello mai caricato — era vivo e possedeva il lock senza aver
mai scritto il file di discovery. ``acquire_daemon_lock`` guarda se il
proprietario e' VIVO, non se sta SERVENDO: ogni daemon successivo (misurato:
PID 45668 alle 17:36) trovava il lock occupato e usciva in silenzio. Risultato:
nessun daemon ha mai servito, ogni client ricadeva sul cold-load in-process
(26 s misurati) contro un budget di 2 s, e il recall degradava a ricerca per
parole chiave — restituendo risultati senza dichiarare il degrado, che e'
l'opposto di cio' che questo prodotto vende.

La catena era muta in tre punti: ``_spawn_detached`` manda stderr su DEVNULL,
``ensure_running`` restituisce False sia che abbia spawnato sia che abbia
fallito, e il client non dice al chiamante che sta rispondendo in modalita'
degradata. Questo file copre il primo anello, quello che rende permanente il
guasto: il lock.

Il criterio non e' "da quanto vive il proprietario" ma "si e' annunciato?".
Un daemon appena partito ha diritto al suo warmup (~20-30 s) senza che nessuno
gli rubi il lock; passata la grazia senza un discovery raggiungibile, e' uno
zombie e il lock va preso.
"""
from __future__ import annotations

import json
import os
import time

import pytest

from verimem import encode_service as svc


@pytest.fixture()
def lock(tmp_path):
    return tmp_path / "daemon.lock"


def _scrivi_lock(path, pid: int, *, eta_s: float = 0.0) -> None:
    path.write_text(str(pid), encoding="utf-8")
    if eta_s:
        vecchio = time.time() - eta_s
        os.utime(path, (vecchio, vecchio))


def test_a_dead_owner_lock_is_stolen(lock, monkeypatch):
    """Regressione del comportamento storico: un proprietario morto non
    trattiene niente."""
    monkeypatch.setattr(svc, "_pid_alive", lambda pid: False)
    _scrivi_lock(lock, 999999)
    assert svc.acquire_daemon_lock(lock) is True


def test_a_live_serving_owner_keeps_the_lock(lock, monkeypatch):
    """Il caso che NON deve rompersi: un daemon sano — vivo e che si e'
    annunciato — resta l'unico a servire. Senza questo, la cura allo zombie
    aprirebbe la porta a due daemon che caricano il modello insieme."""
    monkeypatch.setattr(svc, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(svc, "daemon_usable", lambda *a, **k: True)
    _scrivi_lock(lock, 4242, eta_s=3600)          # vecchio ma SANO
    assert svc.acquire_daemon_lock(lock) is False


def test_a_warming_owner_is_given_its_grace(lock, monkeypatch):
    """Un daemon appena partito non si e' ancora annunciato perche' sta
    caricando il modello: rubargli il lock creerebbe la corsa a due daemon che
    il lock esiste per impedire."""
    monkeypatch.setattr(svc, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(svc, "daemon_usable", lambda *a, **k: False)
    _scrivi_lock(lock, 4242, eta_s=1.0)           # dentro la grazia
    assert svc.acquire_daemon_lock(lock) is False


def test_a_live_owner_that_never_announced_is_a_zombie(lock, monkeypatch):
    """Il caso misurato: vivo, oltre la grazia, e nessun discovery. Prima di
    questo fix bloccava ogni daemon futuro per sempre e il recall restava
    degradato a keyword-search senza dirlo a nessuno."""
    monkeypatch.setattr(svc, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(svc, "daemon_usable", lambda *a, **k: False)
    _scrivi_lock(lock, 4242, eta_s=svc._ZOMBIE_GRACE_S + 30)   # noqa: SLF001
    assert svc.acquire_daemon_lock(lock) is True, (
        "un daemon vivo che non ha mai servito trattiene il lock: nessun "
        "daemon potra' partire e ogni recall restera' degradato")


def test_the_grace_covers_a_first_download_not_just_a_warm_cache_load():
    """La grazia deve coprire il caso lento VERO, che non e' il cold-load a
    cache calda (26-34 s) ma il PRIMO avvio, quando il daemon deve SCARICARE il
    modello (~1 GB).

    Questo test nasce da un controesempio del critic gate, che ha mostrato una
    regressione introdotta dal fix stesso: con la grazia a 120 s, a t=180 s di
    un download in corso un altro processo vedeva "vivo, oltre la grazia, non
    serve" e rubava il lock a un daemon sano, facendo caricare il modello a due
    processi insieme — l'invariante che il lock esiste per garantire. Il lock e'
    scritto una volta sola e mai rinfrescato, quindi durante un load lungo la
    sua eta' cresce senza limite."""
    assert svc._ZOMBIE_GRACE_S >= 300, (           # noqa: SLF001
        f"grazia {svc._ZOMBIE_GRACE_S}s: copre un load a cache calda ma non un "
        "primo download, quindi ruberebbe il lock a un daemon sano e lento")


def test_a_clock_jump_backwards_does_not_grant_an_endless_grace(lock, monkeypatch):
    """Un salto d'orologio all'indietro (NTP) rende l'mtime FUTURO e l'eta'
    negativa: con un confronto ingenuo ``eta <= grazia`` lo zombie resterebbe
    per sempre "in warmup" e non verrebbe mai sostituito. Sollevato da due
    revisioni indipendenti; il caso gemello che invocavano — uno zombie che si
    tiene giovane riscrivendo il lock — oggi non esiste, perche' il lock viene
    scritto una sola volta all'acquisizione e mai piu'."""
    monkeypatch.setattr(svc, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(svc, "daemon_usable", lambda *a, **k: False)
    _scrivi_lock(lock, 4242, eta_s=-3600)          # mtime un'ora nel FUTURO
    assert svc.acquire_daemon_lock(lock) is True, (
        "un mtime nel futuro concede una grazia infinita: lo zombie diventa "
        "permanente al primo salto di orologio")


def test_stealing_uses_a_patient_probe(lock, monkeypatch):
    """Prima di RUBARE, il probe deve essere piu' paziente del probe informativo
    di default (0.4 s). Le due revisioni sostenevano che un daemon sano ma
    occupato fallisca il probe e venga derubato: il presupposto e' sbagliato
    (``is_reachable`` fa solo connect+close e il server ha ``listen(16)``, quindi
    su loopback il kernel accetta anche senza ``accept()`` applicativo), ma
    l'ASIMMETRIA del costo resta — sbagliare qui significa due daemon col
    modello in RAM. Dove sbagliare costa caro si aspetta di piu'."""
    visti: list[float] = []

    def _spia(info=None, timeout=0.4):
        visti.append(timeout)
        return False

    monkeypatch.setattr(svc, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(svc, "daemon_usable", _spia)
    _scrivi_lock(lock, 4242, eta_s=svc._ZOMBIE_GRACE_S + 30)   # noqa: SLF001
    svc.acquire_daemon_lock(lock)
    assert visti, "il probe non e' stato nemmeno eseguito"
    assert max(visti) >= 2.0, (
        f"il furto si decide con un probe da {max(visti)}s: troppo impaziente "
        "per una decisione il cui errore costa due daemon")


def test_an_unreadable_lock_is_not_a_deadlock(lock, monkeypatch):
    """Entrambe le revisioni temevano che "in dubbio non si ruba" bloccasse la
    macchina se il lock diventa illeggibile. Non e' cosi', e va tenuto vero: un
    contenuto illeggibile da' owner=0, che non e' un proprietario vivo, quindi
    il lock viene preso."""
    monkeypatch.setattr(svc, "_pid_alive", lambda pid: True)
    lock.write_text("non-un-pid", encoding="utf-8")
    assert svc.acquire_daemon_lock(lock) is True


def test_an_unreadable_discovery_does_not_make_a_healthy_daemon_a_zombie(
        lock, monkeypatch, tmp_path):
    """Il giudizio deve venire da ``daemon_usable`` (raggiungibile E modello
    giusto), non dalla sola presenza del file: un discovery scritto a meta' o
    di un daemon con un altro modello non e' un daemon che serve."""
    monkeypatch.setattr(svc, "_pid_alive", lambda pid: True)
    disc = tmp_path / "discovery.json"
    disc.write_text(json.dumps({"port": 1, "model": "altro-modello"}),
                    encoding="utf-8")
    monkeypatch.setattr(svc, "DISCOVERY_PATH", disc)
    _scrivi_lock(lock, 4242, eta_s=svc._ZOMBIE_GRACE_S + 30)   # noqa: SLF001
    assert svc.acquire_daemon_lock(lock) is True, (
        "un daemon che annuncia un ALTRO modello non sta servendo questo "
        "corpus: il client lo rifiuta, quindi non deve trattenere il lock")
