"""Every channel must judge a source. The invariant, not one channel's wiring.

Three entry points write facts — ``Memory.add`` (SDK), ``save_checkpoint``
(what ``verimem save`` calls), and the ``hippo_remember`` MCP handler — and each
asks for the moat its own way: ``add`` takes ``ground``, the handler passes
``ground_write``, and until 2026-07-29 the handler passed NOTHING and fell
through to ENGRAM_GROUNDING_WRITE, an env var no file in the tree sets.

The cost of that was not theoretical. On the live store the same proposition,
written with a real source and without one, both landed with grounding_score
NULL — while the CLI path judged 11 of 11 writes the same night. The docs were
not wrong: ebab6e92 (2026-07-17) documented "the moat is ON by default" and its
evidence line names the hardening-audit probe, which runs on the SDK path. The
promise was kept by the channel that was measured.

So this test does not check how any channel is wired. It checks what a user
gets: give a channel a source, and the stored fact carries a verdict. A new
channel that skips the gate breaks this, which is the only thing that stops the
bug from coming back under a different name — the product has 14 gate env vars
plus a per-call override, and remembering to wire each one is not a strategy.

Judge-stubbed, so it costs milliseconds instead of the ~29s CE cold-load.
"""
from __future__ import annotations

import json
import types
from pathlib import Path
from typing import Any

import pytest

PROP = "The invoice total is 1240 euro."
SRC = "Invoice 88: subtotal 1000, VAT 240, total 1240 euro."


class _Judge:
    """Deterministic entailment judge — the gate parses SCORE: N."""

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, system, messages, *, model=None, max_tokens=None):  # noqa: ANN001
        self.calls += 1
        return types.SimpleNamespace(text="SCORE: 95")


@pytest.fixture(autouse=True)
def _no_env_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """The env must NOT be what makes this pass — that is the bug being pinned.
    A developer with ENGRAM_GROUNDING_WRITE=1 in their shell would otherwise
    see every channel judge and never notice one was relying on it."""
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE", raising=False)
    monkeypatch.delenv("ENGRAM_VALIDATE_DEFAULT", raising=False)
    monkeypatch.delenv("VERIMEM_MCP_TRUST_GATE_KNOBS", raising=False)


def _score_of(sm: Any, fact_id: str) -> float | None:
    import sqlite3
    with sqlite3.connect(str(sm.db_path)) as c:
        row = c.execute(
            "SELECT grounding_score FROM facts WHERE id = ?", (fact_id,),
        ).fetchone()
    return row[0] if row else None


def test_the_sdk_channel_judges_a_source(tmp_path: Path) -> None:
    from verimem import Memory
    judge = _Judge()
    m = Memory(path=tmp_path / "s.db", grounding_llm=judge)
    r = m.add(PROP, topic="parity/sdk", source=SRC)
    assert judge.calls >= 1, "the SDK channel never consulted the judge"
    assert r.get("grounding_score") is not None, (
        "the SDK receipt reports no verdict"
    )
    assert _score_of(m.semantic, str(r["id"])) is not None, (
        "judged but not PERSISTED — a verdict that dies with the process is "
        "not provenance, and every later read would call the fact unjudged"
    )


def test_the_checkpoint_channel_judges_a_source(tmp_path: Path) -> None:
    """What `verimem save --source` runs."""
    from verimem import Memory
    from verimem.continuity import save_checkpoint
    judge = _Judge()
    m = Memory(path=tmp_path / "s.db", grounding_llm=judge)
    r = save_checkpoint(m, PROP, topic="parity/cli", source=SRC,
                        principal="cli:local")
    assert judge.calls >= 1, "the checkpoint channel never consulted the judge"
    assert r.get("grounding_score") is not None, (
        "the receipt reports no verdict, so `verimem save` would print "
        "'not verified' for a write that WAS judged"
    )


@pytest.mark.asyncio
async def test_the_mcp_channel_judges_a_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The channel an AGENT writes through — the one that was silently unjudged."""
    from verimem import mcp_server
    from verimem.semantic import SemanticMemory
    judge = _Judge()
    sm = SemanticMemory(db_path=tmp_path / "s.db")

    class _A:
        def __init__(self) -> None:
            self.semantic = sm
            # how the handler reaches a judge: a.wake.llm
            self.wake = types.SimpleNamespace(llm=judge)

    monkeypatch.setattr(mcp_server, "_ag", lambda: _A())

    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    result = await handler(CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name="hippo_remember", arguments={
            "proposition": PROP, "topic": "parity/mcp", "source": SRC,
        }),
    ))
    payload = result.root if hasattr(result, "root") else result
    out = json.loads(next(c.text for c in payload.content if hasattr(c, "text")))

    assert judge.calls >= 1, (
        "the MCP channel stored a sourced write without consulting the judge — "
        "the state the live store was in until 2026-07-29"
    )
    assert out.get("grounding_score") is not None
    assert "judged" in out.get("moat", "").lower()


# ─────────────────────────────────────────────────────────────────────────
# L'INVARIANTE GEMELLA: ogni canale deve dire CHI ha quarantinato.
#
# Stessa forma del difetto sopra, e per la stessa ragione: la promessa era
# tenuta dal canale che qualcuno aveva misurato. `quarantined_by` nasce nel
# write path dell'SDK; il 20/08 si e' misurato che le altre porte scrivevano
# la riga senza autore — 1958 quarantinati su 2329 nel corpus vivo (84,1%)
# non dicono chi li ha fermati.
#
# Anche qui il test non guarda il cablaggio: guarda cosa trova chi rilegge la
# riga domani. Una porta nuova che si dimentica l'autore rompe questo.
# ─────────────────────────────────────────────────────────────────────────

class _GiudiceContrario:
    """La fonte NON sostiene: il moat boccia, e la quarantena e' sua."""

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, system, messages, *, model=None, max_tokens=None):  # noqa: ANN001
        self.calls += 1
        return types.SimpleNamespace(text="SCORE: 2")


CLAIM_FALSO = "The invoice total is 99999 euro."


def _autore_di(sm: Any, fact_id: str):
    import sqlite3
    with sqlite3.connect(str(sm.db_path)) as c:
        row = c.execute(
            "SELECT status, quarantined_by FROM facts WHERE id = ?", (fact_id,),
        ).fetchone()
    return row if row else (None, None)


def test_il_canale_SDK_dice_chi_ha_quarantinato(tmp_path: Path) -> None:
    from verimem import Memory
    m = Memory(path=tmp_path / "s.db", grounding_llm=_GiudiceContrario())
    r = m.add(CLAIM_FALSO, topic="parity/sdk", source=SRC)
    stato, autore = _autore_di(m.semantic, str(r["id"]))
    assert stato == "quarantined", f"il banco non riproduce il caso: {r}"
    assert autore, (
        "la riga dice 'quarantined' e non dice chi: chi la rilegge domani "
        "non ha la ricevuta di questo istante")


@pytest.mark.asyncio
async def test_il_canale_MCP_dice_chi_ha_quarantinato(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """⚠️ LA PORTA DEGLI AGENTI, ed e' quella che pesa di piu' nel corpus:
    storicamente `agent_inference` conta 1445 quarantinati con 4 autori e
    `system_hook` 297 con ZERO. Qui il Fact si costruisce nel server e si
    chiama `semantic.store()` senza passare da `Memory.add()` — dove viveva
    la scrittura dell'autore, come ci era gia' vissuta l'emissione degli
    eventi fino al 2026-08-07."""
    from verimem import mcp_server
    from verimem.semantic import SemanticMemory
    sm = SemanticMemory(db_path=tmp_path / "s.db")

    class _A:
        def __init__(self) -> None:
            self.semantic = sm
            self.wake = types.SimpleNamespace(llm=_GiudiceContrario())

    monkeypatch.setattr(mcp_server, "_ag", lambda: _A())

    from mcp.types import CallToolRequest, CallToolRequestParams
    handler = mcp_server.server.request_handlers[CallToolRequest]
    result = await handler(CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name="hippo_remember", arguments={
            "proposition": CLAIM_FALSO, "topic": "parity/mcp", "source": SRC,
        }),
    ))
    payload = result.root if hasattr(result, "root") else result
    out = json.loads(next(c.text for c in payload.content if hasattr(c, "text")))

    fid = out.get("fact_id") or out.get("id")
    assert fid, f"nessun id nella risposta: {out}"
    stato, autore = _autore_di(sm, str(fid))
    assert stato == "quarantined", f"il banco non riproduce il caso: {out}"
    assert autore, (
        "la porta MCP scrive la riga quarantinata senza autore: e' la porta "
        "da cui scrivono gli agenti, e nel corpus e' quella che ha lasciato "
        "piu' righe mute")


# ─────────────────────────────────────────────────────────────────────────
# LA TERZA INVARIANTE: ogni canale deve CONSERVARE la fonte che dichiara.
#
# Le due sopra chiedono «il canale ha GIUDICATO?» e «dice CHI ha
# quarantinato?». Nessuna chiede «la provenienza e' rimasta scritta?», e per
# questo il difetto qui sotto e' passato: `facts add` GIUDICA (i test di
# sopra passano) e non CONSERVA, quindi il presidio era verde su un canale
# che perdeva meta' del lavoro. E' la forma «il proxy soddisfatto e la
# grandezza vera no».
#
# 🔬 MISURATO sul corpus vivo il 2026-09-06, prima della cura: 345 fatti
# scritti dal 04/08 al 04/09 hanno un `grounding_score` (quindi una source
# c'era, e il moat l'ha letta) e NESSUNA `source_signature`. Il 98,0% viene
# da `cli:local`, la stessa quota di chi la firma ce l'ha (95,0%): non e'
# una porta esotica, e' il comando che si usa tutti i giorni.
#
# ⚠️ E COSTA UNA PROMESSA DEL PRODOTTO: la coesistenza fra fonti distinte
# (`L3-fonti-distinte`, 6bd8c6ae) esige la firma su ENTRAMBI i fatti. Senza,
# due misure diverse scritte con `facts add --source` continuano a
# ritirarsi a vicenda — cioe' proprio il difetto che quella cura chiude.
#
# 📌 IL DIFETTO E' UN PATTERN, NON UN CASO: `test_chi_ha_quarantinato_si_sa_
# anche_domani.py` documenta LO STESSO comportamento su `quarantined_by`.
# `facts add` costruisce il `Fact` a mano e copia da `Memory.add` UN campo
# per volta. Confrontati i due punti, i campi che `Memory.add` assegna e
# `facts add` no sono quattro — `derives_from`, `lineage_to`,
# `source_signature`, `valid_until` — ma solo `--source` e' un flag che
# `facts add` OFFRE: gli altri tre non esistono su quel comando, quindi non
# promettono nulla. Il difetto e' uno, ed e' questo.
def test_il_canale_CLI_conserva_la_fonte_che_ha_dichiarato(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`facts add --source` giudica il fatto: deve anche lasciarne l'impronta."""
    import sqlite3

    for v in ("ENGRAM_DATA_DIR", "HIPPO_DATA_DIR", "VERIMEM_DATA_DIR"):
        monkeypatch.setenv(v, str(tmp_path))
    from typer.testing import CliRunner

    from verimem.cli import app

    res = CliRunner().invoke(app, [
        "facts", "add", "-p", PROP, "-t", "parity/cli", "--source", SRC,
    ])
    assert res.exit_code == 0, res.output

    con = sqlite3.connect(str(tmp_path / "semantic" / "semantic.db"))
    try:
        riga = con.execute(
            "SELECT grounding_score, source_signature FROM facts "
            "ORDER BY created_at DESC LIMIT 1").fetchone()
    finally:
        con.close()
    assert riga is not None, f"nessun fatto scritto: {res.output}"
    punteggio, firma = riga

    # ⚠️ IL CONTROLLO POSITIVO PRIMA DEL BERSAGLIO: se la source non fosse
    # nemmeno arrivata al gate, l'assenza della firma non direbbe niente —
    # direbbe solo che non c'era una fonte da conservare.
    assert punteggio is not None, (
        "la source non e' nemmeno arrivata al moat: questo banco non misura "
        f"cio' per cui esiste. Output: {res.output}")

    assert firma, (
        "`facts add --source` ha fatto GIUDICARE la fonte (grounding_score "
        f"{punteggio}) ma non ne ha conservato l'impronta: il fatto entra "
        "senza provenienza e resta fuori dalla coesistenza fra fonti "
        "distinte. `Memory.add` la scrive in client.py; qui il Fact e' "
        "costruito a mano e la riga manca.")
