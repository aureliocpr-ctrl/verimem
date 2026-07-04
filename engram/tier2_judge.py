"""Tier-2 semantic judge + trust-assessment pipeline (wave-2 anti-confab).

The deterministic lexical layers (L1 keyword detectors, L3 numeric
contradiction, Tier-1 evidence requirement, corroboration) hit their
ceiling on an event-LOG corpus: they cannot tell a durable fact ("the
cache holds 1024 entries") from a coincidental number in narrative text
("3 loop steps", "50ms hook restated across handoffs"). A *semantic* judge
can — but an LLM opinion is itself a claim, so it must never be allowed to
MINT trust.

This module provides:
  • a pluggable :class:`Judge` interface (so a clean-Claude-subscription
    judge, or a cheaper DeepSeek/Kimi CLI gate, drops in without touching
    the pipeline) + hermetic stub judges for tests;
  • :func:`assess_claim_trust` — the composition that decides, for one
    fact, whether trust is WITHHELD (Tier-1), RESTORED (corroboration), or
    sent to the judge for TRIAGE (Tier-2).

NON-NEGOTIABLE INVARIANT
------------------------
The judge may only LOWER trust (``declass``) or FLAG a promotion candidate
(``flag_promote_candidate``) for a human / future evidence to confirm. It
can NEVER raise the resulting confidence above the Tier-1 ceiling on its
opinion alone. Only DETERMINISTIC evidence — independent corroboration or a
``verified_by`` reference — restores full trust. This keeps the judge a
*triage*, not a *certifier*: an LLM cannot confabulate a fact into
"verified". (Same discipline as the rest of the stack: precision over
recall, reversible, opt-in, measured before flipped on.)

The judge is designed to run at CONSOLIDATION time (async, off the write
hot-path), reviewing the specific-unsourced-uncorroborated bucket — not at
every write. Nothing here is wired into a live path yet; it ships as a
tested library so the corpus-wide impact can be benchmarked first.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from .corroboration import corroboration_index
from .evidence_requirement import (
    UNSOURCED_SPECIFIC_CEILING,
    evidence_requirement_enabled,
    is_specific_claim,
)
from .semantic import Fact


class JudgeAction(str, Enum):
    """What the Tier-2 judge recommends for an ambiguous claim."""

    DECLASS = "declass"  # noise / coincidental number → lower trust
    KEEP = "keep"  # neutral / abstain → leave the Tier-1 cap as-is
    PROMOTE_CANDIDATE = "promote_candidate"  # durable+true → FLAG (no auto-raise)


@dataclass(frozen=True)
class JudgeVerdict:
    """A judge's triage opinion. ``confidence`` is the judge's OWN confidence
    in the triage — advisory only; it never feeds the resulting trust."""

    action: JudgeAction
    reason: str = ""
    confidence: float = 0.0


@runtime_checkable
class Judge(Protocol):
    """Pluggable Tier-2 judge.

    Implementations (future, no-USD): a clean-Claude subscription call, a
    DeepSeek/Kimi CLI gate, or — here — a hermetic stub for tests. The
    pipeline depends only on this one method.
    """

    def judge(
        self, proposition: str, *, topic: str = "", context: str = "",
    ) -> JudgeVerdict:
        ...


@dataclass
class FixedJudge:
    """Hermetic stub: always returns ``verdict``. For pipeline tests."""

    verdict: JudgeVerdict

    def judge(
        self, proposition: str, *, topic: str = "", context: str = "",
    ) -> JudgeVerdict:
        return self.verdict


@dataclass
class RecordingJudge:
    """Like :class:`FixedJudge` but records every call as ``(proposition,
    topic)`` in :attr:`calls` — lets a test assert the judge is consulted
    ONLY for the ambiguous bucket (never for sourced / generic /
    corroborated claims, where deterministic logic already decided)."""

    verdict: JudgeVerdict
    calls: list[tuple[str, str]] = field(default_factory=list)

    def judge(
        self, proposition: str, *, topic: str = "", context: str = "",
    ) -> JudgeVerdict:
        self.calls.append((proposition, topic))
        return self.verdict


_LLM_JUDGE_SYSTEM = (
    "You triage a remembered CLAIM for a long-term memory. Default to KEEPING it. Call NOISE "
    "only when you are CONFIDENT the claim records a single execution's transient measurement "
    "— a value true only of one run/attempt/moment, with no standing meaning beyond it "
    "(typical of telemetry, logs, and progress traces). Call it DURABLE when it could be a "
    "standing fact about the world / user / system / configuration — a capacity, limit, "
    "price, identity, setting, decision, or a count of a real persistent thing — even if it "
    "contains a number. When you cannot tell, answer NEUTRAL (keep), NOT NOISE. Judge by the "
    "claim's MEANING, not by surface wordings. Reply with EXACTLY one word: DURABLE, NOISE, "
    "or NEUTRAL.")


@dataclass
class LLMJudge:
    """Concrete Tier-2 judge backed by an injected LLM (subscription/CLI — no external
    key; same injection contract as the grounding gate / reconcile NLI judge). Maps the
    one-word verdict to a JudgeAction. FAIL-SAFE: any error or an unparsed reply → KEEP,
    so the judge never DECLASSes or PROMOTEs on a hiccup — it can only ever LOWER trust on
    a confident NOISE call, upholding the module invariant (a judge triages, never mints)."""

    llm: Any
    model: str | None = None

    def judge(
        self, proposition: str, *, topic: str = "", context: str = "",
    ) -> JudgeVerdict:
        user = f"Claim: {proposition}"
        if topic:
            user += f"\nTopic: {topic}"
        if context:
            user += f"\nContext: {context}"
        try:
            resp = self.llm.complete(
                _LLM_JUDGE_SYSTEM, [{"role": "user", "content": user}],
                model=self.model, max_tokens=8)
            word = (getattr(resp, "text", "") or "").strip().upper()
        except Exception:  # noqa: BLE001 — a judge hiccup must never break consolidation
            return JudgeVerdict(JudgeAction.KEEP, "judge error -> keep (fail-safe)", 0.0)
        if word.startswith("NOISE"):
            return JudgeVerdict(JudgeAction.DECLASS, "ephemeral / coincidental", 0.7)
        if word.startswith("DURABLE"):
            return JudgeVerdict(JudgeAction.PROMOTE_CANDIDATE, "durable fact", 0.7)
        return JudgeVerdict(JudgeAction.KEEP, "neutral / unparsed -> keep", 0.5)


@dataclass(frozen=True)
class TrustDecision:
    """Outcome of :func:`assess_claim_trust` for a single fact.

    stage       — which layer decided: pass_through | withheld | restored | judged
    action      — keep | cap_confidence | restore | declass | flag_promote_candidate
    confidence  — resulting confidence (NEVER above the input on judge opinion)
    status_hint — suggested status (only changes to 'quarantined' on declass)
    reason      — human-readable justification
    corroborations — number of independent distinct-topic witnesses found
    judge_verdict  — the raw verdict, when the judge was consulted
    """

    stage: str
    action: str
    confidence: float
    status_hint: str
    reason: str
    corroborations: int = 0
    judge_verdict: JudgeVerdict | None = None


def assess_claim_trust(
    fact: Fact,
    *,
    corpus: list[Fact] | None = None,
    judge: Judge | None = None,
    enabled: bool | None = None,
    min_corroborations: int = 2,
    ceiling: float = UNSOURCED_SPECIFIC_CEILING,
    declass_confidence: float = 0.3,
    declass_status: str = "quarantined",
) -> TrustDecision:
    """Decide how much to trust ``fact`` by composing the three layers.

    Order (each step can short-circuit):
      1. SOURCED (``verified_by``) → pass through; evidence already exists.
      2. NOT specific (no quantity/year) → pass through; nothing to withhold.
      3. SPECIFIC + UNSOURCED:
         a. ≥ ``min_corroborations`` independent (distinct-topic) same-value
            witnesses in ``corpus`` → RESTORE full trust, deterministically.
            The judge is NOT consulted — evidence beats opinion.
         b. otherwise WITHHOLD to ``ceiling`` (Tier-1), then if a ``judge``
            is supplied, ask it to TRIAGE:
              declass            → lower to ``declass_confidence`` + quarantine
              promote_candidate  → FLAG, but confidence STAYS capped (no raise)
              keep               → the Tier-1 cap stands

    ``corpus`` is the pool of OTHER facts to look for corroboration in
    (``fact`` itself need not be included — it is added internally). Opt-in:
    when ``enabled`` is False (default resolves from
    ``ENGRAM_EVIDENCE_REQUIREMENT``) everything passes through unchanged, so
    corpus-wide impact can be measured before flipping it on.
    """
    if enabled is None:
        enabled = evidence_requirement_enabled()
    conf = float(fact.confidence)
    status = fact.status

    if not enabled:
        return TrustDecision("pass_through", "keep", conf, status, "gate disabled")

    if fact.verified_by:
        return TrustDecision(
            "pass_through", "keep", conf, status, "sourced (verified_by)",
        )

    if not is_specific_claim(fact.proposition):
        return TrustDecision(
            "pass_through", "keep", conf, status, "not a specific claim",
        )

    # specific + unsourced → count independent corroborations (deterministic)
    n = 0
    if corpus:
        idx = corroboration_index([fact, *corpus])
        n = idx.get(fact.id, 0)
    if n >= min_corroborations:
        return TrustDecision(
            "restored", "restore", conf, status,
            f"{n} independent corroborations", corroborations=n,
        )

    capped = min(conf, ceiling)
    if judge is None:
        return TrustDecision(
            "withheld", "cap_confidence", capped, status,
            "specific unsourced uncorroborated → Tier-1 cap", corroborations=n,
        )

    verdict = judge.judge(fact.proposition, topic=fact.topic, context="")
    if verdict.action is JudgeAction.DECLASS:
        return TrustDecision(
            "judged", "declass", min(capped, declass_confidence), declass_status,
            verdict.reason or "judge: declass",
            corroborations=n, judge_verdict=verdict,
        )
    if verdict.action is JudgeAction.PROMOTE_CANDIDATE:
        # INVARIANT: opinion never mints trust. Flag only; confidence stays
        # capped until DETERMINISTIC evidence (corroboration / source / human)
        # arrives.
        return TrustDecision(
            "judged", "flag_promote_candidate", capped, status,
            verdict.reason or "judge: promote candidate (needs evidence)",
            corroborations=n, judge_verdict=verdict,
        )
    # KEEP / anything else → the Tier-1 cap stands
    return TrustDecision(
        "judged", "cap_confidence", capped, status,
        verdict.reason or "judge: keep", corroborations=n, judge_verdict=verdict,
    )


def triage_corpus(
    semantic: Any, judge: Judge, *, limit: int = 1000, apply: bool = True,
    min_corroborations: int = 2, max_judged: int | None = None,
) -> dict:
    """Consolidation-time Tier-2 triage over the live corpus's ambiguous bucket.

    For each SPECIFIC, UNSOURCED, live fact (the only bucket the judge is allowed to
    touch), runs :func:`assess_claim_trust` with ``judge``; on a DECLASS verdict the fact
    is QUARANTINED (``apply=True``) — reversible, never deleted — or merely counted
    (``apply=False``, dry-run). The judge can only LOWER trust here, never raise it; sourced
    or corroborated facts are skipped by the deterministic layers before the judge is asked.
    ``max_judged`` bounds LLM-judge calls per pass (the consolidation stage uses it to cap
    cost per cycle; future cycles handle the rest). Returns ``{reviewed, declassed,
    declassed_ids, applied, candidates, candidates_pending, corpus_truncated, corpus_limit}``
    — the last four SURFACE the caps so a partial pass is never mistaken for full coverage.
    Best-effort per fact; a single judge/quarantine hiccup is skipped, never aborts the pass."""
    facts = semantic.list_facts(limit=limit)
    # NO SILENT CAP (adversarial-review hole #7): a corpus larger than `limit` is truncated
    # here, and `max_judged` bounds judge calls per pass — both are SURFACED in the report
    # (corpus_truncated, candidates_pending) so a caller never mistakes "reviewed N" for
    # "the whole corpus is clean".
    corpus_truncated = len(facts) >= limit  # there may be more facts than we fetched
    reviewed = 0
    candidates = 0  # specific + unsourced + live = the only judge-eligible bucket
    declassed_ids: list[str] = []
    for f in facts:
        if getattr(f, "status", "") in ("quarantined", "orphaned", "legacy_unverified"):
            continue
        if getattr(f, "verified_by", None):
            continue
        if not is_specific_claim(getattr(f, "proposition", "")):
            continue
        candidates += 1  # count ALL eligible, even past budget, to surface the true backlog
        if max_judged is not None and reviewed >= max_judged:
            continue  # eligible but over this pass's budget — pending, NOT silently dropped
        try:
            d = assess_claim_trust(
                f, corpus=[g for g in facts if g.id != f.id], judge=judge,
                enabled=True, min_corroborations=min_corroborations)
        except Exception:  # noqa: BLE001 — one bad fact never aborts the pass
            continue
        reviewed += 1
        if d.action == "declass":
            declassed_ids.append(f.id)
            if apply:
                try:
                    semantic.quarantine_fact(f.id, reason=(d.reason or "tier2:declass"))
                except Exception:  # noqa: BLE001
                    pass
    return {"reviewed": reviewed, "declassed": len(declassed_ids),
            "declassed_ids": declassed_ids, "applied": apply,
            "candidates": candidates, "candidates_pending": max(0, candidates - reviewed),
            "corpus_truncated": corpus_truncated, "corpus_limit": limit}


__all__ = [
    "JudgeAction",
    "JudgeVerdict",
    "Judge",
    "FixedJudge",
    "RecordingJudge",
    "LLMJudge",
    "TrustDecision",
    "assess_claim_trust",
    "triage_corpus",
]
