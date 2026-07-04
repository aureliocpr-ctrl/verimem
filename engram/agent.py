"""High-level orchestrator: HippoAgent.

Convenience facade tying memory + skills + wake + sleep together.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .entity_kg import EntityStore
from .memory import EpisodicMemory
from .observability import emit
from .semantic import SemanticMemory
from .skill import SkillLibrary
from .sleep import SleepEngine, SleepReport
from .tools import ToolSpec
from .tools_extra import all_tools
from .wake import Validator, WakeAgent, WakeConfig, WakeResult


@dataclass
class HippoAgent:
    memory: EpisodicMemory
    skills: SkillLibrary
    semantic: SemanticMemory
    wake: WakeAgent
    sleep: SleepEngine
    entity_kg: EntityStore | None = None

    @classmethod
    def build(
        cls,
        llm: Any | None = None,
        tools: dict[str, ToolSpec] | None = None,
        wake_config: WakeConfig | None = None,
    ) -> HippoAgent:
        memory = EpisodicMemory()
        skills = SkillLibrary()
        # Cycle #111 v2 (2026-05-17): wire CONFIG.project_root so the
        # verified_by hard-gate in SemanticMemory.store() can perform
        # I/O verification (filesystem for file:<path>:<lineno>, git
        # rev-parse for commit <sha>) against the actual repo. Without
        # this, every status='verified' write would be demoted —
        # paranoid default — and production hippo_remember calls
        # marked 'verified' would all land as 'model_claim'.
        from .config import CONFIG as _CONFIG  # local import to avoid cycle
        semantic = SemanticMemory(repo_root=_CONFIG.project_root)
        entity_kg = EntityStore()
        if llm is None:
            # Defer LLM construction (LazyLLM) so the agent — and the read-only
            # dashboard views — build even with no API key / no hosted mode.
            # Eager get_llm() here made /episodes /skills /active-memory 500
            # with "ANTHROPIC_API_KEY not set" (2026-06-06). The real backend is
            # built on first inference access, not at construction.
            from .llm import LazyLLM
            llm = LazyLLM()
        wake = WakeAgent(memory=memory, skills=skills, tools=tools or all_tools(),
                        llm=llm, config=wake_config)
        # Opt-in: route reconcile-on-write conflict confirmation through the semantic
        # NLI judge (validated ~4× recall vs lexical at no precision cost). Lazy —
        # LLMRelationJudge holds the (lazy) llm; no inference until reconcile fires on a
        # real conflict. Off by default; needs ENGRAM_RECONCILE_NLI + ENGRAM_RECONCILE_ON_WRITE.
        import os as _os
        if _os.environ.get("ENGRAM_RECONCILE_NLI", "").strip().lower() in (
            "1", "on", "true", "yes",
        ):
            try:
                from .semantic_conflict import LLMRelationJudge
                semantic.set_reconcile_judge(LLMRelationJudge(llm))
            except Exception:  # noqa: BLE001 — judge wiring must never break agent build
                pass
        sleep = SleepEngine(memory=memory, skills=skills, semantic=semantic, llm=llm)
        return cls(memory=memory, skills=skills, semantic=semantic,
                   wake=wake, sleep=sleep, entity_kg=entity_kg)

    def run_task(self, task_id: str, task_text: str, validator: Validator) -> WakeResult:
        return self.wake.run(task_id=task_id, task_text=task_text, validator=validator)

    def consolidate(self) -> SleepReport:
        return self.sleep.cycle()

    def reset(self) -> None:
        emit("agent_reset")
        self.memory.clear()
        self.skills.clear()
        self.semantic.clear()
