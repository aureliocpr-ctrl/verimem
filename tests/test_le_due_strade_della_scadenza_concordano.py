"""La regola «questo fatto è scaduto» è scritta in DUE posti. Devono concordare.

Debito dichiarato nel doc 85, giuntura G4: «due implementazioni della stessa
regola di scadenza — presidio del confronto fra le due: **non misurato**». 26
file di test nominano `valid_until` e nessuno mette le due strade una accanto
all'altra. Questo file lo fa.

LE DUE STRADE
  · riga per riga — `semantic._fact_is_stale(...)`, sui percorsi freddi;
  · vettoriale    — la maschera del percorso caldo di `recall`,
    `fresh_mask = (view_lv <= now) & (view_vu > now)`, con `view_vu = inf` per i
    fatti senza scadenza. Il codice la chiama, testualmente, «specchio
    vettoriale di `_fact_is_stale`».

Uno specchio si incrina in silenzio: se una delle due cambia, il prodotto
risponde in modo diverso a seconda che la lettura sia calda o fredda, e nessuno
se ne accorge finché un utente non chiede due volte la stessa cosa.

⚠️ MA LE DUE NON SONO LA STESSA FUNZIONE, e questo file NON finge che lo siano.
`_fact_is_stale` decide anche sull'ETÀ (decadimento con emivita); la maschera
vettoriale no. Confrontarle sull'età direbbe «divergono» di una divergenza
VOLUTA, e un presidio che dà falsi allarmi viene spento. Qui si confrontano
solo le due regole che entrambe devono applicare:
  ① `valid_until` nel passato  → escluso (hard-expire, non decadimento);
  ② un timestamp di verifica nel FUTURO → escluso (fail-closed anti-spoof:
     un istante impossibile è un segnale di manomissione, non un dato da
     normalizzare).
La terza regola — l'età — è misurata a parte, per DICHIARARE la divergenza
invece di scoprirla il giorno in cui morde.

PREDIZIONI DEPOSITATE PRIMA DI ESEGUIRE (2026-09-05 23:45):
  P1 — sui casi ① e ② le due strade danno lo stesso verdetto.  ATTESA: VERDE.
  P2 — sull'ETÀ divergono: `_fact_is_stale` esclude un fatto vecchio, la
       maschera lo tiene.                                       ATTESA: VERDE
       (cioè: la divergenza esiste ed è quella attesa). Se fosse ROSSA, o la
       maschera ha imparato il decadimento — e allora il percorso caldo taglia
       fatti che il freddo serve — o `_fact_is_stale` l'ha perso.
  P3 — controllo positivo: su un fatto vivo e recente entrambe SERVONO. Senza,
       un P1 verde potrebbe voler dire «escludono sempre tutto».

⚠️ NESSUN GIUDICE e nessuno store: si chiamano le due funzioni pure. Gira in
meno di un secondo e non contende la macchina a chi misura tempi.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from verimem.semantic import _fact_is_stale  # noqa: E402

_ORA = 2_000_000_000.0            # «adesso» del banco
_GIORNO = 86_400.0
_PASSATO = _ORA - 10 * _GIORNO
_FUTURO = _ORA + 10 * _GIORNO
_MOLTO_VECCHIO = _ORA - 3650 * _GIORNO      # dieci anni: oltre ogni emivita


def _fredda(*, lv=None, created=None, vu=None, ignore_age=False) -> bool:
    """True = ESCLUSO, la strada riga per riga."""
    return _fact_is_stale(lv, created if created is not None else _PASSATO,
                          _ORA, valid_until=vu, ignore_age=ignore_age)


def _calda(*, lv=None, vu=None) -> bool:
    """True = ESCLUSO, la maschera del percorso caldo.

    Riprodotta come sta in `semantic.py`: `view_vu = inf` per i fatti senza
    scadenza, e fresco = `(view_lv <= now) & (view_vu > now)`. Non la importo
    perché lì è in linea dentro `recall`, in mezzo al ranking: estrarla per il
    test cambierebbe il codice che il test deve sorvegliare.
    """
    view_lv = np.array([lv if lv is not None else _PASSATO], dtype=float)
    view_vu = np.array([vu if vu is not None else np.inf], dtype=float)
    fresh = (view_lv <= _ORA) & (view_vu > _ORA)
    return not bool(fresh[0])


CASI_COMUNI = [
    ("scaduto: valid_until nel passato", {"vu": _PASSATO}, True),
    ("scaduto adesso: valid_until == now", {"vu": _ORA}, True),
    ("valido: valid_until nel futuro", {"vu": _FUTURO}, False),
    ("senza scadenza", {}, False),
    ("spoof: verifica nel futuro", {"lv": _FUTURO}, True),
    ("spoof + scadenza futura", {"lv": _FUTURO, "vu": _FUTURO}, True),
]


@pytest.mark.parametrize("nome,kw,atteso", CASI_COMUNI,
                         ids=[c[0] for c in CASI_COMUNI])
def test_P1_le_due_strade_danno_lo_stesso_verdetto(nome, kw, atteso):
    """Sulle due regole che entrambe applicano, lo specchio deve riflettere."""
    fredda, calda = _fredda(**kw), _calda(**kw)
    assert fredda == calda == atteso, (
        f"«{nome}»: riga-per-riga dice escluso={fredda}, la maschera dice "
        f"escluso={calda}, atteso {atteso}. Lo specchio si e' incrinato: il "
        "prodotto risponde diversamente a seconda che la lettura sia calda o "
        "fredda")


def test_P2_sull_eta_divergono_ed_e_voluto():
    """La divergenza NOTA, dichiarata invece che scoperta quando morde.

    `_fact_is_stale` nasconde un fatto molto vecchio (decadimento con emivita);
    la maschera vettoriale non conosce l'età e lo tiene. Se questo test
    diventasse rosso, una delle due ha cambiato mestiere — ed è una notizia,
    non un fastidio.
    """
    vecchio = {"lv": _MOLTO_VECCHIO, "created": _MOLTO_VECCHIO}
    assert _fredda(**vecchio) is True, (
        "la strada fredda NON esclude piu' un fatto di dieci anni: ha perso il "
        "decadimento per eta'")
    assert _calda(lv=_MOLTO_VECCHIO) is False, (
        "la maschera vettoriale ESCLUDE per eta': ha imparato il decadimento, "
        "e allora il percorso caldo taglia fatti che il freddo serve")


def test_P3_controllo_positivo_un_fatto_vivo_lo_servono_entrambe():
    """Senza questo, un P1 verde potrebbe voler dire «escludono sempre tutto»."""
    assert _fredda() is False
    assert _calda() is False
