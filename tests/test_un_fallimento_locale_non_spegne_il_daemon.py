"""Un caricamento fallito QUI non deve far smettere di chiedere a un ALTRO processo.

`try_local_score` chiedeva al daemon condiviso solo quando `judge._load_failed`
era falso. Ma quel campo dice che il caricamento e' fallito **in questo
processo** — RAM, file corrotto, torch assente, una macchina piccola — e il
daemon e' un processo separato col modello gia' in memoria: puo' stare
benissimo. Da quel momento il giudizio non veniva piu' chiesto a chi poteva
darlo.

E la riga sopra la condizione prometteva l'opposto: *«Se il daemon non c'e', non
sa giudicare o e' lento, si degrada ESATTAMENTE come prima»*. Li' non si
degradava: **si saltava il daemon a priori, senza avere alcuna informazione
sulla sua salute.**

MISURATO ALLA PORTA il 2026-08-30 alle 22:16 con il daemon VIVO (porta 61574),
A/B nella stessa esecuzione — banco
`docs/stato-reale/banchi/ws3-un-fallimento-locale-spegne-il-daemon-che-sta-bene.py`::

    _load_failed=False  ->  try_local_score  = (0.5561, 99.64)
    _load_failed=True   ->  try_local_score  = None          <- la clausola
    la STESSA strada a mano ->  _gate_via_daemon = [0.5561]   <- il daemon RISPONDE

⚠️ E IL BANCO SI ERA RIFIUTATO DI CONCLUDERE alle 20:43, quando il daemon era
giu': senza un daemon vivo non si distingue «la clausola spegne una strada» da
«non c'era una strada da spegnere». Il reperto e' rimasto una LETTURA del
sorgente per un'ora e mezza, e lo e' stato detto, finche' il daemon non e'
tornato.

PERCHE' IL COSTO NON E' SIMMETRICO, ed e' la ragione della cura: chiedere costa
una connessione locale con timeout; NON chiedere costa **una scrittura ammessa
senza giudizio** — che il docstring di `_gate_via_daemon` chiama *«precisamente
cio' che questo prodotto esiste per non fare»*.

⚠️ QUESTO FILE NON DIPENDE DAL DAEMON. Il daemon si simula sostituendo
`_gate_via_daemon`: il presidio verifica che la strada venga PERCORSA, non che
sul portatile di chi esegue ci sia un servizio acceso.
"""

from __future__ import annotations

import inspect

import pytest

from verimem import local_grounding as lg


@pytest.fixture
def giudice_freddo(monkeypatch):
    """Un giudice senza scorer, in delegate-only: il regime del server MCP."""
    j = lg.get_local_judge()
    monkeypatch.setattr(j, "_scorer", None, raising=False)
    monkeypatch.setattr(lg, "_delegate_only", lambda: True)
    return j


def _daemon_che_risponde(monkeypatch, punteggio: float = 0.42) -> list:
    """Sostituisce il daemon e registra se e' stato interrogato."""
    chiamate: list = []

    def _finto(pairs, *, info=None):
        chiamate.append(pairs)
        return [punteggio]

    monkeypatch.setattr(lg, "_gate_via_daemon", _finto)
    return chiamate


def test_con_il_caricamento_locale_fallito_si_chiede_lo_stesso_al_daemon(
        giudice_freddo, monkeypatch):
    """IL CUORE: e' la cella che dava None finche' la clausola c'era."""
    monkeypatch.setattr(giudice_freddo, "_load_failed", True, raising=False)
    chiamate = _daemon_che_risponde(monkeypatch)
    esito = lg.try_local_score("la fonte", "il claim")
    assert chiamate, (
        "il daemon NON e' stato interrogato con `_load_failed=True`: la "
        "clausola e' tornata, e un guasto locale spegne di nuovo una strada "
        "che funziona")
    assert esito is not None, esito


def test_senza_fallimento_locale_il_daemon_si_chiede_come_prima(
        giudice_freddo, monkeypatch):
    """⚠️ LA POPOLAZIONE OPPOSTA: la cura non deve cambiare il caso sano. Se
    passasse solo la prima, avrei «curato» spostando il problema."""
    monkeypatch.setattr(giudice_freddo, "_load_failed", False, raising=False)
    chiamate = _daemon_che_risponde(monkeypatch)
    assert lg.try_local_score("la fonte", "il claim") is not None
    assert chiamate


def test_se_il_daemon_non_risponde_si_degrada_come_sempre(
        giudice_freddo, monkeypatch):
    """⚠️ IL DEGRADO DICHIARATO, che la cura non deve toccare: daemon assente o
    muto -> None, e il chiamante fa esattamente cio' che faceva prima. Senza
    questa cella, «si chiede sempre al daemon» potrebbe voler dire «e si
    rimane appesi»."""
    monkeypatch.setattr(giudice_freddo, "_load_failed", True, raising=False)
    monkeypatch.setattr(lg, "_gate_via_daemon", lambda pairs, *, info=None: None)
    monkeypatch.setattr(lg, "warm_local_judge_async", lambda: None)
    assert lg.try_local_score("la fonte", "il claim") is None


def test_la_condizione_non_nomina_piu_il_fallimento_locale():
    """Il presidio strutturale, che dice al prossimo PERCHE' la clausola non
    c'e': un campo che descrive QUESTO processo non decide di un ALTRO."""
    riga = next((r.strip()
                 for r in inspect.getsource(lg.try_local_score).splitlines()
                 if "_delegate_only()" in r and r.strip().startswith("if")), "")
    assert riga, "la riga della delega non si trova piu': parser da rivedere"
    assert "_load_failed" not in riga, riga
