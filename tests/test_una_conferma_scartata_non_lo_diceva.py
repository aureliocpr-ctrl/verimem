"""Una conferma da UNA fonte sola veniva scartata in silenzio.

FINDING DI ws5, con una diagnosi da correggere e un fenomeno vero.

LA SUA MISURA, esatta::

    inizio                 trust=0.5000
    +1 contraddizione      trust=0.3333
    +1 conferma            trust=0.3333    ATTESO 0.500
    +2 conferme            trust=0.3333    ATTESO 0.600

LA SUA DIAGNOSI, da correggere: «le CONFERME non arrivano al ledger» e «una
fonte che sbaglia una volta resta penalizzata per sempre». Rimisurato::

    inizio                      trust=0.5
    +1 contraddizione (1 fonte) trust=0.3333   <- UNA sola BASTA
    +1 conferma  (1 fonte)      trust=0.3333   <- RIFIUTATA: servono >=2
    +1 conferma  (2 fonti)      trust=0.5      <- REGISTRATA
    +1 conferma  (2 fonti)      trust=0.6      <- e RISALE

La conferma arriva eccome: viene **rifiutata da una regola documentata**, che
`observe_confirmation` dichiara nel proprio docstring — «≥2 DISTINCT sources
asserted the same accepted value → all rise. A single (or self-duplicated)
source cannot confirm itself» — ed esiste per impedire che una fonte si
auto-confermi. La reputazione RISALE, e la formula citata da ws5 torna esatta:
(1+1)/(1+1+2)=0.5, (2+1)/(2+1+2)=0.6.

🔑 MA L'ASIMMETRIA CHE HA VISTO È VERA E RESTA::

    observe_confirmation   servono >=2 fonti  per SALIRE
    observe_contradiction  ne basta    1      per SCENDERE

⚠️ E IL DIFETTO VERO È CHE IL RIFIUTO ERA MUTO. Chi chiama
`source_trust_observe(confirmation=["fonte_a"])` non riceveva **nessun segnale**
che l'osservazione era stata scartata: il metodo torna `None` e il numero non
si muove. Chi lo usa conclude «il ledger è rotto» — che è esattamente la
conclusione a cui è arrivato un utente esperto in mezz'ora di misure.

La regola NON si tocca (è documentata e ha una ragione anti-collusione). Si
dichiara il rifiuto: il metodo ora restituisce cosa ha registrato e cosa no.
"""
from __future__ import annotations

import pytest

from verimem.client import Memory


@pytest.fixture()
def mem(tmp_path):
    return Memory(str(tmp_path / "s.db"))


def _trust(mem, src):
    return round(mem._source_trust_book().trust(src), 4)


def test_una_conferma_da_una_fonte_sola_DICE_di_essere_stata_scartata(mem):
    """IL CUORE: il numero non si muove, e prima non si sapeva perché."""
    esito = mem.source_trust_observe(confirmation=["fonte_a"])
    assert esito is not None, "il metodo non dichiara nulla"
    assert esito.get("confirmation_recorded") is False
    assert "2" in str(esito.get("reason", "")), esito


def test_una_conferma_da_DUE_fonti_viene_registrata(mem):
    """Il verso opposto, e la regola che non si tocca."""
    esito = mem.source_trust_observe(confirmation=["fonte_a", "fonte_b"])
    assert esito.get("confirmation_recorded") is True
    assert _trust(mem, "fonte_a") > 0.5


def test_la_reputazione_RISALE(mem):
    """⚠️ CORREGGE LA CONCLUSIONE del referto: «una fonte che sbaglia una
    volta resta penalizzata per sempre» è FALSO. Risale, con ≥2 conferme, e la
    formula dichiarata nel codice torna esatta."""
    mem.source_trust_observe(contradiction="fonte_a")
    assert _trust(mem, "fonte_a") == 0.3333
    mem.source_trust_observe(confirmation=["fonte_a", "fonte_b"])
    assert _trust(mem, "fonte_a") == 0.5      # (1+1)/(1+1+2)
    mem.source_trust_observe(confirmation=["fonte_a", "fonte_b"])
    assert _trust(mem, "fonte_a") == 0.6      # (2+1)/(2+1+2)


def test_una_contraddizione_da_UNA_fonte_basta_a_scendere(mem):
    """L'ASIMMETRIA, messa agli atti così com'è: ≥2 per salire, 1 per
    scendere. Non è curata qui — è una scelta di design che va discussa, non
    ribaltata da me di notte — ma da ora è scritta in un test invece che
    scoperta da un utente in mezz'ora di misure."""
    mem.source_trust_observe(contradiction="fonte_a")
    assert _trust(mem, "fonte_a") < 0.5


def test_chi_non_passa_conferme_non_riceve_rumore(mem):
    """IL PRESIDIO: la dichiarazione compare solo dove c'è qualcosa da dire."""
    esito = mem.source_trust_observe(contradiction="fonte_a")
    assert "confirmation_recorded" not in esito, esito
