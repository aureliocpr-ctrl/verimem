"""The agent-onboarding guide — single source for every surface that teaches a
fresh agent how to use Verimem (mandate 2026-07-18: any new agent must learn the
usage at install time, with no external docs).

Consumed by:
- ``verimem mcp`` — returned in the MCP ``initialize`` response (``instructions``
  field), so every connecting MCP client gets it automatically;
- ``verimem agent-guide`` — prints it in the terminal (paste-able into any
  system prompt / CLAUDE.md / agent config).

Deliberately import-light (stdlib only): the CLI must not pay the mcp_server
import cost just to print the guide.
"""
from __future__ import annotations

#: Concise orientation returned to every MCP client on initialize. Orientation
#: only — each tool's exact arguments live in its own schema.
VERIMEM_AGENT_GUIDE = """\
Verimem is a VERIFIED-memory server for AI agents: writes pass an anti-confab
gate, and a fact its source does not support is QUARANTINED — stored, but kept
OUT of default recall, so you never get it back as truth.

Store with verimem_remember. What checks it, and when — the perimeter, so you
can rely on it:
- ALWAYS: a lexical screen on every write. Unsupported "it works / verified /
  done" self-claims are quarantined, with no LLM call.
- WITH a `source`: the entailment moat, the strong check — the fact is admitted
  only if the source TEXT actually supports it. `verified_by` records WHO
  vouches for a fact and does not run this check; pass the source text to get
  it.
- WITHOUT a source: there is nothing to check the fact against, so the moat does
  not run and the fact is stored as an unverified `model_claim`. Pass a source
  whenever you have one — it is what separates a claim from a verified fact.

Orientation (each tool's exact arguments are in its own schema):
- Retrieve with verimem_recall / verimem_facts_search. Ask verimem_trust_report
  HOW the store knows (a provenance dossier); on a question it cannot support it
  ABSTAINS ("I don't know") instead of stitching a guess from weak matches.
- Search indexed files with verimem_document_semantic_search (exact citations).

Principles: gated writes, provenance on every read, abstention over hallucination.
Prefer grounded writes. Legacy tool names use the hippo_ prefix; both work.
"""

#: Extended terminal guide: the MCP orientation plus the CLI/SDK map an agent
#: (or its human) needs to wire Verimem up from scratch.
AGENT_GUIDE_FULL = VERIMEM_AGENT_GUIDE + """
Wiring it up
------------
MCP (any MCP client — Claude Code, etc.): add to .mcp.json:
  {"mcpServers": {"verimem": {"command": "verimem", "args": ["mcp"],
    "env": {"VERIMEM_HOSTED": "1", "VERIMEM_TOOL_NAMESPACE": "verimem"}}}}
This guide is also delivered automatically to every MCP client on connect
(the `instructions` field of the initialize response).

Python SDK:
  from verimem import Memory
  m = Memory("memory.db")                  # moat ON by default, no llm needed
  m.add("fact", source="the evidence")     # gated write
  m.search("query"); m.explain("query")    # recall / provenance dossier

CLI essentials:
  verimem warmup      # pre-fetch the local models (first run)
  verimem doctor      # diagnose the install: daemon, moat judge, offline pins
  verimem status      # health check          verimem stats   # gate odometer
  verimem index FILE  # document memory       verimem search-docs "query"
  verimem trust "claim" --verified-by ref    # would Verimem trust this?
  verimem airgap [--live]                    # prove zero-egress
"""
