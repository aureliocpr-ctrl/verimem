"""La ricevuta MCP non puo' nominare DUE decisori diversi in due suoi campi.

Il presidio gemello (`test_chi_ha_deciso_la_quarantena.py`) esiste dal 20/08
e i suoi test passano tutti da `Memory(...)`, cioe' dall'SDK. Il commento
nel write path MCP lo dice gia': *«chi scrive in questo prodotto e' quasi
sempre un agente, e un agente passa da qui»*. Quel presidio quindi non
guardava la porta piu' usata — sul journal `flow.write` con `surface=sdk`
sono 18 su 10955.

Misurato alla porta il 30/08, stesso claim e stessa esecuzione sulle due
superfici::

    SDK  quarantined_by = 'L4.1'
    MCP  quarantined_by = 'gate'     <- e nella STESSA ricevuta
                                        anti_confab_warnings[0]['layer'] == 'L4.1'

La causa non era una copia della regola — `mcp_server` chiamava gia'
`chi_ha_quarantinato`, la funzione unica. Era la CHIAMATA: `agito` e' un
parametro opzionale, MCP non lo passava, e il ramo che nomina il layer non
aveva niente su cui girare, cadendo su ``return "gate"``.

Il taglio di questi test e' percio' la COERENZA INTERNA della ricevuta, non
il nome di un layer particolare: se un giorno decidesse un altro layer, il
presidio deve restare valido e continuare a pretendere che i due campi
dicano la stessa cosa.
"""
from __future__ import annotations

import json
import types
from pathlib import Path
from typing import Any

import pytest

from verimem import mcp_server
from verimem.semantic import SemanticMemory

#: Il numero NON e' nella fonte: L4.1 lo vede. Il resto della frase la fonte
#: lo sostiene, cosi' il moat APPROVA e il caso e' «un layer trattiene mentre
#: il giudice e' a favore» — quello in cui `quarantined_by` conta davvero.
_CLAIM = "The index holds 4212 entries."
_FONTE = "The index holds entries and grows daily."


class _StubLLM:
    """Giudice deterministico che APPROVA: cosi' non e' il moat a bloccare."""

    def complete(self, system, messages, *, model=None, max_tokens=None):  # noqa: ANN001
        return types.SimpleNamespace(text="SCORE: 98")


@pytest.fixture
def porta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    sm = SemanticMemory(db_path=tmp_path / "s.db")

    class _Wake:
        llm = _StubLLM()

    class _FakeAgent:
        def __init__(self) -> None:
            self.semantic = sm
            self.wake = _Wake()

    monkeypatch.setattr(mcp_server, "_ag", lambda: _FakeAgent())
    monkeypatch.delenv("ENGRAM_VALIDATE_DEFAULT", raising=False)
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    return sm


async def _invoke(name: str, arguments: dict | None = None) -> dict[str, Any]:
    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments or {}))
    result = await handler(req)
    payload = result.root if hasattr(result, "root") else result
    text = next(c.text for c in payload.content if hasattr(c, "text"))
    return json.loads(text)


@pytest.mark.asyncio
async def test_il_campo_e_i_warning_nominano_LO_STESSO_decisore(porta) -> None:  # noqa: ANN001
    """Il cuore: due campi della stessa risposta non si contraddicono."""
    out = await _invoke("hippo_remember", {
        "proposition": _CLAIM, "topic": "notes/porta-layer", "source": _FONTE,
    })
    if out.get("status") != "quarantined":
        pytest.skip("il gate non ha quarantinato questo claim in questo regime")
    causa = out.get("quarantined_by")
    layers = [w.get("layer") for w in (out.get("anti_confab_warnings") or [])
              if isinstance(w, dict)]
    assert layers, "la ricevuta non porta nessun layer: banco da rivedere"
    assert causa in layers, (
        f"la ricevuta si contraddice: quarantined_by={causa!r} "
        f"mentre i warning nominano {layers!r}")


@pytest.mark.asyncio
async def test_la_causa_non_e_l_etichetta_generica(porta) -> None:  # noqa: ANN001
    """`gate` non e' un'etichetta mancante: e' un'etichetta che porta fuori
    strada — chi legge «gate» accanto a un moat che ha approvato conclude che
    la causa non sia registrata, ed e' il contrario del vero."""
    out = await _invoke("hippo_remember", {
        "proposition": _CLAIM, "topic": "notes/porta-layer-2", "source": _FONTE,
    })
    if out.get("status") != "quarantined":
        pytest.skip("il gate non ha quarantinato questo claim in questo regime")
    assert out.get("quarantined_by") != "gate"


@pytest.mark.asyncio
async def test_CONTROLLO_un_fatto_ammesso_non_nomina_nessun_decisore(porta) -> None:  # noqa: ANN001
    """L'altra popolazione: dove non c'e' quarantena il campo non compare, e
    una scrittura ordinaria non cambia forma."""
    out = await _invoke("hippo_remember", {
        "proposition": "The index holds entries.",
        "topic": "notes/porta-layer-ok", "source": _FONTE,
    })
    if out.get("status") == "quarantined":
        pytest.skip("il gate ha quarantinato anche il claim pulito")
    assert "quarantined_by" not in out
