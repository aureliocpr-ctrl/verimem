"""`verimem save` puo' dire QUANDO il fatto e' vero, non solo quando lo scrivi.

Il prodotto e' bi-temporale: ogni fatto ha il tempo di TRANSAZIONE (created_at,
quando l'abbiamo scritto) e il tempo di EVENTO (asserted_at, quando e' vero).
`recall_as_of` ci costruisce sopra il time-travel, e funziona — provato
end-to-end il 2026-07-30 dall'SDK: un fatto asserito 150 giorni prima della
scrittura viene trovato interrogando 75 giorni fa e NON viene trovato
interrogando 200 giorni fa.

Sul corpus vivo pero' `asserted_at` e' NULL su tutti e 6457 i fatti, e il
motivo e' che il canale da cui passano non lo espone: `Memory.add` (SDK) e
`hippo_remember` (MCP) accettano asserted_at, `verimem save` no. Il secondo
asse temporale esiste, e' testato, ed e' vuoto perche' dalla CLI non c'e' modo
di riempirlo.

E' la stessa forma dei sette difetti di questi giorni — funziona sul canale che
qualcuno ha guardato — con la differenza che qui non manca un campo in uscita:
manca l'ingresso.
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
    d = Path(tempfile.mkdtemp(prefix="asserted_"))
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(d))
    return d


def _riga(d: Path):
    con = sqlite3.connect(str(d / "semantic" / "semantic.db"))
    r = con.execute("SELECT asserted_at, created_at FROM facts "
                    "ORDER BY created_at DESC LIMIT 1").fetchone()
    con.close()
    return r


def test_una_data_iso_finisce_nel_tempo_di_evento(store: Path):
    r = runner.invoke(app, ["save", "Il canone di locazione e 900 euro.",
                            "--topic", "contratti", "--asserted-at",
                            "2026-03-15"])
    assert r.exit_code == 0, _ANSI.sub("", r.output)
    asserted, created = _riga(store)
    assert asserted is not None, "asserted_at non e' stato scritto"
    assert asserted < created, "il fatto e' vero da prima di essere scritto"


def test_senza_il_flag_resta_come_prima(store: Path):
    """None significa «tempo di evento sconosciuto», e i lettori ricadono su
    created_at. Riempirlo d'ufficio con l'ora di scrittura cancellerebbe la
    distinzione fra le due cose."""
    r = runner.invoke(app, ["save", "Un fatto qualunque.", "--topic", "t"])
    assert r.exit_code == 0, _ANSI.sub("", r.output)
    asserted, _ = _riga(store)
    assert asserted is None


def test_una_data_illeggibile_e_un_errore_non_un_silenzio(store: Path):
    """Accettare «marzo» e scrivere None farebbe credere che sia stato
    registrato: peggio di un rifiuto."""
    r = runner.invoke(app, ["save", "x", "--topic", "t",
                            "--asserted-at", "marzo scorso"])
    assert r.exit_code != 0
    assert "asserted" in _ANSI.sub("", r.output).lower()


def test_il_recall_a_quel_momento_lo_trova(store: Path):
    """La prova che serve: il campo alimenta davvero il time-travel."""
    import time
    ora = time.time()
    r = runner.invoke(app, ["save", "Il canone di locazione e 900 euro.",
                            "--topic", "contratti",
                            "--asserted-at", "2026-03-15"])
    assert r.exit_code == 0, _ANSI.sub("", r.output)
    from verimem.semantic import SemanticMemory
    from verimem.temporal_context import recall_as_of
    sm = SemanticMemory(db_path=store / "semantic" / "semantic.db")
    dopo = recall_as_of(sm, "quanto e il canone", when=ora - 30 * 86400, k=3)
    assert dopo, "asserito a marzo, non trovato un mese fa"
