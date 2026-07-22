"""Cycle #138 (2026-05-18) — anti-confabulation gate on write.

Aurelio direttiva 2026-05-18: gate on write. Wraps the L1 family
(cycle 128/130/131) + the L3 validate_claim (cycle #70) into a single
``run_validation_gate(...)`` helper that the hippo_remember handler
calls BEFORE persisting a Fact.

Tiers
-----
* ``validate="off"``  — bypass every check. Pure escape hatch for
  migrations, replays, deliberate writes.
* ``validate="fast"`` (default) — run L1, L1.5, L1.7 detectors. Each is
  a pure substring match; cold execution << 1 ms on the standard
  corpus. Any positive triggers the gate.
* ``validate="full"`` — fast + ``validate_claim`` cycle #70 over the
  agent's semantic memory. Mean ~13 ms, p95 ~40 ms on a 1183-fact live
  corpus (FASE-1 benchmark 2026-05-18). The extra coverage catches
  year-disjoint contradictions (Tonegawa 1987 vs 2014, Anthropic Skills
  2025 vs 2026 — the historical 2026-05-14 confabulations).

Modes
-----
* ``gate_mode="downgrade"`` (default) — if any check fires, persist
  the fact BUT force ``status='provisional'`` so the suspect claim is
  hidden from default recall yet preserved for audit.
* ``gate_mode="reject"`` — if L3 marks the claim ``contradicted``,
  refuse to persist; return action=``reject`` with advice + the
  contradicting fact ids. L1 still merely downgrades (not reject —
  keyword heuristics are too coarse for a hard block).

``force_persist=True`` overrides everything: the gate still runs and
its warnings are reported, but the caller's wish to persist wins.

Env override
------------
``ENGRAM_VALIDATE_DEFAULT`` (``"off"|"fast"|"full"``) sets the default
when the per-call ``validate`` argument is omitted. Lets the operator
toggle the gate globally without code change.
"""
from __future__ import annotations

import os
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from .anti_confabulation import (
    detect_unsupported_diagnosis_claim,
    detect_unsupported_shipped_claim,
    detect_unsupported_task_state_claim,
)

# Cycle 2026-05-27 (round 8): wire L1.16 approval detector.
# Closes business-process gap: "approved/signed-off/authorized" sin
# formal approval evidence (approver/review/pr/ticket/email/chat).
from .l1_approval_detector import detect_unsupported_approval_claim

# Cycle 2026-05-27 (round 10): wire L1.18 automated/scheduled detector.
# Closes scheduler gap: "automated/scheduled/recurring" sin cron/
# workflow/scheduler evidence.
from .l1_automated_detector import detect_unsupported_automated_claim

# Cycle 2026-05-27 (round 5): wire L1.13 completion claim detector.
# Closes A1 ANTI-CONFAB gap per "task done/complete/finished" claims.
# Claude architectural choice post Gemini-GPT divergence (round 5):
# (e) complete/done is ortogonal a L1.0 SHIPPED + L1.10 works +
# L1.11 prod-ready + L1.12 security.
from .l1_completion_detector import detect_unsupported_completion_claim

# Cycle 2026-05-27 (round 6): wire L1.14 documentation detector.
# Closes A4 NO MARKETING gap per "documented/explained" claims.
# Ortogonal a tutti detector esistenti.
from .l1_documentation_detector import detect_unsupported_doc_claim

# Cycle 184 (2026-05-23): wire the cycle-183 FIX-family detector into the
# L1 chain. Kept as a side-by-side import so the legacy 3-detector behaviour
# stays byte-identical if the new module ever needs to be disabled.
from .l1_extended_detector import detect_unsupported_fix_claim

# Cycle 2026-05-27 (round 9): wire L1.17 monitored/observed detector.
# Closes observability gap: "monitored/tracked/alerted" sin dashboard/
# alert/metric/telemetry evidence.
from .l1_monitored_detector import detect_unsupported_monitored_claim

# Cycle 2026-05-27: wire L1.9 performance-claim detector. Closes M12 PTY
# hallucination gap (fact fbaa77df3860). Detects "X->Y", "Nx faster",
# "N% speedup", "game changer" claims without bench evidence.
from .l1_performance_detector import detect_unsupported_performance_claim

# Cycle 2026-05-27 (round 3): wire L1.11 production-ready detector.
# Closes A2 ANTI-HALL + A4 NO MARKETING gap. Detects
# "production-ready/stable/robust" claims without coverage/soak/release.
# Triangulated Claude+Gemini+GPT all voted (b) as L1.11.
from .l1_production_ready_detector import detect_unsupported_prod_ready_claim

# Cycle 2026-05-27 (round 11 final): wire L1.19 quantitative detector.
# Gemini-identified gap: absolute numeric metrics (50ms, 95% coverage,
# 1.2M records) sin measurement source. Distinct da L1.9 comparative.
from .l1_quantitative_detector import detect_unsupported_quant_claim

# Cycle 2026-05-27 (round 4): wire L1.12 security/hardened detector.
# Closes A2 ANTI-HALL gap per security claims. Detects "secure/hardened/
# blindato/CVE-" claims without audit/pentest/threat_model evidence.
# Triangulated Claude+Gemini+GPT all voted (d) as L1.12.
from .l1_security_detector import detect_unsupported_security_claim

# Cycle 2026-05-27 (round 7): wire L1.15 tested/verified detector.
# Ortogonal a L1.10 works (runtime claim) — L1.15 cattura process
# claim su "testato/verificato" sin pytest/coverage evidence.
from .l1_tested_detector import detect_unsupported_tested_claim

# Cycle 2026-05-27 (round 2): wire L1.10 works/confirmed detector.
# Closes A2 ANTI-HALL gap. Detects "funziona/works/confirmed/risolto"
# claims without runtime evidence (pytest/bash:exit0/smoke).
# Triangulated Claude+Gemini+GPT all favored this as L1.10 priority.
from .l1_works_detector import detect_unsupported_works_claim

# Security fix 2026-06-02 (sorelle loop): token-gate the trusted-hook
# bypass. writer_role alone is client-spoofable (set via MCP arguments),
# so the bypass now also requires a server-side secret token.
from .trusted_writer import verify_trusted_writer

ValidateLevel = Literal["off", "fast", "full"]
GateMode = Literal["downgrade", "reject"]
GateAction = Literal["persist", "downgrade", "reject"]


_VALID_LEVELS: frozenset[str] = frozenset({"off", "fast", "full"})
_VALID_MODES: frozenset[str] = frozenset({"downgrade", "reject"})

# Cycle 2026-05-27 (round 12 — F-fix): trusted-hook bypass for
# retrospective continuity facts. Closes BUG where master pre-compact
# fact got quarantined by L1.x detectors firing on retrospective
# keywords (COMPLETO/SHIPPED/Authorized/MONITORED/AUTOMATED).
#
# Design via Claude+Gemini+GPT triangulation: GPT proposal F preferred
# over Gemini D — provenance-based bypass NOT topic-based (topic is
# user-controllable and would let an attacker inject `handoff/` prefix
# to bypass detectors with claims like "X is production-ready").
#
# Bypass requires BOTH conditions:
#   1. writer_role IN TRUSTED_HOOKS (not user-controllable)
#   2. meta_narrative=True (explicit retrospective marker)
#
# Either alone is insufficient — defense in depth.
TRUSTED_HOOKS: frozenset[str] = frozenset({"system_hook", "trusted_hook"})


def _graded_admission() -> bool:
    """Env switch ``ENGRAM_GRADED_ADMISSION`` (DEFAULT OFF — design bf5d322
    step 1). When ON, a grounding SHORTFALL (CE/judge score below the write
    threshold, or the CE review band with no adjudicator) no longer hard-
    quarantines a write that DECLARED a source: the fact persists as a
    low-confidence model_claim and the receipt records the shortfall
    (``L4-grounding-graded`` / ``L4-review-graded`` — non-escalating layers).
    Quarantine stays reserved for injection and active contradiction, which
    escalate independently. Rationale (measured, HaluMem external A/B at the
    shipped cut 40): the hard reject loses 33% of CLEAN facts while noise
    rejection is achievable on the READ side by weighting low-conf items —
    the pre-registered A/B for that flip lives with the design doc."""
    v = os.environ.get("ENGRAM_GRADED_ADMISSION", "").strip().lower()
    return v in ("1", "true", "on", "yes", "enforce")


def _l1_domain_precision() -> bool:
    """Env ``ENGRAM_L1_DOMAIN_PRECISION`` — **DEFAULT ON** (flipped 2026-07-22 on
    Aurelio's mandate: the cures ship ENABLED; explicit opt-out restores the
    legacy always-escalate via "0"/"false"/"off"/"no").

    When on, the L1 keyword escalation is suppressed PER FACT for propositions
    the subject classifier reads as third-party professional facts (see
    ``verimem.subject_extract.is_domain_professional``). Surgical alternative to
    the reverted global L1 flip (d15e4ca): an agent's own software self-claim
    STILL escalates — the carve-out is content-based, not a global disarm.
    Relaxes only L1; L3/L4/injection are untouched. Promotion gates that earned
    the flip: vertical corpus FP 86.7%→0.0%, critic claim_holds (8f6d0ec5 +
    cb26737b), 463-test blast, full suite 7704/0, flip-delta audit (numeric-head
    fail-safe closed pre-flip)."""
    v = os.environ.get("ENGRAM_L1_DOMAIN_PRECISION", "").strip().lower()
    return v not in ("0", "false", "off", "no")


def _is_domain_professional_fact(proposition: str) -> bool:
    """Thin, fail-soft wrapper: a classifier import/logic fault must never crash
    a write — it degrades to 'not domain' (L1 keeps escalating, the safe side)."""
    try:
        from .subject_extract import is_domain_professional
        return bool(is_domain_professional(proposition))
    except Exception:  # noqa: BLE001 — classifier must not break the gate
        return False


def _l1_domain_advisory() -> bool:
    """SERVER-SIDE, deployment-level switch (env ``ENGRAM_L1_DOMAIN_ADVISORY``,
    default OFF). When ON, the L1.x keyword anti-confabulation detectors run and
    surface their warnings but do NOT escalate to quarantine.

    Rationale (measured 2026-07-21: 86.7% of legitimate lawyer/engineer/
    clinician facts quarantined; design memos kimi+glm, verified on source):
    the L1.x family polices an AGENT confabulating about its OWN code work
    ('it works', 'deployed', 'tests pass'). A deployment that stores CUSTOMER
    domain facts has no such agent, so those detectors are category-error there.

    It is an ENV switch, NOT a per-write ``add()`` argument, on purpose: a
    per-write flag is ``writer_role`` without a token — spoofable by an injected
    prompt (the exact hole the trusted-hook bypass had to token-gate at
    :882). A deployment operator sets this once, server-side; a write payload
    can never assert it.

    SCOPE (verified 2026-07-21, kimi review): it relaxes ONLY the L1* keyword
    family — every ``startswith("L1")`` layer (bare L1, L1.5 diagnosis, L1.7
    task-state, L1.8–L1.21), all of which are keyword detectors. The L3
    (contradiction) and L4 (grounding) gates carry ``L3``/``L4`` labels that
    ``startswith("L1")`` does NOT match, so they stay fail-closed.

    DELIBERATELY UNCONDITIONAL (glm review a-1, resolved by measurement): the
    two neighbouring suppressors ``_personal_fp``/``_world_fp`` defer to
    ``_no_dev`` because they are per-fact CONTENT guesses. This one is an
    operator's DEPLOYMENT declaration — higher authority than a keyword guess,
    so it does NOT defer to ``_has_dev_context`` (measured: gating on it
    re-quarantines 3/30 legitimate engineering/clinical facts — 'tested to 400
    kilonewtons', 'the bridge was deployed' — because that heuristic is itself
    keyword-blind, the very disease this cures). The fail-open is bounded: an
    ungrounded dev self-claim in this mode still hits L4 when a grounding judge
    is configured (test_advisory_dev_claim_still_hits_L4_grounding)."""
    v = os.environ.get("ENGRAM_L1_DOMAIN_ADVISORY", "").strip().lower()
    return v in ("1", "true", "on", "yes")


class _SemanticLike(Protocol):
    def search_facts(
        self, query: str, *, limit: int = 20, topic: str | None = None,
    ) -> list[Any]: ...


class _AgentLike(Protocol):
    semantic: _SemanticLike


@dataclass
class GateResult:
    """Outcome of one gate evaluation.

    Attributes
    ----------
    action :
        ``"persist"``  — clean claim; caller stores it as-is.
        ``"downgrade"`` — at least one warning; caller persists with
        ``status="provisional"``.
        ``"reject"`` — L3 contradiction + ``gate_mode="reject"``; caller
        must NOT persist and should return a rejection payload.
    warnings :
        List of ``{"layer": "L1|L1.5|L1.7|L3", "reason": str, ...}``
        dicts. Always populated whenever a detector fired (regardless
        of the final action).
    contradicting_fact_ids :
        Non-empty only when L3 found a contradicting evidence fact.
    advice :
        Caller-facing string suitable for echoing to the LLM/operator.
    """
    action: GateAction
    warnings: list[dict[str, Any]] = field(default_factory=list)
    contradicting_fact_ids: list[str] = field(default_factory=list)
    #: OLD facts a same-source EVOLUTION supersedes (ENGRAM_SUPERSEDE_SAME_SOURCE
    #: enforce): the new write is ADMITTED and these are retired — distinct from
    #: contradicting_fact_ids, which quarantines the NEW write. Empty by default. The
    #: caller must only act on these when ``action == "persist"`` (a new write
    #: quarantined for another reason must not retire the old value).
    supersede_fact_ids: list[str] = field(default_factory=list)
    advice: str = ""
    #: L4 source⊢fact entailment score (0-100) WHEN computed (source + grounding_llm +
    #: ENGRAM_GROUNDING_WRITE), else None. Previously discarded after the pass/fail
    #: decision; now surfaced so the caller can PERSIST it on the fact and condition
    #: retrieval/answering on it (the moonshot 2026-06-20: a write-time trust signal no
    #: competitor has). None = not computed (default fast path).
    grounding_score: float | None = None
    #: judge-of-record: WHICH judge scored L4 ('local' CE, or 'claude'/
    #: 'interactive' injected llm), or None when no entailment judge ran.
    #: Surfaced so a provider swap is auditable, never a silent drift.
    judge: str | None = None
    #: the admission cut the score was compared to (judge-scale-consistent),
    #: or None when no numeric judge ran. score - threshold = the margin.
    threshold: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "warnings": list(self.warnings),
            "contradicting_fact_ids": list(self.contradicting_fact_ids),
            "supersede_fact_ids": list(self.supersede_fact_ids),
            "grounding_score": self.grounding_score,
            "judge": self.judge,
            "threshold": self.threshold,
            "advice": self.advice,
        }


def _resolve_level(level: str | None) -> ValidateLevel:
    """Normalize the requested level, falling back to env then ``"fast"``.

    Unknown values fall back to ``"fast"`` rather than raising — defensive
    against typos in LLM-generated arguments.
    """
    if level is not None:
        v = str(level).strip().lower()
        if v in _VALID_LEVELS:
            return v  # type: ignore[return-value]
    env = os.environ.get("ENGRAM_VALIDATE_DEFAULT", "").strip().lower()
    if env in _VALID_LEVELS:
        return env  # type: ignore[return-value]
    return "fast"


def _resolve_mode(mode: str | None) -> GateMode:
    """Normalize the requested gate mode; unknown values → ``"downgrade"``."""
    if mode is not None:
        v = str(mode).strip().lower()
        if v in _VALID_MODES:
            return v  # type: ignore[return-value]
    return "downgrade"


def _grounding_write_on() -> bool:
    """Whether the opt-in SEMANTIC write-path grounding check (L4) is enabled."""
    import os
    return os.environ.get("ENGRAM_GROUNDING_WRITE", "").strip().lower() in (
        "1", "on", "true", "yes")


def _semantic_conflict_mode() -> str:
    """Mode of the opt-in NLI semantic-contradiction moat (L3-semantic): one of
    ``"off"`` / ``"observe"`` / ``"enforce"`` from ``ENGRAM_SEMANTIC_CONFLICT``.

    - unset → **auto**: ``"enforce"`` iff the local NLI model is already
      installed (``local_relation.local_nli_available()``, filesystem-only);
      otherwise ``"off"`` — a fresh install without the model pays nothing.
    - 0 / off / false / no → ``"off"``: the detector is NOT called; the
      lexical default path (~13ms, no judge) is unchanged, zero cost.
    - observe / log / shadow → ``"observe"``: the detector runs (llm-free, on the
      local NLI cross-encoder when no ``agent.llm`` is present) and SURFACES a
      contradiction as an advisory warning, but does NOT quarantine the write — so
      the false-block rate is measurable on real tenants before enforcing (the same
      observe→enforce discipline as the CE band + source_trust).
    - 1 / on / true / yes / enforce → ``"enforce"``: a contradiction quarantines the
      write (downgrade), as before.
    """
    import os
    v = os.environ.get("ENGRAM_SEMANTIC_CONFLICT", "").strip().lower()
    if v in ("observe", "log", "shadow"):
        return "observe"
    if v in ("1", "on", "true", "yes", "enforce"):
        return "enforce"
    if v in ("0", "off", "false", "no"):
        return "off"
    # UNSET → AUTO (0.7.0): the tier enforces iff the local NLI model is
    # already installed (pure-filesystem check, no load) — shipped capability
    # = enabled capability. A fresh install without the model pays nothing.
    if v == "":
        from . import local_relation as _lr
        if _lr.local_nli_available():
            return "enforce"
    return "off"


def _semantic_conflict_on() -> bool:
    """Back-compat: the L3-semantic moat is active (observe OR enforce)."""
    return _semantic_conflict_mode() != "off"


def _l3_subject_filter() -> bool:
    """ENGRAM_L3_SUBJECT_FILTER (default OFF): filter the sibling list by
    subject (verimem.subject_extract.same_subject) BEFORE the NLI judge —
    different-subject pairs are the judge's measured FP class (the cosine 0.7
    pre-filter is inert: 595/595 corpus pairs clear it). Fail-open by design:
    an unattributable subject compares everything."""
    import os
    return os.environ.get("ENGRAM_L3_SUBJECT_FILTER", "").strip().lower() in (
        "1", "true", "on", "yes", "enforce")


def _supersede_same_source_on() -> bool:
    """When a clash is a same-source EVOLUTION (the source restating its own value with a
    newer valid-time), ADMIT the new write and retire the OLD — instead of quarantining
    the new. **Default ON (2026-07-19):** evolving memory that retires a stale same-source
    value is the product's core promise, not an opt-in.

    Safety without source authentication (verimem has none — ``verified_by`` is caller-
    controlled, even the ``actor:`` prefix is a bare string): (a) the TENANCY isolation
    boundary blocks cross-tenant writes; (b) cross-source clashes never reach this path
    (they classify as 'conflict' → quarantined, not superseded), so the griefing surface
    is intra-tenant only; (c) a single-agent-per-tenant assumption (the sole agent
    superseding its OWN values is the intended feature) holds for the common deployment.
    A multi-agent-per-tenant deployment that cannot trust its own writers sets
    ``ENGRAM_SUPERSEDE_SAME_SOURCE=0`` until per-agent auth (the intra-tenant gap) ships.

    OPEN RISK (independent red-team audit, 2026-07-20): the architecture-A thin tier
    makes assumption (c) FALSE BY CONSTRUCTION where it is used — N agent sessions behind
    one shared server authenticate with ONE tenant key, so they are many writers in one
    tenant, and a single compromised session can retire another's true values (spoofable
    ``verified_by`` + caller-controlled ``asserted_at`` → same-source "evolution"). The
    default is deliberately left ON pending an explicit product decision; a shared-server
    deployment that cannot trust every session sets ``ENGRAM_SUPERSEDE_SAME_SOURCE=0``.
    Documented rather than silently flipped: changing a shipped default is a product
    call, not an audit side effect."""
    import os
    _explicit = os.environ.get("ENGRAM_SUPERSEDE_SAME_SOURCE")
    if _explicit is not None and _explicit.strip() != "":
        # An operator who knows their writers stays in control, both ways.
        return _explicit.strip().lower() not in ("0", "off", "false", "no")
    # No explicit setting: the default FOLLOWS the assumption it rests on.
    # A shared server (architecture A) has N agent sessions behind ONE tenant
    # key -> many writers in one tenant -> premise (c) is false by
    # construction, so the safe default THERE is off. An embedded
    # single-agent store keeps it on: retiring its own stale value is the
    # product's core promise, and the sole writer cannot grief itself.
    _shared = os.environ.get("VERIMEM_MULTI_WRITER", "").strip().lower()
    if _shared not in ("", "0", "off", "false", "no"):
        return False
    return True


def _route_evolutions(agent: Any, verified_by: Any, asserted_at: float | None,
                      ids: list[str], supersede_ids: list[str],
                      new_status: str | None = None) -> list[str]:
    """Partition contradicting OLD fact ids into EVOLUTIONS (same canonical source +
    later valid-time + at least as trusted → appended to ``supersede_ids``, retired) and
    genuine CONFLICTS (returned, to quarantine the new write). This gives contradictions
    caught by the LEXICAL L3 (numeric / version / date — the most common evolutions) the
    same handling as the NLI layer. Fetches each old fact from the agent's store.

    RANK FLOOR (anti-confab): a weaker new write never supersedes a STRONGER old one — an
    unverified ``model_claim`` contradicting a ``verified`` fact is a suspect
    confabulation, not an evolution, so it stays a CONFLICT (quarantined), protecting the
    verified fact. Any miss OR a cross-source clash also stays a conflict (griefing guard)."""
    import time as _t
    import types as _ty

    from .semantic import _STATUS_RANK
    from .supersession_policy import classify_write_relation
    sm = getattr(agent, "semantic", None) if agent is not None else None
    if sm is None:
        return list(ids)
    cand = _ty.SimpleNamespace(verified_by=verified_by, created_at=_t.time(),
                               asserted_at=asserted_at)
    _nr = _STATUS_RANK.get(new_status or "model_claim", 2)
    conflicts: list[str] = []
    for cid in ids:
        try:
            old = sm.get(cid)
        except Exception:  # noqa: BLE001 — a lookup miss is treated as a conflict
            old = None
        if (old is not None
                and classify_write_relation(cand, old) == "evolution"
                and _STATUS_RANK.get(getattr(old, "status", "model_claim"), 2) <= _nr):
            if cid not in supersede_ids:
                supersede_ids.append(cid)
        else:
            conflicts.append(cid)
    return conflicts


#: statuses that are OUT of trusted recall — a new write must NOT be flagged as
#: contradicting one of these (it was already retired), and they must not cost a
#: judge call. Mirrors SemanticMemory.live_topic_siblings' SQL exclusion set.
_NON_LIVE_STATUSES = frozenset({"orphaned", "quarantined", "user_belief"})


def _live_topic_siblings(sm: Any, topic: str | None, *, limit: int = 200) -> list:
    """Same-topic, LIVE facts to compare a new write against for semantic
    contradiction. Prefer the store's indexed ``live_topic_siblings`` (bounded SQL);
    fall back to scanning ``all()`` for duck-typed / older stores, applying the SAME
    exclusions in memory. Excluding already-superseded / quarantined facts is
    correctness (a contradiction against a retired value is a false positive); using
    the indexed query is what keeps the opt-in moat off the O(store) ``all()`` path."""
    t = topic or ""
    getter = getattr(sm, "live_topic_siblings", None)
    if callable(getter):
        try:
            return list(getter(t, limit=limit))
        except Exception:  # noqa: BLE001 — any store error → fall back to the scan
            pass
    out: list = []
    for f in sm.all():
        if getattr(f, "topic", None) != t:
            continue
        if getattr(f, "superseded_by", None):
            continue
        if getattr(f, "status", None) in _NON_LIVE_STATUSES:
            continue
        out.append(f)
        if len(out) >= limit:
            break
    return out


#: explicit non-verification disclaimers (multi-language) — the honest marker
#: that turns attributed reported speech into a safe-to-record fact.
_NONVERIFY_RE = re.compile(
    r"\b(?:not\s+(?:yet\s+)?verified|unverified|unconfirmed|not\s+confirmed"
    r"|have\s*n'?t\s+verified|cannot\s+confirm|can'?t\s+confirm"
    r"|allegedly|supposedly|reportedly|purportedly|unproven"
    r"|non\s+verificato|non\s+confermato|da\s+verificare|non\s+abbiamo\s+verificato"
    r"|nicht\s+verifiziert|unbestätigt|no\s+verificado|non\s+vérifié"
    r"|не\s+проверено|未验证|未確認)\b",
    re.IGNORECASE,
)


def _is_honest_reported(proposition: str) -> bool:
    """True iff the proposition is BOTH third-party-attributed reported speech
    AND carries an explicit non-verification disclaimer. Both are required:
    attribution alone is not enough (bare attributed hype stays caught)."""
    try:
        from .semantic_selfclaim import _looks_reported
    except Exception:  # noqa: BLE001 — never let the guard break the gate
        return False
    return bool(_looks_reported(proposition)) and bool(
        _NONVERIFY_RE.search(proposition))


def _l1_warnings(
    proposition: str, verified_by: Iterable[str] | None,
) -> list[dict[str, Any]]:
    """Run the L1 family detectors; return one warning dict per positive.

    Cycle 184 (2026-05-23) extends the original 3-detector chain with
    L1.8 ``detect_unsupported_fix_claim`` (cycle 183 FIX/RESOLVED/
    PATCHED/REPAIRED keyword family). The fix-claim detector accepts
    richer evidence shapes (``pytest:<test>_PASS`` and
    ``bash:<cmd>...exit0...`` count as evidence, not only ``commit:``
    refs) because a local "FIXED" claim can be backed by a green test
    even without a git commit yet.

    ``verified_by`` is materialised once into a list so multiple
    detectors that iterate it independently never share a consumed
    generator.
    """
    # Materialise verified_by so each detector iterates an independent
    # list view (cheap; the iterable is typically <10 entries).
    vb_list: list[str] | None = (
        None if verified_by is None else [str(x) for x in verified_by]
    )

    # Bound the lexical scan (gateway load probe 2026-07-17): the L1 keyword
    # detectors look for short claim phrases near the start; a 64KB paste is a
    # document, and an unbounded scan is a DoS surface (one bad-backtracking
    # regex hangs every write). Cap once here so EVERY detector below is O(1)
    # in the input size. _LEXICAL_SCAN_CAP defined with the escalation helpers.
    proposition = (proposition or "")[:_LEXICAL_SCAN_CAP]

    out: list[dict[str, Any]] = []
    for layer, detect in (
        ("L1", detect_unsupported_shipped_claim),
        ("L1.5", detect_unsupported_diagnosis_claim),
        ("L1.7", detect_unsupported_task_state_claim),
    ):
        reason = detect(proposition=proposition, verified_by=vb_list)
        if reason:
            out.append({"layer": layer, "reason": reason})
    # Cycle 184: L1.8 has a richer Warning struct (keyword + advice).
    fix = detect_unsupported_fix_claim(
        proposition=proposition, verified_by=vb_list,
    )
    if fix is not None:
        out.append({
            "layer": "L1.8",
            "reason": (
                f"FIX-family claim '{fix.keyword}' lacks an evidence ref "
                f"(commit:/pr:/file:/git:/pytest:_PASS/bash:exit0)"
            ),
            "advice": fix.advice,
            "keyword": fix.keyword,
        })

    # Cycle 2026-05-27: L1.9 performance-claim detector.
    perf = detect_unsupported_performance_claim(
        proposition=proposition, verified_by=vb_list,
    )
    if perf is not None:
        out.append({
            "layer": "L1.9",
            "reason": (
                f"Performance claim '{perf.matched_text}' "
                f"(kind={perf.pattern_kind}) lacks bench evidence "
                f"(bench:/measure:/perf:/timing:/latency:)"
            ),
            "advice": perf.advice,
            "pattern_kind": perf.pattern_kind,
            "matched_text": perf.matched_text,
        })

    # Cycle 2026-05-27 (round 2): L1.10 works/confirmed detector.
    works = detect_unsupported_works_claim(
        proposition=proposition, verified_by=vb_list,
    )
    if works is not None:
        out.append({
            "layer": "L1.10",
            "reason": (
                f"Works/confirmed claim '{works.matched_text}' lacks "
                f"runtime evidence (pytest:_PASS/bash:exit0/smoke:)"
            ),
            "advice": works.advice,
            "matched_text": works.matched_text,
        })

    # Cycle 2026-05-27 (round 3): L1.11 production-ready/stable detector.
    prod = detect_unsupported_prod_ready_claim(
        proposition=proposition, verified_by=vb_list,
    )
    if prod is not None:
        out.append({
            "layer": "L1.11",
            "reason": (
                f"Production-ready/stable claim '{prod.matched_text}' "
                f"lacks formal validation evidence "
                f"(coverage:/soak:/regression:_PASS/ci:green)"
            ),
            "advice": prod.advice,
            "matched_text": prod.matched_text,
        })

    # Cycle 2026-05-27 (round 4): L1.12 security/hardened detector.
    sec = detect_unsupported_security_claim(
        proposition=proposition, verified_by=vb_list,
    )
    if sec is not None:
        out.append({
            "layer": "L1.12",
            "reason": (
                f"Security claim '{sec.matched_text}' lacks audit "
                f"evidence (audit:/pentest:/threat_model:/"
                f"bandit:/semgrep:/vuln_scan:)"
            ),
            "advice": sec.advice,
            "matched_text": sec.matched_text,
        })

    # Cycle 2026-05-27 (round 5): L1.13 completion claim detector.
    comp = detect_unsupported_completion_claim(
        proposition=proposition, verified_by=vb_list,
    )
    if comp is not None:
        out.append({
            "layer": "L1.13",
            "reason": (
                f"Completion claim '{comp.matched_text}' lacks closing "
                f"criteria (task:_closed/acceptance_test:_PASS/"
                f"dod:_met/review:_approved/pr:_merged/pytest:_PASS)"
            ),
            "advice": comp.advice,
            "matched_text": comp.matched_text,
        })

    # Cycle 2026-05-27 (round 6): L1.14 documentation detector.
    doc = detect_unsupported_doc_claim(
        proposition=proposition, verified_by=vb_list,
    )
    if doc is not None:
        out.append({
            "layer": "L1.14",
            "reason": (
                f"Documentation claim '{doc.matched_text}' lacks docs "
                f"evidence (docs:/md:/file:_md/readme:/changelog:)"
            ),
            "advice": doc.advice,
            "matched_text": doc.matched_text,
        })

    # Cycle 2026-05-27 (round 7): L1.15 tested/verified detector.
    tested = detect_unsupported_tested_claim(
        proposition=proposition, verified_by=vb_list,
    )
    if tested is not None:
        out.append({
            "layer": "L1.15",
            "reason": (
                f"Tested/verified claim '{tested.matched_text}' lacks "
                f"test evidence (pytest:_PASS/test_coverage:/ci:green)"
            ),
            "advice": tested.advice,
            "matched_text": tested.matched_text,
        })

    # Cycle 2026-05-27 (round 8): L1.16 approval detector.
    appr = detect_unsupported_approval_claim(
        proposition=proposition, verified_by=vb_list,
    )
    if appr is not None:
        out.append({
            "layer": "L1.16",
            "reason": (
                f"Approval claim '{appr.matched_text}' lacks formal "
                f"approval evidence (approval:_signed/review:_approved/"
                f"pr:_approved/ticket:_approved)"
            ),
            "advice": appr.advice,
            "matched_text": appr.matched_text,
        })

    # Cycle 2026-05-27 (round 9): L1.17 monitored/observed detector.
    mon = detect_unsupported_monitored_claim(
        proposition=proposition, verified_by=vb_list,
    )
    if mon is not None:
        out.append({
            "layer": "L1.17",
            "reason": (
                f"Monitoring claim '{mon.matched_text}' lacks "
                f"observability evidence (dashboard:/alert:/"
                f"prometheus:/metric:/sentry:)"
            ),
            "advice": mon.advice,
            "matched_text": mon.matched_text,
        })

    # Cycle 2026-05-27 (round 10): L1.18 automated/scheduled detector.
    auto = detect_unsupported_automated_claim(
        proposition=proposition, verified_by=vb_list,
    )
    if auto is not None:
        out.append({
            "layer": "L1.18",
            "reason": (
                f"Automation claim '{auto.matched_text}' lacks "
                f"scheduler evidence (cron:/schedule:/scheduler:/"
                f"workflow:/systemd:/airflow:/celery:)"
            ),
            "advice": auto.advice,
            "matched_text": auto.matched_text,
        })

    # Cycle 2026-05-27 (round 11 final): L1.19 quantitative metric detector.
    # Closes Gemini-identified gap: absolute numeric claims (50ms, 95%
    # coverage, 1.2M records) sin measurement source.
    quant = detect_unsupported_quant_claim(
        proposition=proposition, verified_by=vb_list,
    )
    if quant is not None:
        out.append({
            "layer": "L1.19",
            "reason": (
                f"Quantitative metric claim '{quant.matched_text}' "
                f"(kind={quant.pattern_kind}) lacks measurement "
                f"evidence (bench:/measure:/coverage:/report:/query:)"
            ),
            "advice": quant.advice,
            "pattern_kind": quant.pattern_kind,
            "matched_text": quant.matched_text,
        })

    # 2026-07-09: L1.20 multilingual SEMANTIC self-claim detector — closes the
    # measured 8-of-10-languages hole (the keyword family above is EN/IT-only;
    # the same hype claim in es/fr/de/pt/ru/zh/ja/ar passed clean). Embedding
    # dual-check calibrated at recall 1.0 / 0 FP across 10 languages; fail-open
    # and evidence-disarmed like every other L1 detector.
    # 2026-07-10 (red-team): L1.21 quality-superlative / sycophancy detector —
    # the deterministic net behind the fuzzy L1.20 embedding, which a flattery
    # prefix ("as you correctly said…") can dilute below threshold.
    from .l1_quality_detector import detect_unsupported_quality_claim
    qual = detect_unsupported_quality_claim(
        proposition=proposition, verified_by=vb_list)
    if qual is not None:
        out.append({
            "layer": "L1.21",
            "reason": (
                f"Quality superlative '{qual.matched_text}' asserts "
                f"perfection without evidence"
            ),
            "advice": qual.advice,
            "matched_text": qual.matched_text,
        })

    from .semantic_selfclaim import detect_semantic_selfclaim
    sem = detect_semantic_selfclaim(proposition, vb_list)
    if sem is not None:
        out.append(sem)

    # 2026-07-10 (red-team FP fix): honest reported speech — a claim
    # ATTRIBUTED to a third party AND carrying an explicit non-verification
    # disclaimer ("the vendor claims it works, we have NOT verified it") is a
    # record of someone else's claim, not our confabulation → drop the
    # state/success-family warnings. HARD stance preserved: bare attributed
    # hype (no disclaimer) stays caught. Quantitative/perf layers are kept —
    # a fabricated NUMBER is flagged regardless of attribution.
    if out and _is_honest_reported(proposition):
        _STATE_FAMILY = {"L1", "L1.8", "L1.10", "L1.11", "L1.12", "L1.13",
                         "L1.14", "L1.15", "L1.16", "L1.17", "L1.18",
                         "L1.20", "L1.21"}
        out = [w for w in out if w.get("layer") not in _STATE_FAMILY]
    return out


def _l3_check(
    agent: _AgentLike | None,
    proposition: str,
    topic_hint: str | None,
) -> dict[str, Any] | None:
    """Run cycle #70 ``validate_claim`` against ``agent.semantic``.

    Returns ``None`` when the agent (or semantic store) is unavailable
    so callers can degrade gracefully — better miss a check than crash
    a write path.
    """
    if agent is None or getattr(agent, "semantic", None) is None:
        return None
    try:
        from .validate_claim import validate_claim
    except Exception:  # pragma: no cover — defensive
        return None
    try:
        return validate_claim(
            agent, proposition,
            topic_hint=topic_hint or None,
            threshold=0.6,
        )
    except Exception:  # noqa: BLE001 — never crash the write
        return None


#: Software/dev CONTEXT tokens (distinct from the L1 trigger words themselves). The L1
#: dev-claim detectors (shipped/done/confirmed/scheduled/automatically/verified) are meant to
#: catch the AGENT confabulating completion of ITS OWN WORK; on ordinary personal facts
#: ("dentist appointment scheduled", "rent recurring", "I confirmed the reservation") they are
#: FALSE POSITIVES that quarantine legitimate, high-value memories (WF3 2026-06-19: ~40%
#: of personal-assistant facts hard-excluded from recall). So an L1 hit only ESCALATES to
#: downgrade/quarantine when the proposition also carries a software/dev ARTIFACT signal.
_DEV_CONTEXT = re.compile(
    r"\b(?:commit|pull[- ]?request|PR|issue|branch|repo(?:sitory)?|git|"
    r"deploy(?:ed|ment)?|build|CI|CD|pipeline|release|rollback|patch|refactor|"
    r"test(?:s|ed|ing)?|pytest|bug|crash|hang|traceback|regression|"
    r"feature|module|function|class|method|endpoint|API|server|daemon|service|"
    r"script|codebase|schema|migration|database|query|compile|"
    r"production|staging|prod|merge[ds]?|wired|implement(?:ed|ation)?|"
    # Italian dev vocabulary (the agent logs dev-claims in IT too): produzione,
    # modulo, testato/a, verificato/a, validato/a, rilasciato, distribuito, ciclo,
    # sistema, funzione, implementato, corretto, risolto, compilato, schierato.
    r"produzione|modulo|testat[oaie]|verificat[oaie]|validat[oaie]|rilasciat[oaie]|"
    r"distribuit[oaie]|ciclo|sistema|funzione|implementat[oaie]|corrett[oaie]|"
    r"risolt[oaie]|compilat[oaie]|schierat[oaie]|"
    r"file|line\s*\d+|cycle\s*#?\d+|loop\s*\d+)\b"
    # `path.ext` and `name.attr:line` — BOUNDED runs. The old `\w+\.\w+:\d+`
    # made `\w+` backtrack catastrophically O(n^2) on a long no-space blob
    # (gateway load probe 2026-07-17: 22.65s on a 64KB fact). {1,64} caps the
    # backtrack window without changing any real match (identifiers are short).
    r"|\.(?:py|js|ts|rs|go|java|sql|md|json|yaml|toml)\b|\b\w{1,64}\.\w{1,64}:\d{1,9}\b",
    re.IGNORECASE,
)

#: Lexical-scan cap (gateway load probe 2026-07-17). The L1 keyword/regex family
#: looks for SHORT dev/personal/hype phrases; a real fact carrying such a signal
#: has it near the start. A 64KB paste is a document (README routes those to
#: DocumentIndex), and scanning it megabyte-deep is pointless AND a DoS surface
#: (one bad-backtracking pattern hangs every write). So every lexical helper
#: scans at most this prefix — O(1) in the input size regardless of the pattern.
_LEXICAL_SCAN_CAP = 8192


def _has_dev_context(proposition: str) -> bool:
    """True if the proposition carries a software/dev artifact signal."""
    return bool(_DEV_CONTEXT.search((proposition or "")[:_LEXICAL_SCAN_CAP]))


#: PERSONAL/everyday-life signal (first-person OR a personal-life domain noun). The L1
#: dev-claim detectors are SUPPRESSED only when this is present AND there is NO dev signal —
#: so existing dev-claim behavior is unchanged (no personal signal => still escalates), while
#: personal-assistant facts ("dentist appointment scheduled", "rent is recurring monthly",
#: "I confirmed the reservation") stay recallable instead of being quarantined (WF3 2026-06-19).
#: NB (critic 2026-06-20, split 1-1): do NOT include bare first-person pronouns (I/we/my) —
#: first-person is the AGENT's own self-narration register, so "I finished the task" / "we
#: completed everything, it's all done" would wrongly suppress the very completion-confab L1.13
#: exists to catch. A personal fact is identified by a personal-DOMAIN noun, not by a pronoun.
_PERSONAL_CONTEXT = re.compile(
    r"\b(?:appointment|dentist|doctor|physician|clinic|hospital|allerg\w*|"
    r"medication|prescription|pill|dose|vaccine|"
    r"rent|mortgage|\bbill\b|bills|subscription|salary|paycheck|"
    r"birthday|anniversary|wedding|reservation|booking|flight|hotel|trip|"
    r"vacation|holiday|grocery|groceries|dinner|lunch|breakfast|restaurant|recipe|"
    r"gym|workout|yoga|meeting|"
    r"family|mother|father|\bmom\b|\bdad\b|wife|husband|spouse|partner|"
    r"son|daughter|\bkid\b|kids|child|children|friend|colleague|boss|"
    r"\bpet\b|\bdog\b|\bcat\b|\bcar\b|apartment|house|home|school|homework|"
    r"\bbook\b|movie|concert|hobby|"
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|tonight|weekend)\b",
    re.IGNORECASE,
)


def _has_personal_context(proposition: str) -> bool:
    """True if the proposition reads as a personal/everyday fact (first-person or a
    personal-life domain). Used to SUPPRESS L1 dev-claim FPs on such facts."""
    return bool(_PERSONAL_CONTEXT.search((proposition or "")[:_LEXICAL_SCAN_CAP]))


#: HISTORICAL WORLD-FACT completion (moat e2e opus bench, 2026-07-17). L1.13 fires on
#: the word "completed"/"finished" — but "The bridge was completed in 1998" is a
#: third-person historical fact about a structure/artifact, NOT the AGENT confabulating
#: completion of its own work (the register L1.13 exists for: "task done", "I finished
#: the task"). A PASSIVE completion/creation verb ANCHORED to a calendar year is the
#: unambiguous world-fact construction. Suppressed only when there is ALSO no dev
#: artifact — so "The migration was completed in 2023" (dev context) still escalates.
_HISTORICAL_COMPLETION = re.compile(
    r"\b(?:was|were|got|been|is|are)\s+(?:completed|finished|built|constructed|"
    r"erected|opened|established|founded|inaugurated|closed|demolished|destroyed|"
    r"renovated|restored)\b"
    # Italian: fu/venne/è stato ... completato/costruito/fondato/aperto/chiuso/…
    r"|\b(?:fu|venne|vennero|furono|è\s+stat[oa]|era\s+stat[oa])\s+"
    r"(?:completat[oa]|finit[oa]|costruit[oa]|erett[oa]|apert[oa]|fondat[oa]|"
    r"chius[oa]|inaugurat[oa]|demolit[oa]|restaurat[oa])\b",
    re.IGNORECASE,
)
_CALENDAR_YEAR = re.compile(r"\b(?:1[0-9]|20)\d{2}\b")


def _is_historical_completion(proposition: str) -> bool:
    """True if the proposition is a passive completion/creation statement anchored to a
    calendar year (a historical world-fact), used to SUPPRESS the L1.13 completion FP."""
    p = (proposition or "")[:_LEXICAL_SCAN_CAP]
    return bool(_HISTORICAL_COMPLETION.search(p)) and bool(_CALENDAR_YEAR.search(p))


def run_validation_gate(
    *,
    proposition: str,
    verified_by: Iterable[str] | None,
    topic: str | None,
    agent: _AgentLike | None,
    validate: str | None = None,
    gate_mode: str | None = None,
    force_persist: bool = False,
    writer_role: str | None = None,
    meta_narrative: bool = False,
    hook_token: str | None = None,
    repo_root: Any = None,
    source: str | None = None,
    grounding_llm: Any = None,
    ground_write: bool | None = None,
    asserted_at: float | None = None,
    status: str | None = None,
) -> GateResult:
    """Evaluate the anti-confab gate; return a ``GateResult``.

    Pure function over the inputs except for one BUS-emit-free
    ``validate_claim`` call (which is itself a read-only lookup on the
    agent's semantic store).

    Trusted-hook bypass (cycle 2026-05-27 round 12 — F-fix):
    When ``writer_role`` is in ``TRUSTED_HOOKS`` AND
    ``meta_narrative=True``, the gate short-circuits with
    ``action="persist"`` and skips ALL L1.x detectors. This handles
    retrospective continuity facts (pre-compact master facts) whose
    narrative naturally contains keywords like SHIPPED/COMPLETO/
    AUTHORIZED/MONITORED that would otherwise quarantine them.

    Both conditions are required (defense in depth): an attacker who
    only controls the proposition text or topic cannot fake the
    ``writer_role`` field (it is set by trusted writers like the
    pre-compact hook).
    """
    level = _resolve_level(validate)
    mode = _resolve_mode(gate_mode)

    # Fast path: off → never gate.
    if level == "off":
        return GateResult(action="persist")

    # Cycle 2026-05-27 round 12 — F-fix trusted-hook bypass.
    # Provenance-based, NOT topic-based (topic is user-controllable).
    # Security fix 2026-06-02: token-gated. writer_role is client-
    # spoofable via MCP arguments, so the bypass now requires a
    # server-side secret (verify_trusted_writer, fail-closed when the
    # ENGRAM_HOOK_TOKEN env is unset or the token is absent/wrong).
    if meta_narrative and verify_trusted_writer(writer_role, hook_token):
        return GateResult(action="persist")

    warnings = _l1_warnings(proposition, verified_by)
    contradicting_ids: list[str] = []
    supersede_ids: list[str] = []
    advice = ""

    # EVIDENCE-EXISTENCE (buco #2, 2026-06-02 — opt-in via repo_root).
    # I detector L1 verificano il FORMATO di verified_by (un `commit:`-shaped
    # ref sopprime il warning), NON l'ESISTENZA. provenance_validator verifica
    # l'esistenza ma (a) solo per status='verified' in store, (b) parsa la
    # forma SPAZIO `commit <sha>`, NON la forma colon `commit:<sha>` del gate
    # (falsificato empiricamente). Quindi un `commit:deadbeef` fabbricato ma
    # ben formato sopprime il detector e fa persistere -> residuo REALE.
    #
    # Fix: quando il chiamante fornisce repo_root, se la prova ha "ripulito" un
    # claim (L1 NON fira CON la prova ma firerebbe SENZA) e NESSUN ref esiste
    # davvero nel repo -> trattalo come claim non supportato (downgrade). Senza
    # repo_root il comportamento resta format-only (default invariato, hermetic-
    # safe: i test honoring-evidence non passano repo_root).
    if repo_root is not None and not warnings and verified_by is not None:
        would_fire_without_evidence = _l1_warnings(proposition, None)
        if would_fire_without_evidence:
            from .provenance_validator import any_evidence_ref_exists
            if not any_evidence_ref_exists(verified_by, repo_root=repo_root):
                for w in would_fire_without_evidence:
                    w["evidence_existence"] = True
                warnings = would_fire_without_evidence
                advice = (
                    "verified_by ben formato ma NESSUN ref esiste nel repo "
                    "(commit/file fabbricato): la prova non e' verificabile -> "
                    "downgrade. Fornisci un commit:/file: reale."
                )

    if level == "full":
        r = _l3_check(agent, proposition, topic)
        if r is not None and r.get("verdict") == "contradicted":
            ev = [str(x) for x in (r.get("evidence_facts") or [])]
            advice = str(r.get("advice", ""))
            # Same-source EVOLUTION routing (ENGRAM_SUPERSEDE_SAME_SOURCE): a lexically-
            # caught contradiction (numeric/version/date) against the SAME source's earlier
            # value is an evolution — retire the old, admit the new — not a quarantine.
            _conflicts = ev
            if _supersede_same_source_on() and ev:
                _conflicts = _route_evolutions(agent, verified_by, asserted_at, ev,
                                               supersede_ids, status)
            if _conflicts:
                warnings.append({
                    "layer": "L3",
                    "reason": "validate_claim verdict=contradicted",
                    "advice": advice,
                })
                contradicting_ids = _conflicts
            elif ev:  # every contradiction was a same-source evolution → admit + supersede
                warnings.append({
                    "layer": "L3-supersession",
                    "reason": "a newer same-source value supersedes a stored fact",
                    "advice": "this write updates an earlier value from the same source; "
                              "the older value is superseded.",
                })

    # L3-SEMANTIC (NLI moat): the lexical L3 (validate_claim, "puramente lessicale")
    # misses conflicts where the WORDS differ but the MEANING contradicts a stored
    # fact. detect_semantic_conflicts adds the entailment-model trigger (timestamp-
    # aware: supersession over time is NOT a contradiction). Opt-in
    # (ENGRAM_SEMANTIC_CONFLICT) so the default path is unchanged (no judge call).
    # When ON, the judge is the injected ``agent.llm`` if present, else the local NLI
    # cross-encoder (llm-free, Phase 1.1) — so the moat works subscription-free /
    # offline. observe mode surfaces without quarantining; enforce quarantines. Never
    # crashes the write (fail-soft to no warning).
    _sc_mode = _semantic_conflict_mode()
    if level == "full" and _sc_mode != "off":
        _sm = getattr(agent, "semantic", None) if agent is not None else None
        if _sm is not None:
            try:
                import time as _t
                import types as _ty

                from .semantic_conflict import (
                    LLMRelationJudge,
                    detect_semantic_conflicts,
                )
                _judge_llm = getattr(agent, "llm", None) if agent is not None else None
                if _judge_llm is not None:
                    _judge = LLMRelationJudge(_judge_llm)
                else:
                    # llm-free fallback: the local NLI cross-encoder (no claude -p).
                    # Fail-soft — classify() returns NEUTRAL if the model can't load,
                    # so a missing model degrades to "no warning", never a crash.
                    from .local_relation import get_local_relation_judge
                    _judge = get_local_relation_judge()
                _new = _ty.SimpleNamespace(
                    id="__candidate__", proposition=proposition,
                    topic=topic, created_at=_t.time(), verified_by=verified_by,
                    asserted_at=asserted_at,
                )
                _sibs = _live_topic_siblings(_sm, topic, limit=200)
                if _l3_subject_filter():
                    # P2 subject pre-filter (env, default OFF): only siblings
                    # ABOUT the same subject reach the NLI. Fail-soft to keep:
                    # a matcher error must never hide a real conflict.
                    def _keep(s) -> bool:
                        try:
                            from .subject_extract import same_subject
                            return same_subject(
                                proposition, getattr(s, "proposition", ""))
                        except Exception:  # noqa: BLE001
                            return True
                    _sibs = [s for s in _sibs if _keep(s)]
                _sib_by_id = {getattr(f, "id", None): f for f in _sibs}
                _observe = _sc_mode == "observe"
                from .semantic import _STATUS_RANK
                from .supersession_policy import classify_write_relation
                _supersede_on = _supersede_same_source_on()
                _new_rank = _STATUS_RANK.get(status or "model_claim", 2)
                for _w in detect_semantic_conflicts(_new, _sibs, _judge):
                    if getattr(_w, "kind", "") != "semantic_conflict":
                        continue
                    _oid = getattr(_w, "other_fact_id", "")
                    # provenance+time split: a same-source NEWER value is an EVOLUTION
                    # (the source superseding itself), not a cross-source contradiction —
                    # the deterministic fix for the local NLI's measured temporal
                    # over-flag (2026-07-19). Cross-source stays 'conflict' (griefing guard).
                    _old = _sib_by_id.get(_oid)
                    # DIARY GUARD (precision, 2026-07-19): two statements
                    # indexing DIFFERENT events of the same kind ("On day 4
                    # ..." vs "On day 5 ...") are distinct entries, not one
                    # value evolving — the NLI over-flags them. Skip entirely:
                    # no supersession, no quarantine, no observe noise.
                    # (Found live: 12 diary adds collapsed under auto-NLI and
                    # count() dropped below ground truth.)
                    from .quantity_match import distinct_event_indices
                    if (_old is not None and distinct_event_indices(
                            proposition, getattr(_old, "proposition", ""))):
                        continue
                    _rel = ("conflict" if _old is None
                            else classify_write_relation(_new, _old))
                    if _observe:
                        # observe: surface but do NOT act, so the FP rate is measurable.
                        if _rel == "evolution":
                            warnings.append({
                                "layer": "L3-supersession-observe",
                                "reason": "a newer same-source value supersedes a stored "
                                          "fact (observe mode: logged, NOT applied)",
                                "advice": "this write updates an earlier value from the "
                                          "same source; in enforce mode the older value "
                                          "would be superseded, not flagged a conflict.",
                                "other_fact_id": _oid,
                            })
                        else:
                            warnings.append({
                                "layer": "L3-semantic-observe",
                                "reason": "NLI judge: contradiction with a stored fact "
                                          "(observe mode: logged, NOT quarantined)",
                                "advice": "a stored memory semantically contradicts this "
                                          "claim; set ENGRAM_SEMANTIC_CONFLICT=1 to enforce.",
                                "other_fact_id": _oid,
                            })
                    elif (_rel == "evolution" and _supersede_on and _old is not None
                          and _STATUS_RANK.get(getattr(_old, "status", "model_claim"), 2)
                          <= _new_rank):
                        # enforce + ENGRAM_SUPERSEDE_SAME_SOURCE: the same source updated
                        # its own value with an at-least-as-trusted claim → ADMIT the new
                        # (does not escalate) and retire the OLD via supersede_ids. The
                        # rank floor keeps a weak new from retiring a stronger old (an
                        # unverified claim never supersedes a verified fact — anti-confab).
                        # The handler applies it ONLY when the new write is ultimately
                        # admitted (action=='persist').
                        warnings.append({
                            "layer": "L3-supersession",
                            "reason": "a newer same-source value supersedes a stored fact",
                            "advice": "this write updates an earlier value from the same "
                                      "source; the older value is superseded.",
                            "other_fact_id": _oid,
                        })
                        if _oid:
                            supersede_ids.append(_oid)
                    else:
                        # cross-source conflict, OR evolution with supersede OFF: the
                        # conservative default — quarantine the new claim.
                        warnings.append({
                            "layer": "L3-semantic",
                            "reason": "NLI judge: contradiction with a stored fact",
                            "advice": "a stored memory semantically contradicts this "
                                      "claim (not a lexical/numeric clash).",
                            "other_fact_id": _oid,
                        })
                        if _oid:
                            contradicting_ids.append(_oid)
            except Exception:  # noqa: BLE001 — optional moat must never crash a write
                pass

    # SEMANTIC grounding (R10 moat, AUROC 0.971 on SNLI faithful-vs-confabulated): when a
    # SOURCE is provided, verify it ENTAILS the proposition — catches confabulated
    # INFERENCES the lexical L1/L3 detectors miss (a fact the source does not state).
    # ON by default (2026-07-17 flip): the balanced preset passes ground_write=True, so L4
    # runs whenever a SOURCE and a judge are present (injected grounding LLM or the local
    # CE). ground_write=False — or no source / no judge — skips it (fail-open, no LLM call).
    grounding_val: float | None = None
    # judge-of-record for this write (set below IFF the L4 numeric judge scored)
    _judge_of_record: str | None = None
    _threshold_of_record: float | None = None
    # ``ground_write`` per-call override (S1 fix, 2026-07-04 adversarial review):
    # the entailment moat was unreachable from Memory.add() — triple opt-in
    # (source + injected llm + ENGRAM_GROUNDING_WRITE) and no per-call switch.
    # ground_write=True runs L4 for THIS write regardless of the env default;
    # None falls back to the env. The local CE backend needs no injected llm,
    # so a local judge OR an injected llm satisfies the "have a judge" arm.
    from .grounding_gate import _resolve_backend
    from .local_grounding import local_ce_available
    _ground_on = _grounding_write_on() if ground_write is None else bool(ground_write)
    # The moat has a judge when: an llm was injected, the backend is explicitly
    # 'local', OR (2026-07-18) no llm but the multilingual local CE is on disk —
    # so a brand-new user with no llm gets the moat ON by default instead of a
    # silent fail-open. The CE is multilingual (measured EN/IT/FR/ES), so this is
    # NOT English-only. If the CE isn't present either, fall through to the honest
    # L4-skipped advisory below.
    _have_judge = (grounding_llm is not None
                   or _resolve_backend() == "local"
                   or local_ce_available())
    def _emit_l4_skipped() -> None:
        # A sourced write with NO reachable grounding judge — neither an injected
        # llm NOR the local CE (never downloaded, or unloadable at score-time) —
        # is NOT entailment-verified. Say so out loud, NEVER a silent skip. The
        # write is still ADMITTED (source-provenance rule below) but its provenance
        # carries this advisory: recallable, honestly labelled "grounding not
        # verified", never passed off as verified. (2026-07-18: the CE is the
        # default judge when present and is multilingual — measured EN/IT/FR/ES.)
        warnings.append({
            "layer": "L4-skipped",
            "reason": "source provided but no grounding judge is available - "
                      "entailment NOT verified",
            "advice": "the local grounding model is not installed and no llm was "
                      "passed. Run `verimem warmup` to fetch the free multilingual "
                      "CE judge, or pass Memory(llm=...) — either turns the "
                      "source-entailment moat on.",
        })

    if source and _ground_on and _have_judge:
        # score and cut resolved for the SAME judge (local CE vs claude scales differ —
        # the 2026-07-02 critic caught the calibrated cut not reaching this L4 site).
        from .grounding_gate import (
            NoGroundingJudge,
            _ce_band_enforced,
            _ce_band_tau_hi,
            fact_grounding_score_ex,
            resolve_write_threshold_for,
        )
        try:
            gscore, _judge_used = fact_grounding_score_ex(grounding_llm, source, proposition)
        except (FileNotFoundError, OSError, ImportError, NoGroundingJudge):
            # ONLY "the judge isn't really reachable" is tolerated here (missing /
            # unloadable model). A DEDICATED NoGroundingJudge — not the whole
            # RuntimeError family — so a real ML fault (torch shape mismatch, CUDA
            # OOM: also RuntimeError) PROPAGATES instead of being laundered into a
            # silent admission (opus review 2026-07-18, findings D + B).
            gscore, _judge_used = None, None
        if gscore is None:
            # The CE was advertised present but could not score → treat as "no
            # judge" RIGHT HERE. The `elif` below is unreachable once this `if`
            # was taken, so emitting the advisory there was dead code (that was
            # the silent fail-open opus caught).
            _emit_l4_skipped()
        else:
            grounding_val = float(gscore)  # persist the score even when it PASSES
            _judge_of_record = _judge_used
            _threshold_of_record = resolve_write_threshold_for(_judge_used)
            if gscore < _threshold_of_record:
                if _graded_admission():
                    # GRADED ADMISSION (design bf5d322 step 1, env-gated,
                    # DEFAULT OFF): "not proven enough" is not "malicious".
                    # Measured at the shipped cut 40 (HaluMem external A/B):
                    # hard-reject here loses 33% of CLEAN facts. With the env
                    # ON the write persists as a low-confidence model_claim and
                    # the receipt says so; quarantine stays reserved for
                    # injection / active contradiction (they escalate below
                    # regardless). Layer name deliberately NOT "L4-grounding"
                    # so the escalation equality check does not fire.
                    warnings.append({
                        "layer": "L4-grounding-graded",
                        "reason": f"graded admission: grounding {gscore:.0f} below "
                                  f"threshold {_threshold_of_record:.0f} — admitted "
                                  "as low-confidence, NOT verified "
                                  "(ENGRAM_GRADED_ADMISSION)",
                        "advice": "the declared source does not entail this claim; "
                                  "it is stored as an unproven low-confidence "
                                  "memory. Unset ENGRAM_GRADED_ADMISSION to "
                                  "restore hard quarantine.",
                        "grounding_score": gscore,
                    })
                else:
                    warnings.append({
                        "layer": "L4-grounding",
                        "reason": f"source does not entail the proposition "
                                  f"(grounding {gscore:.0f} below threshold)",
                        "advice": "the source does not support this proposition — likely a "
                                  "confabulated inference, not a stated fact.",
                        "grounding_score": gscore,
                    })
                    advice = advice or "Source does not entail the claim (semantic grounding)."
            elif (_judge_used == "local" and _ce_band_enforced()
                  and gscore < _ce_band_tau_hi()):
                # BAND ESCALATION (0.7.0): before parking the write for review,
                # ask an AVAILABLE llm judge to adjudicate the CE's uncertain
                # sliver -- auto-discovered claude CLI (subscription, no key)
                # when no llm was injected. Fail-soft: None -> held for review
                # exactly as before; an unreadable verdict never admits.
                _esc = None
                if grounding_llm is None:
                    from . import band_escalation as _be
                    _esc = _be.escalate_band(source, proposition)
                if _esc is not None:
                    _esc_score, _esc_judge = _esc
                    grounding_val = float(_esc_score)
                    _judge_of_record = _esc_judge   # local-band / claude-band
                    _threshold_of_record = resolve_write_threshold_for("claude")
                    if _esc_score < _threshold_of_record:
                        if _graded_admission():
                            # coherence with the main sub-threshold branch: a
                            # grounding shortfall admits as low-confidence
                            # under graded admission, whoever scored it.
                            warnings.append({
                                "layer": "L4-grounding-graded",
                                "reason": f"graded admission: band judge "
                                          f"({_esc_judge}) scored {_esc_score:.0f} "
                                          "below threshold — admitted as "
                                          "low-confidence, NOT verified",
                                "advice": "the llm adjudicated the source does not "
                                          "entail this claim; stored as an unproven "
                                          "low-confidence memory.",
                                "grounding_score": _esc_score,
                            })
                        else:
                            warnings.append({
                                "layer": "L4-grounding",
                                "reason": f"band escalation ({_esc_judge}): llm judge scored "
                                          f"{_esc_score:.0f} below the claude-scale "
                                          f"threshold {_threshold_of_record:.0f}",
                                "advice": "the CE was unsure and the llm judge "
                                          "adjudicated NOT entailed -- likely a "
                                          "confabulated inference, not a stated fact.",
                                "grounding_score": _esc_score,
                            })
                            advice = advice or ("Source does not entail the claim "
                                                "(band llm adjudication).")
                    # else: llm adjudicated entailed -> admitted clean,
                    # judge-of-record 'claude-band' on the receipt.
                else:
                    if _graded_admission():
                        # no adjudicator available: under graded admission the
                        # borderline write persists as low-confidence instead
                        # of being held — otherwise a BETTER score (band) would
                        # fare WORSE than a sub-threshold one (admitted above).
                        warnings.append({
                            "layer": "L4-review-graded",
                            "reason": f"graded admission: borderline grounding "
                                      f"({gscore:.0f}) in the CE review band — "
                                      "admitted as low-confidence, NOT verified",
                            "advice": "the local CE is not confident the source "
                                      "entails this claim; stored as an unproven "
                                      "low-confidence memory.",
                            "grounding_score": gscore,
                        })
                    else:
                        warnings.append({
                            "layer": "L4-review",
                            "reason": f"borderline grounding ({gscore:.0f}) in the CE review "
                                      f"band [{_threshold_of_record:.0f}, "
                                      f"{_ce_band_tau_hi():.0f}) - held for review, not admitted",
                            "advice": "the local CE is not confident the source entails this "
                                      "claim; pass Memory(llm=...) to adjudicate the borderline "
                                      "zone, or review the held fact.",
                            "grounding_score": gscore,
                        })
    elif source and not _have_judge:
        _emit_l4_skipped()

    # Decision tree.
    has_l3_contradict = any(w.get("layer") == "L3" for w in warnings)
    has_l3_semantic = any(w.get("layer") == "L3-semantic" for w in warnings)
    has_grounding_fail = any(w.get("layer") == "L4-grounding" for w in warnings)
    has_l4_review = any(w.get("layer") == "L4-review" for w in warnings)
    # WF3 2026-06-19 PRECISION FIX: the L1 lexical dev-claim detectors fire on ordinary
    # personal words ('scheduled'/'done'/'confirmed'/'automatically'/'recurring') and were
    # quarantining ~40% of legitimate personal-assistant facts out of recall. They are meant
    # for the AGENT confabulating completion of ITS OWN WORK. So an L1 hit is SUPPRESSED (does
    # not quarantine; fact stays recallable, warnings advisory) ONLY on a clear personal/
    # everyday fact with NO dev signal — otherwise it escalates exactly as before (every
    # existing dev-claim case is unchanged: no personal signal => still escalates).
    # L3 (contradiction) and L4 (grounding) are semantic, not keyword FPs -> always escalate.
    has_l1 = any(str(w.get("layer", "")).startswith("L1") for w in warnings)
    _no_dev = not _has_dev_context(proposition)
    _personal_fp = _has_personal_context(proposition) and _no_dev
    # HISTORICAL world-fact FP (moat e2e bench 2026-07-17): "The bridge was completed in
    # 1998" is not an agent task-completion claim. Suppress the L1 escalation exactly as
    # for personal facts — advisory only, stays recallable — but keep dev-anchored claims
    # ("The migration was completed in 2023") escalating.
    _world_fp = _is_historical_completion(proposition) and _no_dev
    # SERVER-SIDE domain-advisory mode (measured 2026-07-21: 86.7% vertical FP):
    # a deployment that stores customer domain facts, not an agent's self-claims
    # about code, declares ENGRAM_L1_DOMAIN_ADVISORY — L1 keyword warnings are
    # still computed and surfaced but do not escalate to quarantine. Env-only,
    # never a per-write flag (that would be spoofable); relaxes ONLY L1 — the
    # L3/L4 semantic gates below are untouched.
    _domain_advisory = _l1_domain_advisory()
    # PER-FACT domain-precision carve-out (design (d), env ENGRAM_L1_DOMAIN_
    # PRECISION, DEFAULT OFF). Unlike _domain_advisory (which disarms L1 for the
    # WHOLE deployment), this suppresses the L1 escalation ONLY for a fact the
    # subject classifier reads as a third-party professional fact — an agent's
    # self-claim about its OWN software ('the migration is complete') is NOT
    # domain and still escalates. Content-based, not a spoofable field; the
    # subject HEAD (not the ambiguous verb) is the discriminator. Relaxes ONLY
    # L1 — L3/L4/injection escalate independently below.
    _domain_precision_fp = (has_l1 and _l1_domain_precision()
                            and _is_domain_professional_fact(proposition))
    # A declared source is caller-controlled and unverified (spoofable like the
    # writer_role the trusted-hook bypass had to token-gate). It therefore does
    # NOT downgrade an L1 hit: the gate stays fail-closed and quarantines a
    # shape-confab regardless of an attached source. The honest recovery path
    # for a real documental fact is a grounding JUDGE (L4), which verifies
    # source-entailment; the L4-skipped advisory above says so when none is set.
    l1_escalates = (has_l1 and not _personal_fp and not _world_fp
                    and not _domain_advisory and not _domain_precision_fp)
    if _domain_precision_fp and not _personal_fp and not _world_fp \
            and not _domain_advisory:
        # Record the per-fact stand-down (``*-observe``: surfaced, never a block
        # reason nor a ledger credit). Only when precision is the reason L1 did
        # not escalate — if a carve-out or the global switch already did, that
        # marker owns it.
        warnings.append({
            "layer": "L1-domain-precision-observe",
            "reason": "ENGRAM_L1_DOMAIN_PRECISION active: the subject reads as a "
                      "third-party professional fact, so the L1 keyword hit was "
                      "kept advisory rather than escalated",
            "advice": "unset ENGRAM_L1_DOMAIN_PRECISION to restore L1 keyword "
                      "escalation for this write",
        })
    if _domain_advisory and has_l1 and not _personal_fp and not _world_fp:
        # Critic probe 3 on e41991e (2026-07-21): the switch used to leave NO
        # trace — a disarmed-L1 deployment's receipts were indistinguishable
        # from an armed one's, and a mid-process env mutation disarmed the
        # layer fleet-wide with no audit record. Record the STAND-DOWN on the
        # receipt (``*-observe`` convention: surfaced, never owns a block
        # reason nor a ledger credit). Guarded on exactly the term the switch
        # flips in ``l1_escalates`` — an L1 hit no carve-out suppressed. Under
        # force_persist or an L3/L4 co-fire the final outcome is the same with
        # or without the switch (critic 2026-07-21, probe c): the marker still
        # stamps there, and its reason text stays literally true — L1 was kept
        # advisory by the switch; it just wasn't the deciding factor.
        warnings.append({
            "layer": "L1-domain-advisory-observe",
            "reason": "ENGRAM_L1_DOMAIN_ADVISORY active: an L1 keyword hit "
                      "that would have escalated was kept advisory by the "
                      "deployment-wide switch",
            "advice": "unset ENGRAM_L1_DOMAIN_ADVISORY to restore L1 keyword "
                      "escalation",
        })
    def _mk(action: GateAction, *, advice_: str = advice,
            warnings_: list | None = None) -> GateResult:
        # Every gate outcome carries the judge-of-record + threshold, so the
        # write receipt classifies the evidence honestly (no silent verdicts).
        # dedup (order-preserving): the lexical L3 and the NLI layer can both flag the
        # same pair, so an id could otherwise appear twice (a spurious duplicate in the
        # receipt + a harmless-but-noisy second supersede attempt).
        _sup = list(dict.fromkeys(supersede_ids))
        _sup_set = set(_sup)
        return GateResult(
            action=action,
            warnings=warnings if warnings_ is None else warnings_,
            contradicting_fact_ids=[c for c in dict.fromkeys(contradicting_ids)
                                    if c not in _sup_set],
            supersede_fact_ids=_sup,
            advice=advice_,
            grounding_score=grounding_val,
            judge=_judge_of_record,
            threshold=_threshold_of_record,
        )
    if force_persist:
        # Caller demands persist; we still surface warnings.
        return _mk("persist")
    if (has_l3_contradict or has_l3_semantic or has_grounding_fail) and mode == "reject":
        return _mk("reject", advice_=advice or "Claim contradicted by existing memory.")
    if (has_l3_contradict or has_l3_semantic or has_grounding_fail
            or has_l4_review or l1_escalates):
        return _mk("downgrade")
    if warnings:
        # L1 false positives on personal/non-dev text: keep the fact recallable, surface
        # the detectors as advisory only (no quarantine).
        return _mk("persist")
    return _mk("persist", warnings_=[])


__all__ = [
    "GateResult",
    "GateAction",
    "GateMode",
    "ValidateLevel",
    "TRUSTED_HOOKS",
    "run_validation_gate",
]
