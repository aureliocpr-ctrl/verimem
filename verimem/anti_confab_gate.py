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
    advice: str = ""
    #: L4 source⊢fact entailment score (0-100) WHEN computed (source + grounding_llm +
    #: ENGRAM_GROUNDING_WRITE), else None. Previously discarded after the pass/fail
    #: decision; now surfaced so the caller can PERSIST it on the fact and condition
    #: retrieval/answering on it (the moonshot 2026-06-20: a write-time trust signal no
    #: competitor has). None = not computed (default fast path).
    grounding_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "warnings": list(self.warnings),
            "contradicting_fact_ids": list(self.contradicting_fact_ids),
            "grounding_score": self.grounding_score,
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


def _semantic_conflict_on() -> bool:
    """Whether the opt-in NLI semantic-contradiction check (L3-semantic) is enabled.
    Default OFF: it issues an LLM judgement per same-topic sibling above the cosine
    pre-filter, so it changes the gate's cost profile (the lexical default is ~13ms,
    no LLM). Activates the previously-dormant ``semantic_conflict`` moat."""
    import os
    return os.environ.get("ENGRAM_SEMANTIC_CONFLICT", "").strip().lower() in (
        "1", "on", "true", "yes")


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
            warnings.append({
                "layer": "L3",
                "reason": "validate_claim verdict=contradicted",
                "advice": r.get("advice", ""),
            })
            ev = r.get("evidence_facts") or []
            contradicting_ids = [str(x) for x in ev]
            advice = str(r.get("advice", ""))

    # L3-SEMANTIC (NLI moat): the lexical L3 (validate_claim, "puramente lessicale")
    # misses conflicts where the WORDS differ but the MEANING contradicts a stored
    # fact. detect_semantic_conflicts adds the entailment-model trigger (timestamp-
    # aware: supersession over time is NOT a contradiction). Opt-in
    # (ENGRAM_SEMANTIC_CONFLICT) + needs agent.llm, so the default path is unchanged
    # (no LLM call). Activates the previously-dormant semantic_conflict layer; never
    # crashes the write (fail-soft to no warning).
    if level == "full" and _semantic_conflict_on():
        _judge_llm = getattr(agent, "llm", None) if agent is not None else None
        _sm = getattr(agent, "semantic", None) if agent is not None else None
        if _judge_llm is not None and _sm is not None:
            try:
                import time as _t
                import types as _ty

                from .semantic_conflict import (
                    LLMRelationJudge,
                    detect_semantic_conflicts,
                )
                _new = _ty.SimpleNamespace(
                    id="__candidate__", proposition=proposition,
                    topic=topic, created_at=_t.time(),
                )
                _sibs = [f for f in _sm.all()
                         if getattr(f, "topic", None) == topic][:200]
                for _w in detect_semantic_conflicts(
                    _new, _sibs, LLMRelationJudge(_judge_llm)
                ):
                    if getattr(_w, "kind", "") == "semantic_conflict":
                        warnings.append({
                            "layer": "L3-semantic",
                            "reason": "NLI judge: contradiction with a stored fact",
                            "advice": "a stored memory semantically contradicts this "
                                      "claim (not a lexical/numeric clash).",
                            "other_fact_id": getattr(_w, "other_fact_id", ""),
                        })
                        _oid = getattr(_w, "other_fact_id", "")
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
        from .grounding_gate import fact_grounding_score_ex, resolve_write_threshold_for
        try:
            gscore, _judge_used = fact_grounding_score_ex(grounding_llm, source, proposition)
        except (FileNotFoundError, OSError, ImportError, RuntimeError):
            # ONLY a missing / unloadable local model is tolerated here (a judge
            # advertised as present that turns out unreachable). Any OTHER
            # exception is a real bug — it MUST propagate, never be laundered into
            # a silent admission (opus review 2026-07-18, blocking finding D).
            gscore, _judge_used = None, None
        if gscore is None:
            # The CE was advertised present but could not score → treat as "no
            # judge" RIGHT HERE. The `elif` below is unreachable once this `if`
            # was taken, so emitting the advisory there was dead code (that was
            # the silent fail-open opus caught).
            _emit_l4_skipped()
        else:
            grounding_val = float(gscore)  # persist the score even when it PASSES
            if gscore < resolve_write_threshold_for(_judge_used):
                warnings.append({
                    "layer": "L4-grounding",
                    "reason": f"source does not entail the proposition "
                              f"(grounding {gscore:.0f} below threshold)",
                    "advice": "the source does not support this proposition — likely a "
                              "confabulated inference, not a stated fact.",
                    "grounding_score": gscore,
                })
                advice = advice or "Source does not entail the claim (semantic grounding)."
    elif source and not _have_judge:
        _emit_l4_skipped()

    # Decision tree.
    has_l3_contradict = any(w.get("layer") == "L3" for w in warnings)
    has_l3_semantic = any(w.get("layer") == "L3-semantic" for w in warnings)
    has_grounding_fail = any(w.get("layer") == "L4-grounding" for w in warnings)
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
    # A declared source is caller-controlled and unverified (spoofable like the
    # writer_role the trusted-hook bypass had to token-gate). It therefore does
    # NOT downgrade an L1 hit: the gate stays fail-closed and quarantines a
    # shape-confab regardless of an attached source. The honest recovery path
    # for a real documental fact is a grounding JUDGE (L4), which verifies
    # source-entailment; the L4-skipped advisory above says so when none is set.
    l1_escalates = has_l1 and not _personal_fp and not _world_fp
    if force_persist:
        # Caller demands persist; we still surface warnings.
        return GateResult(
            action="persist",
            warnings=warnings,
            contradicting_fact_ids=contradicting_ids,
            advice=advice,
            grounding_score=grounding_val,
        )
    if (has_l3_contradict or has_l3_semantic or has_grounding_fail) and mode == "reject":
        return GateResult(
            action="reject",
            warnings=warnings,
            contradicting_fact_ids=contradicting_ids,
            advice=advice or "Claim contradicted by existing memory.",
            grounding_score=grounding_val,
        )
    if has_l3_contradict or has_l3_semantic or has_grounding_fail or l1_escalates:
        return GateResult(
            action="downgrade",
            warnings=warnings,
            contradicting_fact_ids=contradicting_ids,
            advice=advice,
            grounding_score=grounding_val,
        )
    if warnings:
        # L1 false positives on personal/non-dev text: keep the fact recallable, surface
        # the detectors as advisory only (no quarantine).
        return GateResult(action="persist", warnings=warnings, advice=advice,
                          grounding_score=grounding_val)
    return GateResult(action="persist", grounding_score=grounding_val)


__all__ = [
    "GateResult",
    "GateAction",
    "GateMode",
    "ValidateLevel",
    "TRUSTED_HOOKS",
    "run_validation_gate",
]
