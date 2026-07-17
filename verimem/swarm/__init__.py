"""Cycle #148 (2026-05-18 sera) — Engram Swarm.

Orchestrator wrapper su primitive native Claude Code:
    • ``claude --bg`` (agent-view, v2.1.139+) — background sessions
    • CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 (agent-teams, v2.1.32+) — inter-
      agent SendMessage + shared task list

Cosa aggiunge ``engram swarm`` sopra le primitive:
    • Persistenza HippoAgent: ogni messaggio inter-agent → fact su topic
      chat dedicato → sopravvivenza cross-session (agent-teams in-process
      NON sopravvive a /resume).
    • Schemas typed (pydantic): SwarmConfig + AgentSpec validation.
    • Audit episode per ogni agent finish con related_episode_ids ai
      master node HippoAgent (no più frammentazione).
    • CLI ``engram swarm {spawn,status,kill,logs}``.
    • Bridge a ``engram lab live`` (cycle 146) per dashboard real-time.

Non sostituisce le primitive native — le sfrutta. Build subito su API
maintained da Anthropic invece di reinventing subprocess.Popen.
"""
from __future__ import annotations

from .schemas import AgentSpec, SwarmConfig

__all__ = ["AgentSpec", "SwarmConfig"]
