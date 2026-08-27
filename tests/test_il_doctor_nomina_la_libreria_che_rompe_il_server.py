"""Il `doctor` deve nominare `mcp`, che e' la libreria che rompe il server.

Il 2026-08-26 abbiamo dimostrato ESEGUENDO la riga che `@server.list_tools()` —
il decoratore in `verimem/mcp_server.py` — solleva `AttributeError` sotto
`mcp 2.1.1` e riesce sotto `1.26.0`: la 2.x ha rimosso l'API di basso livello
su cui il server e' costruito. `pyproject` porta il tetto `mcp>=1.0.0,<2` dal
29/07, ma un tetto protegge solo chi installa da zero — non chi aggiorna `mcp`
a mano, ne' chi installa in un ambiente dove la 2.x c'e' gia'.

Il 2026-08-27 `git grep -c "\bmcp\b" verimem/doctor.py` dava **zero**: la sola
rottura che sappiamo riprodurre non aveva un controllo che la nominasse, e chi
la incontrava vedeva un traceback invece di una riga.

⚖️ LIMITE DICHIARATO: questo non aiuta chi ha gia' installato una versione
rotta — quella porta con se' il proprio `doctor`. Serve da qui in avanti.
"""
from __future__ import annotations

import pytest

from verimem import doctor as D


def _mcp(checks):
    return [c for c in checks if c["name"] == "mcp"]


def test_con_mcp_2_il_doctor_lo_dice(monkeypatch) -> None:
    """CONTROLLO NEGATIVO: la versione che rompe deve produrre un FAIL."""
    monkeypatch.setattr(D, "_versione_di_mcp", lambda: "2.1.1")
    c = _mcp(D.run_doctor())
    assert c, "nessun controllo si chiama «mcp»: la rottura resta senza nome"
    assert c[0]["status"] == D.FAIL, f"mcp 2.1.1 non e' segnalato: {c[0]}"
    assert "2.1.1" in c[0]["detail"], "il detail non dice quale versione ha trovato"
    assert c[0].get("fix"), "un FAIL senza «fix» lascia l'utente dove l'ha trovato"


def test_con_mcp_1_il_doctor_tace(monkeypatch) -> None:
    """CONTROLLO POSITIVO: se il criterio non distingue, e' un allarme inutile."""
    monkeypatch.setattr(D, "_versione_di_mcp", lambda: "1.26.0")
    c = _mcp(D.run_doctor())
    assert c, "il controllo deve esserci anche quando va tutto bene"
    assert c[0]["status"] == D.OK, f"mcp 1.26.0 e' la versione BUONA: {c[0]}"


def test_senza_mcp_installato_non_e_un_errore(monkeypatch) -> None:
    """`mcp` e' un extra: chi non usa il server MCP non deve vedere un rosso."""
    monkeypatch.setattr(D, "_versione_di_mcp", lambda: None)
    c = _mcp(D.run_doctor())
    assert c and c[0]["status"] != D.FAIL, (
        f"non aver installato un EXTRA non e' un guasto: {c}")


@pytest.mark.parametrize("v, rotto", [
    ("1.26.0", False), ("1.9.4", False), ("1.29.1", False),
    ("2.0.0", True), ("2.1.1", True), ("10.0.0", True),
])
def test_il_confine_e_la_major_non_la_stringa(monkeypatch, v, rotto) -> None:
    """⚠️ `"2" in v` direbbe rotto anche per `1.2.0`, e `v > "1"` per `10.0.0`
    direbbe sano: il confine e' la MAJOR, e va confrontata come numero."""
    monkeypatch.setattr(D, "_versione_di_mcp", lambda: v)
    c = _mcp(D.run_doctor())
    assert (c[0]["status"] == D.FAIL) is rotto, f"{v} classificata male: {c[0]}"
