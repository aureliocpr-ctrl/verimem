"""Cycle #148.4 (2026-05-18 sera) — HippoAgent bridge for Claude bg sessions.

Mirrors session state changes into HippoAgent so that:
    1. Every meaningful transition becomes a chat fact on the swarm
       topic → cross-session conversational survival
    2. Every completion becomes an Episode linked (via narrative_link
       causal_edges) to the swarm coordination hub + the per-project
       master HippoAgent node → no fragmentation

Why this exists: ``claude --bg`` and ``agent-teams`` are in-memory and
local to the supervisor process. On supervisor restart the conversation
history persists in JSONL transcripts, but the inter-agent message
graph and the live state machine do not. The bridge gives us a
durable, queryable, lineage-traceable record that survives compaction.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from ..episode import Episode
from ..memory import EpisodicMemory
from ..semantic import Fact, SemanticMemory
from .state import SessionState, read_state

# State values we consider terminal for poll_until_done.
_TERMINAL_STATES: frozenset[str] = frozenset(
    {"done", "failed", "stopped", "error", "completed"},
)


def _hhmmss(ts: float | None = None) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts or time.time()))


def mirror_state_change(
    short_id: str,
    prev: SessionState | None,
    curr: SessionState,
    *,
    topic: str,
    sm: SemanticMemory,
    agent_name: str,
) -> str | None:
    """Write one chat fact iff ``curr.state`` differs from ``prev.state``.

    Returns the new fact id, or ``None`` when no transition happened.
    Tempo updates and detail-only changes are intentionally suppressed
    to keep the chat signal-to-noise high.
    """
    if prev is not None and (prev.state or "") == (curr.state or ""):
        return None

    transition = f"{(prev.state if prev else '∅') or '∅'} → {curr.state or '∅'}"
    detail_tail = f" — {curr.detail}" if curr.detail else ""
    role = f"swarm-{agent_name}"

    proposition = (
        f"[{role} @{_hhmmss()}] session {short_id} state: "
        f"{transition}{detail_tail}"
    )
    fact = Fact(
        proposition=proposition,
        topic=topic,
        confidence=1.0,
        verified_by=[f"claude:session:{short_id}"],
        status="model_claim",
    )
    sm.store(fact)
    return fact.id


def record_completion_episode(
    short_id: str,
    *,
    state: SessionState,
    run_id: str,
    agent_name: str,
    mem: EpisodicMemory,
    hub_ep_id: str | None = None,
    master_ep_id: str | None = None,
) -> str:
    """Create one Episode summarising the agent finish and link it.

    Outcome is derived from ``state.state``:
        • ``done`` / ``completed`` → success
        • everything else (failed, stopped, error, running-at-deadline) → failure

    Returns the new Episode id. If ``hub_ep_id`` or ``master_ep_id`` are
    provided, ``narrative_link`` causal_edges are written from the new
    episode to each of them — so cycle 144 auto-consolidation +
    ``hippo_lineage_trace`` reach the swarm sub-tasks from the master.
    """
    is_success = (state.state or "").lower() in ("done", "completed")
    outcome = "success" if is_success else "failure"

    final = (
        f"swarm agent {agent_name} (session {short_id}) finished in "
        f"state={state.state!r} tempo={state.tempo!r}\n"
        f"intent: {state.intent or '(none)'}\n"
        f"result: {state.output_result or '(no output captured)'}\n"
        f"detail: {state.detail or '(no detail)'}\n"
        f"jsonl: {state.jsonl_path or '(no transcript)'}"
    )

    ep = Episode(
        task_id=f"swarm/{run_id}/{agent_name}",
        task_text=(
            f"Cycle 148 swarm agent {agent_name} in run {run_id} "
            f"(claude --bg session {short_id})"
        ),
        final_answer=final,
        outcome=outcome,  # type: ignore[arg-type]
        created_at=time.time(),
    )
    mem.store(ep)

    # Cross-link via narrative_link to hub + master so cycle 144 +
    # hippo_lineage_trace walk the swarm in one hop.
    for dst in (hub_ep_id, master_ep_id):
        if not dst:
            continue
        with mem._connect() as conn:  # noqa: SLF001
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO causal_edges "
                    "(src_episode_id, dst_episode_id, via_skill_id, weight) "
                    "VALUES (?, ?, ?, ?)",
                    (ep.id, dst, "narrative_link", 1.0),
                )
            except Exception:  # noqa: BLE001 — defensive on edge insert
                pass
    return ep.id


def poll_until_done(
    short_id: str,
    *,
    topic: str,
    sm: SemanticMemory,
    mem: EpisodicMemory,
    run_id: str,
    agent_name: str,
    jobs_dir: Path | None = None,
    hub_ep_id: str | None = None,
    master_ep_id: str | None = None,
    poll_interval_sec: float = 1.0,
    deadline_sec: float = 600.0,
    sleeper: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.time,
) -> SessionState:
    """Poll ``read_state`` in a loop until terminal or deadline.

    Each state transition is mirrored. On a terminal state, a completion
    episode is recorded. On deadline elapse the function returns the
    last-seen state without recording a completion episode (the operator
    can decide whether to ``claude stop`` the session).
    """
    prev: SessionState | None = None
    deadline = clock() + deadline_sec
    last: SessionState | None = None

    while True:
        curr = read_state(short_id, jobs_dir=jobs_dir)
        if curr is None:
            # State file not yet written by the supervisor — wait one tick.
            if clock() >= deadline:
                return prev or SessionState()
            sleeper(poll_interval_sec)
            continue

        last = curr
        # Mirror only true state transitions (prev=None first time too).
        mirror_state_change(
            short_id, prev, curr,
            topic=topic, sm=sm, agent_name=agent_name,
        )
        prev = curr

        if (curr.state or "").lower() in _TERMINAL_STATES:
            record_completion_episode(
                short_id,
                state=curr,
                run_id=run_id,
                agent_name=agent_name,
                mem=mem,
                hub_ep_id=hub_ep_id,
                master_ep_id=master_ep_id,
            )
            return curr

        if clock() >= deadline:
            return last

        sleeper(poll_interval_sec)
