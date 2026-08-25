"""Il campo `moat` afferma l'implicazione anche quando la fonte NEGA il fatto.

`test_il_campo_moat_dice_anche_i_no.py` ha curato il ramo dei RESPINTI: un
fatto quarantinato non si sente più dire che la fonte lo implica. Resta scoperto
il ramo degli AMMESSI, e lì la frase non è un dettaglio di forma: è l'unica cosa
che l'agente legge per sapere se può fidarsi.

MISURATO (25/08, build 397c6375, `call_tool` in-process, store temporaneo):

    source     «Il registro dei rilasci mostra: tag v0.7.0 pubblicato su PyPI
                il 10 luglio. Il file pyproject.toml dichiara version = 0.7.6.
                NESSUN ALTRO TAG ESISTE.»
    claim      «Il registro dei rilasci mostra il tag v0.7.0 pubblicato su
                PyPI, e il tag v0.7.6 e' gia' stato pubblicato.»
    ricevuta   grounding 99.98391723632812 · status model_claim · layers []
               anti_confab_warnings []
               moat  «judged 100.0 — the source entails this fact»

La fonte dice che nessun altro tag esiste; il claim afferma che quel tag è
stato pubblicato; il campo risponde che la fonte IMPLICA il fatto. Identico in
inglese (99.98168182373047), quindi non è un difetto di lingua.

PERCHE' NON BASTA «dire entails solo quando è vero»: il gate non lo sa. Sul caso
vero di `test_il_campo_moat_dice_anche_i_no` (una citazione letterale) il
punteggio è alto esattamente come qui. Le due situazioni sono indistinguibili
per il giudice, quindi l'unica frase che non mente in entrambe è quella che
riporta CIO' CHE IL GATE HA FATTO — ha dato un punteggio — invece di asserire
un fatto sul mondo.

Cfr. la misura di @ws2 sulla contraddizione lessicalmente esplicita (presa 6/6,
IT ed EN): il gate trova il termine opposto quando c'è. Qui non c'è nulla da
confrontare — serve applicare un universale — e il punteggio resta alto.
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


FONTE_CHE_NEGA = (
    "Il registro dei rilasci mostra: tag v0.7.0 pubblicato su PyPI il 10 "
    "luglio. Il file pyproject.toml dichiara version = 0.7.6. Nessun altro "
    "tag esiste."
)
CLAIM_FALSO = (
    "Il registro dei rilasci mostra il tag v0.7.0 pubblicato su PyPI, e il "
    "tag v0.7.6 e' gia' stato pubblicato."
)


def test_un_ammesso_non_afferma_che_la_fonte_lo_implica(store):
    """Il campo non deve asserire l'implicazione: il gate l'ha SCORATA."""
    out = _remember({
        "proposition": CLAIM_FALSO, "topic": "t", "source": FONTE_CHE_NEGA,
    })
    moat = str(out.get("moat", ""))
    if "judged" not in moat:
        pytest.skip(f"il moat non ha giudicato su questo ambiente: {moat!r}")
    if str(out.get("status", "")) == "quarantined":
        pytest.skip(f"respinto qui: non e' il ramo degli ammessi ({moat!r})")
    assert "the source entails this fact" not in moat, (
        "il campo afferma che la fonte IMPLICA il fatto, ma la fonte lo nega "
        f"('Nessun altro tag esiste') e il gate non ha verificato nulla: {moat!r}"
    )


def test_un_ammesso_riporta_il_punteggio_non_un_verdetto_sul_mondo(store):
    """Qualunque sia il testo scelto, deve restare leggibile il punteggio e
    deve NON esserci un'asserzione di implicazione."""
    out = _remember({
        "proposition": CLAIM_FALSO, "topic": "t", "source": FONTE_CHE_NEGA,
    })
    moat = str(out.get("moat", ""))
    if "judged" not in moat:
        pytest.skip(f"il moat non ha giudicato: {moat!r}")
    if str(out.get("status", "")) == "quarantined":
        pytest.skip("respinto: non e' questo il ramo")
    assert "judged" in moat, moat
    assert "entails this fact" not in moat or "does NOT" in moat, moat
