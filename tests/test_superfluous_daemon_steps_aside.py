"""Un daemon che non serve piu' nessuno non deve tenere 2 GB per otto ore.

MISURATO IL 25/07 sulla macchina reale: due daemon vivi, 1933 MB e 1912 MB, e
un solo file di discovery. Il non annunciato non riceve nessuna richiesta —
nessun client sa che esiste — ma resta in RAM fino all'idle timeout di 8 ore.
Il lock impedisce due daemon all'AVVIO; non c'e' niente che li riduca a uno se
ci arrivano dopo, e ci si arriva: il lock viene ceduto quando il proprietario
sembra incastrato, e cambiando modello di embedding il daemon vecchio risponde
ancora ma serve il modello sbagliato.

COME, E PERCHE' NON ALTRIMENTI. Due varianti erano sul tavolo: uscire subito,
oppure abbassare l'idle timeout e lasciare che sia la via d'uscita gia'
esistente a occuparsene. Due revisioni avversarie indipendenti hanno bocciato
la prima con lo stesso controesempio: durante il passaggio di consegne
entrambi i daemon possono leggere un file che nomina l'altro e uscire tutti e
due, lasciando la macchina senza daemon; e se il vincitore muore subito dopo,
chi e' gia' uscito non c'e' piu' per subentrare. Abbassare l'idle non ha
nessuno dei due difetti: e' reversibile a ogni giro di controllo, e un daemon
ancora usato da qualche client con la porta in cache semplicemente non viene
mai dichiarato inattivo — che e' la risposta giusta, non un'eccezione.

Il secondo test qui sotto riguarda un difetto diverso trovato sulla stessa
riga: ``ENGRAM_ENCODE_IDLE_S=0``, che la documentazione del modulo descrive
come "never idle-exit / permanent daemon", faceva uscire il daemon dopo un
secondo. Misurato prima di scrivere il test.
"""
from __future__ import annotations

import json
import os
import socket
import threading
import time
from contextlib import contextmanager

import pytest

from verimem import encode_service


def _fake_encode(text):
    return [float(len(text)), 1.5, -2.0]


@contextmanager
def _porta_in_ascolto():
    """Un daemon FINTO ma che RISPONDE al ping riflettendo il nonce.

    Fino al 26/07 bastava una porta nuda: l'arbitraggio verificava la
    raggiungibilita', non l'identita' di chi ascolta. Dal 27/07 (health
    probe) chiede la salute — una porta muta ora rappresenta un daemon
    WEDGED, che e' il caso opposto — quindi il fake deve parlare il
    protocollo per impersonare un daemon vivo."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    stop = threading.Event()
    try:
        sock.bind(("127.0.0.1", 0))
        sock.listen(8)

        def _rispondi():
            sock.settimeout(0.1)
            while not stop.is_set():
                try:
                    c, _ = sock.accept()
                except OSError:
                    continue
                try:
                    req = encode_service.recv_msg(c)
                    encode_service.send_msg(c, {
                        "ok": True, "model": "altro-daemon", "dim": 3,
                        "pid": 424242, "nonce": (req or {}).get("nonce")})
                except OSError:
                    pass
                finally:
                    c.close()

        threading.Thread(target=_rispondi, daemon=True).start()
        yield sock.getsockname()[1]
    finally:
        stop.set()
        sock.close()


@pytest.fixture()
def srv(tmp_path):
    s = encode_service.EncodeServer(
        encode_fn=_fake_encode, idle_timeout_s=8 * 3600,
        discovery_path=tmp_path / "encode_service.json", model_name="test-model")
    s.start()
    try:
        yield s, tmp_path / "encode_service.json"
    finally:
        s.stop()


def _annuncia_altro(path, porta):
    path.write_text(json.dumps({
        "pid": os.getpid() + 100000, "port": porta, "host": "127.0.0.1",
        "model": "test-model", "dim": 3, "token": "x",
    }), encoding="utf-8")


def test_the_announced_daemon_keeps_the_long_idle(srv):
    """Chi e' annunciato sta servendo: niente cambia per lui."""
    s, path = srv
    s._republish_discovery_if_unclaimed()
    assert s._effective_idle_timeout() == 8 * 3600


def test_a_daemon_that_is_not_the_announced_one_shortens_its_idle(srv):
    """Il caso misurato: un altro daemon e' annunciato e risponde, quindi
    nessun client cerchera' mai me. Restare otto ore costa 2 GB per niente."""
    s, path = srv
    with _porta_in_ascolto() as porta:
        _annuncia_altro(path, porta)
        s._republish_discovery_if_unclaimed()
        assert s._effective_idle_timeout() < 8 * 3600, (
            "un daemon che nessuno puo' trovare aspetta otto ore con il "
            "modello in RAM")


def test_an_announcer_that_does_not_answer_leaves_me_useful(srv):
    """Il file nomina un daemon SCOMPARSO: non c'e' nessun altro che serva, e
    infatti me lo riprendo. Ritirarmi qui vorrebbe dire lasciare la macchina
    senza daemon."""
    s, path = srv
    _annuncia_altro(path, 1)          # porta morta
    s._republish_discovery_if_unclaimed()
    s._republish_discovery_if_unclaimed()   # la seconda osservazione lo assegna
    assert s._effective_idle_timeout() == 8 * 3600


def test_becoming_the_announced_one_again_restores_the_long_idle(srv):
    """Reversibile a ogni giro: e' la proprieta' che ha fatto scartare l'uscita
    immediata. Se il vincitore sparisce, chi si era fatto da parte torna utile
    senza che nessuno debba riavviarlo."""
    s, path = srv
    with _porta_in_ascolto() as porta:
        _annuncia_altro(path, porta)
        s._republish_discovery_if_unclaimed()
        assert s._effective_idle_timeout() < 8 * 3600
    # fuori dal with la porta e' chiusa: l'altro non c'e' piu'
    s._republish_discovery_if_unclaimed()
    s._republish_discovery_if_unclaimed()
    assert s._effective_idle_timeout() == 8 * 3600, (
        "il daemon e' rimasto in ritirata dopo che l'altro e' sparito")


def test_a_superfluous_daemon_actually_exits(tmp_path, monkeypatch):
    """Il flag non basta: quello che conta e' che la RAM torni indietro. Qui il
    loop gira davvero e deve terminare da solo."""
    monkeypatch.setattr(encode_service, "_SUPERFLUOUS_IDLE_S", 0.5)
    monkeypatch.setattr(encode_service, "_DISCOVERY_CHECK_INTERVAL_S", 0.0)
    path = tmp_path / "encode_service.json"
    s = encode_service.EncodeServer(
        encode_fn=_fake_encode, idle_timeout_s=8 * 3600,
        discovery_path=path, model_name="test-model")
    s.start()
    with _porta_in_ascolto() as porta:
        _annuncia_altro(path, porta)
        t = threading.Thread(target=s.serve_forever, daemon=True)
        t.start()
        t.join(timeout=15)
        vivo = t.is_alive()
    s.stop()
    assert not vivo, (
        "il daemon superfluo non e' uscito: la RAM resta occupata fino alle "
        "otto ore")


def test_the_announced_daemon_does_not_exit(tmp_path, monkeypatch):
    """Il controllo che il test qui sopra non stia misurando 'esce sempre'."""
    monkeypatch.setattr(encode_service, "_SUPERFLUOUS_IDLE_S", 0.5)
    monkeypatch.setattr(encode_service, "_DISCOVERY_CHECK_INTERVAL_S", 0.0)
    path = tmp_path / "encode_service.json"
    s = encode_service.EncodeServer(
        encode_fn=_fake_encode, idle_timeout_s=8 * 3600,
        discovery_path=path, model_name="test-model")
    s.start()
    t = threading.Thread(target=s.serve_forever, daemon=True)
    t.start()
    try:
        t.join(timeout=4)
        assert t.is_alive(), "il daemon ANNUNCIATO e' uscito: sta servendo"
    finally:
        s.stop()
        t.join(timeout=3)


def test_zero_means_permanent_as_the_module_documents(tmp_path):
    """``ENGRAM_ENCODE_IDLE_S=0`` e' documentato come "never idle-exit /
    permanent daemon". Faceva uscire il daemon dopo 1,0 s — misurato — perche'
    la condizione era ``idle > timeout`` e ogni durata e' maggiore di zero.
    Chi lo imposta per avere un daemon permanente otteneva l'opposto."""
    s = encode_service.EncodeServer(
        encode_fn=_fake_encode, idle_timeout_s=0,
        discovery_path=tmp_path / "encode_service.json", model_name="test-model")
    s.start()
    t = threading.Thread(target=s.serve_forever, daemon=True)
    t.start()
    try:
        t.join(timeout=4)
        assert t.is_alive(), (
            "con idle timeout 0, documentato come permanente, il daemon e' "
            "uscito da solo")
    finally:
        s.stop()
        t.join(timeout=3)


def test_a_freshly_demoted_daemon_stays_as_a_warm_standby(srv):
    """Il conto non parte solo dall'ultima richiesta, ma anche dalla
    retrocessione. Prezzo del caso, da una revisione avversaria: retrocesso
    mentre era gia' inattivo da 59 s, uscirebbe un secondo dopo — e se il
    vincitore muore in quella finestra non resta nessuno a riprendersi il file,
    trasformando 4 s di recupero in 26 s di cold-load per il client successivo.

    Piu' un daemon era inattivo, piu' in fretta sparirebbe: esattamente al
    contrario di quel che serve, perche' un daemon inattivo e' lo standby che
    costa meno tenere."""
    s, path = srv
    s._last_request = time.time() - 10 * 3600      # inattivo da ore
    with _porta_in_ascolto() as porta:
        _annuncia_altro(path, porta)
        s._republish_discovery_if_unclaimed()
        assert not s._should_idle_exit(), (
            "il daemon appena retrocesso se n'e' andato subito: lo standby "
            "caldo sparisce proprio quando potrebbe servire da ripiego")

        # passato il tempo di standby, e sempre inattivo, se ne va
        s._superfluous_since -= s._effective_idle_timeout() + 1
        assert s._should_idle_exit()


def test_a_permanent_daemon_still_steps_aside_when_unreachable(tmp_path):
    """"Permanente" e' una promessa sul daemon che SERVE, non su ogni processo
    residuo che nessuno puo' raggiungere.

    Due revisioni avversarie indipendenti hanno indicato questo come il caso
    peggiore, e l'argomento che decide non e' la frequenza ma la monotonia:
    senza nessuno che li raccolga, ogni cessione spuria del lock aggiunge
    qualche GB che non torna piu', fino all'OOM. Il daemon ANNUNCIATO con
    idle 0 continua a non uscire mai — vedi il test qui sotto."""
    path = tmp_path / "encode_service.json"
    s = encode_service.EncodeServer(
        encode_fn=_fake_encode, idle_timeout_s=0,      # "permanente"
        discovery_path=path, model_name="test-model")
    s.start()
    try:
        with _porta_in_ascolto() as porta:
            _annuncia_altro(path, porta)
            s._republish_discovery_if_unclaimed()
            assert s._effective_idle_timeout() == encode_service._SUPERFLUOUS_IDLE_S
            s._last_request = time.time() - 10 * 3600
            s._superfluous_since -= encode_service._SUPERFLUOUS_IDLE_S + 1
            assert s._should_idle_exit(), (
                "un daemon irraggiungibile configurato permanente resta per "
                "sempre: la RAM si accumula a ogni cessione del lock e nessuno "
                "la raccoglie")
    finally:
        s.stop()


def test_a_restarted_daemon_does_not_stay_in_retreat(tmp_path):
    """Riavviare il server nello stesso processo — che ``acquire_daemon_lock``
    dichiara di sostenere, "our own pid is re-entrant" — riscrive il discovery
    col proprio pid ma non azzera nulla di quel che il server pensava prima.

    Scritto perche' la mutazione che toglie il riconoscimento del proprio pid
    NON veniva rilevata da nessun altro test: tutti gli altri percorsi che
    tornano utili passano da altri rami, che il flag lo azzerano gia'. Questo
    e' l'unico modo di arrivarci restando superflui, e senza il ramo il daemon
    uscirebbe dopo un minuto pur essendo rimasto l'unico."""
    path = tmp_path / "encode_service.json"
    s = encode_service.EncodeServer(
        encode_fn=_fake_encode, idle_timeout_s=8 * 3600,
        discovery_path=path, model_name="test-model")
    s.start()
    with _porta_in_ascolto() as porta:
        _annuncia_altro(path, porta)
        s._republish_discovery_if_unclaimed()
        assert s._superfluous, "presupposto del test: si e' fatto da parte"

    s.stop()
    s.start()          # riavvio: il discovery torna a nominare noi
    try:
        s._republish_discovery_if_unclaimed()
        assert s._effective_idle_timeout() == 8 * 3600, (
            "il daemon riavviato e' rimasto in ritirata: esce dopo un minuto "
            "pur essendo l'unico rimasto")
    finally:
        s.stop()


def test_a_short_configured_idle_is_not_lengthened(srv):
    """Chi ha configurato un idle piu' corto della soglia di ritirata non deve
    vederselo allungare proprio quando il daemon e' diventato inutile."""
    s, path = srv
    s._idle_timeout_s = 5.0
    with _porta_in_ascolto() as porta:
        _annuncia_altro(path, porta)
        s._republish_discovery_if_unclaimed()
        assert s._effective_idle_timeout() == 5.0
