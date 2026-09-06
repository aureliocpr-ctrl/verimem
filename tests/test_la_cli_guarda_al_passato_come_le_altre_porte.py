"""La riga di comando risponde ad `as_of` come le altre due porte.

Il 06/09 `include_superseded` e' stato curato sul ramo `as_of` (T18): era
accettato dalla firma pubblica e ingoiato in silenzio. La cura sta in
`recall_as_of` + `client.py`, e la CLI **eredita** — ma «eredita» e' un
ragionamento, non una misura, e stanotte due ragionamenti identici hanno dato
un esito ciascuno: l'SDK «delega al tool giusto, quindi e' a posto» era FALSO,
la CLI «eredita» era vero. Una su due.

⚠️ E LA MISURA CHE L'HA PROVATO NON ERA UN PRESIDIO: l'ho eseguita a mano da
riga di comando, una volta, alle 04:16. Questa cella la mette in CI, che e' la
differenza fra «funzionava quella notte» e «continua a funzionare».

Il caso e' quello della QA — TRE fatti in catena, non due:

    A (asserito _BASE)  --ritirato da-->  B  ... T ...  --> C

a **T** il corrente era **B**; **A** era gia' ritirato, **C** non esisteva.
Con due soli fatti le due richieste chiedono la stessa cosa e non separano
«i filtri COMPONGONO» da «uno dei due e' IGNORATO».

Niente giudice, niente orologio del muro: `sm.store()` diretto e `asserted_at`
su un epoch fisso.
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

_BASE = 1_700_000_000.0
_DAY = 86400.0
_ISTANTE_T = _BASE + 300 * _DAY


@pytest.fixture()
def store_con_catena(tmp_path, monkeypatch):
    """Lo store che la CLI aprira': stessa dir, stessa catena."""
    for nome in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(nome, str(tmp_path))
    m = Memory()
    #: ⚠️ `Memory()` SENZA argomento: e' la riga del Quickstart, ed e' anche
    #: l'unico modo di aprire lo STESSO file che aprira' la CLI. Passare un
    #: path (`Memory("x.db")`) crea un secondo store e la cella misurerebbe
    #: due archivi diversi — l'errore che mi e' costato un rosso falso il
    #: 04/09 e che @ws7 ha poi trovato come difetto vero del prodotto (T16).
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


def _recall(*argomenti: str) -> str:
    esito = CliRunner().invoke(app, ["recall", "quanto e' il canone",
                                     "--k", "5", *argomenti])
    assert esito.exit_code == 0, f"la CLI e' uscita con {esito.exit_code}"
    return esito.stdout


def test_la_cli_senza_as_of_serve_il_presente(store_con_catena) -> None:
    """CONTROLLO POSITIVO: se cade, il resto del file non misura niente."""
    uscita = _recall()
    assert "3400" in uscita, "la CLI non serve nemmeno il corrente"
    assert "2400" not in uscita, "senza chiederli, i ritirati non escono"


def test_la_cli_con_as_of_serve_il_corrente_di_allora(store_con_catena) -> None:
    uscita = _recall("--as-of", str(int(_ISTANTE_T)))
    assert "2900" in uscita, (
        "a quell'istante il corrente era B (2900): la CLI deve dare quello")
    assert "3400" not in uscita, (
        "C non esisteva ancora a quell'istante e non deve comparire")


def test_la_cli_con_as_of_e_superseded_serve_anche_la_storia(
        store_con_catena) -> None:
    """Il caso che separa «composto» da «ignorato».

    Prima di T18 questa richiesta rendeva la riga IDENTICA a quella senza
    `--include-superseded`: il parametro arrivava alla firma e non arrivava
    al filtro. Misurato dalla QA sulla CLI il 06/09.
    """
    uscita = _recall("--as-of", str(int(_ISTANTE_T)), "--include-superseded")
    assert "2900" in uscita, "il corrente di allora resta il primo cittadino"
    assert "2400" in uscita, (
        "chiedendo i ritirati, A deve comparire: se manca, il parametro e' "
        "accettato e ingoiato — il difetto che T18 ha chiuso sulle tre porte")
