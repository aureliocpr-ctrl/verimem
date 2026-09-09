"""T-MAP-11, seconda parte — la stessa soglia, due politiche diverse.

Le due porte usano lo STESSO numero: `grounding_gate.LOCAL_CE_MOAT_THRESHOLD`
= 40.0, e la riga 550 di quel file lo dice («same as the conversation-ingest
path»). Ma il write path TRATTIENE la fascia incerta [40, 80)
(`_ce_band_enforced`, attiva di default dal 2026-07-19) e l'ingest no: sopra 40
ammetteva e basta.

Misurato il 2026-09-09: tre invenzioni plausibili sullo stesso dialogo valevano
**60,22 · 88,80 · 50,00** — due delle tre cadono nella fascia, ed e' esattamente
il «2 su 3 fermati da `Memory.add(source=)` e 0 su 3 dall'ingest» che la mappa
aveva registrato senza saperne la causa.

Qui il punteggio e' FINTO apposta (60,22, il numero vero della prima
invenzione): il banco misura la POLITICA — cosa fa la porta con un punteggio
nella fascia — non la bravura del modello, che e' misurata a parte su HaluEval
(dev n=100: 46 invenzioni ammesse su 100; heldout n=200 mai letto: 94 su 200).

    python -m pytest tests/test_l_ingest_ammetteva_la_fascia_che_il_write_path_trattiene.py -q
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import types

import pytest

DIALOGO = ("Cliente: confermo il canone del capannone 12 a 5900 euro. "
           "Agente: perfetto, la consegna resta il 3 marzo.")
DETTO = "Il canone del capannone 12 e' 5900 euro."
#: nessuno l'ha detto. Punteggio vero del cross-encoder su questa coppia: 60,22
#: — sopra la soglia 40 dell'ingest, DENTRO la fascia [40, 80) del write path.
NELLA_FASCIA = "Il capannone 12 e' stato venduto nel 2019."


class _Estrattore:
    def complete(self, system, messages, *, model=None, max_tokens=1200):
        r = types.SimpleNamespace()
        r.text = "\n".join([DETTO, NELLA_FASCIA])
        return r


def _giudice_finto(monkeypatch: pytest.MonkeyPatch) -> None:
    """Il cross-encoder, sostituito da due numeri veri e fermi."""
    from verimem import local_grounding

    def _score(source: str, fact: str, *, focus_budget=None):
        return (60.22 if fact == NELLA_FASCIA else 99.90), 99.6413

    monkeypatch.setattr(local_grounding, "try_local_score", _score)


def _righe(db_path) -> dict[str, str]:
    with sqlite3.connect(str(db_path)) as con:
        return dict(con.execute("SELECT proposition, status FROM facts").fetchall())


def _ingerisci_dalla_porta_mcp(monkeypatch: pytest.MonkeyPatch, tmp_path, nome: str):
    from verimem import mcp_server
    from verimem.semantic import SemanticMemory

    sm = SemanticMemory(db_path=tmp_path / nome)
    agente = types.SimpleNamespace(
        semantic=sm, wake=types.SimpleNamespace(llm=_Estrattore()))
    monkeypatch.setattr(mcp_server, "_ag", lambda: agente)
    monkeypatch.setattr(mcp_server, "_agent", agente, raising=False)
    fuori = asyncio.run(mcp_server._call_tool_impl("hippo_ingest_conversation", {
        "messages": [{"role": "user", "content": DIALOGO}],
        "conversation_id": "t-map-11-banda",
    }))
    return json.loads(fuori[0].text), _righe(sm.db_path)


@pytest.fixture()
def isolato(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("HIPPO_ENCODE_DELEGATE_ONLY", raising=False)
    monkeypatch.delenv("VERIMEM_CE_BAND_ENFORCE", raising=False)
    monkeypatch.delenv("ENGRAM_INGEST_GROUND_THRESHOLD", raising=False)
    return tmp_path


def test_un_punteggio_nella_fascia_incerta_non_entra_come_un_fatto_detto(
        monkeypatch: pytest.MonkeyPatch, isolato) -> None:
    """RED prima della cura: 60,22 > 40 -> ammesso, e il fatto che nessuno ha
    detto sta in memoria accanto a quello vero."""
    _giudice_finto(monkeypatch)
    esito, righe = _ingerisci_dalla_porta_mcp(monkeypatch, isolato, "fascia.db")
    assert esito.get("error") is None, esito
    assert righe.get(DETTO) != "quarantined", righe
    assert righe.get(NELLA_FASCIA) == "quarantined", (
        f"un punteggio nella fascia [40, 80) — 60,22 — e' entrato come "
        f"{righe.get(NELLA_FASCIA)!r}, mentre Memory.add lo tratterrebbe: "
        f"righe {righe}")


def test_la_ricevuta_dice_quanti_ne_ha_fermati(
        monkeypatch: pytest.MonkeyPatch, isolato) -> None:
    """Una quarantena che la ricevuta non nomina e' invisibile a chi chiama."""
    _giudice_finto(monkeypatch)
    esito, _ = _ingerisci_dalla_porta_mcp(monkeypatch, isolato, "ricevuta.db")
    assert esito.get("quarantined") == 1, esito
    assert "does NOT state" in (esito.get("note") or ""), esito.get("note")


def test_l_interruttore_della_fascia_e_onorato_anche_qui(
        monkeypatch: pytest.MonkeyPatch, isolato) -> None:
    """L'A/B nella stessa esecuzione: con VERIMEM_CE_BAND_ENFORCE=0 — la leva
    che il write path gia' offre — la porta torna a comportarsi come prima.
    Se questo test fosse verde anche col primo, la fascia non starebbe
    decidendo niente."""
    _giudice_finto(monkeypatch)
    monkeypatch.setenv("VERIMEM_CE_BAND_ENFORCE", "0")
    _esito, righe = _ingerisci_dalla_porta_mcp(monkeypatch, isolato, "spenta.db")
    assert righe.get(NELLA_FASCIA) != "quarantined", righe
