"""Cycle #148.7 (2026-05-18 sera) — REAL haiku integration test.

Opt-in via ``ENGRAM_SWARM_INTEGRATION=1`` env var so the default test
run never spawns a real ``claude --bg`` (which costs subscription
quota). This test:

    1. Spawns ONE haiku agent with a trivial prompt + budget cap $0.05
    2. Polls real ``~/.claude/jobs/<id>/state.json`` until done
    3. Verifies the bridge wrote chat facts + a success Episode
    4. Cleans up with ``claude stop`` + ``claude rm`` so the dev DB
       doesn't grow with test artifacts

Manually run with::

    ENGRAM_SWARM_INTEGRATION=1 pytest tests/swarm/test_integration_haiku.py -v

Cost: ~$0.001 (one haiku turn, <50 tokens i/o).
"""
from __future__ import annotations

import os
import subprocess
import time
import uuid
from pathlib import Path

import pytest

from engram.memory import EpisodicMemory
from engram.semantic import SemanticMemory
from engram.swarm.bridge import poll_until_done
from engram.swarm.lifecycle import remove_session, stop_session
from engram.swarm.schemas import AgentSpec
from engram.swarm.spawn import spawn_agent
from engram.swarm.state import read_state

_INTEGRATION_ENABLED = os.environ.get("ENGRAM_SWARM_INTEGRATION", "") == "1"


@pytest.mark.skipif(
    not _INTEGRATION_ENABLED,
    reason="set ENGRAM_SWARM_INTEGRATION=1 to exercise real claude --bg",
)
def test_haiku_spawn_poll_cleanup_end_to_end(tmp_path: Path) -> None:
    """Real claude --bg haiku smoke. Total wallclock <60s."""
    run_id = f"cycle148-smoke-{uuid.uuid4().hex[:6]}"
    topic = f"lab/swarm/{run_id}"
    spec = AgentSpec(
        name="smoke",
        prompt=(
            "Output exactly the literal string HAIKU_SWARM_OK on a single "
            "line, then stop. Do nothing else."
        ),
        model="haiku",
        max_budget_usd=0.05,
        permission_mode="plan",
        worktree=False,  # no git workdir needed for smoke
        bare=False,
        max_turns=2,
    )
    sm = SemanticMemory(db_path=tmp_path / "sem.db")
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")

    # 1. Spawn
    res = spawn_agent(spec, run_id=run_id)
    assert res.short_id, "must return short id"
    short_id = res.short_id

    try:
        # 2. Poll until done (max 60s wall clock)
        final = poll_until_done(
            short_id,
            topic=topic, sm=sm, mem=mem,
            run_id=run_id, agent_name="smoke",
            poll_interval_sec=2.0,
            deadline_sec=60.0,
        )
        assert final.state in ("done", "completed"), (
            f"haiku must reach done, got state={final.state!r} "
            f"detail={final.detail!r}"
        )

        # 3. Verify bridge wrote chat facts + completion episode
        with sm._connect() as conn:  # noqa: SLF001
            chat_count = conn.execute(
                "SELECT COUNT(*) FROM facts WHERE topic = ?", (topic,),
            ).fetchone()[0]
        assert chat_count >= 1, (
            f"bridge must write ≥1 chat fact, got {chat_count}"
        )
        with mem._connect() as conn:  # noqa: SLF001
            ep_count = conn.execute(
                "SELECT COUNT(*) FROM episodes WHERE task_id LIKE ?",
                (f"swarm/{run_id}/%",),
            ).fetchone()[0]
        assert ep_count >= 1, (
            f"bridge must record ≥1 completion episode, got {ep_count}"
        )

        # 4. State.json must contain the output
        st = read_state(short_id)
        assert st is not None
        assert st.output_result and "HAIKU_SWARM_OK" in st.output_result, (
            f"haiku must echo HAIKU_SWARM_OK, got "
            f"output_result={st.output_result!r}"
        )
    finally:
        # 5. Cleanup — never leave a dev DB session lying around
        stop_session(short_id, topic=topic, sm=sm, agent_name="test-cleanup")
        time.sleep(0.5)  # give supervisor a beat to terminate
        remove_session(short_id, topic=topic, sm=sm, agent_name="test-cleanup")
