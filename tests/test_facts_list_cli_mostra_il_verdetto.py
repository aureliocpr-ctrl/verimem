"""`verimem facts list` mostra la confidenza e non il verdetto.

La tabella e' questa (corpus di prova, 2026-07-30):

    id       │ topic │ status      │ conf │ proposition
    27c13297 │ prova │ model_claim │ 0.50 │ Il servizio ... porta 8443.

`conf 0.50` e' il numero che `doctor` segnala come ANTI-correlato con la
verifica: sul corpus vivo i 35 fatti giudicati dal moat stanno tutti a 0.5 e i
4720 mai giudicati a 0.866 di media. Quindi la tabella piu' usata per guardare
i fatti mostra la misura fuorviante e tace quella vera.

Il tool MCP gemello, `hippo_facts_list`, porta il verdetto da ieri. E' di nuovo
la forma di questi giorni — curato il canale che qualcuno ha guardato — su una
coppia che fa la stessa cosa con due nomi.
"""
from __future__ import annotations

import re
import sqlite3
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> Path:
    d = Path(tempfile.mkdtemp(prefix="factslist_"))
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(d))
    r = runner.invoke(app, ["save", "Il servizio ascolta sulla porta 8443.",
                            "--topic", "prova"])
    assert r.exit_code == 0, r.output
    con = sqlite3.connect(str(d / "semantic" / "semantic.db"))
    con.execute("UPDATE facts SET grounding_score = 93.5")
    con.commit()
    con.close()
    return d


def _tabella(args: list[str]) -> str:
    r = runner.invoke(app, args)
    assert r.exit_code == 0, r.output
    # la tabella manda a capo dentro le celle: tolgo i bordi e riunisco
    piatto = _ANSI.sub("", r.output)
    return re.sub(r"[│┌┐└┘├┤┬┴─\s]+", " ", piatto)


def test_la_tabella_porta_il_verdetto(store: Path):
    out = _tabella(["facts", "list"])
    assert "93" in out, f"nessun verdetto nella tabella:\n{out[:400]}"


def test_un_fatto_mai_giudicato_non_mostra_uno_zero(store: Path):
    """«mai giudicato» e «giudicato male» non possono apparire uguali: e' la
    distinzione che questo prodotto vende."""
    con = sqlite3.connect(str(store / "semantic" / "semantic.db"))
    con.execute("UPDATE facts SET grounding_score = NULL")
    con.commit()
    con.close()
    out = _tabella(["facts", "list"])
    assert "0.0" not in out and "93" not in out, out[:400]


def test_la_confidenza_resta_visibile(store: Path):
    """Si affianca, non sostituisce: chi leggeva la confidenza continua a
    trovarla — e ora vede accanto la misura con cui confrontarla."""
    out = _tabella(["facts", "list"])
    assert "0.50" in out or "0.5" in out, out[:400]
