"""Muro 1, pezzo 3c: le TRE porte dicono quale claim e' stato fermato.

Il gate (pezzo 3a, main 22947ae9) decompone la scrittura e giudica ogni
claim con L1; la ricevuta del gate porta `claims`, `claims_verdict` e
`decomposed`. Ma le tre porte costruiscono la loro risposta a mano
(client.py `_out`, mcp_server.py il dict di hippo_remember, cli.py la
stampa di `facts add`): un campo nuovo nel gate NON arriva all'utente
finche' ognuna non lo copia. «Una capacita' = tre porte, stessa risposta,
stesso schema» (ws2). Cella per porta, come chiede il design §6 passo 3.

Falsificazione: con la cura delle porte stashata (il gate resta quello di
main) le tre celle devono cadere; con la cura, passare.
"""
from __future__ import annotations

import asyncio
import json
import os

import pytest

COMPOSTA = "Il comando warmup e' finito alle 14:53 ed e' verificata"
TOPIC = "prova/muro-1-porte"


def _json_di(out):
    """call_tool rende una stringa JSON o una lista di TextContent."""
    if isinstance(out, str):
        return json.loads(out)
    if isinstance(out, (list, tuple)) and out:
        primo = out[0]
        return json.loads(getattr(primo, "text", primo))
    return out


def _fermati(verdetti):
    return [v for v in (verdetti or []) if v.get("layer")]


def test_CONTROLLO_quale_albero_sto_misurando():
    import verimem
    qui = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert os.path.abspath(verimem.__file__).startswith(os.path.abspath(qui)), (
        verimem.__file__, qui)


def test_la_porta_SDK_dice_quale_claim_e_stato_fermato(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "0")
    from verimem import Memory
    m = Memory(str(tmp_path / "porte.db"))
    r = m.add(COMPOSTA, topic=TOPIC)
    assert r.get("decomposed") is True, r
    assert len(r.get("claims") or []) == 2, r
    fermati = _fermati(r.get("claims_verdict"))
    assert [v["claim"] for v in fermati] == [1], r
    assert str(fermati[0]["layer"]).startswith("L1"), r


def test_la_porta_MCP_dice_quale_claim_e_stato_fermato(isolated_corpus, monkeypatch):
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "0")
    from verimem import mcp_server as srv
    out = _json_di(asyncio.run(srv.call_tool("hippo_remember", {
        "proposition": COMPOSTA, "topic": TOPIC})))
    assert out.get("decomposed") is True, out
    assert len(out.get("claims") or []) == 2, out
    fermati = _fermati(out.get("claims_verdict"))
    assert [v["claim"] for v in fermati] == [1], out
    assert str(fermati[0]["layer"]).startswith("L1"), out


def test_la_porta_CLI_dice_quale_claim_e_stato_fermato(isolated_corpus, monkeypatch):
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "0")
    from typer.testing import CliRunner

    from verimem.cli import app
    res = CliRunner().invoke(app, ["facts", "add", "--proposition", COMPOSTA,
                                   "--topic", TOPIC])
    testo = res.output
    assert res.exit_code == 0, testo
    assert "claim 2/2 fermato da L1" in testo, testo
