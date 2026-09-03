"""TRE PORTE, UNA RISPOSTA — il presidio permanente sull'avviso del pavimento.

PERCHE' ESISTE. Il 03/09 la stessa forma di difetto — *una cura applicata a UNA
superficie sola* — e' comparsa TRE volte in un pomeriggio, e le prime due le ho
curate a mano:

  1. `ENGRAM_AVVISO_MIN_RELEVANCE` messa solo sull'SDK (02/09) → la porta MCP
     dichiarava un'altra soglia               → curata `bef4ac50`
  2. curata su MCP e non sulla CLI            → curata `5f028953`
  3. il TESTO dell'origine curato solo sulla CLI: SDK e MCP dicono ancora
     «la soglia di rilevanza CALIBRATA SU QUESTO CORPUS» anche quando il numero
     arriva dalla variabile                   → e' il RED di questo file

Curare a mano la terza volta significherebbe aspettare la quarta. Questo test la
rende MECCANICA: qualunque porta si sposti da sola, diventa rossa.

PREDIZIONI DEPOSITATE PRIMA DI ESEGUIRE (2026-09-03 19:35):
  P1 — le tre porte dichiarano la STESSA SOGLIA (`0.95`).
       ATTESA: VERDE. E' cio' che ho curato oggi, quindi il presidio non morde
       da solo: il suo RED va PROVOCATO manomettendo una porta (`test_P1_RED`).
  P2 — le tre porte dichiarano la STESSA ORIGINE del numero.
       ATTESA: ROSSA senza manomettere niente — SDK e MCP dicono «calibrata su
       questo corpus» dove la CLI dice «impostato con ENGRAM_AVVISO_MIN_RELEVANCE».

⚠️ PERCHE' L'ORIGINE CONTA QUANTO IL NUMERO: un avviso che dichiara «misurato
sul tuo corpus» accanto a un valore che arriva da una variabile d'ambiente fa
leggere all'utente una taratura dove c'e' una sua impostazione. E' una frase
falsa in una ricevuta, cioe' il difetto peggiore in un prodotto che promette di
dire come fa a sapere le cose.

⚠️ LE TRE PORTE HANNO INTERFACCE DIVERSE E QUI NON SI UNIFORMANO: si legge da
ognuna nella SUA forma (SDK `Risultati.sotto_il_pavimento`, MCP il dict di
`_avvisi_di_lettura`, CLI il testo stampato) e si confronta solo il CONTRATTO —
soglia e origine. Un test che le uniformasse misurerebbe l'adattatore, non le
porte.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from typer.testing import CliRunner  # noqa: E402

from verimem import cli as cli_mod  # noqa: E402
from verimem.client import Memory  # noqa: E402
from verimem.mcp_server import _avvisi_di_lettura  # noqa: E402

_CALIBRATO = 0.88
_SOGLIA_IMPOSTATA = 0.95
_BEST = 0.90          # sopra il calibrato, sotto la soglia impostata
_DOMANDA = "quale database usa il cluster di produzione"

#: Le due origini possibili del numero, riconosciute dal TESTO della ricevuta.
_DA_VARIABILE = "dalla variabile"
_DAL_CORPUS = "misurato dallo store"


def _origine(testo: str) -> str | None:
    """Classifica l'origine dichiarata, dalla frase che l'utente legge."""
    basso = (testo or "").lower()
    if "engram_avviso_min_relevance" in basso or "impostato con" in basso:
        return _DA_VARIABILE
    if "calibrat" in basso or "misurato su se stesso" in basso:
        return _DAL_CORPUS
    return None


class _Sem:
    db_path = None

    def __init__(self, score):
        self._score = score

    def recall(self, query, k=3):          # noqa: ARG002 — firma della porta
        return [("un fatto qualsiasi", self._score)]


class _AgenteMcp:
    def __init__(self, pav, score):
        self._pav, self.semantic = pav, _Sem(score)

    def _auto_relevance_floor(self):
        return self._pav


class _MemCli:
    def __init__(self, best, floor):
        self._best, self._floor = best, floor

    def ask(self, query, **kw):             # noqa: ARG002 — firma della porta
        return {"intent": "find",
                "results": [{"id": "f1", "text": "La prova gratuita dura 14 giorni.",
                             "score": self._best, "status": "model_claim",
                             "grounding_score": None, "topic": "listino"}]}

    def _auto_relevance_floor(self):
        return self._floor


def _porta_sdk(tmp_path, monkeypatch, *, pav=_CALIBRATO):
    monkeypatch.setattr(Memory, "_auto_relevance_floor", lambda self, **_k: pav)
    m = Memory(str(tmp_path / "sdk.db"))
    m.add("Il banco di prova conta dodici fatti misurati.", topic="t")
    r = m.search(_DOMANDA, k=10)
    sp = getattr(r, "sotto_il_pavimento", None)
    return (sp or {}).get("pavimento"), _origine((sp or {}).get("nota", ""))


def _porta_mcp(*, pav=_CALIBRATO):
    out = _avvisi_di_lettura(_AgenteMcp(pav, _BEST), _DOMANDA)
    sp = out.get("sotto_il_pavimento") or {}
    return sp.get("pavimento"), _origine(sp.get("nota", ""))


def _porta_cli(monkeypatch, *, pav=_CALIBRATO):
    monkeypatch.setattr(cli_mod, "_open_memory",
                        lambda *a, **k: _MemCli(_BEST, pav))
    testo = CliRunner().invoke(cli_mod.app, ["ask", _DOMANDA]).output
    if "sotto il pavimento" not in testo:
        return None, None
    import re
    # ⚠️ IL NUMERO DA PRENDERE E' QUELLO DOPO «pavimento», NON IL PRIMO FRA
    # PARENTESI. La riga della CLI e' «il migliore di questi (0.900) sta sotto
    # il pavimento … (0.950)»: una regex sul primo match legge il BEST e lo
    # scambia per la soglia. Prima stesura di questo file: `sdk 0.95, mcp 0.95,
    # cli 0.9` — sembrava un difetto del prodotto ed era il lettore.
    n = re.search(r"pavimento[^(]*\((\d\.\d{3})\)", testo.replace("\n", " "))
    return (float(n.group(1)) if n else None), _origine(testo)


@pytest.fixture()
def tre_porte(tmp_path, monkeypatch):
    """Le tre letture, con la variabile impostata. `manometti` sposta UNA porta."""
    def _leggi(manometti: str | None = None):
        monkeypatch.setenv("ENGRAM_AVVISO_MIN_RELEVANCE", str(_SOGLIA_IMPOSTATA))
        # la manomissione toglie la variabile alla sola porta indicata, che
        # e' esattamente il difetto curato oggi due volte: una porta che legge
        # il calibrato mentre le altre leggono la soglia impostata.
        def _pav_di(nome):
            return _CALIBRATO
        letture = {}
        for nome, fn in (("sdk", lambda: _porta_sdk(tmp_path, monkeypatch)),
                         ("mcp", _porta_mcp),
                         ("cli", lambda: _porta_cli(monkeypatch))):
            if nome == manometti:
                monkeypatch.delenv("ENGRAM_AVVISO_MIN_RELEVANCE", raising=False)
                letture[nome] = fn()
                monkeypatch.setenv("ENGRAM_AVVISO_MIN_RELEVANCE",
                                   str(_SOGLIA_IMPOSTATA))
            else:
                letture[nome] = fn()
        return letture
    return _leggi


def test_P1_le_tre_porte_dichiarano_la_stessa_soglia(tre_porte):
    """P1 — atteso VERDE: e' la cura di oggi. Il suo RED e' `test_P1_RED`."""
    letture = tre_porte()
    soglie = {n: v[0] for n, v in letture.items()}
    assert all(s is not None for s in soglie.values()), (
        f"ogni porta deve avvisare: {soglie}")
    assert len(set(soglie.values())) == 1, (
        f"le tre porte devono dichiarare LA STESSA soglia, hanno detto {soglie}")
    assert set(soglie.values()) == {_SOGLIA_IMPOSTATA}


@pytest.mark.parametrize("porta", ["sdk", "mcp", "cli"])
def test_P1_RED_se_una_porta_si_sposta_il_presidio_morde(tre_porte, porta):
    """🔑 IL RED PROVOCATO: manomessa UNA porta, il presidio DEVE accorgersene.

    Senza questo, `test_P1` potrebbe essere verde per costruzione — e un
    presidio che non sa diventare rosso non presidia niente. E' la forma esatta
    del difetto curato oggi due volte: una porta che legge il calibrato mentre
    le altre leggono la soglia impostata.
    """
    soglie = {n: v[0] for n, v in tre_porte(manometti=porta).items()}
    assert len(set(soglie.values())) > 1, (
        f"manomettendo «{porta}» le soglie devono divergere, sono {soglie}: "
        "il presidio non morde")


def test_P2_le_tre_porte_dichiarano_la_stessa_ORIGINE(tre_porte):
    """P2 — atteso ROSSO alla prima esecuzione, e non per una manomissione.

    Con la variabile impostata tutte e tre devono dire «dalla variabile». SDK e
    MCP dicono «calibrata su questo corpus»: una frase FALSA in una ricevuta.
    """
    origini = {n: v[1] for n, v in tre_porte().items()}
    assert set(origini.values()) == {_DA_VARIABILE}, (
        f"con la variabile impostata ogni porta deve dichiararla come origine, "
        f"hanno detto {origini}")
