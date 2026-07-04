"""Cycle #148.6 (2026-05-18 sera) — swarm orchestrator RED phase.

The orchestrator stitches the previous five modules:
    1. Validate SwarmConfig (cycle 148.1)
    2. Create coordination hub Episode (this module)
    3. Spawn each agent via spawn_agent (cycle 148.2)
    4. In parallel: poll_until_done each agent (cycle 148.4)
    5. Aggregate outcomes into a SwarmReport
    6. Mirror everything to HippoAgent (cycles 148.3+148.4)

API:
    run_swarm(config, *, sm, mem, jobs_dir=None,
              spawn_fn=spawn_agent, poll_fn=poll_until_done,
              hub_master_ep_id=None) -> SwarmReport

    SwarmReport.run_id
    SwarmReport.hub_ep_id
    SwarmReport.agents: list[AgentReport]
    SwarmReport.success_count
    SwarmReport.failure_count
"""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from engram.memory import EpisodicMemory
from engram.semantic import SemanticMemory
from engram.swarm.orchestrator import AgentReport, SwarmReport, run_swarm
from engram.swarm.schemas import AgentSpec, SwarmConfig
from engram.swarm.spawn import SpawnResult
from engram.swarm.state import SessionState


def _spawn_fn_factory(short_ids: list[str]):
    """Returns a fake spawn_fn that hands back deterministic short_ids."""
    idx = iter(short_ids)

    def fake(spec, *, run_id, swarm_cwd=None, env_overrides=None,
            timeout_sec=60.0):
        return SpawnResult(
            short_id=next(idx),
            command=["claude", "--bg", "test", spec.prompt],
            stdout=f"backgrounded · {short_ids[0]}\n",
        )

    return fake


def _poll_fn_factory(outcomes: dict[str, str]):
    """Returns a fake poll_fn that synthesises a SessionState per short_id."""

    def fake(short_id, *, topic, sm, mem, run_id, agent_name,
            jobs_dir=None, hub_ep_id=None, master_ep_id=None,
            poll_interval_sec=1.0, deadline_sec=600.0, sleeper=time.sleep):
        return SessionState.from_raw({
            "state": outcomes.get(short_id, "done"),
            "tempo": "idle",
            "daemonShort": short_id,
            "intent": f"task for {agent_name}",
            "output": {"result": f"result of {agent_name}"},
        })

    return fake


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sem.db")


@pytest.fixture
def mem(tmp_path: Path) -> EpisodicMemory:
    return EpisodicMemory(db_path=tmp_path / "ep.db")


@pytest.fixture
def cfg2() -> SwarmConfig:
    return SwarmConfig(
        run_id="cycle148-orch-test",
        topic="lab/swarm/cycle148-orch-test",
        agents=[
            AgentSpec(name="alpha", prompt="task A"),
            AgentSpec(name="beta", prompt="task B"),
        ],
        timeout_sec=10,
    )


class TestRunSwarm:
    """run_swarm spawns all agents, polls each, aggregates."""

    def test_spawns_each_agent_and_creates_hub_episode(
        self, cfg2: SwarmConfig, sm: SemanticMemory, mem: EpisodicMemory,
    ) -> None:
        report = run_swarm(
            cfg2,
            sm=sm, mem=mem,
            spawn_fn=_spawn_fn_factory(["aaaa1111", "bbbb2222"]),
            poll_fn=_poll_fn_factory({"aaaa1111": "done", "bbbb2222": "done"}),
        )
        assert isinstance(report, SwarmReport)
        assert report.run_id == "cycle148-orch-test"
        assert report.hub_ep_id  # hub episode created
        assert len(report.agents) == 2
        assert {a.agent_name for a in report.agents} == {"alpha", "beta"}
        # Hub episode exists in DB
        with mem._connect() as conn:  # noqa: SLF001
            row = conn.execute(
                "SELECT id, task_id FROM episodes WHERE id = ?",
                (report.hub_ep_id,),
            ).fetchone()
        assert row is not None
        assert "cycle148-orch-test" in (row["task_id"] or "")

    def test_aggregates_success_and_failure_counts(
        self, cfg2: SwarmConfig, sm: SemanticMemory, mem: EpisodicMemory,
    ) -> None:
        report = run_swarm(
            cfg2, sm=sm, mem=mem,
            spawn_fn=_spawn_fn_factory(["xx1", "yy2"]),
            poll_fn=_poll_fn_factory({"xx1": "done", "yy2": "failed"}),
        )
        assert report.success_count == 1
        assert report.failure_count == 1
        outcomes = {a.agent_name: a.final_state for a in report.agents}
        assert outcomes == {"alpha": "done", "beta": "failed"}

    def test_writes_chat_fact_for_each_agent_completion(
        self, cfg2: SwarmConfig, sm: SemanticMemory, mem: EpisodicMemory,
    ) -> None:
        run_swarm(
            cfg2, sm=sm, mem=mem,
            spawn_fn=_spawn_fn_factory(["p1", "p2"]),
            poll_fn=_poll_fn_factory({"p1": "done", "p2": "done"}),
        )
        with sm._connect() as conn:  # noqa: SLF001
            rows = conn.execute(
                "SELECT proposition FROM facts WHERE topic = ?",
                ("lab/swarm/cycle148-orch-test",),
            ).fetchall()
        # Expect at least: hub announcement + per-agent state transitions.
        # poll_fn fake produces 1 transition per agent (None → done) + final summary.
        assert len(rows) >= 2, (
            f"cycle 148.6: expected ≥2 chat facts (per-agent transitions), "
            f"got {len(rows)}: {[r['proposition'][:80] for r in rows]!r}"
        )

    def test_links_agent_episodes_to_hub_via_causal_edges(
        self, cfg2: SwarmConfig, sm: SemanticMemory, mem: EpisodicMemory,
        tmp_path: Path,
    ) -> None:
        # Use the REAL poll_until_done with a seeded jobs_dir so the
        # production bridge code runs end-to-end and writes real edges.
        import json as _json

        from engram.swarm.bridge import poll_until_done as real_poll
        jobs = tmp_path / "jobs"
        for sid in ("q1", "q2"):
            sd = jobs / sid
            sd.mkdir(parents=True)
            (sd / "state.json").write_text(_json.dumps({
                "state": "done", "tempo": "idle",
                "daemonShort": sid, "sessionId": f"{sid}-full",
                "intent": f"task {sid}",
                "output": {"result": f"result {sid}"},
            }), encoding="utf-8")

        def _wrapped_poll(short_id, *, topic, sm, mem, run_id, agent_name,
                           jobs_dir=None, hub_ep_id=None, master_ep_id=None,
                           poll_interval_sec=1.0, deadline_sec=600.0,
                           sleeper=time.sleep):
            # Force the real poll to look at our seeded fixture dir, no
            # matter what the orchestrator passed.
            return real_poll(
                short_id, topic=topic, sm=sm, mem=mem,
                run_id=run_id, agent_name=agent_name,
                jobs_dir=jobs,
                hub_ep_id=hub_ep_id, master_ep_id=master_ep_id,
                poll_interval_sec=0.01,
                deadline_sec=2.0,
                sleeper=lambda s: None,
            )

        report = run_swarm(
            cfg2, sm=sm, mem=mem,
            spawn_fn=_spawn_fn_factory(["q1", "q2"]),
            poll_fn=_wrapped_poll,
        )
        with mem._connect() as conn:  # noqa: SLF001
            rows = conn.execute(
                "SELECT src_episode_id FROM causal_edges "
                "WHERE dst_episode_id = ? AND via_skill_id = ?",
                (report.hub_ep_id, "narrative_link"),
            ).fetchall()
        srcs = {r["src_episode_id"] for r in rows}
        assert len(srcs) >= 2, (
            f"cycle 148.6: each agent ep must narrative_link to hub, "
            f"got {len(srcs)} distinct srcs"
        )
