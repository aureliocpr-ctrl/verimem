"""`tip` e `recent` mostrano lo status e non il verdetto del moat.

Sul corpus vivo 2026-07-30:

    $ verimem tip
    0508d280af97  2026-07-30 01:22  model_claim narrative
    $ verimem recent
      0508d280af97  07-30 01:22  model_claim  handoff/...
      e5fe0b97862f  07-30 01:21  model_claim  handoff/...

Quei fatti erano stati ammessi dal moat a 100.0 e 99.9. `model_claim` e' lo
status — «affermazione di un modello» — e resta identico che il moat abbia
giudicato o non abbia mai guardato: la riga non distingue le due cose.

E' la stessa cura di ca85cb0a sulle tre superfici di lettura MCP, mancata su due
comandi CLI. Contano piu' delle altre per un motivo pratico: `tip` e `recent`
sono cio' che si guarda per RIPRENDERE il lavoro dopo un compact, quindi sono il
punto in cui un checkpoint mai verificato viene riletto come acquisito.
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


def _plain(t: str) -> str:
    return _ANSI.sub("", t or "")


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> Path:
    d = Path(tempfile.mkdtemp(prefix="chain_verdict_"))
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(d))
    r = runner.invoke(app, ["save", "Il totale della fattura e 1240 euro.",
                            "--topic", "prova/verdetto"])
    assert r.exit_code == 0, r.output
    # un verdetto noto, senza dipendere dal giudice installato
    db = d / "semantic" / "semantic.db"
    con = sqlite3.connect(str(db))
    con.execute("UPDATE facts SET grounding_score = 97.5")
    con.commit()
    con.close()
    return d


#: IL PUNTEGGIO INTERO, mai le prime due cifre. `97` nudo si trova dentro un id
#: esadecimale, e in questo stesso file ce ne sono due che lo contengono
#: (`0508d280af97`, `e5fe0b97862f`): i due test qui sotto potevano passare
#: SENZA che la superficie stampasse alcun verdetto — un presidio che non
#: presidia, che e' peggio di un presidio assente.
#:
#: Scoperto il 2026-08-01 dal gemello di questo difetto, che sull'altro verso
#: aveva fatto fallire la CI su macOS: il fatto era nato `5936ecc7` e il `93`
#: cercato «non doveva esserci» si trovava dentro l'id. Stessa causa, due
#: sintomi opposti — falso positivo qui, falso negativo la'.
#:
#: `97.5` col punto in un id esadecimale non ci sta. E' la lezione gia' in
#: memoria dopo sei falsi allarmi in una sessione: interroga la struttura, non
#: il testo.
_VERDETTO = "97.5"


def test_tip_shows_the_moat_verdict(store: Path):
    r = runner.invoke(app, ["tip"])
    assert r.exit_code == 0, r.output
    out = _plain(r.output)
    assert _VERDETTO in out, (
        f"`tip` non mostra il verdetto del fatto che serve a riprendere:\n{out}"
    )


def test_recent_shows_the_moat_verdict(store: Path):
    r = runner.invoke(app, ["recent"])
    assert r.exit_code == 0, r.output
    out = _plain(r.output)
    assert _VERDETTO in out, f"`recent` non mostra il verdetto:\n{out}"


def test_an_unjudged_fact_is_not_shown_as_a_number(store: Path):
    """None non e' zero: «mai giudicato» deve restare distinguibile da un
    punteggio basso, la stessa distinzione che doctor fa fra UNKNOWN e zero."""
    db = store / "semantic" / "semantic.db"
    con = sqlite3.connect(str(db))
    con.execute("UPDATE facts SET grounding_score = NULL")
    con.commit()
    con.close()
    out = _plain(runner.invoke(app, ["recent"]).output)
    # Il terzo test dello stesso difetto, e questo l'ha mostrato DAL VIVO: alla
    # prima esecuzione dopo la cura degli altri due, l'id generato era
    # `3d12839735c7` e il `97` che «non doveva esserci» stava dentro l'id. Tre
    # test, tre volte la stessa causa, in un file solo.
    assert "0.0" not in out and _VERDETTO not in out, (
        f"un fatto mai giudicato appare con un punteggio:\n{out}"
    )
    assert "--" in out, (
        f"la superficie non dichiara «mai giudicato»: una cella vuota si legge "
        f"come uno zero, che e' la distinzione che questo prodotto vende\n{out}"
    )
