"""Le tabelle di `verimem facts recall` e `facts search` portano il verdetto.

Trovate dal censimento CLI, dopo che `verimem recall` era gia' stato curato:
esistono DUE comandi che fanno la stessa cosa con nomi diversi — `recall` e
`facts recall` — e curarne uno non cura l'altro.

    Recall 'su quale porta ...'
    id       │ sim   │ status      │ topic │ proposition
    27c1329  │ 0.903 │ model_claim │ prova │ Il servizio ... 8443.

`sim` e' la somiglianza fra domanda e fatto, `status` dice che cosa e' il fatto:
nessuno dei due dice se qualcuno l'ha verificato.
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
FATTO = "Il servizio di fatturazione ascolta sulla porta 8443."


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch) -> Path:
    d = Path(tempfile.mkdtemp(prefix="factsrecall_"))
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(d))
    r = runner.invoke(app, ["save", FATTO, "--topic", "prova"])
    assert r.exit_code == 0, r.output
    con = sqlite3.connect(str(d / "semantic" / "semantic.db"))
    con.execute("UPDATE facts SET grounding_score = 91.5")
    con.commit()
    con.close()
    return d


def _tabella(args: list[str]) -> str:
    r = runner.invoke(app, args)
    assert r.exit_code == 0, r.output
    piatto = _ANSI.sub("", r.output)
    return re.sub(r"[│┌┐└┘├┤┬┴─\s]+", " ", piatto)


#: La query e' il fatto IDENTICO: la suite sostituisce l'embedder con uno stub
#: deterministico, quindi la somiglianza fra una domanda e una risposta qui non
#: esiste. Si misura la colonna, non il retrieval.
@pytest.mark.parametrize("cmd", [
    ["facts", "recall", FATTO],
    ["facts", "search", "8443"],
])
def test_la_tabella_porta_il_verdetto(cmd, store: Path):
    out = _tabella(cmd)
    assert "8443" in out, f"{cmd} non ha trovato il fatto:\n{out[:300]}"
    assert "91" in out, f"{cmd} non porta il verdetto:\n{out[:400]}"


@pytest.mark.parametrize("cmd", [
    ["facts", "recall", FATTO],
    ["facts", "search", "8443"],
])
def test_un_fatto_mai_giudicato_non_mostra_uno_zero(cmd, store: Path):
    con = sqlite3.connect(str(store / "semantic" / "semantic.db"))
    con.execute("UPDATE facts SET grounding_score = NULL")
    con.commit()
    con.close()
    out = _tabella(cmd)
    assert "8443" in out
    assert "91" not in out and " 0.0 " not in out, out[:400]
