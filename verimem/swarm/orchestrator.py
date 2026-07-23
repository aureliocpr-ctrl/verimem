"""Cycle #148.6 (2026-05-18 sera) — Engram Swarm orchestrator.

Stitches schemas + spawn + state + bridge + lifecycle into a single
top-level :func:`run_swarm` call. Use this when you want one Python
entry point for a full swarm run; the CLI in :mod:`verimem.swarm.cli`
delegates here.

Flow:
    1. Validate config (already done by pydantic at construction).
    2. Create a coordination hub Episode + opening chat fact.
    3. For each AgentSpec: ``spawn_agent`` synchronously to get the
       short id (the spawn itself returns in <2s — only the daemon job
       sits long).
    4. In parallel (threading.Thread): ``poll_until_done`` each agent's
       state.json. Each poller mirrors transitions + records the
       completion episode + narrative_link edges to hub.
    5. Aggregate into SwarmReport.
    6. Write final summary chat fact on topic.

Parallelism: threading (not asyncio) because ``poll_until_done`` does
blocking sleep + sqlite calls — threads are simpler and CPython releases
the GIL on these primitives.
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ..episode import Episode
from ..memory import EpisodicMemory
from ..orchestration import CHRONICLE_CONFIDENCE, agent_principal
from .bridge import poll_until_done
from .schemas import SwarmConfig
from .spawn import SpawnResult, spawn_agent
from .state import SessionState

if TYPE_CHECKING:  # avoid a hard import cycle at module load
    from ..client import Memory


@dataclass
class AgentReport:
    agent_name: str
    short_id: str | None
    final_state: str
    final_state_obj: SessionState | None = None
    spawned_at: float = 0.0
    finished_at: float = 0.0
    error: str | None = None


@dataclass
class SwarmReport:
    run_id: str
    topic: str
    hub_ep_id: str
    agents: list[AgentReport] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    started_at: float = 0.0
    finished_at: float = 0.0


def _create_hub_episode(
    config: SwarmConfig, mem: EpisodicMemory,
    *, hub_master_ep_id: str | None = None,
) -> str:
    intro_lines = [
        f"Engram Swarm run {config.run_id} — {len(config.agents)} agents on topic {config.topic}.",
    ]
    for a in config.agents:
        intro_lines.append(
            f"  • {a.name} model={a.model} budget=${a.max_budget_usd} "
            f"perm={a.permission_mode} worktree={a.worktree}",
        )
    intro = "\n".join(intro_lines)

    ep = Episode(
        task_id=f"swarm/{config.run_id}/hub",
        task_text=(
            f"Engram Swarm coordination hub for run {config.run_id} "
            f"on topic {config.topic}"
        ),
        final_answer=intro,
        outcome="success",
        created_at=time.time(),
    )
    mem.store(ep)
    if hub_master_ep_id:
        with mem._connect() as conn:  # noqa: SLF001
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO causal_edges "
                    "(src_episode_id, dst_episode_id, via_skill_id, weight) "
                    "VALUES (?, ?, ?, ?)",
                    (ep.id, hub_master_ep_id, "narrative_link", 1.0),
                )
            except Exception:  # noqa: BLE001
                pass
    return ep.id


def _opening_chat_fact(
    config: SwarmConfig, memory: Memory,
) -> str | None:
    """Chronicle the run START. Returns the fact id so the closing
    chronicle can chain its ``lineage_to`` back to it (one navigable
    run thread)."""
    proposition = (
        f"[swarm-ORCHESTRATOR @{time.strftime('%H:%M:%S')}] run "
        f"{config.run_id} START with {len(config.agents)} agents: "
        + ", ".join(f"{a.name}({a.model})" for a in config.agents)
    )
    r = memory.add(
        proposition, topic=config.topic,
        principal=agent_principal("swarm", config.run_id, "hub"),
        chronicle=True, meta_narrative=True,
        confidence=CHRONICLE_CONFIDENCE,
    )
    return r.get("id") if r.get("stored") else None


def _final_chat_fact(
    config: SwarmConfig, report: SwarmReport, memory: Memory,
    *, opening_fact_id: str | None = None,
) -> str | None:
    """Chronicle the run FINISHED, chained to the opening chronicle."""
    proposition = (
        f"[swarm-ORCHESTRATOR @{time.strftime('%H:%M:%S')}] run "
        f"{config.run_id} FINISHED success={report.success_count} "
        f"failure={report.failure_count} of {len(report.agents)} agents"
    )
    r = memory.add(
        proposition, topic=config.topic,
        verified_by=[f"swarm:run:{config.run_id}"],
        principal=agent_principal("swarm", config.run_id, "hub"),
        chronicle=True, meta_narrative=True,
        confidence=CHRONICLE_CONFIDENCE,
        lineage_to=[opening_fact_id] if opening_fact_id else None,
    )
    return r.get("id") if r.get("stored") else None


def run_swarm(
    config: SwarmConfig,
    *,
    memory: Memory,
    mem: EpisodicMemory,
    jobs_dir: Path | None = None,
    spawn_fn: Callable[..., SpawnResult] = spawn_agent,
    poll_fn: Callable[..., SessionState] = poll_until_done,
    hub_master_ep_id: str | None = None,
) -> SwarmReport:
    """Run one swarm end-to-end. Blocks until every agent finishes
    (or the swarm's ``timeout_sec`` deadline elapses for each agent).

    ``memory`` is the gated SDK ``Memory`` — every chronicle fact goes
    through its moat. ``mem`` is the episodic log (raw by design: the
    gate governs recalled facts, not the audit trail).
    """
    started = time.time()
    hub_ep_id = _create_hub_episode(
        config, mem, hub_master_ep_id=hub_master_ep_id,
    )
    opening_fact_id = _opening_chat_fact(config, memory)

    # Spawn synchronously (each call <2s).
    spawn_outcomes: dict[str, SpawnResult | str] = {}
    for spec in config.agents:
        try:
            res = spawn_fn(
                spec,
                run_id=config.run_id,
                swarm_cwd=Path(config.cwd) if config.cwd else None,
            )
            spawn_outcomes[spec.name] = res
        except Exception as exc:  # noqa: BLE001 — surface as agent failure
            spawn_outcomes[spec.name] = f"spawn error: {exc}"

    # Poll all in parallel via threads.
    results: dict[str, SessionState] = {}
    errors: dict[str, str] = {}
    threads: list[threading.Thread] = []

    def _worker(name: str, short_id: str) -> None:
        try:
            final = poll_fn(
                short_id,
                topic=config.topic,
                memory=memory, mem=mem,
                run_id=config.run_id,
                agent_name=name,
                jobs_dir=jobs_dir,
                hub_ep_id=hub_ep_id,
                master_ep_id=hub_master_ep_id,
                poll_interval_sec=1.0,
                deadline_sec=float(config.timeout_sec),
            )
            results[name] = final
        except Exception as exc:  # noqa: BLE001
            errors[name] = str(exc)

    for spec in config.agents:
        out = spawn_outcomes[spec.name]
        if isinstance(out, SpawnResult):
            t = threading.Thread(
                target=_worker, args=(spec.name, out.short_id), daemon=True,
            )
            t.start()
            threads.append(t)
        else:
            errors[spec.name] = str(out)

    for t in threads:
        # Each agent has its own internal deadline (config.timeout_sec).
        # Outer join uses 1.5× as belt-and-suspenders to release the worker.
        t.join(timeout=config.timeout_sec * 1.5)

    # Aggregate.
    agent_reports: list[AgentReport] = []
    succ = 0
    fail = 0
    for spec in config.agents:
        sid = None
        out = spawn_outcomes[spec.name]
        if isinstance(out, SpawnResult):
            sid = out.short_id
        st = results.get(spec.name)
        err = errors.get(spec.name)
        final_state = (st.state if st else "no-state") if not err else "spawn-error"
        is_succ = final_state.lower() in ("done", "completed")
        if is_succ:
            succ += 1
        else:
            fail += 1
        agent_reports.append(AgentReport(
            agent_name=spec.name,
            short_id=sid,
            final_state=final_state,
            final_state_obj=st,
            spawned_at=out.spawned_at if isinstance(out, SpawnResult) else 0.0,
            finished_at=time.time(),
            error=err,
        ))

    report = SwarmReport(
        run_id=config.run_id,
        topic=config.topic,
        hub_ep_id=hub_ep_id,
        agents=agent_reports,
        success_count=succ,
        failure_count=fail,
        started_at=started,
        finished_at=time.time(),
    )
    _final_chat_fact(config, report, memory, opening_fact_id=opening_fact_id)
    return report
