"""Cycle #148.1 (2026-05-18 sera) — swarm schemas RED phase.

Aurelio direttiva: prodotto qualità Anthropic-lab, no marketing, lab REALE.
Cycle 148 wrappa primitive native `claude --bg` + `agent-teams` (env var
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS) per dare osservabilità +
persistenza HippoAgent. Sub-fase 1.1 = schemas pydantic.

API contract testato qui:

    AgentSpec — single agent in a swarm run.
        name (str, required, unique within swarm)
        prompt (str, required, the initial task description)
        model (Literal["haiku","sonnet","opus"], default "haiku")
        max_budget_usd (float, default 1.0)
        permission_mode (Literal["plan","acceptEdits","bypassPermissions","default"], default "plan")
        allowed_tools (list[str]|None, default None = all defaults)
        worktree (bool, default True — use --worktree auto)
        bare (bool, default False)
        max_turns (int|None, default None)
        cwd (str|None, default None = use swarm cwd)

    SwarmConfig — top-level swarm run.
        run_id (str, required, unique, used in topic + episode)
        topic (str, required, e.g. "lab/swarm/<run_id>")
        agents (list[AgentSpec], min 1, max 8)
        timeout_sec (int, default 600)
        cwd (str|None, default None = cwd at invocation)
        enable_agent_teams (bool, default True — sets env var)

TDD strict RED→GREEN: this file must fail import on engram.swarm.schemas.
"""
from __future__ import annotations

import pytest

# RED MARKER
from engram.swarm.schemas import AgentSpec, SwarmConfig


class TestAgentSpec:
    """AgentSpec validates a single agent definition."""

    def test_minimal_valid_spec(self) -> None:
        a = AgentSpec(name="agent-a", prompt="say hello")
        assert a.name == "agent-a"
        assert a.prompt == "say hello"
        assert a.model == "haiku"  # default cost-aware
        assert a.max_budget_usd == 1.0
        assert a.permission_mode == "plan"  # safer default
        assert a.worktree is True
        assert a.bare is False

    def test_full_valid_spec(self) -> None:
        a = AgentSpec(
            name="agent-b",
            prompt="review PR #85",
            model="sonnet",
            max_budget_usd=5.0,
            permission_mode="acceptEdits",
            allowed_tools=["Read", "Grep", "Glob"],
            worktree=False,
            bare=True,
            max_turns=10,
            cwd="/tmp/agent-b-work",
        )
        assert a.model == "sonnet"
        assert a.max_budget_usd == 5.0
        assert a.permission_mode == "acceptEdits"
        assert a.allowed_tools == ["Read", "Grep", "Glob"]
        assert a.bare is True

    def test_invalid_model_raises(self) -> None:
        with pytest.raises(Exception):  # pydantic ValidationError
            AgentSpec(name="x", prompt="y", model="gpt-4")  # type: ignore[arg-type]

    def test_invalid_permission_mode_raises(self) -> None:
        with pytest.raises(Exception):
            AgentSpec(name="x", prompt="y", permission_mode="wild")  # type: ignore[arg-type]

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(Exception):
            AgentSpec(name="", prompt="y")

    def test_empty_prompt_rejected(self) -> None:
        with pytest.raises(Exception):
            AgentSpec(name="x", prompt="")


class TestSwarmConfig:
    """SwarmConfig validates a swarm run definition."""

    def test_minimal_valid_swarm(self) -> None:
        c = SwarmConfig(
            run_id="cycle148-test",
            topic="lab/swarm/cycle148-test",
            agents=[AgentSpec(name="a", prompt="x")],
        )
        assert c.run_id == "cycle148-test"
        assert c.topic == "lab/swarm/cycle148-test"
        assert len(c.agents) == 1
        assert c.timeout_sec == 600
        assert c.enable_agent_teams is True

    def test_max_8_agents_enforced(self) -> None:
        agents = [AgentSpec(name=f"a-{i}", prompt="x") for i in range(9)]
        with pytest.raises(Exception):
            SwarmConfig(run_id="r", topic="t", agents=agents)

    def test_empty_agents_rejected(self) -> None:
        with pytest.raises(Exception):
            SwarmConfig(run_id="r", topic="t", agents=[])

    def test_duplicate_agent_names_rejected(self) -> None:
        with pytest.raises(Exception):
            SwarmConfig(
                run_id="r", topic="t",
                agents=[
                    AgentSpec(name="dup", prompt="x"),
                    AgentSpec(name="dup", prompt="y"),
                ],
            )
