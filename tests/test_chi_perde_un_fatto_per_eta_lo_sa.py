"""Chi perde un fatto per ETÀ deve saperlo, come chi lo perde per scadenza.

Il prodotto sa già che le cause di una risposta più corta si confondono:
l'avviso di `client.py` ne elenca tre — il pavimento, la data nella domanda, la
scadenza dichiarata — e dice esplicitamente cosa NON è, perché senza il «non è»
un avviso viene attribuito alla causa sbagliata. La QUARTA strada, il decay per
età (`semantic.py`, «lift the AGE-based freshness hiding»), non è in
quell'elenco.

MISURATO SULLA PORTA VERA, in processi separati, prima di scrivere una riga:

    CONTROLLO  fatto fresco                -> esce
    A.         valid_until passato         -> non esce, E L'AVVISO LO DICE
    B.         vecchio 365 giorni          -> non esce, e l'uscita è
                                              «no facts found» e basta

Due modi di perdere un fatto, un avviso solo. Chi lo perde per età legge la
stessa cosa di chi non ha mai scritto niente — e se va a cercare «expired»
trova l'altra definizione, quella di `valid_until`.

⚠️ NASCE ROSSO, ed è voluto: la terza e la quarta cella cadono finché la porta
non nomina la freschezza. Le altre sono controlli e devono stare verdi anche
prima, o il banco non misura la cosa giusta.

Niente giudice e niente orologio del muro dove conta: le date stanno su
`created_at`/`valid_until` calcolate da un `adesso` catturato una volta.
"""
from __future__ import annotations

import time

import pytest
from typer.testing import CliRunner

from verimem.cli import app
from verimem.client import Memory
from verimem.semantic import Fact

_GIORNO = 86400.0
_TESTO = "Il canone di locazione del capannone e' 2900 euro."
_QUERY = "quanto e' il canone di locazione"


def _punta_env(monkeypatch, dove) -> None:
    for nome in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(nome, str(dove))


def _scrivi(tmp_path, monkeypatch, **campi):
    """Uno store con UN fatto solo, e la porta puntata lì.

    ⚠️ `Memory()` senza argomento: è la riga del Quickstart ed è l'unico modo
    di aprire lo stesso file che aprirà la CLI. E lo store si apre DOPO aver
    spostato l'ambiente, mai prima: il `CliRunner` gira nello stesso processo
    e riuserebbe quello già aperto — misurato, è costato un rosso falso.
    """
    _punta_env(monkeypatch, tmp_path)
    m = Memory()
    m.semantic.store(Fact(id="F", proposition=_TESTO, topic="t", **campi),
                     embed="sync")
    return m


def _recall(*argomenti: str) -> str:
    esito = CliRunner().invoke(app, ["recall", _QUERY, "--k", "5", *argomenti])
    assert esito.exit_code == 0, f"la porta è uscita con {esito.exit_code}"
    return esito.stdout


def test_controllo_positivo_un_fatto_fresco_esce(tmp_path, monkeypatch) -> None:
    """Se cade, «non esce» sotto non distingue nascosto da banco cieco."""
    _scrivi(tmp_path, monkeypatch)
    assert "2900" in _recall(), "nemmeno un fatto fresco esce: banco cieco"


def test_controllo_la_scadenza_dichiarata_ha_gia_la_sua_frase(
        tmp_path, monkeypatch) -> None:
    """Il gemello che FUNZIONA — il metro con cui si misura l'altro.

    Se questa cade, il difetto è nell'avviso degli scaduti e non nella quarta
    causa: questo file non c'entra e va riletto prima di toccare qualcosa.
    """
    adesso = time.time()
    _scrivi(tmp_path, monkeypatch, valid_until=adesso - 3600.0)
    uscita = _recall()
    assert "2900" not in uscita, "un fatto scaduto non si serve"
    assert "SCADUT" in uscita.upper(), (
        "l'avviso della scadenza dichiarata non compare più: è il metro di "
        "questo banco, va sistemato quello prima")


def test_chi_perde_un_fatto_per_eta_riceve_una_frase(
        tmp_path, monkeypatch) -> None:
    """⚠️ RED: oggi l'uscita è «no facts found» e basta."""
    adesso = time.time()
    _scrivi(tmp_path, monkeypatch, created_at=adesso - 365 * _GIORNO)
    uscita = _recall()
    assert "2900" not in uscita, (
        "il decay non nasconde più questo fatto: il difetto non si manifesta "
        "così e il banco va riformulato, non fatto passare")
    basso = uscita.lower()
    assert any(p in basso for p in ("freschezza", "età", "eta'", "emivit")), (
        "il fatto è sparito per ETÀ e l'utente non ha una frase che glielo "
        "dica, mentre per la scadenza dichiarata ce l'ha: due modi di perdere "
        "un fatto, un avviso solo")


def test_l_avviso_dice_anche_come_vederli(tmp_path, monkeypatch) -> None:
    """⚠️ RED: un avviso che non dice il rimedio lascia l'utente dov'era.

    `--deep` esiste da sempre e fa esattamente questo. Il difetto non è che
    manchi la strada: è che nessuno la indichi nel momento in cui serve.
    """
    adesso = time.time()
    _scrivi(tmp_path, monkeypatch, created_at=adesso - 365 * _GIORNO)
    assert "--deep" in _recall(), (
        "l'avviso non nomina `--deep`: il rimedio c'è e l'utente non lo sa")
    #: e il rimedio deve FUNZIONARE, o l'avviso indica una strada chiusa
    assert "2900" in _recall("--deep"), (
        "`--deep` non riporta il fatto nascosto: l'avviso indicherebbe un "
        "rimedio che non cura")


def test_non_si_accende_quando_non_deve(tmp_path, monkeypatch) -> None:
    """Un avviso che compare sempre è rumore, e il rumore si smette di leggere."""
    _scrivi(tmp_path, monkeypatch)
    basso = _recall().lower()
    assert "2900" in basso
    assert not any(p in basso for p in ("freschezza", "emivit")), (
        "il fatto è stato servito: nessuna freschezza da dichiarare")


def test_non_attribuisce_all_eta_cio_che_ha_tolto_il_pavimento(
        tmp_path, monkeypatch) -> None:
    """⚠️ NASCE ROSSO CONTRO LA PRIMA STESURA DI QUESTA STESSA CURA.

    La prima versione chiedeva `deep=True` e, trovando qualcosa, dichiarava la
    freschezza. Ma `deep` solleva SOLO il nascondimento per età: se la risposta
    era vuota per un'altra ragione — il pavimento — quella richiesta rende
    fatti che con l'età non c'entrano, e l'avviso attribuisce l'assenza alla
    causa sbagliata. Misurato sulla porta vera, su un fatto FRESCO tagliato da
    `--min-relevance 0.99`:

        ⚠ 1 fatto/i esistono ma la FRESCHEZZA li tiene fuori
          (... non e' il pavimento ...)

    cioè la frase affermava il contrario del vero, ed era il difetto curato da
    questo file riprodotto un piano più su. Solo la DIFFERENZA fra la pesca
    profonda e quella normale è attribuibile alla freschezza.
    """
    _scrivi(tmp_path, monkeypatch)      #: fatto FRESCO: l'età non c'entra
    uscita = _recall("--min-relevance", "0.99")
    assert "2900" not in uscita, (
        "il pavimento 0.99 non ha tagliato: la cella non misura più il caso "
        "che le interessa")
    basso = uscita.lower()
    assert "freschezza" not in basso, (
        "il fatto è stato tolto dal PAVIMENTO e l'avviso lo attribuisce "
        "all'ETÀ — per giunta dicendo «non è il pavimento», cioè il contrario "
        "del vero")


@pytest.mark.parametrize("campi,atteso", [
    ({"valid_until": -3600.0}, "SCADUT"),
    ({"created_at": -365 * _GIORNO}, "FRESCHEZZA"),
])
def test_le_due_cause_restano_distinguibili(tmp_path, monkeypatch, campi,
                                            atteso) -> None:
    """Due assenze, due frasi DIVERSE — è tutto il punto del ticket.

    Se le due cause producessero la stessa frase, avremmo sostituito «un solo
    segnale per due significati» con «un solo avviso per due cause»: lo stesso
    difetto un piano più su.
    """
    adesso = time.time()
    _scrivi(tmp_path, monkeypatch, **{k: adesso + v for k, v in campi.items()})
    uscita = _recall().upper()
    assert atteso in uscita, f"manca {atteso!r} per {list(campi)}"
    altro = "FRESCHEZZA" if atteso == "SCADUT" else "SCADUT"
    assert altro not in uscita, (
        f"compare anche {altro!r}: le due cause non sono distinguibili, ed è "
        "esattamente il difetto che stiamo curando")
