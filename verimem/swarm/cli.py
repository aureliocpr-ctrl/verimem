"""Cycle #148.6.b (2026-05-18 sera) — Engram Swarm CLI surface.

Typer sub-app for human + agent operator commands:

    engram swarm run <config.yaml>     # end-to-end swarm run
    engram swarm status <run_id>       # list active sessions matching run
    engram swarm logs <short_id>       # passthrough to ``claude logs``
    engram swarm kill <run_id>         # ``claude stop`` for every match
    engram swarm clean <run_id>        # ``claude rm`` for every match

YAML schema mirrors :class:`SwarmConfig` 1:1, including per-agent
overrides for model / budget / permission / worktree / bare. Sample::

    run_id: cycle148-cli-test
    topic: lab/swarm/cycle148-cli-test
    timeout_sec: 600
    agents:
      - name: a
        prompt: |
          Do task A...
        model: haiku
        max_budget_usd: 0.5
        permission_mode: plan
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from .._proc_quiet import quiet_popen_kwargs
from ..memory import EpisodicMemory
from ..semantic import SemanticMemory
from .lifecycle import (
    list_swarm_sessions,
    remove_session,
    respawn_session,
    stop_session,
)
from .orchestrator import run_swarm
from .schemas import SwarmConfig

swarm_app = typer.Typer(
    help="Engram Swarm — orchestrate Claude --bg agent teams",
    no_args_is_help=True,
)
_console = Console()


def _load_config(path: Path) -> SwarmConfig:
    if not path.exists():
        raise typer.BadParameter(f"config file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise typer.BadParameter("config root must be a YAML mapping")
    return SwarmConfig.model_validate(data)


@swarm_app.command("run")
def run_cmd(
    config_path: Path = typer.Argument(  # noqa: B008 — typer convention
        ..., help="Path to swarm YAML config.",
    ),
    hub_master_ep_id: str = typer.Option(
        None, "--master-ep",
        help="Optional master-node Episode id to link the hub to.",
    ),
) -> None:
    """End-to-end swarm run: spawn N agents, poll until done, report."""
    cfg = _load_config(config_path)
    sm = SemanticMemory()
    mem = EpisodicMemory()

    _console.print(
        f"[cyan]Starting swarm[/cyan] run_id=[bold]{cfg.run_id}[/bold] "
        f"with {len(cfg.agents)} agents on topic [bold]{cfg.topic}[/bold]",
    )
    report = run_swarm(
        cfg, sm=sm, mem=mem,
        hub_master_ep_id=hub_master_ep_id,
    )

    tbl = Table(title=f"Swarm Report: {cfg.run_id}", expand=False)
    tbl.add_column("agent", style="bold")
    tbl.add_column("short_id")
    tbl.add_column("final_state")
    tbl.add_column("error")
    for a in report.agents:
        tbl.add_row(
            a.agent_name,
            a.short_id or "—",
            a.final_state,
            (a.error or "")[:40],
        )
    _console.print(tbl)
    _console.print(
        f"[green]success={report.success_count}[/green]  "
        f"[red]failure={report.failure_count}[/red]  "
        f"hub_ep={report.hub_ep_id}",
    )
    raise typer.Exit(code=0 if report.failure_count == 0 else 1)


@swarm_app.command("status")
def status_cmd(
    run_id: str = typer.Argument(..., help="Swarm run_id to inspect."),
) -> None:
    """List background sessions whose display name starts with <run_id>-."""
    ids = list_swarm_sessions(run_id)
    if not ids:
        _console.print(f"[dim]no sessions found for run_id={run_id}[/dim]")
        raise typer.Exit(code=0)
    for sid in ids:
        _console.print(sid)


@swarm_app.command("logs")
def logs_cmd(
    short_id: str = typer.Argument(..., help="Background session short id."),
) -> None:
    """Passthrough to ``claude logs <short_id>`` (terminal dump)."""
    proc = subprocess.run(
        ["claude", "logs", short_id],
        capture_output=True, text=True, timeout=15.0, check=False,
        **quiet_popen_kwargs(),
    )
    sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    raise typer.Exit(code=proc.returncode)


@swarm_app.command("kill")
def kill_cmd(
    run_id: str = typer.Argument(..., help="Swarm run_id to stop."),
    topic: str = typer.Option(
        None, "--topic",
        help="Audit chat topic (default: lab/swarm/<run_id>).",
    ),
) -> None:
    """``claude stop`` every session whose name starts with <run_id>-."""
    sm = SemanticMemory()
    chat_topic = topic or f"lab/swarm/{run_id}"
    ids = list_swarm_sessions(run_id)
    if not ids:
        _console.print(f"[dim]no sessions to kill for run_id={run_id}[/dim]")
        raise typer.Exit(code=0)
    failures = 0
    for sid in ids:
        ok = stop_session(sid, topic=chat_topic, sm=sm, agent_name="cli")
        marker = "[green]✓[/green]" if ok else "[red]✗[/red]"
        _console.print(f"  {marker} stop {sid}")
        if not ok:
            failures += 1
    raise typer.Exit(code=0 if failures == 0 else 1)


@swarm_app.command("clean")
def clean_cmd(
    run_id: str = typer.Argument(..., help="Swarm run_id to clean."),
    topic: str = typer.Option(
        None, "--topic",
        help="Audit chat topic (default: lab/swarm/<run_id>).",
    ),
) -> None:
    """``claude rm`` every session whose name starts with <run_id>-."""
    sm = SemanticMemory()
    chat_topic = topic or f"lab/swarm/{run_id}"
    ids = list_swarm_sessions(run_id)
    if not ids:
        _console.print(f"[dim]no sessions to clean for run_id={run_id}[/dim]")
        raise typer.Exit(code=0)
    failures = 0
    for sid in ids:
        ok = remove_session(sid, topic=chat_topic, sm=sm, agent_name="cli")
        marker = "[green]✓[/green]" if ok else "[red]✗[/red]"
        _console.print(f"  {marker} rm {sid}")
        if not ok:
            failures += 1
    raise typer.Exit(code=0 if failures == 0 else 1)


@swarm_app.command("respawn")
def respawn_cmd(
    short_id: str = typer.Argument(..., help="Session short id."),
    run_id: str = typer.Argument(..., help="Parent run_id (for audit)."),
    topic: str = typer.Option(
        None, "--topic",
        help="Audit chat topic (default: lab/swarm/<run_id>).",
    ),
) -> None:
    """``claude respawn`` one session with audit."""
    sm = SemanticMemory()
    chat_topic = topic or f"lab/swarm/{run_id}"
    ok = respawn_session(
        short_id, topic=chat_topic, sm=sm, agent_name="cli",
    )
    _console.print(
        f"  [green]✓[/green] respawn {short_id}" if ok
        else f"  [red]✗[/red] respawn {short_id} FAILED",
    )
    raise typer.Exit(code=0 if ok else 1)
