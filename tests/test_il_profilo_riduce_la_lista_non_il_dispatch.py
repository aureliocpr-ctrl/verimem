"""ws4 — profilo di esposizione: la lista si riduce, il dispatch mai.

Misura del 2026-07-31: tools/list = 168.169 char (~42k token) per ogni
client a ogni sessione; 126 tool su 244 mai chiamati in 78 giorni = 48%
del prompt. Il profilo ``core`` (default) li toglie dalla lista; ``full``
espone tutto; un tool nascosto chiamato per nome risponde comunque.
"""
from __future__ import annotations

import asyncio
import json

import pytest

from verimem import mcp_server
from verimem.tool_profile import HIDDEN_IN_CORE_PROFILE


def _names(monkeypatch, profilo: str) -> set[str]:
    monkeypatch.setenv("VERIMEM_TOOL_PROFILE", profilo)
    tools = asyncio.run(mcp_server.list_tools())
    return {t.name for t in tools}


def test_core_toglie_i_mai_usati_e_tiene_i_vivi(monkeypatch) -> None:
    core = _names(monkeypatch, "core")
    assert "hippo_health" in core, "un tool vivo deve restare esposto"
    assert "hippo_trajectory_render" not in core, (
        "un tool della famiglia trajectory (zero chiamate in 78 giorni) "
        "non deve pesare sul prompt di default"
    )
    assert not (core & HIDDEN_IN_CORE_PROFILE), (
        "nessun nome della lista nascosta deve comparire nel profilo core"
    )


def test_full_espone_tutto(monkeypatch) -> None:
    core = _names(monkeypatch, "core")
    full = _names(monkeypatch, "full")
    assert core < full, "core deve essere un sottoinsieme proprio di full"
    assert HIDDEN_IN_CORE_PROFILE <= full


def test_il_risparmio_e_reale(monkeypatch) -> None:
    monkeypatch.setenv("VERIMEM_TOOL_PROFILE", "full")
    tutti = asyncio.run(mcp_server.list_tools())
    blob = {t.name: len(json.dumps(t.model_dump())) for t in tutti}
    pieno = sum(blob.values())
    core = sum(v for k, v in blob.items() if k not in HIDDEN_IN_CORE_PROFILE)
    assert core < pieno * 0.6, (
        f"il profilo core deve tagliare almeno il 40% del prompt: "
        f"{core:,} su {pieno:,}"
    )


def test_un_tool_nascosto_risponde_comunque(monkeypatch, tmp_path) -> None:
    """Il profilo governa la LISTA, mai il dispatch: chi chiama per nome
    un tool non esposto viene servito — nessun flusso puo' rompersi."""
    monkeypatch.setenv("VERIMEM_TOOL_PROFILE", "core")
    nascosto = "hippo_trajectory_render"
    assert nascosto in HIDDEN_IN_CORE_PROFILE
    out = asyncio.run(mcp_server.call_tool(nascosto, {"episode_id": "inesistente"}))
    testo = out[0].text
    assert "unknown_tool" not in testo, (
        "il dispatch non deve trattare un tool nascosto come inesistente"
    )
