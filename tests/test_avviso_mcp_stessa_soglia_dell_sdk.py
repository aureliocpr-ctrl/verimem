"""La porta MCP e l'SDK devono dichiarare LA STESSA soglia di bassa confidenza.

IL DIFETTO, e l'ho introdotto io il 2026-09-02. `client.py` ha preso
`_pavimento_avviso()` — la soglia dell'avviso, separata da quella del taglio,
con `ENGRAM_AVVISO_MIN_RELEVANCE` per chi ha rimisurato sul suo corpus. Ma la
porta MCP **non riusa** quel campo: `_avvisi_di_lettura` RICOSTRUISCE l'avviso
con `_pavimento_di(agent)`, che legge solo `_auto_relevance_floor`.
⇒ chi imposta la variabile la vede valere sull'SDK e NON sulla porta
dell'agente: **una memoria, due risposte** — la stessa classe di difetto che
questo file di test presidia da agosto («CLI avvisa, SDK avvisa, MCP tace»),
riaperta da una cura fatta su una superficie sola.

⚠️ IN UNA MEMORIA PER AGENTI QUESTA E' LA PORTA CHE CONTA DI PIU', e il
docstring di `_avvisi_di_lettura` lo dice gia': «un difetto che qui non arriva
e' codice che gira e il cui effetto non raggiunge mai l'utente».

PERCHE' LA SOGLIA VA CAMBIATA — misurato il 2026-09-02 sul corpus vivo
(17 279 fatti; 80 query vere, 17 in tema senza risposta, 10 fuori tema)::

    soglia 0,8805 (il calibrato)   VERE marcate 47/80 (58,8%)   LONTANE 10/10
    soglia 0,839                   VERE marcate  3/80 ( 3,8%)   LONTANE 10/10

Il commento di `mcp_server.py` lo dichiarava gia' senza il numero: «quanto
spesso questa nota si accendera' NON E' DECISO... col pavimento che la stima
produce scatterebbe su quasi ogni risposta». **Il 58,8% e' quel «quasi ogni».**

⛔ E RESTA VERO CHE `0,839` NON E' UN DEFAULT: su un altro corpus domande CON
risposta hanno `score_migliore` 0,7715 e 0,603 (misurato dentro la suite, in
`test_il_recall_rispondeva_anche_quando_non_sapeva`), mentre sul corpus vivo le
vere stanno a 0,858-0,90. Le scale non sono confrontabili fra corpora: un numero
fisso non e' trasferibile, e il pavimento adattivo e' lavoro 0.8.0. Qui si cura
solo l'ASIMMETRIA fra le due porte.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verimem.mcp_server import _avvisi_di_lettura  # noqa: E402

_PAV_CALIBRATO = 0.88
_BEST = 0.90          # sopra il calibrato, sotto una soglia esplicita di 0.95


class _Sem:
    db_path = None

    def __init__(self, score):
        self._score = score

    def recall(self, query, k=3):          # noqa: ARG002 — firma della porta
        return [("un fatto qualsiasi", self._score)]


class _Agente:
    """La forma minima che `_avvisi_di_lettura` sa leggere."""

    def __init__(self, pav=_PAV_CALIBRATO, score=_BEST):
        self._pav = pav
        self.semantic = _Sem(score)

    def _auto_relevance_floor(self):
        return self._pav


def test_la_variabile_vale_anche_sulla_porta_dell_agente(monkeypatch):
    """RED prima della cura: con la variabile impostata la porta MCP tace.

    Con `best` 0.90 e calibrato 0.88 nessun avviso esce (0.90 non e' sotto
    0.88). Con la soglia dell'avviso a 0.95 l'avviso DEVE uscire e dichiarare
    0.95 — che e' quello che fa gia' l'SDK.
    """
    monkeypatch.setenv("ENGRAM_AVVISO_MIN_RELEVANCE", "0.95")
    out = _avvisi_di_lettura(_Agente(), "una domanda")
    sp = out.get("sotto_il_pavimento")
    assert sp is not None, (
        "con la soglia dell'avviso a 0.95 e il migliore a 0.90 la porta MCP "
        "deve avvisare: oggi legge solo il pavimento calibrato e tace")
    assert sp["pavimento"] == 0.95, (
        f"la porta deve dichiarare la soglia dell'avviso, ha dichiarato "
        f"{sp['pavimento']}")


def test_senza_la_variabile_la_porta_non_cambia(monkeypatch):
    """🔑 CONTROLLO: senza variabile resta il pavimento calibrato, come sempre."""
    monkeypatch.delenv("ENGRAM_AVVISO_MIN_RELEVANCE", raising=False)
    # best 0.50, sotto il calibrato 0.88 -> l'avviso esce col calibrato
    out = _avvisi_di_lettura(_Agente(score=0.50), "una domanda")
    sp = out.get("sotto_il_pavimento")
    assert sp is not None
    assert sp["pavimento"] == _PAV_CALIBRATO, (
        f"senza variabile deve restare il calibrato {_PAV_CALIBRATO}, ha "
        f"dichiarato {sp['pavimento']}")


def test_su_un_negozio_non_calibrato_la_porta_tace(monkeypatch):
    """🔑 IL CONTROLLO CHE DEVE POTER FALLIRE.

    `if pav` in `_avvisi_di_lettura` e' la stessa guardia che l'SDK ha in
    `client.py`: dove il negozio non si e' calibrato i punteggi stanno su
    un'altra scala e confrontarli con una soglia misurata altrove accenderebbe
    l'avviso su tutto. La cura NON deve rimuovere quella guardia — senza questo
    test, farlo passerebbe con gli altri due verdi.
    """
    monkeypatch.setenv("ENGRAM_AVVISO_MIN_RELEVANCE", "0.95")
    out = _avvisi_di_lettura(_Agente(pav=0.0, score=0.10), "una domanda")
    assert out.get("sotto_il_pavimento") is None, (
        "su un negozio non calibrato la porta deve tacere, anche con la "
        "variabile impostata")
