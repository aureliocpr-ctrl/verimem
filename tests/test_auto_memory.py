"""AutoMemory — memoria automatica opt-in, gated (roadmap #10).

Il differenziante dichiarato: mem0 assorbe tutto quello che vede; qui
l'automatismo è OPT-IN (è una classe separata: se non la costruisci non
esiste) e ogni fatto passa la STESSA pipeline gated dell'ingest esplicito
(estrazione atomica → gate anti-confab → provenienza conversazionale).
v0 deterministico: flush a soglia di turni — il filtro qualità è già nel
consolidate (droppa chit-chat) e nel gate; nessuna seconda decisione LLM.
"""
from __future__ import annotations

from verimem.auto_memory import AutoMemory
from verimem.client import Memory


class _StubLLM:
    """Estrattore stub: una riga-fatto per ogni turno utente osservato."""

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, system, messages, **kw):
        self.calls += 1
        convo = messages[0]["content"]
        facts = [f"The user said fact number {i}"
                 for i, line in enumerate(convo.splitlines())
                 if line.startswith("user:")]

        class R:
            text = "\n".join(facts)
            total_tokens = 5
        return R()


def _auto(tmp_path, **kw):
    llm = _StubLLM()
    mem = Memory(tmp_path / "m.db", llm=llm)
    return AutoMemory(mem, conversation_id="auto-test", **kw), mem, llm


def test_no_flush_below_buffer_threshold(tmp_path):
    auto, mem, llm = _auto(tmp_path, max_buffer_turns=6)
    for i in range(4):
        r = auto.observe("user", f"turn {i}")
        assert r["flushed"] is False
    assert llm.calls == 0, "nessuna call LLM finché il buffer non è pieno"
    assert mem.search("turn", k=3) == []


def test_flush_fires_at_buffer_threshold_and_stores_gated(tmp_path):
    auto, mem, llm = _auto(tmp_path, max_buffer_turns=4)
    results = [auto.observe("user", f"my favourite colour is number {i}")
               for i in range(4)]
    assert results[-1]["flushed"] is True
    assert results[-1]["stored"] > 0
    assert llm.calls >= 1
    assert auto.pending_turns == 0, "il buffer si svuota dopo il flush"
    hits = mem.search("fact number", k=5)
    assert hits, "i fatti auto-osservati sono nel recall"
    assert all(h["status"] in ("model_claim", "quarantined") for h in hits), (
        "auto-memoria = claim gated, mai verità laundered"
    )


def test_manual_flush_respects_min_turns(tmp_path):
    auto, mem, llm = _auto(tmp_path, min_turns=3, max_buffer_turns=10)
    auto.observe("user", "hello")
    r = auto.flush()
    assert r["flushed"] is False and llm.calls == 0, (
        "sotto min_turns il flush manuale è no-op: 2 battute non sono memoria"
    )
    auto.observe("assistant", "hi! how can I help?")
    auto.observe("user", "I moved to Berlin in March")
    r2 = auto.flush()
    assert r2["flushed"] is True and r2["stored"] > 0


def test_empty_and_blank_messages_are_ignored(tmp_path):
    auto, *_ = _auto(tmp_path, max_buffer_turns=3)
    auto.observe("user", "")
    auto.observe("user", "   ")
    assert auto.pending_turns == 0
