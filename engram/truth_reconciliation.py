"""R&D 2026-06-16 — truth-reconciliation P1 (update-on-write).

STATUS: tested prototype. Decision logic (classify_conflict), candidate-matching
(find_related_candidates / reconcile_against_corpus via the entity-KG) and the
over-trust measure are all validated. Still NOT wired into the live write path
(`SemanticMemory.store`) — that is the remaining step. By default
reconcile_against_corpus is FAIL-SAFE: it contests, it never auto-supersedes on a
correlation match (auto_supersede is opt-in). Remaining before production: the
write-path wiring AND a real semantic conflict detector (today's matching is
correlation by shared entity, not conflict). No production caller yet.

Converts an observed conflict between a new fact and an older one into either a
supersession (a temporal knowledge-update -> old becomes obsolete) or a recorded
contradiction (a genuine dispute -> contested). This is the mechanism the
calibration study showed is the ONLY lever on dangerous over-trust: it drives
`unobserved_p` toward 0 for the updates that pass through the write path.

Fail-safe by construction: only a clear, authority-respecting temporal update
supersedes; everything else is contested (visible + recoverable). A wrong
supersede deletes truth from the live set; a wrong contested only adds a doubt.
"""
from __future__ import annotations

import re

from ._telemetry_prefixes import TIER_KNOWLEDGE, classify_tier

_STATUS_AUTHORITY = {"verified": 3, "model_claim": 2, "legacy_unverified": 1}
_DAY = 86400.0
_CONFLICT_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _is_reconcilable(fact) -> bool:
    """Tier guard (2026-07-02): the knowledge-reconcile judge acts on
    tier=knowledge facts ONLY. The real-corpus NLI scan showed the residual
    contradiction pairs were machine telemetry (bus/consensus verdicts,
    dream/*/state, metric/event_*) and verbatim dialog transcripts — superseding
    or contesting those is judge noise, not truth maintenance."""
    return classify_tier(getattr(fact, "topic", "") or "") == TIER_KNOWLEDGE


def _conflict_tokens(text: str) -> set[str]:
    return {t.lower() for t in _CONFLICT_TOKEN_RE.findall(text or "")}


def _default_max_diff() -> int:
    """Token-difference tolerance for looks_like_conflict, env-tunable. DEFAULT STAYS 1.
    A sweep (benchmark/reconcile_truth_maintenance.py) suggested 3 lifts HaluMem update-
    recall 2%→7.5% at 0 false-supersede on a same-user *proxy* control — BUT the unit tests
    (test_truth_reconciliation_conflict) caught what that proxy missed: at max_diff≥2,
    "config X is 5s" vs "config X owner is Bob" (a COMPLEMENTARY value-vs-owner pair)
    misclassifies as a conflict. So loosening is NOT free — it trades complementary-attribute
    precision (the gate's whole safety property) for marginal recall. Lexical token-matching
    can't have both; the real fix is the semantic NLI detector (engram/semantic_conflict.py).
    Kept at 1; ENGRAM_RECONCILE_MAX_DIFF lets a deployment opt into the tradeoff knowingly."""
    import os
    try:
        return max(1, int(os.environ.get("ENGRAM_RECONCILE_MAX_DIFF", "1")))
    except ValueError:
        return 1


def looks_like_conflict(
    prop_a: str, prop_b: str, *, min_shared: int = 2, max_diff: int | None = None,
) -> bool:
    """Best-effort token heuristic: True when the two propositions look like the
    SAME subject/attribute with a DIFFERENT value (enough shared tokens, a small
    localized difference on each side). NOT a semantic detector — it guards the
    opt-in supersede path so a COMPLEMENTARY fact (different attribute, same
    entity) is not superseded; the fail-safe default never depends on it.
    ``max_diff`` defaults to ``_default_max_diff()`` (env-tunable) when not given.
    """
    if max_diff is None:
        max_diff = _default_max_diff()
    ta, tb = _conflict_tokens(prop_a), _conflict_tokens(prop_b)
    only_a, only_b = ta - tb, tb - ta
    if not only_a or not only_b:
        return False  # identical / one subsumes the other -> not a value conflict
    return (len(ta & tb) >= min_shared
            and len(only_a) <= max_diff and len(only_b) <= max_diff)


def _authority(fact) -> tuple[int, float]:
    rank = _STATUS_AUTHORITY.get(getattr(fact, "status", "model_claim"), 2)
    return (rank, float(getattr(fact, "confidence", 0.0) or 0.0))


def _has_evidence(fact) -> bool:
    """A fact carries EVIDENCE iff it cites a verified source or is status=verified.
    Self-reported confidence is NOT evidence (it is gameable — an insistent user or
    sycophantic agent just asserts high confidence)."""
    if getattr(fact, "status", "") == "verified":
        return True
    return bool(getattr(fact, "verified_by", None))


def classify_conflict(old, new, *, now: float, min_age_gap_days: float = 1.0,
                      require_evidence_to_supersede: bool = False) -> str:
    """Classify a conflict between an older fact and a newer one.

    Returns ``'update'`` (new supersedes old) ONLY when new is clearly more
    recent (created at least ``min_age_gap_days`` after old) AND at least as
    authoritative (status rank, then confidence). Otherwise ``'dispute'``
    (contested). Fail-safe: any ambiguity resolves to 'dispute'.

    ``require_evidence_to_supersede`` (opt-in; default off = unchanged) is the
    ANTI-SYCOPHANCY gate (Study C 2026-06-17, measured cave-rate 0.5): a bare claim
    with NO evidence (no ``verified_by``, status != verified) never supersedes a
    prior fact on recency/confidence alone — it can only CONTEST. This stops the
    memory from caving to a confident or merely-newer assertion. Cost (stated): a
    legitimate evidence-free self-update is contested (surfaced) instead of applied
    — the fail-safe direction (contesting is recoverable; a wrong supersede deletes
    truth), consistent with the rest of the stack.
    """
    age_gap_days = (float(new.created_at) - float(old.created_at)) / _DAY
    if age_gap_days < min_age_gap_days:
        return "dispute"          # too close in time -> not a clean update
    if _authority(new) < _authority(old):
        return "dispute"          # newer but LESS authoritative -> don't overwrite
    if require_evidence_to_supersede and not _has_evidence(new):
        return "dispute"          # anti-sycophancy: bare assertion never supersedes
    return "update"


def reconcile_fact_on_write(
    sm, new_fact, candidates, *, now: float, contradiction_store,
    min_age_gap_days: float = 1.0, judge=None,
) -> dict:
    """Reconcile ``new_fact`` against conflicting older ``candidates`` (same
    subject). Clean temporal updates supersede; disputes are recorded contested.

    Returns ``{"superseded": [ids], "contested": [ids]}``. Best-effort per
    candidate: a supersede conflict/error downgrades that candidate to contested
    (fail-safe) rather than aborting; recording a doubt never raises into the
    write path.
    """
    from engram.contradiction import Contradiction
    from engram.semantic import SupersedeConflict, SupersedeError

    if not _is_reconcilable(new_fact):
        return {"superseded": [], "contested": []}
    superseded: list[str] = []
    contested: list[str] = []
    for old in candidates:
        if not _is_reconcilable(old):
            continue  # telemetry/test/dialog: untouchable by the judge
        verdict = classify_conflict(
            old, new_fact, now=now, min_age_gap_days=min_age_gap_days)
        if verdict == "update" and not _is_conflict(
            getattr(old, "proposition", ""),
            getattr(new_fact, "proposition", ""), judge,
        ):
            verdict = "dispute"  # temporal update but NOT the same attribute
        if verdict == "update":
            try:
                sm.supersede(old.id, new_fact.id,
                             reason="reconcile:update-on-write")
                superseded.append(old.id)
                continue
            except (SupersedeConflict, SupersedeError):
                verdict = "dispute"   # fall through -> contested (fail-safe)
        try:
            contradiction_store.add(Contradiction(
                fact_a_id=old.id, fact_b_id=new_fact.id,
                kind="update-conflict", similarity=0.9))
        except Exception:  # noqa: BLE001 — recording a doubt must not crash write
            pass
        contested.append(old.id)
    return {"superseded": superseded, "contested": contested}


def _is_conflict(old_prop: str, new_prop: str, judge=None) -> bool:
    """Conflict confirmation. With a semantic ``judge`` (RelationJudge), True iff it
    classifies the pair CONTRADICTION — this catches paraphrase/antonym value-conflicts
    the lexical heuristic misses AND rejects same-entity COMPLEMENTARY facts (different
    attribute -> NEUTRAL), solving both failure modes of looks_like_conflict. Without a
    judge, falls back to the lexical heuristic (unchanged default)."""
    if judge is None:
        return looks_like_conflict(old_prop, new_prop)
    try:
        from .semantic_conflict import Relation
        return judge.classify(old_prop, new_prop) == Relation.CONTRADICTION
    except Exception:  # noqa: BLE001 — a judge hiccup falls back to lexical, never crashes
        return looks_like_conflict(old_prop, new_prop)


def find_related_candidates(sm, new_fact, entity_store, *, judge=None) -> list:
    """Find older facts that could be an update of ``new_fact``: linked to >=1
    of its entities, not itself, not already superseded, and not an
    exact-proposition duplicate.

    A candidate must share an entity, differ in proposition, be live, AND pass
    looks_like_conflict (same subject/attribute, different value). The last
    filter was added after a real-corpus dry-run: shared-entity-ONLY matching
    explodes on popular entities (5090 spurious candidates on 16 facts), which
    the fail-safe default would have turned into 5090 false 'contested'. Still
    best-effort token-based, not semantic; the fail-safe default remains.
    """
    seen: set[str] = set()
    out: list = []
    new_prop = (getattr(new_fact, "proposition", "") or "").strip()
    for eid in entity_store.entities_for_fact(new_fact.id):
        for fid in entity_store.facts_for_entity(eid):
            if fid == new_fact.id or fid in seen:
                continue
            seen.add(fid)
            old = sm.get(fid)
            if old is None or getattr(old, "superseded_by", None):
                continue
            old_prop = (getattr(old, "proposition", "") or "").strip()
            if old_prop == new_prop:
                continue  # exact duplicate, not an update
            if not _is_conflict(old_prop, new_prop, judge):
                continue  # shares an entity but not the same attribute -> ignore
            out.append(old)
    return out


def reconcile_against_corpus(
    sm, new_fact, entity_store, *, contradiction_store, now: float,
    min_age_gap_days: float = 1.0, auto_supersede: bool = False, judge=None,
) -> dict:
    """End-to-end P1: FIND shared-entity candidates for ``new_fact`` (instead of
    being handed them), then reconcile.

    ``auto_supersede=False`` (default, fail-safe): every found candidate is
    recorded CONTESTED, never superseded. find_related_candidates matches by
    CORRELATION (shared entity + distinct proposition), NOT by a semantic
    conflict detector — so a *complementary* fact (e.g. "config X owner is Bob"
    vs "config X is 5s") could otherwise be wrongly superseded. Auto-supersede on
    correlation alone deletes truth from the live set; contesting only adds a
    visible, recoverable doubt. Set ``True`` only where the candidate set is
    trusted to be genuinely conflicting (e.g. a real conflict detector upstream).

    Tier guard: a non-knowledge ``new_fact`` (telemetry/test/dialog) is a no-op
    before any entity lookup, and non-knowledge candidates are skipped.
    """
    if not _is_reconcilable(new_fact):
        return {"superseded": [], "contested": []}
    candidates = [c for c in find_related_candidates(
        sm, new_fact, entity_store, judge=judge) if _is_reconcilable(c)]
    if auto_supersede:
        return reconcile_fact_on_write(
            sm, new_fact, candidates, now=now,
            contradiction_store=contradiction_store,
            min_age_gap_days=min_age_gap_days, judge=judge)
    from engram.contradiction import Contradiction
    contested: list[str] = []
    for old in candidates:
        try:
            contradiction_store.add(Contradiction(
                fact_a_id=old.id, fact_b_id=new_fact.id,
                kind="reconcile-candidate", similarity=0.8))
        except Exception:  # noqa: BLE001 — recording a doubt must not crash write
            pass
        contested.append(old.id)
    return {"superseded": [], "contested": contested}


__all__ = [
    "classify_conflict",
    "looks_like_conflict",
    "reconcile_fact_on_write",
    "find_related_candidates",
    "reconcile_against_corpus",
]
