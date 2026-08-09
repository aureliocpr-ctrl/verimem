"""Il campo `moat` affermava l'implicazione anche sui fatti respinti.

`hippo_remember` restituisce un campo `moat` che deve dire in quale dei
QUATTRO stati si trova il giudizio — e il commento che lo introduce lo dice
esplicitamente: «Four states, because "you gave me nothing to check" and "I am
switched off" send the caller to fix different things».

Gli stati implementati erano tre. Il ramo del giudizio girato:

    mcp_server.py:12694
    if isinstance(_gs_out, (int, float)):
        _moat = f"judged {_gs_out:.1f} — the source entails this fact"

discrimina su «il giudizio E' girato» e vi attacca una frase che asserisce
L'ESITO. Misurato dall'altra istanza eseguendo due scritture vere: la stessa
ricevuta portava

    moat:    "judged 0.3 — the source entails this fact"
    status:  quarantined
    warning: source does not entail

cioè tre campi della stessa risposta, due che dicono no e uno che dice sì.

E' il campo che la regola O3 prescrive di leggere quando un fatto torna «not
run»: mente proprio a chi segue la regola.

E' anche il MIO sweep mancato: `76d5dc1c` ha curato la stessa identica cosa
sulla ricevuta della CLI («la ricevuta diceva "the source entails" anche
mentre bocciava») e non ha guardato questo canale — cinque ore prima, nello
stesso giorno.
"""
from __future__ import annotations

import asyncio
import json

import pytest


def _remember(args: dict) -> dict:
    from verimem import mcp_server as srv
    res = asyncio.run(srv.call_tool("hippo_remember", args))
    return json.loads(res[0].text)


@pytest.fixture()
def store(tmp_path, monkeypatch):
    from verimem import mcp_server as srv
    from verimem.client import Memory

    m = Memory(path=tmp_path / "m.db")

    class _Ag:
        def __init__(self):
            self.semantic = m.semantic
    monkeypatch.setattr(srv, "_ag", lambda: _Ag())
    return m


def test_un_fatto_respinto_non_si_sente_dire_che_la_source_lo_implica(store):
    """Il caso misurato: punteggio basso, status quarantined, e il campo che
    dovrebbe spiegare il rifiuto affermava l'implicazione."""
    out = _remember({
        "proposition": "Il piano annuale costa 500 euro.",
        "topic": "t",
        "source": "Il piano annuale costa 100 euro e include il supporto.",
    })
    moat = str(out.get("moat", ""))
    if "judged" not in moat:
        pytest.skip(f"il moat non ha giudicato su questo ambiente: {moat!r}")
    if str(out.get("status", "")) != "quarantined":
        pytest.skip(f"non respinto qui: status={out.get('status')!r}")
    assert "does NOT entail" in moat or "entails" not in moat, (
        f"il campo afferma l'implicazione mentre il fatto e' respinto: {moat!r}")


def test_un_fatto_ammesso_continua_a_dirlo(store):
    """Il caso che gia' funzionava non deve rompersi."""
    out = _remember({
        "proposition": "Il piano annuale costa 100 euro.",
        "topic": "t",
        "source": "Il piano annuale costa 100 euro e include il supporto.",
    })
    moat = str(out.get("moat", ""))
    if "judged" not in moat:
        pytest.skip(f"il moat non ha giudicato: {moat!r}")
    if str(out.get("status", "")) == "quarantined":
        pytest.skip("respinto: non e' questo il caso")
    assert "entails this fact" in moat and "NOT" not in moat, moat


def test_senza_source_il_campo_dice_che_non_ha_girato(store):
    """Il terzo stato resta distinto: «non ho niente da controllare» non e'
    «ho controllato e passa»."""
    out = _remember({"proposition": "Una nota qualunque.", "topic": "t"})
    moat = str(out.get("moat", ""))
    assert "not run" in moat, moat
