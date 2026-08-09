"""Il passato si può chiedere anche dalla riga di comando.

Il README lo promette fra le cinque righe che descrivono il prodotto::

    **Bi-temporal history** — facts carry both *when it happened* and *when we
    learned it*. Query the past (`as_of`), see transitions … and audit every
    revision.

Verificato il 2026-07-31 usando il prodotto come un utente. Cosa REGGE, e va
detto con la stessa precisione dei difetti:

* `Memory.history` restituisce la catena completa delle supersessioni
  (PostgreSQL → MySQL → MariaDB con i `superseded_by`), dà la STESSA storia da
  qualunque id della catena, e distingue un fatto senza storia (1 voce) da un
  id inesistente (0 voci);
* `Memory.search(query, as_of=<epoch>)` fa davvero time-travel: sullo stesso
  store, senza `as_of` risponde «MySQL», con `as_of` all'istante precedente
  risponde «PostgreSQL».

Il buco era solo qui::

    MCP  hippo_recall_as_of      dichiarato
    SDK  Memory.search(as_of=…)  funziona
    CLI  verimem recall --as-of  NO

Un buco piccolo, e per questo vale la pena dirlo con onestà: la prima stesura
di questo file dava per mancante anche l'SDK, perché cercavo un metodo di nome
`recall_as_of` invece della capacità. Leggere il codice prima di curarlo ha
evitato di riscrivere qualcosa che esisteva — la superficie da aggiungere è una
sola, non due.
"""
from __future__ import annotations

import re
import time

import pytest
from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


@pytest.fixture()
def store_con_una_storia(tmp_path, monkeypatch):
    """PostgreSQL, poi MySQL. `quando` è l'istante in cui valeva il primo."""
    for k in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(k, str(tmp_path))
    from verimem.client import Memory
    from verimem.config import CONFIG

    # Si scrive DOVE LA CLI LEGGE. `CONFIG` è congelato all'import, quindi un
    # path esplicito su tmp_path darebbe uno store che il comando non guarda —
    # e il test fallirebbe con «no facts found» dicendo però «il time-travel
    # non funziona». Stessa trappola già pagata su `verimem status`.
    m = Memory(path=CONFIG.semantic_db)
    m.add("Il database di produzione e' PostgreSQL.", topic="infra/db")
    quando = time.time()
    time.sleep(1.1)
    m.add("Il database di produzione e' MySQL.", topic="infra/db")
    return m, quando


def test_l_sdk_il_passato_lo_sa_gia_dire(store_con_una_storia):
    """Presidio, non cura: questa capacità c'è, e un test che la fissa impedisce
    che sparisca mentre si aggiunge la porta accanto."""
    m, quando = store_con_una_storia
    adesso = " ".join(h["text"] for h in m.search("database di produzione", k=3))
    prima = " ".join(h["text"] for h in
                     m.search("database di produzione", k=3, as_of=quando))
    assert "mysql" in adesso.lower(), adesso
    assert "postgresql" in prima.lower(), prima
    assert "mysql" not in prima.lower(), (
        f"il passato contiene un fatto che allora non esisteva: {prima}")


def test_la_cli_sa_chiedere_il_passato(store_con_una_storia):
    """Il canale che mancava. `--as-of` prende un epoch, che è il tempo con cui
    il resto del prodotto ragiona."""
    _, quando = store_con_una_storia
    r = runner.invoke(app, ["recall", "database di produzione",
                            "--as-of", str(quando)])
    out = _ANSI.sub("", r.output)
    assert r.exit_code == 0, out
    assert "postgresql" in out.lower(), out


def test_senza_as_of_la_cli_risponde_col_presente(store_con_una_storia):
    """Controprova: se anche il presente dicesse PostgreSQL, il test sopra
    passerebbe per la ragione sbagliata."""
    r = runner.invoke(app, ["recall", "database di produzione"])
    out = _ANSI.sub("", r.output)
    assert r.exit_code == 0, out
    assert "mysql" in out.lower(), out


def test_un_as_of_prima_di_tutto_non_inventa_niente(store_con_una_storia):
    r = runner.invoke(app, ["recall", "database di produzione", "--as-of", "1"])
    out = _ANSI.sub("", r.output)
    assert r.exit_code == 0, out
    assert "postgresql" not in out.lower() and "mysql" not in out.lower(), out


def test_un_as_of_illeggibile_lo_dice_invece_di_ignorarlo(store_con_una_storia):
    """Silenziare un `--as-of` malformato servirebbe il PRESENTE a chi ha
    chiesto il passato, senza che se ne accorga: la risposta sarebbe
    plausibile e sbagliata."""
    r = runner.invoke(app, ["recall", "database di produzione",
                            "--as-of", "l'anno scorso"])
    out = _ANSI.sub("", r.output)
    assert r.exit_code != 0 or "as-of" in out.lower() or "epoch" in out.lower(), out
