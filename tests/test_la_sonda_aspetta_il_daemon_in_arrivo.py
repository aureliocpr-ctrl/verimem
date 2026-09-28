"""Un daemon che sta partendo si aspetta: non si carica il giudice in casa.

MISURATO il 2026-09-25 all'avvio della macchina (moduli caricati da ciascun
processo): degli 11 server MCP, 10 senza torch a 354-359 MB, e UNO — nato 7 s
dopo il daemon condiviso — con torch e il giudice, 2474 MB, per tutta la sua
vita. Quel server non ha fatto nessuna chiamata (log di audit): il giudice l'ha
caricato il precarico, perche' la sonda smetteva di aspettare dopo 25 s mentre
il daemon teneva il lock e stava ancora caricando.

La promessa di #132 (T203) e' «il server non carica il giudice se il daemon sa
giudicare»: un daemon che sta per saperlo fare va aspettato.

QUESTO FILE NON CARICA NESSUN MODELLO: il giudice e' finto (conta le chiamate a
`_ensure_scorer`) e il tempo e' un orologio finto, cosi' un'attesa di dieci
minuti dura zero secondi veri.
"""

from __future__ import annotations

import socket

import pytest

from verimem import encode_service, local_grounding, preload


class _GiudiceFinto:
    def __init__(self):
        self.caricamenti = 0

    def _ensure_scorer(self):
        self.caricamenti += 1


class _Orologio:
    """Il tempo di `preload`: `sleep` fa avanzare `time`, senza aspettare."""

    def __init__(self):
        self.t = 1_000_000.0
        self.partenza = self.t

    def time(self):
        return self.t

    def sleep(self, secondi):
        self.t += secondi

    @property
    def trascorsi(self):
        return self.t - self.partenza


@pytest.fixture
def giudice(monkeypatch, tmp_path):
    # I TRE alias della cartella dati e il log degli eventi: con uno solo
    # isolato, una scrittura finirebbe nello store vero.
    for alias in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(alias, str(tmp_path))
    monkeypatch.setenv("ENGRAM_EVENT_LOG", str(tmp_path / "eventi.jsonl"))
    # Il conftest spegne il servizio per ogni test: senza questa riga la sonda
    # non partirebbe mai e la cella misurerebbe «servizio spento».
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "1")
    # I 25 s dell'embedder: qui zero, e' il tempo DOPO che la cella misura.
    monkeypatch.setattr(preload, "_DAEMON_WARM_WAIT_S", 0.0)
    # Il rifiuto e' la risposta all'ultima sonda DI QUESTO THREAD: una cella
    # non deve leggere quello lasciato dalla precedente.
    rifiuto = getattr(local_grounding, "_rifiuto_del_giudice", None)
    if rifiuto is not None:
        monkeypatch.setattr(rifiuto, "motivo", None, raising=False)
    finto = _GiudiceFinto()
    monkeypatch.setattr(local_grounding, "get_local_judge", lambda: finto)
    return finto


@pytest.fixture
def orologio(monkeypatch):
    o = _Orologio()
    monkeypatch.setattr(preload, "time", o)
    return o


def _daemon_in_arrivo(monkeypatch, valore: bool) -> None:
    # raising=False: sul tronco la funzione non esiste e nessuno la chiama.
    monkeypatch.setattr(encode_service, "daemon_in_arrivo",
                        lambda *a, **k: valore, raising=False)


def test_un_daemon_in_arrivo_si_aspetta_invece_di_caricare_in_casa(
        giudice, orologio, monkeypatch):
    """LA CURA. RED sul tronco: dopo l'attesa dell'embedder caricava in casa."""
    risposte = iter([None, None, None, [0.9]])
    monkeypatch.setattr(local_grounding, "_gate_via_daemon",
                        lambda *a, **k: next(risposte))
    _daemon_in_arrivo(monkeypatch, True)

    preload._warm_moat_judge(log=None)

    assert giudice.caricamenti == 0, (
        "il daemon stava partendo e ha giudicato alla quarta sonda, ma il "
        "server si e' caricato il giudice prima: 2474 MB invece di 357")


def test_si_aspetta_fino_alla_grazia_del_daemon_e_non_oltre(
        giudice, orologio, monkeypatch):
    """Un daemon in arrivo che non giudica MAI si aspetta fino alla grazia che il
    daemon stesso si da' per caricare, poi il ripiego. RED sul tronco: non
    aspettava affatto."""
    monkeypatch.setattr(local_grounding, "_gate_via_daemon", lambda *a, **k: None)
    _daemon_in_arrivo(monkeypatch, True)

    preload._warm_moat_judge(log=None)

    grazia = encode_service._ZOMBIE_GRACE_S
    assert giudice.caricamenti == 1, "dopo il tetto il ripiego deve restare"
    assert grazia <= orologio.trascorsi <= grazia + 2, (
        f"attesa di {orologio.trascorsi:.0f} s: il tetto e' la grazia del "
        f"daemon, {grazia:.0f} s")


def test_un_daemon_che_rifiuta_non_si_aspetta(giudice, orologio, monkeypatch):
    """Il daemon RISPONDE «this daemon cannot judge»: non giudichera' mai, e
    aspettarlo lascerebbe le prime scritture senza giudizio per niente. Passa
    dal vero `_gate_via_daemon`, con il socket finto."""

    class _Connessione:
        def settimeout(self, _t):
            pass

        def close(self):
            pass

    monkeypatch.setattr(encode_service, "read_discovery",
                        lambda *a, **k: {"port": 1, "host": "127.0.0.1"})
    monkeypatch.setattr(socket, "create_connection",
                        lambda *a, **k: _Connessione())
    monkeypatch.setattr(encode_service, "send_msg", lambda *a, **k: None)
    monkeypatch.setattr(encode_service, "recv_msg", lambda *a, **k: {
        "ok": False, "error": "this daemon cannot judge"})
    _daemon_in_arrivo(monkeypatch, True)

    preload._warm_moat_judge(log=None)

    assert giudice.caricamenti == 1
    assert orologio.trascorsi < 5, (
        f"aspettato {orologio.trascorsi:.0f} s un daemon che aveva gia' "
        "risposto di no")


def test_senza_un_daemon_in_arrivo_il_ripiego_e_quello_di_prima(
        giudice, orologio, monkeypatch):
    """Nessuno tiene il lock: niente da aspettare, il giudice si carica."""
    monkeypatch.setattr(local_grounding, "_gate_via_daemon", lambda *a, **k: None)
    _daemon_in_arrivo(monkeypatch, False)

    preload._warm_moat_judge(log=None)

    assert giudice.caricamenti == 1
    assert orologio.trascorsi < 5


def test_all_avvio_sincrono_l_attesa_resta_quella_dell_embedder(
        giudice, orologio, monkeypatch):
    """Con `HIPPO_PRELOAD_BACKGROUND=0` l'avvio aspetta il precarico, e il client
    MCP chiude la connessione dopo 30 s: li' non si aspetta la grazia del daemon
    anche se un daemon e' in arrivo."""
    monkeypatch.setenv("HIPPO_EAGER_PRELOAD", "1")
    monkeypatch.setenv("HIPPO_PRELOAD_BACKGROUND", "0")
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    monkeypatch.setenv("HIPPO_RERANK_PRELOAD", "0")
    monkeypatch.setattr(preload, "_scalda_le_librerie_del_giudice",
                        lambda **k: None)
    # l'embedder trova il daemon e torna subito: qui si guarda solo il giudice
    monkeypatch.setattr(encode_service, "daemon_usable", lambda *a, **k: True)
    monkeypatch.setattr(local_grounding, "_gate_via_daemon", lambda *a, **k: None)
    _daemon_in_arrivo(monkeypatch, True)

    preload.preload_embedding(log=None)

    assert giudice.caricamenti == 1
    assert orologio.trascorsi < 5, (
        f"l'avvio sincrono ha aspettato {orologio.trascorsi:.0f} s: il client "
        "MCP avrebbe gia' chiuso la connessione")
