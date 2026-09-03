"""Dalla riga di comando si deve poter dire fino a quando un fatto vale.

`valid_until` morde da tempo — un fatto scaduto sparisce dal top-k — e da oggi
le porte in lettura lo DICHIARANO (SDK, `recall`, `ask`). Ma il campo era
popolato su **0 fatti su 17098** nel corpus di casa, e la ragione si vede qui:
**non c'era modo di scriverlo se non dall'SDK**. Una capacità cablata a cui
nessuno può dare materiale non emette segnale, e si legge come assente.

⚠️ L'ORDINE È VOLUTO, ed è stato dichiarato prima di cominciare: PRIMA la riga
che dichiara, POI la porta che scrive. Al contrario si darebbe agli utenti un
modo di far sparire fatti senza un modo di accorgersene.

⚠️ E IL CASO CHE CONTA DI PIÙ È IL TERZO: una data illeggibile non deve
scrivere il fatto **senza** scadenza. Sarebbe il difetto peggiore di tutti —
chi ha chiesto una validità limitata si ritroverebbe un fatto eterno, e il
messaggio d'errore su una riga già scorsa non lo salverebbe.

⛔ Lo store è un `Memory` VERO su tempdir passato con lo stesso monkeypatch di
`_open_memory` che la casa usa: la CLI non può aprire lo store di Aurelio.
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from typer.testing import CliRunner  # noqa: E402

from verimem import cli as cli_mod  # noqa: E402
from verimem.client import Memory  # noqa: E402

FRASE = "Il permesso di transito del lotto B12 vale fino a fine mese."


@pytest.fixture()
def cli(monkeypatch):
    mem = Memory(str(Path(tempfile.mkdtemp(prefix="cli_vu_")) / "s.db"))
    monkeypatch.setattr(cli_mod, "_open_memory", lambda *a, **k: mem)

    def _run(*argv):
        return mem, CliRunner().invoke(cli_mod.app, list(argv))
    return _run


def _ultimo(mem):
    """L'ultimo fatto scritto, letto dallo store — non dall'uscita del comando.

    ⚠️ Si guarda il DATO, non la riga stampata: un comando può dire «fatto» e
    non aver scritto nulla, ed è precisamente ciò che questi test devono poter
    distinguere.
    """
    with mem.semantic._connect() as c:  # noqa: SLF001 — lettura di verifica
        r = c.execute("SELECT id, valid_until FROM facts "
                      "ORDER BY rowid DESC LIMIT 1").fetchone()
    return r


def test_senza_l_opzione_il_fatto_non_ha_scadenza(cli):
    """CONTROLLO POSITIVO al rovescio: se il campo risultasse popolato sempre,
    il test sotto passerebbe senza dimostrare che l'opzione fa qualcosa."""
    mem, res = cli("remember", FRASE, "--topic", "vu/senza")
    assert res.exit_code == 0, res.output
    riga = _ultimo(mem)
    assert riga is not None, "il fatto non e' stato scritto affatto"
    assert riga["valid_until"] is None, (
        f"nessuna scadenza chiesta e il campo e' popolato: {riga['valid_until']!r}"
    )


def test_con_una_data_il_fatto_porta_la_scadenza(cli):
    mem, res = cli("remember", FRASE, "--topic", "vu/data",
                   "--valid-until", "2020-01-01")
    assert res.exit_code == 0, res.output
    riga = _ultimo(mem)
    assert riga is not None, "il fatto non e' stato scritto"
    assert riga["valid_until"] is not None, (
        f"`--valid-until` accettata e il campo e' vuoto: la porta prende "
        f"l'opzione e non la usa. Uscita: {res.output[:200]!r}"
    )
    assert float(riga["valid_until"]) < time.time(), (
        f"la data del 2020 deve finire nel PASSATO: {riga['valid_until']!r}"
    )


def test_una_data_illeggibile_non_scrive_un_fatto_ETERNO(cli):
    """IL CASO PEGGIORE. Se il parsing fallisce e il fatto viene scritto lo
    stesso, chi aveva chiesto una validità limitata ottiene l'opposto: un fatto
    che non scade mai. Un errore stampato su una riga già scorsa non lo salva.
    """
    mem, res = cli("remember", FRASE, "--topic", "vu/rotta",
                   "--valid-until", "il mese prossimo")
    riga = _ultimo(mem)
    if riga is not None:
        assert riga["valid_until"] is not None, (
            "la data era illeggibile e il fatto e' stato scritto SENZA "
            "scadenza: chi chiedeva una validita' limitata ha ottenuto un "
            "fatto eterno, che e' il contrario di quel che ha chiesto"
        )
    assert res.exit_code != 0 or "valid-until" in res.output.lower(), (
        f"la data era illeggibile e il comando non lo dice: {res.output[:200]!r}"
    )


def test_dalla_CLI_a_CLI_scrivo_una_scadenza_e_la_CLI_me_lo_dice(cli):
    """IL CERCHIO. Le due metà di questo lavoro sono nate separate — la riga che
    dichiara (SDK, poi `recall`, poi `ask`) e la porta che scrive — e finché non
    si parlano sono due metà, non una capacità.

    Qui si scrive DALLA riga di comando un fatto già scaduto, e si chiede DALLA
    riga di comando: la risposta deve dire che qualcosa è stato tolto.

    ⚠️ CONTROLLO POSITIVO dentro il test: prima si verifica che un fatto VIVO
    sullo stesso tema venga servito. Senza, un recall vuoto — per la query, per
    il pavimento, per il gate — farebbe passare o cadere questo test per una
    ragione che non c'entra con la scadenza.
    """
    mem, r1 = cli("remember",
                  "Il varco nord del deposito di Verona resta aperto ai mezzi pesanti.",
                  "--topic", "giro/vivo")
    assert r1.exit_code == 0, r1.output
    _, r2 = cli("remember",
                "Il varco sud del deposito di Verona resta aperto ai mezzi pesanti.",
                "--topic", "giro/scaduto", "--valid-until", "2020-06-30")
    assert r2.exit_code == 0, r2.output

    _, r3 = cli("recall", "quale varco del deposito di Verona resta aperto")
    out = r3.output
    assert "varco" in out or "Verona" in out, (
        f"la CLI non serve nemmeno il fatto VIVO: questo test non sta "
        f"misurando la scadenza. Uscita: {out[:300]!r}"
    )
    assert "scadut" in out.lower(), (
        f"scritta una scadenza dalla CLI, la CLI non dice di averla applicata: "
        f"le due meta' non si parlano. Uscita: {out[:300]!r}"
    )
