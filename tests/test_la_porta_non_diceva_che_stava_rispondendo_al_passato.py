"""La riga di comando rispondeva AL PASSATO senza dirlo.

2026-09-07. `Risultati.letto_al_passato` esiste da quando esiste il routing
temporale: quando la porta deduce una data dalla domanda e il filtro toglie
qualcosa, l'SDK lo dichiara con l'istante, il conteggio e una nota. La riga di
comando non nominava quel campo in nessun punto — grep sul CONTENUTO, non sul
nome dei file: zero occorrenze in `cli.py` e zero in `mcp_server.py`.

E' la stessa forma che `_avviso_scaduti` porta scritta nel proprio docstring —
«un campo esiste sull'OGGETTO, non sulla PORTA» — con la differenza che quella
era stata curata e questa no. Il punto in cui si vede meglio e' proprio
l'avviso della scadenza, che per non far attribuire l'assenza alla causa
sbagliata arriva a elencare cosa NON e' stato: «non e' il pavimento e **non e'
una data nella domanda**». La data nella domanda, quando la causa era LEI, non
si presentava a nessuno.

⚠️ QUESTO FILE PRESIDIA IL RAMO DEDOTTO, e la scelta e' deliberata: li' la
dichiarazione dell'SDK e' comportamento consolidato, quindi cio' che si misura
qui e' solo se la PORTA la mostra. Il ramo `as_of` esplicito e' oggetto di una
decisione aperta sul canale (07/09) e sta in un altro banco: mescolarli
renderebbe questo rosso illeggibile — non si saprebbe se e' caduta la porta o
se e' cambiata la decisione.

Niente giudice: `sm.store()` diretto con `asserted_at` su epoch fissi.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from typer.testing import CliRunner  # noqa: E402

from verimem.cli import app  # noqa: E402
from verimem.client import Memory  # noqa: E402
from verimem.semantic import Fact  # noqa: E402

_BASE = 1_700_000_000.0          # 14/11/2023
_DAY = 86400.0


@pytest.fixture()
def store_con_catena(tmp_path, monkeypatch):
    """Tre canoni in catena, l'ultimo asserito nel 2025."""
    for nome in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(nome, str(tmp_path))
    #: ⚠️ `Memory()` SENZA argomento: e' l'unico modo di aprire lo STESSO file
    #: che aprira' la CLI. Un path esplicito crea un secondo store e la cella
    #: misurerebbe due archivi diversi.
    m = Memory()
    for fid, quando, testo in (
            ("A", _BASE, "Il canone e' 2400 euro."),
            ("B", _BASE + 100 * _DAY, "Il canone e' 2900 euro."),
            ("C", _BASE + 500 * _DAY, "Il canone e' 3400 euro.")):
        m.semantic.store(Fact(id=fid, proposition=testo, topic="t",
                              asserted_at=quando), embed="sync")
    m.semantic.supersede("A", "B", principal="test:suite",
                         reason="same-source evolution")
    m.semantic.supersede("B", "C", principal="test:suite",
                         reason="same-source evolution")
    return m


def _recall(domanda: str, *argomenti: str) -> str:
    esito = CliRunner().invoke(app, ["recall", domanda, "--k", "5", *argomenti])
    assert esito.exit_code == 0, f"la CLI e' uscita con {esito.exit_code}"
    return esito.stdout


def test_CONTROLLO_senza_data_la_porta_serve_il_presente(store_con_catena):
    """Se cade, il test qui sotto non misura la porta ma il banco."""
    uscita = _recall("quanto e' il canone")
    assert "3400" in uscita, "la CLI non serve nemmeno il corrente"
    assert "AL " not in uscita, (
        "senza nessuna data la porta annuncia un viaggio nel tempo: e' il "
        "rumore al posto del silenzio, il difetto opposto a quello curato qui")


def test_la_porta_DICE_che_la_risposta_e_di_un_altro_istante(store_con_catena):
    """Il presidio. La domanda nomina una data, il filtro toglie il canone del
    2025, e chi legge deve vederlo scritto — non dedurlo dall'assenza."""
    uscita = _recall("cosa risultava sul canone al 1 giugno 2024")
    # CONTROLLO INTERNO: senza questo, un'uscita muta perche' la data non e'
    # stata dedotta sarebbe indistinguibile da una muta perche' la porta tace.
    assert "2900" in uscita, (
        "la data non e' stata dedotta dalla domanda (o il filtro non ha "
        "agito): a giugno 2024 il corrente era 2900. Senza il viaggio nel "
        "tempo non c'e' niente da dichiarare e questo test non misura la "
        f"porta. LA PORTA HA STAMPATO: {uscita!r}")
    assert "3400" not in uscita, (
        "il canone del 2025 e' uscito: il filtro temporale non ha scartato "
        f"nulla, quindi non c'e' la riduzione da dichiarare. USCITA: {uscita!r}")
    assert "AL " in uscita, (
        "la porta ha risposto con lo stato di un ALTRO istante e non l'ha "
        "detto: `Risultati.letto_al_passato` era popolato e nessuno lo "
        "stampava. Chi legge vede un canone plausibile e non ha modo di "
        "sapere che sta guardando il passato.")
