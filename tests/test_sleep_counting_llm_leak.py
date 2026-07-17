"""RED->GREEN (§8 rescan2 'sleep.py _CountingLLM leak no try/finally').

SleepEngine.cycle() avvolge self.llm in un _CountingLLM per contare le chiamate
(FORGIA #50) e lo ripristina a fine ciclo. Ma il restore NON e' in un finally:
se uno stage solleva, self.llm resta il wrapper. Al cycle SUCCESSIVO
``original_llm = self.llm`` cattura il wrapper -> si ri-wrappa
``_CountingLLM(_CountingLLM(...))`` (nesting illimitato) e il restore riporta al
wrapper, non all'LLM reale -> leak permanente + conteggio cumulativo falsato.

Fix (minimale, basso rischio su sleep-core delicato): smontare un eventuale
wrapper residuo PRIMA di ri-wrappare (``getattr(self.llm, '_inner', self.llm)``)
-> niente nesting, ogni cycle riparte dall'LLM reale. Self-healing.

Hermetic: DB temporanei (tmp_data_dir), MockLLM, nessun DB reale.
"""
from __future__ import annotations

from verimem.episode import Episode, Trace
from verimem.llm import MockLLM
from verimem.memory import EpisodicMemory
from verimem.semantic import SemanticMemory
from verimem.skill import SkillLibrary
from verimem.sleep import SleepEngine


def _ep(i):
    return Episode(
        task_id=f"t{i}", task_text="Reverse a string in Python", outcome="success",
        final_answer="x",
        traces=[Trace(step=1, thought="t", action="a", action_input="{}", observation="o")],
        tokens_used=10,
    )


class _StaleWrapper:
    """Simula un _CountingLLM rimasto montato da un cycle precedente fallito
    (stessa interfaccia + attributo _inner che punta all'LLM reale)."""

    def __init__(self, inner):
        self._inner = inner

    def supports_tools(self):
        return self._inner.supports_tools()

    def complete(self, *a, **k):
        return self._inner.complete(*a, **k)

    def complete_with_tools(self, *a, **k):
        return self._inner.complete_with_tools(*a, **k)


def test_cycle_does_not_nest_leftover_counting_wrapper(tmp_data_dir):
    mem = EpisodicMemory(tmp_data_dir / "episodes" / "ep.db")
    sk = SkillLibrary(tmp_data_dir / "skills", tmp_data_dir / "skills" / "idx.db")
    sem = SemanticMemory(tmp_data_dir / "semantic" / "sem.db")
    for i in range(3):
        mem.store(_ep(i))
    real = MockLLM(scripted=["{}"] * 30)
    engine = SleepEngine(memory=mem, skills=sk, semantic=sem, llm=real)
    # simula il wrapper residuo di un cycle precedente uscito per eccezione
    engine.llm = _StaleWrapper(real)

    engine.cycle()

    # dopo un cycle pulito self.llm DEVE essere l'LLM reale, non un wrapper
    # (ne' lo stale _StaleWrapper, ne' un _CountingLLM annidato).
    assert engine.llm is real, (
        "cycle() deve smontare il wrapper residuo e ripristinare l'LLM reale "
        "(no nesting / no leak cumulativo)"
    )
