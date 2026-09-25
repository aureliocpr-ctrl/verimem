"""T204 — la ricevuta dell'ingest deve dire se il giudice ha girato.

Alla PORTA, SDK `Memory.add(messages)` e MCP `hippo_ingest_conversation`, col
giudizio chiesto (il default), due bracci che differiscono SOLO nel giudice:

* braccio A — il giudice è ASSENTE: `local_grounding.try_local_score` torna
  None, cioè quello che il prodotto vede quando il cross-encoder non c'è;
* braccio B — il giudice c'è e AMMETTE tutti i fatti (punteggio 99,0).

In tutti e due i bracci ogni fatto estratto entra come `model_claim`. Le righe
dello store differiscono già: `grounding_score` è NULL in A e 99,0 in B. È il
CONTROLLO POSITIVO, controllato per primo, e dice che i due bracci sono davvero
diversi. Deve differire anche la ricevuta che riceve chi chiama, e quella di A
deve nominare il giudice mancato con la parola della porta di scrittura,
`not_run:no_judge` (`client.esito_del_moat`): un solo insieme di stringhe per
le due porte.

Predizione su c524fa07, scritta PRIMA di eseguire: le due ricevute sono uguali
chiave per chiave (stored 3, rejected 0, niente `quarantined`, e alla porta MCP
la stessa nota), quindi le due celle sono rosse. Se differissero già, la
predizione sarebbe falsificata e il difetto non sarebbe quello della nota.

Il giudice è sostituito UN livello sotto `_grounds` (`try_local_score`), così
`_grounds` resta quello vero: è lui che trasforma «giudice assente» in
`(True, None)`, e il RED deve passare da lì.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import types

import pytest

DIALOGO = ("Cliente: buongiorno, confermo il canone del capannone 12 a 5900 euro. "
           "Agente: perfetto, e la consegna resta il 3 marzo.")

FATTI = [
    "Il canone del capannone 12 e' 5900 euro.",
    "La consegna del capannone 12 e' il 3 marzo.",
    "Il cliente conferma il canone del capannone 12.",
]


class _Estrattore:
    """L'LLM di estrazione e di consolidamento: rende sempre gli stessi tre fatti."""

    def complete(self, system, messages, *, model=None, max_tokens=1200):
        r = types.SimpleNamespace()
        r.text = "\n".join(FATTI)
        return r


def _giudice(monkeypatch: pytest.MonkeyPatch, punteggio: float | None) -> None:
    """None = giudice assente; un numero = il giudice che dà quel punteggio."""
    from verimem import local_grounding as lg

    def _try_local_score(source, fact, **_kw):
        return None if punteggio is None else (punteggio, None)

    monkeypatch.setattr(lg, "try_local_score", _try_local_score)


def _punteggi(db_path) -> dict[str, float | None]:
    with sqlite3.connect(str(db_path)) as con:
        return dict(con.execute(
            "SELECT proposition, grounding_score FROM facts").fetchall())


def _ricevuta_sdk(tmp, nome, monkeypatch, punteggio):
    from verimem.client import Memory

    _giudice(monkeypatch, punteggio)
    m = Memory(str(tmp / f"{nome}.db"), llm=_Estrattore())
    res = m.add([{"role": "user", "content": DIALOGO}], conversation_id="t204")
    return res, _punteggi(m.semantic.db_path)


def _ricevuta_mcp(tmp, nome, monkeypatch, punteggio):
    from verimem import mcp_server
    from verimem.semantic import SemanticMemory

    _giudice(monkeypatch, punteggio)
    sm = SemanticMemory(db_path=tmp / f"{nome}.db")
    agente = types.SimpleNamespace(
        semantic=sm, wake=types.SimpleNamespace(llm=_Estrattore()))
    monkeypatch.setattr(mcp_server, "_ag", lambda: agente)
    monkeypatch.setattr(mcp_server, "_agent", agente, raising=False)
    fuori = asyncio.run(mcp_server._call_tool_impl("hippo_ingest_conversation", {
        "messages": [{"role": "user", "content": DIALOGO}],
        "conversation_id": "t204",
    }))
    return json.loads(fuori[0].text), _punteggi(sm.db_path)


@pytest.fixture()
def isolato(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Nessuna scrittura fuori da tmp_path, e lo si CONTROLLA invece di crederlo.

    Tutti e tre gli alias della cartella dati (`_compat._ALIAS_DATA_DIR`: vince
    il primo), il log degli eventi, il log di audit della porta MCP (se non
    impostato ricade su `CONFIG.data_dir`, che si risolve all'import) e la casa:
    alcuni percorsi sono fissi su `Path.home()` e gli alias non li vedono.
    """
    from pathlib import Path

    dati = tmp_path / "dati"
    casa = tmp_path / "casa"
    dati.mkdir()
    casa.mkdir()
    for alias in ("HIPPO_DATA_DIR", "ENGRAM_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(alias, str(dati))
    monkeypatch.setenv("ENGRAM_EVENT_LOG", str(dati / "eventi.jsonl"))
    monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(dati / "mcp_audit.log"))
    monkeypatch.setenv("USERPROFILE", str(casa))
    monkeypatch.setenv("HOME", str(casa))
    monkeypatch.delenv("HIPPO_ENCODE_DELEGATE_ONLY", raising=False)

    # CONTROLLO POSITIVO dell'isolamento: la cartella che il prodotto usa DAVVERO.
    from verimem._compat import provenienza_data_dir
    usata = Path(provenienza_data_dir().percorso)
    assert usata == dati, (
        f"il prodotto userebbe {usata}, non la cartella del banco {dati}")
    assert Path.home() == casa, f"Path.home() e' ancora {Path.home()}"
    return tmp_path


@pytest.mark.parametrize("porta", ["sdk", "mcp"])
def test_la_ricevuta_dell_ingest_dice_se_il_giudice_ha_girato(
        monkeypatch: pytest.MonkeyPatch, isolato, porta: str) -> None:
    fai = _ricevuta_sdk if porta == "sdk" else _ricevuta_mcp
    senza, righe_senza = fai(isolato, f"{porta}_senza_giudice", monkeypatch, None)
    con, righe_con = fai(isolato, f"{porta}_con_giudice", monkeypatch, 99.0)

    # CONTROLLO POSITIVO NEL BRACCIO: le righe dello store devono già differire.
    # Se questo cade, il banco non vede il giudice, e il resto non misura niente.
    assert len(righe_senza) == len(FATTI) == len(righe_con), (righe_senza, righe_con)
    assert all(v is None for v in righe_senza.values()), righe_senza
    assert all(v == 99.0 for v in righe_con.values()), righe_con

    def _senza_id(r: dict) -> dict:
        return {k: v for k, v in r.items() if k != "fact_ids"}

    assert _senza_id(senza) != _senza_id(con), (
        f"porta {porta}: la ricevuta è la STESSA con il giudice assente e con il "
        f"giudice che ammette tutto — chi la legge non può sapere che i fatti "
        f"non sono stati giudicati: {_senza_id(senza)}")
    assert "not_run:no_judge" in json.dumps(senza), (
        f"porta {porta}: la ricevuta non nomina il giudice mancato con la parola "
        f"della porta di scrittura (not_run:no_judge): {senza}")
