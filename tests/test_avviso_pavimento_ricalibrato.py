"""L'avviso «sotto il pavimento» dichiara una soglia MISURATA, non quella del taglio.

PERCHE'. `Risultati.sotto_il_pavimento` esiste dalla 0.7.x ed e' gia' acceso nel default,
ma dichiarava il pavimento CALIBRATO (`_auto_relevance_floor`). Misurato il 2026-09-02 sul
corpus vivo (17 279 fatti; 80 query vere, 17 domande in tema senza risposta, 10 fuori tema,
`scripts/banco_avviso_marcatura.py`):

    soglia 0,8805 (il calibrato)   VERE marcate 47/80 (58,8%)   LONTANE 10/10   VICINE 17/17
    soglia 0,839  (questa)         VERE marcate  3/80 ( 3,8%)   LONTANE 10/10   VICINE  3/17

⇒ col calibrato l'avviso si accendeva su SEI RISPOSTE BUONE SU DIECI: un segnale che esce
quasi sempre non informa, ed e' il difetto che il commento di `client.py` gia' temeva
(«rumore al posto del silenzio»). ⚠️ NON E' GRATIS: la copertura sulle domande VICINE
scende da 17/17 a 3/17 — si scambia copertura con precisione, e i due numeri vanno detti
insieme.

⚠️ PERCHE' UN NUMERO FISSO E NON `auto`: tre stime del pavimento calibrato sullo stesso
store hanno dato 0,8797 · 0,8805 · 0,8853, cioe' un'escursione di 5,6 millesimi contro una
finestra utile di 13 (0,833-0,845).

🔑 PERCHE' QUESTI TEST FORZANO IL PAVIMENTO CALIBRATO A UN VALORE DI PRODUZIONE. Su uno
store di test `_auto_relevance_floor()` vale `0.0` — non ha materiale per calibrarsi — e i
punteggi vivono su un'altra scala. Un test che non lo forzasse misurerebbe un mondo che in
produzione non esiste: la prima stesura di questi test lo faceva, e la cura che ne e' uscita
ha rotto SEI controlli (i test che presidiano il caso in cui l'avviso NON deve uscire).
⇒ qui `_auto_relevance_floor` e' monkeypatchato a `0.88`, il valore osservato sul corpus
vero, e l'ultimo test presidia proprio il negozio NON calibrato.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verimem.client import Memory  # noqa: E402

_DOMANDA_FUORI_TEMA = "ricetta carbonara guanciale pecorino uova"
_PAV_DI_PRODUZIONE = 0.88


def _store(tmp_path, nome, *, calibrato=_PAV_DI_PRODUZIONE, monkeypatch=None):
    m = Memory(str(tmp_path / nome))
    m.add("Il banco di prova conta dodici fatti misurati.", topic="t")
    if monkeypatch is not None:
        monkeypatch.setattr(type(m), "_auto_relevance_floor",
                            lambda self, **_k: calibrato)
    return m


def test_l_avviso_dichiara_il_pavimento_misurato(tmp_path, monkeypatch):
    """Con la variabile impostata, la soglia dichiarata e' quella MISURATA."""
    monkeypatch.setenv("ENGRAM_AVVISO_MIN_RELEVANCE", "0.839")
    m = _store(tmp_path, "avv.db", monkeypatch=monkeypatch)
    r = m.search(_DOMANDA_FUORI_TEMA, k=10)
    sp = getattr(r, "sotto_il_pavimento", None)
    assert sp is not None, "l'avviso deve uscire quando nulla supera la soglia"
    assert sp["pavimento"] == 0.839, (
        f"l'avviso deve dichiarare 0.839, ha dichiarato {sp['pavimento']}")


def test_la_variabile_sovrascrive_il_pavimento_dell_avviso(tmp_path, monkeypatch):
    """Chi ha un corpus diverso rimisura e imposta il suo valore."""
    monkeypatch.setenv("ENGRAM_AVVISO_MIN_RELEVANCE", "0.95")
    m = _store(tmp_path, "avv_env.db", monkeypatch=monkeypatch)
    r = m.search(_DOMANDA_FUORI_TEMA, k=10)
    sp = getattr(r, "sotto_il_pavimento", None)
    assert sp is not None
    assert sp["pavimento"] == 0.95


def test_senza_la_variabile_il_comportamento_non_cambia(tmp_path, monkeypatch):
    """🔑 IL CONTROLLO CHE HA DECISO LA FORMA DELLA CURA.

    Provato ad accendere `0.839` come DEFAULT: quattro controlli di
    `test_il_recall_rispondeva_anche_quando_non_sapeva.py` si sono rotti, perche'
    li' domande CON risposta corretta hanno `score_migliore` `0,7715` e `0,603` —
    molto sotto `0,839`. Sul corpus vivo le vere stanno a 0,858-0,90: le due
    popolazioni non vivono sulla stessa scala, e un numero fisso non e'
    trasferibile. ⇒ senza variabile si dichiara il pavimento calibrato, come
    sempre.
    """
    m = _store(tmp_path, "default.db", monkeypatch=monkeypatch)
    r = m.search(_DOMANDA_FUORI_TEMA, k=10)
    sp = getattr(r, "sotto_il_pavimento", None)
    assert sp is not None
    assert sp["pavimento"] == _PAV_DI_PRODUZIONE, (
        f"senza la variabile deve restare il calibrato {_PAV_DI_PRODUZIONE}, "
        f"ha dichiarato {sp['pavimento']}")


def test_il_taglio_resta_sulla_soglia_di_chi_lo_chiede(tmp_path, monkeypatch):
    """🔑 CONTROLLO CHE DEVE POTER FALLIRE: la cura tocca l'AVVISO, non il TAGLIO.

    `_auto_relevance_floor` ha 10 chiamate in 6 file — il taglio di `search`,
    `explain`, il guardian, quattro punti del server MCP e la mappa
    dell'ignoranza. Spostarne il valore alla FONTE le muoverebbe tutte, ed e'
    l'incidente del 2026-07-30 (`max(floor, noise_floor)`, scritto, misurato e
    ritirato per aver mutato la mappa).
    """
    m = _store(tmp_path, "taglio.db", monkeypatch=monkeypatch)
    r = m.search("banco prova fatti misurati dodici", k=10, min_relevance=0.99)
    sp = getattr(r, "sotto_il_pavimento", None)
    assert sp is not None, "con tutto tagliato l'avviso deve uscire"
    assert sp["pavimento"] == 0.99, (
        f"il taglio deve dichiarare la soglia richiesta, ha dichiarato "
        f"{sp['pavimento']}")


def test_su_un_negozio_NON_calibrato_non_cambia_nulla(tmp_path, monkeypatch):
    """🔑 IL SECONDO CONTROLLO, ed e' quello che la prima stesura non aveva.

    Con `_auto_relevance_floor()` a `0.0` — un negozio troppo piccolo per
    calibrarsi — i punteggi stanno su un'altra scala e confrontarli con `0.839`
    accenderebbe l'avviso su tutto. Il comportamento deve restare quello di
    prima: nessun avviso quando non si e' tagliato niente.
    """
    m = _store(tmp_path, "piccolo.db", calibrato=0.0, monkeypatch=monkeypatch)
    r = m.search(_DOMANDA_FUORI_TEMA, k=10)
    assert getattr(r, "sotto_il_pavimento", None) is None, (
        "su un negozio non calibrato l'avviso non deve comparire: la soglia "
        "misurata su un altro corpus non e' confrontabile con questi punteggi")
