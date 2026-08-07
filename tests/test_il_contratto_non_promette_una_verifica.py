"""Il contratto emetteva `last_verified_at` esattamente sui fatti mai
verificati.

Due fatti misurati, che presi insieme si invertono:

1. ws5, 2026-08-07 — il campo avanza su 2762 fatti e di quelli **zero**
   hanno un `grounding_score`: si muove solo dove un giudizio non c'è
   mai stato (migrazione o re-embedding — un tocco, non un verdetto).
2. `fact_contract.fact_payload` lo OMETTE quando coincide con
   `created_at` e lo TIENE quando differisce.

⇒ Un consumatore che legge un fatto vede una chiave chiamata
`last_verified_at` **solo** sui fatti che nessuno ha mai verificato, e non
la vede su quelli che un verdetto ce l'hanno. Il segnale è invertito, e
succede nel modulo che esiste per essere l'unica superficie onesta.

La regola di emissione ora è la stessa che governa la freschezza nel
dossier: il campo esce quando un VERDETTO lo sostiene. Una definizione
sola, due chiamanti — due copie della stessa regola divergono, ed è la
prima delle classi che questo prodotto ripete.

⚠️ Il dato grezzo non sparisce: `trust_report` continua a portarlo, dove
sta accanto alla spiegazione di cosa sia. Sparisce dal payload generico,
dove veniva letto per quello che il nome promette.
"""
from __future__ import annotations

import time

from verimem.fact_contract import fact_payload, verifica_sostenuta

_GIORNO = 86400.0


class _Fatto:
    """Duck-typed come tutto ciò che passa dal contratto (il modulo accetta
    di proposito anche ciò che non è un `Fact`)."""

    def __init__(self, *, last_verified_at, grounding_score):
        self.id = "f1"
        self.proposition = "the head office is in Milan"
        self.topic = "hq"
        self.status = "provisional"
        self.confidence = 0.5
        self.verified_by = None
        self.created_at = time.time() - 80 * _GIORNO
        self.last_verified_at = last_verified_at
        self.grounding_score = grounding_score


def test_un_tocco_senza_verdetto_non_esce_come_verifica():
    """Il caso dei 2762: il campo è avanzato, il giudizio non c'è mai
    stato. Una chiave che si chiama così, su un fatto così, mente."""
    out = fact_payload(_Fatto(last_verified_at=time.time() - _GIORNO,
                              grounding_score=None))
    assert "last_verified_at" not in out, out


def test_con_un_verdetto_il_campo_esce():
    """Non lo sto sopprimendo: quando un verdetto lo sostiene, la
    ri-verifica è un dato vero e va detta."""
    ora = time.time()
    out = fact_payload(_Fatto(last_verified_at=ora - _GIORNO,
                              grounding_score=98.0))
    assert out["last_verified_at"] == ora - _GIORNO


def test_coincidente_con_la_creazione_resta_omesso_come_prima():
    """La regola vecchia non si perde: coincidere con `created_at` non
    dice niente, e continuava a non uscire."""
    f = _Fatto(last_verified_at=None, grounding_score=98.0)
    f.last_verified_at = f.created_at
    assert "last_verified_at" not in fact_payload(f)


def test_la_regola_e_UNA_e_la_usano_entrambe_le_superfici():
    """Il dossier di fiducia e il contratto devono decidere con la STESSA
    funzione: due copie della stessa regola divergono, ed è la prima
    delle classi che questo prodotto ripete."""
    ora = time.time()
    senza = _Fatto(last_verified_at=ora - _GIORNO, grounding_score=None)
    con = _Fatto(last_verified_at=ora - _GIORNO, grounding_score=98.0)

    assert verifica_sostenuta(senza) is False
    assert verifica_sostenuta(con) is True

    import inspect

    from verimem import trust_report
    assert "verifica_sostenuta" in inspect.getsource(trust_report), (
        "il dossier riscrive la regola invece di importarla")


def test_il_dato_grezzo_resta_dove_e_spiegato():
    """Non sparisce dal prodotto: il dossier lo porta comunque, accanto a
    `age_basis` che dice cosa il numero misura davvero."""
    import inspect

    from verimem import trust_report
    src = inspect.getsource(trust_report)
    assert '"last_verified_at": _lv_raw' in src, (
        "il dossier deve continuare a esporre il campo grezzo")
