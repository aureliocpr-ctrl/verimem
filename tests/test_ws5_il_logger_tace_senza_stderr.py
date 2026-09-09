"""Senza `sys.stderr`, il logger deve TACERE — non ripiegare su stdout.

`observability.route_logs_to_stderr()` esiste per una ragione sola, e il file
la dichiara alla riga 22-25: il server MCP stdio possiede stdout, e «any extra
byte breaks JSON-RPC framing». La funzione instrada i log su stderr.

Ma `PrintLoggerFactory(file=sys.stderr)` legge `sys.stderr` AL MOMENTO DELLA
CHIAMATA, e un processo senza console — `pythonw`, un servizio Windows, un
launcher GUI — ha `sys.stderr is None`. Li' `file=None` NON significa «non
scrivere»: Python lo legge come «il default», cioe' **stdout**. ⇒ la difesa del
canale JSON-RPC si rovescia proprio nella condizione che doveva coprire.

E' la stessa trappola che `test_ws5_il_download_del_giudice_lo_dice_all_utente`
presidia per `print(x, file=None)`. Quel file difendeva l'annuncio del
download; il logger non lo difendeva nessuno — e infatti il rosso Windows di
quel file (T41) era proprio un evento `flow.warmup what=moat-judge` finito su
stdout da qui, non un difetto suo.

Misurato il 2026-09-09 prima della cura: 86 byte su stdout.
"""
from __future__ import annotations

import sys

import pytest
import structlog

from verimem import observability as obs


@pytest.fixture
def logger_ripristinato():
    """Rimette il logger a posto, qualunque cosa faccia il test.

    Senza questo, un test che configura structlog con uno stderr finto LASCIA
    quella configurazione a tutti i test successivi: e' esattamente il
    meccanismo con cui il rosso di T41 compariva solo in suite e mai sul file
    da solo.
    """
    yield
    obs.route_logs_to_stderr()


def test_senza_stderr_il_logger_non_scrive_su_stdout(monkeypatch, capsys,
                                                     logger_ripristinato):
    monkeypatch.setattr(sys, "stderr", None)

    obs.route_logs_to_stderr()
    structlog.get_logger().warning("flow.warmup", what="moat-judge")

    finito = capsys.readouterr().out
    assert not finito.strip(), (
        "senza stderr il logger deve TACERE, non ripiegare su stdout: nel "
        f"server MCP stdout e' il canale JSON-RPC. Finiti {len(finito)} byte: "
        f"{finito!r}")


def test_con_stderr_il_logger_scrive_ancora(monkeypatch, capsys,
                                            logger_ripristinato):
    """La cura non deve comprare il silenzio spegnendo il logging.

    Il rischio di «tacere quando manca stderr» e' di tacere e basta: questo
    tiene il caso normale, ed e' il controllo che puo' falsificare la cura.
    """
    obs.route_logs_to_stderr()
    structlog.get_logger().warning("flow.warmup", what="moat-judge")

    catturato = capsys.readouterr()
    assert "flow.warmup" in catturato.err, (
        "con uno stderr vero il messaggio deve continuare ad arrivare su "
        f"stderr; catturato err={catturato.err!r} out={catturato.out!r}")
    assert not catturato.out.strip(), \
        "e non deve MAI finire su stdout, nemmeno nel caso normale"
