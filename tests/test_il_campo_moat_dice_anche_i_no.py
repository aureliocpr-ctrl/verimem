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


def test_un_fatto_ammesso_non_riceve_il_messaggio_del_respinto(store):
    """L'INTENTO di questo test resta quello di prima — un ammesso non deve
    sentirsi dire cio' che si dice a un respinto — ma l'assert non lega piu'
    l'intento a UNA stringa.

    25/08, @ws1: la frase che questo test fissava («entails this fact») e' stata
    misurata FALSA su un ammesso. Fonte «…Nessun altro tag esiste» + claim «…il
    tag v0.7.6 e' gia' stato pubblicato» -> 99.98 e «the source entails this
    fact» (identico in EN, 99.98168). Qui sotto il caso e' una citazione
    letterale, quindi l'implicazione c'e' davvero e il punteggio e' alto
    ESATTAMENTE COME LA': il gate non distingue i due, e nessuna condizione puo'
    dire «entails» solo quando e' vero. ⇒ il ramo degli ammessi ora riporta il
    punteggio invece di asserire il mondo, e questo test verifica la proprieta'
    che conta (non confondere ammesso con respinto) senza fissare il testo.
    Cfr. `tests/test_la_riga_che_mente.py`.
    """
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
    assert "does NOT entail" not in moat, (
        f"a un fatto AMMESSO e' arrivato il messaggio del respinto: {moat!r}")
    assert "judged" in moat, (
        f"il punteggio deve restare leggibile sulla ricevuta: {moat!r}")


def test_senza_source_il_campo_dice_che_non_ha_girato(store):
    """Il terzo stato resta distinto: «non ho niente da controllare» non e'
    «ho controllato e passa»."""
    out = _remember({"proposition": "Una nota qualunque.", "topic": "t"})
    moat = str(out.get("moat", ""))
    assert "not run" in moat, moat


def test_una_quarantena_LESSICALE_non_si_attribuisce_al_moat(store):
    """IL QUARTO STATO, che mancava: il moat PASSA e il fatto e' trattenuto
    lo stesso, da uno screen lessicale.

    I tre test sopra coprono respinto-dal-moat, ammesso, e senza-source. In
    tutti e tre `status == "quarantined"` coincide con «il moat ha detto no»,
    e su quella popolazione la riga del ramo negativo e' VERA. Ma la condizione
    che la sceglie e' `status != "quarantined"` (mcp_server.py:13347), e lo
    status lo decide QUALUNQUE layer: L1.19 chiede un'attestazione di misura e
    trattiene il fatto mentre il giudice ha dato 100.0.

    MISURATO, stesso claim e stessa fonte, un processo, store condiviso:
        SDK  status=quarantined  score=100.0  layer=['L1.19']  moat='passed'
        MCP  status=quarantined  score=100.0  layer=['L1.19']
             moat='judged 100.0 — the source does NOT entail this fact:
                   that is why it is quarantined'
    La stessa decisione, spiegata in due modi opposti a seconda della porta.

    ⚠️ E il danno non e' estetico: chi legge quella frase conclude che la sua
    FONTE e' cattiva e la riscrive, mentre la cura e' aggiungere un `bench:` a
    `verified_by`. Una motivazione falsa manda a fare la cosa sbagliata.

    L'SDK non ha il difetto perche' DERIVA il campo da cio' che il gate ha
    detto (`esito_del_moat(gate, warnings, source=source)`, client.py:942) e un
    suo commento registra proprio questo caso: «moat passa + parola L1 :
    moat=passed gs=96.810 QUARANTINED». Qui invece lo status viene ricalcolato,
    e ricalcolare e' cio' che permette alle due porte di divergere.

    ⛔ IL CLAIM E' IN INGLESE DI PROPOSITO: la forma italiana con l'apostrofo
    cade su L1.19 solo grazie a una cura del 27/08, e un presidio che dipende
    da un'altra cura diventa muto se quella viene ritirata. In inglese L1.19
    scatta da sempre.
    """
    out = _remember({
        "proposition": "Latency is 240 ms.",
        "topic": "t",
        "source": "  latency p50 ......... 240 ms\n  campioni ............ 1000",
    })
    moat = str(out.get("moat", ""))
    if "judged" not in moat:
        pytest.skip(f"il moat non ha giudicato su questo ambiente: {moat!r}")
    if str(out.get("status", "")) != "quarantined":
        pytest.skip(f"L1.19 non ha trattenuto qui: status={out.get('status')!r}")
    layer = [w.get("layer") for w in (out.get("anti_confab_warnings") or [])
             if isinstance(w, dict)]
    if not any(str(x).startswith("L1") for x in layer):
        pytest.skip(f"la quarantena non viene da uno screen lessicale: {layer}")
    assert "does NOT entail" not in moat, (
        f"la quarantena viene da {layer} e il giudice ha dato "
        f"{out.get('grounding_score')}, ma il campo che spiega il PERCHE' "
        f"attribuisce il rifiuto al moat: {moat!r}. Sulla stessa scrittura "
        "l'SDK dice 'passed'")
