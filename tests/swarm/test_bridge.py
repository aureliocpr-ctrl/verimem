"""Cycle #148.4 (2026-05-18 sera) — swarm bridge HippoAgent (RED phase).

The bridge mirrors Claude bg session state changes into HippoAgent memory:
    • Every meaningful state transition → one chat fact on the swarm topic
    • Every session completion → one failure/success Episode linked to
      the swarm coordination hub via related_episode_ids

This persistence is the whole point of ``engram swarm`` on top of the
native ``claude --bg`` — agent-teams mailbox is in-memory only and dies
on supervisor restart. The bridge gives cross-session survival.

API:
    mirror_state_change(short_id, prev: SessionState|None, curr: SessionState,
                        *, topic: str, sm: SemanticMemory,
                        agent_name: str) -> str | None
        Returns the new Fact id if a transition was written, else None.

    record_completion_episode(short_id, *, state: SessionState,
                              run_id: str, agent_name: str,
                              mem: EpisodicMemory,
                              hub_ep_id: str | None = None,
                              master_ep_id: str | None = None) -> str
        Returns the new Episode id. Outcome derived from state.state.

    poll_until_done(short_id, *, topic, sm, mem, run_id, agent_name,
                    jobs_dir, hub_ep_id=None, master_ep_id=None,
                    poll_interval_sec=1.0, deadline_sec=600,
                    sleeper=time.sleep) -> SessionState
        Polls read_state in a loop until ``state.state`` is one of
        {"done","failed","stopped"} or deadline elapsed. Each transition
        triggers mirror_state_change. On completion, records episode.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from engram.memory import EpisodicMemory
from engram.semantic import SemanticMemory
from engram.swarm.bridge import (
    mirror_state_change,
    poll_until_done,
    record_completion_episode,
)
from engram.swarm.state import SessionState

_TOPIC = "lab/swarm/test-bridge-cycle148"


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sem.db")


@pytest.fixture
def mem(tmp_path: Path) -> EpisodicMemory:
    return EpisodicMemory(db_path=tmp_path / "ep.db")


def _state(state: str = "running", detail: str = "") -> SessionState:
    return SessionState.from_raw({
        "state": state,
        "tempo": "working" if state == "running" else "idle",
        "detail": detail,
        "intent": "test intent",
        "daemonShort": "abc12345",
        "sessionId": "abc12345-full-uuid",
    })


class TestMirrorStateChange:
    """``mirror_state_change`` writes a chat fact on transition."""

    def test_writes_fact_on_first_seen(self, sm: SemanticMemory) -> None:
        curr = _state("running", detail="starting up")
        fact_id = mirror_state_change(
            "abc12345", None, curr,
            topic=_TOPIC, sm=sm, agent_name="agent-a",
        )
        assert fact_id is not None, (
            "cycle 148.4: first-seen state must produce a chat fact"
        )
        # Verify it landed in semantic.db with the right topic.
        with sm._connect() as conn:  # noqa: SLF001
            row = conn.execute(
                "SELECT proposition, topic FROM facts WHERE id = ?",
                (fact_id,),
            ).fetchone()
        assert row is not None
        assert row["topic"] == _TOPIC
        # The fact must surface the agent role + new state.
        assert "agent-a" in row["proposition"]
        assert "running" in row["proposition"]

    def test_skips_when_state_unchanged(self, sm: SemanticMemory) -> None:
        prev = _state("running")
        curr = _state("running", detail="same state, new tempo update")
        out = mirror_state_change(
            "abc12345", prev, curr,
            topic=_TOPIC, sm=sm, agent_name="agent-a",
        )
        assert out is None, (
            "cycle 148.4: same state.state means no new chat fact "
            "(tempo updates are noise)"
        )

    def test_writes_fact_on_done(self, sm: SemanticMemory) -> None:
        prev = _state("running")
        curr = _state("done", detail="task complete")
        fact_id = mirror_state_change(
            "abc12345", prev, curr,
            topic=_TOPIC, sm=sm, agent_name="agent-a",
        )
        assert fact_id is not None
        with sm._connect() as conn:  # noqa: SLF001
            row = conn.execute(
                "SELECT proposition FROM facts WHERE id = ?", (fact_id,),
            ).fetchone()
        assert "done" in row["proposition"]


class TestRecordCompletionEpisode:
    """``record_completion_episode`` writes a linked Episode."""

    def test_creates_success_episode_on_done(
        self, mem: EpisodicMemory,
    ) -> None:
        st = _state("done", detail="task ok")
        ep_id = record_completion_episode(
            "abc12345",
            state=st,
            run_id="cycle148-test",
            agent_name="agent-a",
            mem=mem,
        )
        assert ep_id
        with mem._connect() as conn:  # noqa: SLF001
            row = conn.execute(
                "SELECT outcome, task_id FROM episodes WHERE id = ?",
                (ep_id,),
            ).fetchone()
        assert row["outcome"] == "success"
        assert "cycle148-test" in row["task_id"] or "agent-a" in row["task_id"]

    def test_creates_failure_episode_on_failed(
        self, mem: EpisodicMemory,
    ) -> None:
        st = _state("failed", detail="boom")
        ep_id = record_completion_episode(
            "abc12345",
            state=st,
            run_id="r",
            agent_name="agent-x",
            mem=mem,
        )
        with mem._connect() as conn:  # noqa: SLF001
            row = conn.execute(
                "SELECT outcome FROM episodes WHERE id = ?", (ep_id,),
            ).fetchone()
        assert row["outcome"] == "failure"

    def test_creates_narrative_link_edges_to_hub_and_master(
        self, mem: EpisodicMemory,
    ) -> None:
        st = _state("done")
        ep_id = record_completion_episode(
            "abc12345",
            state=st,
            run_id="r",
            agent_name="a",
            mem=mem,
            hub_ep_id="hub-ep-id-fake",
            master_ep_id="master-ep-id-fake",
        )
        with mem._connect() as conn:  # noqa: SLF001
            rows = conn.execute(
                "SELECT dst_episode_id FROM causal_edges "
                "WHERE src_episode_id = ? AND via_skill_id = ?",
                (ep_id, "narrative_link"),
            ).fetchall()
        dst = {r["dst_episode_id"] for r in rows}
        assert "hub-ep-id-fake" in dst
        assert "master-ep-id-fake" in dst


class TestPollUntilDone:
    """``poll_until_done`` loops until terminal + records completion."""

    def test_exits_on_done_state(
        self, tmp_path: Path, sm: SemanticMemory, mem: EpisodicMemory,
    ) -> None:
        # Seed a jobs_dir with a fake session whose state.json says done.
        jobs_dir = tmp_path / "jobs"
        sess = jobs_dir / "abc12345"
        sess.mkdir(parents=True)
        (sess / "state.json").write_text(
            json.dumps({
                "state": "done",
                "tempo": "idle",
                "intent": "x",
                "output": {"result": "ALL_OK"},
                "daemonShort": "abc12345",
                "sessionId": "abc12345-full",
            }),
            encoding="utf-8",
        )
        # Sleeper that fast-forwards without consuming wall time.
        ticks: list[float] = []

        def fake_sleep(s: float) -> None:
            ticks.append(s)

        final = poll_until_done(
            "abc12345",
            topic=_TOPIC,
            sm=sm, mem=mem,
            run_id="cycle148-test",
            agent_name="agent-a",
            jobs_dir=jobs_dir,
            poll_interval_sec=0.01,
            deadline_sec=5.0,
            sleeper=fake_sleep,
        )
        assert final.state == "done"
        # An episode for completion must have been recorded.
        with mem._connect() as conn:  # noqa: SLF001
            cnt = conn.execute(
                "SELECT COUNT(*) FROM episodes WHERE outcome = ?",
                ("success",),
            ).fetchone()[0]
        assert cnt >= 1

    def test_deadline_aborts_with_running_state(
        self, tmp_path: Path, sm: SemanticMemory, mem: EpisodicMemory,
    ) -> None:
        jobs_dir = tmp_path / "jobs"
        sess = jobs_dir / "abc12345"
        sess.mkdir(parents=True)
        (sess / "state.json").write_text(
            json.dumps({
                "state": "running",
                "tempo": "working",
                "daemonShort": "abc12345",
            }),
            encoding="utf-8",
        )
        # Deterministic VIRTUAL clock advanced by the (fake) sleeper, so the
        # deadline is honored on any runner regardless of wall-clock speed or
        # coarse OS timer granularity. Replaces a flaky absolute `dt < 2.0`
        # bound that broke on a slow/loaded Windows CI runner (job ran 21m vs
        # 5m on ubuntu). Tests the real invariant: the loop aborts via deadline
        # in a BOUNDED number of polls, deterministically.
        virtual = {"t": 1000.0}
        polls = {"n": 0}

        def fake_sleep(dt: float) -> None:
            polls["n"] += 1
            virtual["t"] += dt
            if polls["n"] > 1000:  # safety net: deadline never honored
                raise AssertionError("deadline must abort the loop")

        final = poll_until_done(
            "abc12345",
            topic=_TOPIC, sm=sm, mem=mem,
            run_id="r", agent_name="a",
            jobs_dir=jobs_dir,
            poll_interval_sec=0.01,
            deadline_sec=0.05,
            sleeper=fake_sleep,
            clock=lambda: virtual["t"],
        )
        assert final.state == "running"  # never reached terminal
        # 0.05s deadline / 0.01s interval => ~5 polls; bounded + deterministic
        assert polls["n"] <= 8, f"deadline not honored promptly: {polls['n']} polls"
