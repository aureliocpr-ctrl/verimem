"""Cycle #148.1 (2026-05-18 sera) — swarm schemas (pydantic).

Two typed records validate every swarm run:

    AgentSpec  — single Claude Code background agent
    SwarmConfig — top-level swarm run (1..8 agents + shared topic)

Defaults are cost-aware (model=haiku) and safety-first (permission_mode=
plan). Override per AgentSpec when a task genuinely needs sonnet/opus or
write access.

Validation rules enforced here so the orchestrator can rely on a
well-formed config:
    • name non-empty
    • prompt non-empty
    • model ∈ {haiku, sonnet, opus}
    • permission_mode ∈ {plan, acceptEdits, bypassPermissions, default,
                          auto, dontAsk}
    • 1 ≤ |agents| ≤ 8 (Anthropic agent-teams practical limit)
    • agent names unique within a swarm
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# Aliases match `claude --model` (latest aliases) and full names. We
# accept the short aliases here; the spawn layer converts to the actual
# CLI flag value.
ModelName = Literal["haiku", "sonnet", "opus"]

# Mirrors `claude --permission-mode` choices from the CLI reference.
# Default is ``plan`` — sub-agent can plan + propose but cannot edit
# until the orchestrator (or its operator) approves.
PermissionMode = Literal[
    "plan",
    "acceptEdits",
    "bypassPermissions",
    "default",
    "auto",
    "dontAsk",
]


class AgentSpec(BaseModel):
    """One Claude Code background agent inside a swarm run."""

    name: str = Field(..., min_length=1, max_length=64)
    prompt: str = Field(..., min_length=1)
    model: ModelName = "haiku"
    max_budget_usd: float = Field(default=1.0, gt=0.0)
    permission_mode: PermissionMode = "plan"
    allowed_tools: list[str] | None = None
    worktree: bool = True
    bare: bool = False
    max_turns: int | None = Field(default=None, gt=0)
    cwd: str | None = None

    model_config = {"frozen": False, "validate_assignment": True}


class SwarmConfig(BaseModel):
    """Top-level swarm run definition."""

    run_id: str = Field(..., min_length=1, max_length=128)
    topic: str = Field(..., min_length=1)
    agents: list[AgentSpec] = Field(..., min_length=1, max_length=8)
    timeout_sec: int = Field(default=600, gt=0)
    cwd: str | None = None
    enable_agent_teams: bool = True

    @field_validator("topic")
    @classmethod
    def _topic_shape(cls, v: str) -> str:
        # Soft validation: encourage lab/swarm/<x> namespace but accept
        # any non-empty string the operator wants.
        return v.strip()

    @model_validator(mode="after")
    def _unique_agent_names(self) -> SwarmConfig:
        names = [a.name for a in self.agents]
        if len(set(names)) != len(names):
            seen: dict[str, int] = {}
            for n in names:
                seen[n] = seen.get(n, 0) + 1
            dups = [n for n, c in seen.items() if c > 1]
            raise ValueError(
                f"swarm config: duplicate agent names {dups!r}",
            )
        return self
