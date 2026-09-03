"""Cycle 2026-05-27 round 13 P0.5 — capability permission matrix registry.

Audit gap X1: 215 tool MCP senza una matrice di permessi sono
ingestibili, e un marketplace di plugin senza policy di permessi e'
veleno. Prima di una dashboard serve almeno una CLI/TUI che mostri
tool, capability, ultimi effetti, rollback disponibili e quarantene.

Per-tool declarations:
    capability:        READ / WRITE / EXECUTE / NETWORK / DESTRUCTIVE
    risk_level:        low / medium / high / critical
    reversibility:     yes / undoable / no
    requires_confirm:  must-prompt user before exec
    requires_sandbox:  must route through sandbox.SandboxedShell
    mandatory_log:     must always audit-log
    writes_memory:     mutates the persistent semantic store
    executes_command:  invokes shell / subprocess

Usage from MCP tool dispatcher OR sandbox wrapper:
    cap = REGISTRY.get("hippo_fact_forget")
    if cap.requires_confirm and not user_confirmed:
        return _err("requires user confirmation")

Initial population: ~15 critical tool that touch memory / shell / network.
The remaining 200 default to a conservative {READ, low, yes, no, no, no,
no, no} entry — they can be tightened later without breaking compat.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Capability = Literal["READ", "WRITE", "EXECUTE", "NETWORK", "DESTRUCTIVE"]
Risk = Literal["low", "medium", "high", "critical"]
Reversibility = Literal["yes", "undoable", "no"]


@dataclass(frozen=True)
class ToolCapability:
    """Static metadata describing what a tool can do + how it must be gated."""
    name: str
    capability: Capability
    risk_level: Risk
    reversibility: Reversibility
    requires_confirm: bool = False
    requires_sandbox: bool = False
    mandatory_log: bool = True
    writes_memory: bool = False
    executes_command: bool = False
    #: salta il gate senza lasciare traccia (efficienza sui READ). Prima
    #: del 03/09 era una lista a parte in `mcp_server.GATING_BYPASS_LIST`:
    #: due classificazioni, 5 tool su 28 in comune, e due voci che non
    #: corrispondevano a nessun tool. Ora la lista DERIVA da qui.
    gating_bypass: bool = False
    notes: str = ""


# Cycle 2026-05-27 round 14 FIX 1 (agy audit High): fail-CLOSED default.
# Pre-fix (round 13) ritornava {READ, low, no-confirm, no-sandbox} per tool
# unknown — fail-OPEN classico: un nuovo tool destructive non-classificato
# veniva trattato come read-only safe. agy audit confermato anti-pattern
# critical su tool_registry.py:190-204.
#
# Post-fix: tool unknown → DESTRUCTIVE/critical + requires_confirm=True +
# requires_sandbox=True + mandatory_log=True. Il caller deve esplicitamente
# whitelist il tool (via register()) prima di poterlo usare senza confirm.
DEFAULT_CAPABILITY = ToolCapability(
    name="<unknown>",
    capability="DESTRUCTIVE",
    risk_level="critical",
    reversibility="no",
    requires_confirm=True,
    requires_sandbox=True,
    mandatory_log=True,
    writes_memory=True,
    executes_command=True,
    notes=(
        "Fail-CLOSED default for unclassified tools. "
        "Register the tool explicitly via REGISTRY.register() before use."
    ),
)


# Initial classifications. Cycle 2026-05-27: 15 critical tool seeds.
# Extend over time as new tool are wired; new entries don't need migration.
_INITIAL_CAPS: tuple[ToolCapability, ...] = (
    # ---- WRITE memory ----
    ToolCapability(
        name="hippo_remember",
        capability="WRITE", risk_level="medium",
        reversibility="undoable",
        writes_memory=True,
        notes="Persists a fact. Gate auto-quarantines unverified claims.",
    ),
    ToolCapability(
        name="hippo_record_episode",
        capability="WRITE", risk_level="medium",
        reversibility="undoable",
        writes_memory=True,
        notes="Persists an episode + key_facts.",
    ),
    ToolCapability(
        name="hippo_skill_promote",
        capability="WRITE", risk_level="medium",
        reversibility="undoable",
        writes_memory=True,
    ),
    # ---- DESTRUCTIVE memory ----
    ToolCapability(
        name="hippo_fact_forget",
        capability="DESTRUCTIVE", risk_level="high",
        reversibility="no",
        requires_confirm=True,
        writes_memory=True,
        notes="Hard delete. Use hippo_fact_forget_with_undo for safety net.",
    ),
    ToolCapability(
        name="hippo_fact_forget_with_undo",
        capability="DESTRUCTIVE", risk_level="medium",
        reversibility="undoable",
        writes_memory=True,
        notes="Cycle round 13 P0c. Snapshots row to facts_undo_log (7d TTL).",
    ),
    ToolCapability(
        name="hippo_forget_scope",
        capability="DESTRUCTIVE", risk_level="medium",
        reversibility="undoable",
        requires_confirm=True,
        writes_memory=True,
        notes="B-1 mem0 delete_all(scope). dry_run default True; per-fact undo.",
    ),
    ToolCapability(
        name="hippo_undo_destructive_op",
        capability="WRITE", risk_level="low",
        reversibility="yes",
        writes_memory=True,
        notes="Restores a prior undoable destructive op.",
    ),
    ToolCapability(
        name="hippo_forget",
        capability="DESTRUCTIVE", risk_level="high",
        reversibility="no",
        requires_confirm=True,
        writes_memory=True,
        notes="Episode forget. Symmetric to fact forget.",
    ),
    ToolCapability(
        name="hippo_fact_supersede",
        capability="DESTRUCTIVE", risk_level="medium",
        reversibility="undoable",
        writes_memory=True,
        notes="Marks fact superseded. Reversible by editing superseded_by.",
    ),
    ToolCapability(
        name="hippo_decay_run",
        capability="DESTRUCTIVE", risk_level="high",
        reversibility="no",
        requires_confirm=True,
        writes_memory=True,
        notes="Decay sweep. Can mass-update statuses.",
    ),
    # ---- EXECUTE / SHELL ----
    ToolCapability(
        name="hippo_run_task",
        capability="EXECUTE", risk_level="high",
        reversibility="no",
        requires_sandbox=True,
        executes_command=True,
        notes="Runs LLM-driven task with tool calls. Sandbox-required.",
    ),
    ToolCapability(
        name="sandbox_exec",
        capability="EXECUTE", risk_level="high",
        reversibility="no",
        requires_confirm=False,
        requires_sandbox=True,
        executes_command=True,
        mandatory_log=True,
        notes=(
            "Task #48. Runs a command via SandboxedShell deny-by-default. "
            "No per-call confirm: the allowlist+denylist IS the gate "
            "(mirrors hippo_run_task). Always audited."
        ),
    ),
    # ---- READ memory ----
    ToolCapability(
        name="hippo_facts_search",
        gating_bypass=True,
        capability="READ", risk_level="low",
        reversibility="yes",
    ),
    ToolCapability(
        name="hippo_facts_recall",
        gating_bypass=True,
        capability="READ", risk_level="low",
        reversibility="yes",
    ),
    ToolCapability(
        name="hippo_recall",
        gating_bypass=True,
        capability="READ", risk_level="low",
        reversibility="yes",
    ),
    ToolCapability(
        name="hippo_undo_list",
        gating_bypass=True,
        capability="READ", risk_level="low",
        reversibility="yes",
    ),
    ToolCapability(
        name="hippo_retirement_log",
        gating_bypass=True,
        capability="READ", risk_level="low",
        reversibility="yes",
        notes="retirements as (loser, winner) pairs + "
              "survivability quartet. Read-only window on supersessions.",
    ),
    # Cycle 15 round 1 — anti-confab scrubber tools.
    ToolCapability(
        name="hippo_anti_confab_scan",
        gating_bypass=True,
        capability="READ", risk_level="low",
        reversibility="yes",
        notes="L2 reconciler scan over corpus. Read-only.",
    ),
    ToolCapability(
        name="hippo_anti_confab_apply",
        capability="WRITE", risk_level="medium",
        reversibility="undoable",
        writes_memory=True,
        notes="L2 reconciler apply (mark_orphaned). Undoable via status flip.",
    ),
    # ---- Cycle 03/09: i DODICI tool piu' CHIAMATI del journal.
    # Scelti per FREQUENZA e non per elenco: i 20 gia' classificati
    # coprivano il 38,1% delle chiamate reali, questi ne coprono un altro
    # 10,6% (misura in docs/stato-reale, cella W7-133). Per ognuno la
    # classificazione viene dalla descrizione che il tool dichiara di se'
    # o dalla riga di codice che lo prova, non dal nome.
    ToolCapability(
        name="hippo_recall_history",
        capability="READ", risk_level="low",
        reversibility="yes",
        notes="Answer-with-history recall: legge e arricchisce.",
    ),
    ToolCapability(
        name="hippo_facts_list",
        gating_bypass=True,
        capability="READ", risk_level="low",
        reversibility="yes",
        notes="Listing paginato dei fatti. Anche in GATING_BYPASS_LIST.",
    ),
    ToolCapability(
        name="hippo_trust_report",
        capability="READ", risk_level="low",
        reversibility="yes",
        notes="Dossier delle prove dietro una risposta.",
    ),
    ToolCapability(
        name="hippo_validate_claim",
        capability="READ", risk_level="low",
        reversibility="yes",
        notes="Handler mcp_server.py:12663-12673: chiama validate_claim e ritorna. Nel modulo le occorrenze di write sono tutte in commenti.",
    ),
    ToolCapability(
        name="hippo_facts_recent",
        gating_bypass=True,
        capability="READ", risk_level="low",
        reversibility="yes",
        notes="Ultimi N fatti per created_at. Anche in bypass.",
    ),
    ToolCapability(
        name="hippo_search",
        capability="READ", risk_level="low",
        reversibility="yes",
        notes="Ricerca per parola chiave sugli episodi.",
    ),
    ToolCapability(
        name="hippo_facts_find_conflicting",
        capability="READ", risk_level="low",
        reversibility="yes",
        notes="Audit L3 delle contraddizioni: legge.",
    ),
    ToolCapability(
        name="hippo_episode_list",
        gating_bypass=True,
        capability="READ", risk_level="low",
        reversibility="yes",
        notes="Listing paginato degli episodi. Anche in bypass.",
    ),
    ToolCapability(
        name="hippo_contradictions_list",
        capability="READ", risk_level="low",
        reversibility="yes",
        notes="Elenca le contraddizioni non risolte.",
    ),
    ToolCapability(
        name="hippo_consolidate",
        capability="WRITE", risk_level="medium",
        reversibility="undoable",
        writes_memory=True,
        notes="Trigger a sleep consolidation cycle: rielabora e scrive.",
    ),
    ToolCapability(
        name="hippo_contradictions_scan",
        capability="WRITE", risk_level="medium",
        reversibility="undoable",
        writes_memory=True,
        notes="PERSISTE le contraddizioni trovate — contradiction.py:625 e INSERT OR IGNORE in ContradictionStore.add (:637).",
    ),
    ToolCapability(
        name="hippo_skill_retire",
        capability="DESTRUCTIVE", risk_level="medium",
        reversibility="undoable",
        requires_confirm=True,
        writes_memory=True,
        notes="Ritira (archivia) una skill per id. E undoable, quindi la regola DESTRUCTIVE+irreversibile non lo obbligherebbe: la conferma e una scelta PIU prudente della regola, concordata il 03/09.",
    ),
    # ---- Cycle 03/09: i tool che SALTANO il gate.
    # Erano una lista a parte (`GATING_BYPASS_LIST`, 28 voci di cui solo
    # 5 anche qui, e due che non erano tool). Ora stanno qui con
    # `gating_bypass=True` e la lista si deriva. Tutti READ: l'handler
    # di ciascuno e' stato letto per intero, non a finestra.
    ToolCapability(
        name="hippo_chain_facts",
        capability="READ", risk_level="low",
        reversibility="yes", gating_bypass=True,
    ),
    ToolCapability(
        name="hippo_corpus_size",
        capability="READ", risk_level="low",
        reversibility="yes", gating_bypass=True,
    ),
    ToolCapability(
        name="hippo_count_by_agent",
        capability="READ", risk_level="low",
        reversibility="yes", gating_bypass=True,
    ),
    ToolCapability(
        name="hippo_dashboard_overview",
        capability="READ", risk_level="low",
        reversibility="yes", gating_bypass=True,
    ),
    ToolCapability(
        name="hippo_dashboard_overview_v2",
        capability="READ", risk_level="low",
        reversibility="yes", gating_bypass=True,
    ),
    ToolCapability(
        name="hippo_document_get",
        capability="READ", risk_level="low",
        reversibility="yes", gating_bypass=True,
    ),
    ToolCapability(
        name="hippo_document_list",
        capability="READ", risk_level="low",
        reversibility="yes", gating_bypass=True,
    ),
    ToolCapability(
        name="hippo_document_search",
        capability="READ", risk_level="low",
        reversibility="yes", gating_bypass=True,
    ),
    ToolCapability(
        name="hippo_document_versions",
        capability="READ", risk_level="low",
        reversibility="yes", gating_bypass=True,
    ),
    ToolCapability(
        name="hippo_episode_batch_get",
        capability="READ", risk_level="low",
        reversibility="yes", gating_bypass=True,
    ),
    ToolCapability(
        name="hippo_episode_get",
        capability="READ", risk_level="low",
        reversibility="yes", gating_bypass=True,
    ),
    ToolCapability(
        name="hippo_facts_topics",
        capability="READ", risk_level="low",
        reversibility="yes", gating_bypass=True,
    ),
    ToolCapability(
        name="hippo_health",
        capability="READ", risk_level="low",
        reversibility="yes", gating_bypass=True,
    ),
    ToolCapability(
        name="hippo_skill_describe",
        capability="READ", risk_level="low",
        reversibility="yes", gating_bypass=True,
    ),
    ToolCapability(
        name="hippo_skill_top",
        capability="READ", risk_level="low",
        reversibility="yes", gating_bypass=True,
    ),
    ToolCapability(
        name="hippo_skills_recent",
        capability="READ", risk_level="low",
        reversibility="yes", gating_bypass=True,
    ),
    ToolCapability(
        name="hippo_stats",
        capability="READ", risk_level="low",
        reversibility="yes", gating_bypass=True,
    ),
    ToolCapability(
        name="hippo_status",
        capability="READ", risk_level="low",
        reversibility="yes", gating_bypass=True,
    ),
    ToolCapability(
        name="hippo_transcript_recall",
        capability="READ", risk_level="low",
        reversibility="yes", gating_bypass=True,
    ),
)


@dataclass
class CapabilityRegistry:
    """Mutable registry. Initial population via _INITIAL_CAPS; extend at runtime
    via ``register``. Lookups via ``get`` (returns DEFAULT_CAPABILITY for
    unknown names so the matrix is closed/total)."""
    _caps: dict[str, ToolCapability] = field(default_factory=dict)

    def register(self, cap: ToolCapability) -> None:
        """Add or overwrite an entry. Idempotent."""
        self._caps[cap.name] = cap

    def get(self, name: str) -> ToolCapability:
        """Look up by name. Returns DEFAULT_CAPABILITY (READ/low) if unknown."""
        cap = self._caps.get(name)
        if cap is None:
            # Synthesize a default with the real name for audit clarity.
            return ToolCapability(
                name=name,
                capability=DEFAULT_CAPABILITY.capability,
                risk_level=DEFAULT_CAPABILITY.risk_level,
                reversibility=DEFAULT_CAPABILITY.reversibility,
                requires_confirm=DEFAULT_CAPABILITY.requires_confirm,
                requires_sandbox=DEFAULT_CAPABILITY.requires_sandbox,
                mandatory_log=DEFAULT_CAPABILITY.mandatory_log,
                writes_memory=DEFAULT_CAPABILITY.writes_memory,
                executes_command=DEFAULT_CAPABILITY.executes_command,
                notes="Auto-default (not classified yet).",
            )
        return cap

    def all(self) -> list[ToolCapability]:
        return sorted(self._caps.values(), key=lambda c: c.name)

    def by_capability(self, cap: Capability) -> list[ToolCapability]:
        return [c for c in self._caps.values() if c.capability == cap]

    def by_risk(self, risk: Risk) -> list[ToolCapability]:
        return [c for c in self._caps.values() if c.risk_level == risk]

    def writes_memory(self) -> list[ToolCapability]:
        return [c for c in self._caps.values() if c.writes_memory]

    def executes_command(self) -> list[ToolCapability]:
        return [c for c in self._caps.values() if c.executes_command]

    def requires_confirm(self) -> list[ToolCapability]:
        return [c for c in self._caps.values() if c.requires_confirm]


def build_default_registry() -> CapabilityRegistry:
    """Construct a fresh registry pre-populated with the 15 critical seeds."""
    reg = CapabilityRegistry()
    for cap in _INITIAL_CAPS:
        reg.register(cap)
    return reg


# Singleton convenience (module-level).
REGISTRY: CapabilityRegistry = build_default_registry()


__all__ = [
    "Capability",
    "CapabilityRegistry",
    "DEFAULT_CAPABILITY",
    "REGISTRY",
    "Reversibility",
    "Risk",
    "ToolCapability",
    "build_default_registry",
]
