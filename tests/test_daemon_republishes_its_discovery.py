"""Un daemon vivo a cui sparisce il discovery deve riannunciarsi.

RESIDUO OSSERVATO IL 25/07, dopo aver curato ``ensure_running`` perche' non
cancellasse il file di un daemon sano: sotto il carico di una full suite il
probe da 2 s e' stato mancato lo stesso, il file e' stato rimosso e un daemon
da ~2 GB e' rimasto orfano — vivo, con il modello in RAM, e invisibile a
chiunque fino all'idle timeout di 8 ore.

Il fix precedente riduce la finestra, non la chiude, e non puo' chiuderla: si
puo' sempre allungare il probe e trovare un carico che lo superi. Il difetto
di fondo e' un altro, ed e' asimmetrico: il discovery viene scritto UNA VOLTA
all'avvio, mentre chiunque puo' cancellarlo in qualsiasi momento. Un fatto che
un solo lato puo' distruggere e nessuno puo' ricostruire non e' recuperabile.

La cura sta dalla parte di chi sa la verita': il daemon e' l'unico che sa di
essere vivo e su quale porta, quindi e' lui a doversi riannunciare quando si
accorge che nessuno lo annuncia piu'. Cosi' la finestra si chiude da sola in
pochi secondi invece di durare ore, qualunque sia stata la causa della
cancellazione — probe mancato, pulizia manuale, un altro processo.

CONFINE DELIBERATO: si riscrive solo un discovery **assente**. Se il file c'e'
ed e' di un ALTRO daemon non si tocca — due daemon che si riscrivono a vicenda
sarebbero un flip-flop peggiore del problema di partenza, e chi ha il file ha
gia' vinto la corsa. Vedi ``test_another_daemons_discovery_is_left_alone``.
"""
from __future__ import annotations

import json
import os
import threading
import time

import pytest

from verimem import encode_service


def _fake_encode(text):
    return [float(len(text)), 1.5, -2.0]


def _wait_for(pred, timeout: float = 6.0, step: float = 0.05) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(step)
    return False


def _pid_dichiarato(path) -> int | None:
    """Il pid annunciato dal file, o None se il file non annuncia nessuno.

    Serve un helper esplicito perche' i casi da attendere includono un file
    ASSENTE e uno CORROTTO: un predicato che leggesse e basta solleverebbe, e
    l'attesa fallirebbe con un errore invece di riprovare.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data.get("pid") if isinstance(data, dict) else None


@pytest.fixture()
def running(tmp_path, monkeypatch):
    """Un daemon vero, in ascolto, con il loop attivo — non un finto.

    L'intervallo di controllo va azzerato: in produzione e' di qualche secondo
    per non fare I/O inutile, e un test che lo aspettasse davvero sarebbe lento
    senza misurare niente di piu'.
    """
    monkeypatch.setattr(encode_service, "_DISCOVERY_CHECK_INTERVAL_S", 0.0)
    path = tmp_path / "encode_service.json"
    srv = encode_service.EncodeServer(
        encode_fn=_fake_encode,
        idle_timeout_s=30,
        discovery_path=path,
        model_name="test-model",
    )
    srv.start()
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield srv, path
    finally:
        srv.stop()
        thread.join(timeout=3)


def test_a_deleted_discovery_is_republished(running):
    """Il caso misurato: qualcuno cancella il file mentre il daemon sta bene."""
    srv, path = running
    assert path.exists(), "il daemon non ha annunciato se stesso all'avvio"
    before = json.loads(path.read_text(encoding="utf-8"))

    path.unlink()  # esattamente cio' che ensure_running fa quando manca il probe

    assert _wait_for(path.exists), (
        "il discovery cancellato non e' stato riscritto: un daemon vivo, con il "
        "modello in RAM, resta invisibile a ogni client fino all'idle timeout")
    after = json.loads(path.read_text(encoding="utf-8"))
    assert after["port"] == before["port"]
    assert after["pid"] == before["pid"] == os.getpid()


def test_the_republished_file_still_authenticates_the_same_clients(running):
    """Il token e' per-boot, non per-file: riscriverlo con un token nuovo
    scaricherebbe i client che avevano gia' letto il vecchio, trasformando una
    cura in un'interruzione."""
    srv, path = running
    before = json.loads(path.read_text(encoding="utf-8"))
    path.unlink()
    assert _wait_for(path.exists)
    after = json.loads(path.read_text(encoding="utf-8"))
    assert after["token"] == before["token"], (
        "la ripubblicazione ha cambiato il token: i client che lo avevano gia' "
        "letto vengono rifiutati con 'unauthorized'")
    assert after["model"] == before["model"]
    assert after["dim"] == before["dim"]


def test_another_daemons_discovery_is_left_alone(running):
    """Il confine: se il file c'e' ed e' di un altro, chi lo ha scritto ha
    vinto la corsa. Sovrascriverlo farebbe rimbalzare i client fra due porte."""
    srv, path = running
    altrui = {
        "pid": os.getpid() + 100000, "port": 1, "host": "127.0.0.1",
        "model": "un-altro", "dim": 4, "started_at": time.time(), "token": "x",
    }
    path.write_text(json.dumps(altrui), encoding="utf-8")

    # abbastanza giri del loop perche' l'avrebbe gia' sovrascritto se volesse
    time.sleep(2.5)
    assert json.loads(path.read_text(encoding="utf-8"))["pid"] == altrui["pid"], (
        "il daemon ha sovrascritto il discovery di un altro: due daemon vivi si "
        "rincorrono a vicenda e i client rimbalzano fra due porte")


def test_a_discovery_that_claims_nobody_is_taken_over(running):
    """Un file illeggibile non e' di nessuno: non identifica un proprietario da
    rispettare, e lasciarlo li' costerebbe a ogni client una connect fallita.
    Chi e' vivo e sa la propria porta se lo prende."""
    srv, path = running
    path.write_text("{ questo non e' json", encoding="utf-8")
    assert _wait_for(lambda: _pid_dichiarato(path) == os.getpid()), (
        "un discovery corrotto e' rimasto corrotto con un daemon vivo a fianco")


def test_a_file_being_written_right_now_is_not_stolen(tmp_path):
    """La race che ha fatto fallire ``test_another_daemons_discovery_is_left_alone``
    una volta su cinque, a seconda dell'ordine dei test: chi scrive senza
    rename atomico passa per uno stato in cui il file esiste ma e' vuoto, e un
    lettore che capitasse li' concluderebbe 'non e' di nessuno' e lo prenderebbe
    — sovrascrivendo il daemon che stava nascendo.

    Deterministico di proposito: niente thread, niente attese. Si chiama il
    controllo due volte a mano, come farebbero due giri del loop, con il file
    che nel frattempo finisce di essere scritto."""
    path = tmp_path / "encode_service.json"
    srv = encode_service.EncodeServer(
        encode_fn=_fake_encode, discovery_path=path, model_name="test-model")

    path.write_text("", encoding="utf-8")     # scrittura a meta'
    srv._republish_discovery_if_unclaimed()
    assert path.read_text(encoding="utf-8") == "", (
        "un file vuoto per un istante e' stato preso al primo sguardo")

    altrui = {"pid": os.getpid() + 100000, "port": 1, "host": "127.0.0.1"}
    path.write_text(json.dumps(altrui), encoding="utf-8")   # scrittura finita
    srv._republish_discovery_if_unclaimed()
    assert _pid_dichiarato(path) == altrui["pid"], (
        "il secondo sguardo ha visto un file valido e lo ha preso lo stesso")


def test_a_stably_unclaimed_file_is_taken_on_the_second_look(tmp_path):
    """L'altro lato della pazienza: se il file resta illeggibile non e' una
    scrittura in corso, e allora va preso — altrimenti la cura non curerebbe."""
    path = tmp_path / "encode_service.json"
    srv = encode_service.EncodeServer(
        encode_fn=_fake_encode, discovery_path=path, model_name="test-model")

    path.write_text("{ rotto", encoding="utf-8")
    srv._republish_discovery_if_unclaimed()
    assert _pid_dichiarato(path) is None, "preso al primo sguardo"
    srv._republish_discovery_if_unclaimed()
    assert _pid_dichiarato(path) == os.getpid(), (
        "un file stabilmente illeggibile non e' stato preso nemmeno al secondo "
        "sguardo: il daemon resta invisibile")


def test_a_missing_file_is_taken_at_once(tmp_path):
    """Il caso vero — quello misurato in produzione — non paga la pazienza:
    la cancellazione e' atomica e il lock garantisce un solo daemon, quindi non
    c'e' nessuna ambiguita' da attendere. Ogni giro in piu' sarebbe tempo in cui
    ogni client paga il cold-load da 26 s."""
    path = tmp_path / "encode_service.json"
    srv = encode_service.EncodeServer(
        encode_fn=_fake_encode, discovery_path=path, model_name="test-model")
    srv.start()
    try:
        path.unlink()
        srv._republish_discovery_if_unclaimed()
        assert _pid_dichiarato(path) == os.getpid(), (
            "un file ASSENTE ha aspettato un secondo giro")
    finally:
        srv.stop()


def test_the_daemon_does_not_rewrite_its_own_file_every_pass(running, monkeypatch):
    """Il controllo e' una lettura, non una scrittura: finche' il file e' suo e
    sta bene non si tocca. Riscriverlo a ogni giro sarebbe I/O inutile su un
    file che i client leggono, e per giunta con una finestra di rename in cui
    non esiste."""
    srv, path = running
    scritture = []
    vero = encode_service.EncodeServer._write_discovery
    monkeypatch.setattr(
        encode_service.EncodeServer, "_write_discovery",
        lambda self: (scritture.append(1), vero(self))[1])

    time.sleep(2.5)  # diversi giri del loop, con l'intervallo azzerato
    assert not scritture, (
        f"il daemon ha riscritto il proprio discovery {len(scritture)} volte "
        "pur essendo gia' pubblicato correttamente")
