"""Justified Memory — a Truth-Maintenance layer for LLM memory (the 2027 thesis).

A memory that maintains JUSTIFIED TRUE BELIEF, not stored strings. Concatenates classical
truth-maintenance (Doyle 1979 JTMS: a belief is held BECAUSE of a justification; when the
justification fails, the belief is retracted) with admission-time NLI grounding
(`grounding_gate`): the justification of a belief is concrete and verifiable = the SOURCE
entails the PROPOSITION. See docs/JUSTIFIED_MEMORY.md for the design + the verified SOTA gap.

Lifecycle of a belief:
  admit ──(source⊧proposition ≥ θ)──▶ believed
  believed ──source SUPERSEDED──▶ retracted     (justification replaced)
  believed ──source CONTRADICTED──▶ contested    (justification disputed)
  believed ──valid_until passed──▶ stale         (justification expired)
Only ``believed`` (and not expired) beliefs are SERVED as truth. The novelty vs the SOTA:
beliefs auto-retract when their grounding fails — no agent-memory product does this.

Pure core: the grounder (LLM entailment) is INJECTED, so the lifecycle logic is unit-tested
deterministically with stubs. O5: the grounder is the only LLM cost, paid once at admission.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace

_DEFAULT_THRESHOLD = 85.0

# A belief is "active" (re-evaluable each maintenance pass) in these states; rejected is
# terminal (never admitted), retracted is terminal (justification permanently replaced).
_ACTIVE = ("believed", "contested", "stale")


@dataclass(frozen=True)
class Belief:
    """A proposition held BECAUSE of a justification (source span + grounding score)."""

    id: str
    proposition: str
    source: str                       # the justification text that should entail the prop
    grounding_score: float            # how strongly source entails proposition (0-100)
    status: str = "believed"          # believed | rejected | retracted | contested | stale
    valid_until: float | None = None  # epoch; None = no temporal bound
    depends_on: tuple[str, ...] = ()  # ids of OTHER beliefs this one is derived from (ATMS)

    @property
    def justified(self) -> bool:
        """Currently held as TRUE (admitted, not retracted/contested/expired)."""
        return self.status == "believed"


def admit(grounder: Callable[[str, str], float], proposition: str, source: str, *,
          threshold: float = _DEFAULT_THRESHOLD, valid_until: float | None = None,
          bid: str = "b") -> Belief:
    """Admit a candidate belief ONLY if its source justifies it (source ⊧ proposition ≥ θ).
    ``grounder(source, proposition) -> score 0-100``. Below θ → status 'rejected'
    (never enters the believed set). The grounded admission gate, as a TMS justification."""
    score = grounder(source, proposition)
    status = "believed" if score >= threshold else "rejected"
    return Belief(bid, proposition, source, float(score), status, valid_until)


def maintain(beliefs: Iterable[Belief], *, now: float,
             superseded_ids: Iterable[str] = (),
             contradicted_ids: Iterable[str] = ()) -> list[Belief]:
    """Truth-maintenance pass: re-derive each ACTIVE belief's status from whether its
    justification still holds. A belief whose source was SUPERSEDED is retracted; whose
    source is CONTRADICTED is contested; whose ``valid_until`` passed is stale; otherwise it
    recovers to believed (e.g. a contradiction was resolved). Terminal states (rejected,
    retracted) are left untouched. Pure."""
    sup = set(superseded_ids)
    con = set(contradicted_ids)
    out: list[Belief] = []
    for b in beliefs:
        if b.status not in _ACTIVE:
            out.append(b)
            continue
        if b.id in sup:
            st = "retracted"
        elif b.id in con:
            st = "contested"
        elif b.valid_until is not None and now >= b.valid_until:
            st = "stale"
        else:
            st = "believed"
        out.append(replace(b, status=st))
    return out


def propagate(beliefs: Iterable[Belief], *, now: float) -> list[Belief]:
    """ATMS-style TRANSITIVE retraction (de Kleer 1986): a belief derived from other
    beliefs (``depends_on``) loses its justification the moment ANY of those supporting
    beliefs is no longer justified — and that loss cascades. Run AFTER ``maintain`` (which
    sets the leaf statuses from sources/time/contradiction); ``propagate`` then closes the
    dependency graph to a fixpoint. The capability no agent-memory product has: invalidate a
    foundational fact and everything inferred from it auto-retracts. Pure."""
    by_id = {b.id: b for b in beliefs}
    status = {b.id: b.status for b in beliefs}

    def _justified(bid: str) -> bool:
        b = by_id[bid]
        if status[bid] != "believed":
            return False
        return not (b.valid_until is not None and now >= b.valid_until)

    changed = True
    while changed:                       # fixpoint: cascade until no status flips
        changed = False
        for b in beliefs:
            if status[b.id] != "believed" or not b.depends_on:
                continue
            # only belief-id deps are checked; a dep not in the set is a raw source (present)
            if any(d in by_id and not _justified(d) for d in b.depends_on):
                status[b.id] = "retracted"
                changed = True
    return [replace(b, status=status[b.id]) for b in beliefs]


def served(beliefs: Iterable[Belief], *, now: float) -> list[Belief]:
    """The beliefs the memory will serve AS TRUTH: justified (believed) and not expired.
    This is the read-path discipline — never serve a retracted/contested/stale belief."""
    return [b for b in beliefs
            if b.status == "believed" and not (b.valid_until is not None and now >= b.valid_until)]


def justified_belief_integrity(served_beliefs: list[Belief],
                               currently_true_ids: Iterable[str]) -> float:
    """JBI — the new metric: of the beliefs SERVED as truth, the fraction that are actually
    currently true. 1.0 if nothing served (served no falsehood). The axis the retrieval-SOTA
    ignores: not 'did you retrieve it' but 'is what you served still TRUE'."""
    truth = set(currently_true_ids)
    if not served_beliefs:
        return 1.0
    return sum(1 for b in served_beliefs if b.id in truth) / len(served_beliefs)


# ---- PRODUCTION bridge: run the lifecycle over REAL stored facts ------------------
# Closes the critic's "library not live" FAIL: map an Engram Fact (duck-typed: .id,
# .proposition, .superseded_by, .valid_until, .lineage_parents/.source_episodes/
# .verified_by) to a Belief and run maintain+propagate with DETERMINISTIC triggers
# (no LLM): superseded_by set -> retract; valid_until passed -> stale; lineage_parents ->
# dependency cascade. Read-only audit (reports what WOULD retract) — no store mutation.

def _attr(fact: object, name: str, default: object = None) -> object:
    if isinstance(fact, dict):
        return fact.get(name, default)
    return getattr(fact, name, default)


def fact_to_belief(fact: object) -> Belief:
    """Duck-typed Engram Fact -> Belief. Provenance presence (verified_by/source_episodes)
    is the justification; ``depends_on`` comes ONLY from a TYPED logical-derivation edge
    (``derives_from`` / ``depends_on`` / ``lineage_parents`` alias).

    IMPORTANT (R26 correction): we do NOT use the Fact field ``lineage_to`` here. Verified on
    the real corpus, ``lineage_to`` is a NARRATIVE/session-successor pointer (95% cross-topic
    ``clp --lineage-to auto`` chain links), not a logical-derivation edge — superseding a
    narrative predecessor does not strip a successor's justification. Feeding lineage_to into
    the ATMS cascade produced false retractions. Until the write-path records a typed
    derivation edge, real facts have none → propagate correctly stays dormant (R23) instead of
    cascading on the wrong edges. ``benchmark.lineage_cascade_exposure`` measures the lineage_to
    NARRATIVE graph separately (as an exposure upper bound), and reads that field directly."""
    fid = str(_attr(fact, "id", "") or "")
    prop = str(_attr(fact, "proposition", "") or "")
    prov = _attr(fact, "verified_by") or _attr(fact, "source_episodes") or ""
    source = str(prov) if prov not in (None, "", "[]", "null") else ""
    deps = (_attr(fact, "derives_from") or _attr(fact, "depends_on")
            or _attr(fact, "lineage_parents") or ())
    if isinstance(deps, str):
        deps = tuple(d.strip() for d in deps.strip("[]").split(",") if d.strip())
    else:
        deps = tuple(str(d) for d in deps)
    vu = _attr(fact, "valid_until")
    return Belief(id=fid, proposition=prop, source=source,
                  grounding_score=100.0 if _attr(fact, "status") == "verified" else 50.0,
                  status="believed", valid_until=float(vu) if vu is not None else None,
                  depends_on=deps)


def audit_facts(facts: Iterable[object], *, now: float,
                scope_topic: str | None = None,
                contradicted_ids: Iterable[str] = ()) -> dict[str, object]:
    """Read-only truth-maintenance audit over REAL facts (deterministic triggers).
    Returns what is SERVED vs what WOULD be retracted (superseded / dependency-cascade),
    CONTESTED (contradicted), or STALE — the live, production-reachable form of
    maintain+propagate. No mutation.

    ``contradicted_ids`` (retraction-trigger #4, R28): ids the CALLER determined are
    contradicted (e.g. by an NLI pass over ``semantic_conflict``). They become ``contested``
    (NOT served as truth) and, like supersession, their TYPED-derivation descendants cascade.
    The param keeps this function PURE/deterministic — the costly NLI lives in the caller and
    is opt-in. ``superseded_by`` (a stored field) stays the deterministic supersession source.

    ALL passed facts become belief NODES (superseded ones too) so the ATMS cascade can reach
    a derived fact whose foundation was superseded — the capability `propagate` exists for.
    ``scope_topic`` filters the REPORT (served/would_retract/…) to one topic WITHOUT shrinking
    the graph: callers pass the full corpus so a cross-topic foundation is still a node, then
    scope the output — else a topic-scoped load drops the foundation and silently serves a
    fact whose justification failed (the cross-topic leak the critic found)."""
    facts = list(facts)
    superseded_ids = [str(_attr(f, "id", "")) for f in facts if _attr(f, "superseded_by")]
    con_ids = [str(i) for i in contradicted_ids]
    beliefs = [fact_to_belief(f) for f in facts]
    maintained = propagate(
        maintain(beliefs, now=now, superseded_ids=superseded_ids,
                 contradicted_ids=con_ids), now=now)

    in_scope = {str(_attr(f, "id", "")) for f in facts
                if scope_topic is None or _attr(f, "topic") == scope_topic}
    scoped = [b for b in maintained if b.id in in_scope]
    srv = [b for b in served(maintained, now=now) if b.id in in_scope]
    by_status: dict[str, int] = {}
    for b in scoped:
        by_status[b.status] = by_status.get(b.status, 0) + 1
    return {
        "n_facts": len(scoped), "n_graph": len(facts),
        "scope_topic": scope_topic, "n_superseded_input": len(superseded_ids),
        "n_contradicted_input": len(con_ids),
        "served": len(srv), "served_ids": [b.id for b in srv],
        "would_retract_ids": [b.id for b in scoped if b.status == "retracted"],
        "would_contest_ids": [b.id for b in scoped if b.status == "contested"],
        "would_stale_ids": [b.id for b in scoped if b.status == "stale"],
        "status_counts": by_status,
    }


def collect_contradicted_ids(facts: Iterable[object], judge: object, *,
                             min_cosine: float = 0.86,
                             cosine_fn: Callable[[object, object], float] | None = None,
                             ) -> list[str]:
    """Compute the ids of LIVE facts contradicted by another live fact — the input for
    ``audit_facts(contradicted_ids=...)`` (retraction-trigger #4). Reuses
    ``semantic_conflict.detect_semantic_conflicts`` (cosine pre-filter → NLI judge on the
    narrow candidate set). BOTH members of a contradicting pair are returned: neither should
    be served as confident truth until a separate reconciliation picks the winner.

    ``judge`` is INJECTED (a ``semantic_conflict.RelationJudge``) so this is deterministic in
    tests; the costly LLM judge is supplied only by the opt-in caller. Superseded facts are
    excluded (already retracted by ``maintain``).

    CAVEAT (honest, carried): this inherits the NLI contradiction false-positive rate — on the
    real corpus ~3.4% residual after the semantic_conflict upstream filter (corpus_fp_real
    bench). It SURFACES contested facts for review (read-only audit); it does NOT auto-mutate
    the store, which is why a moderate FP rate is acceptable here but would not be for
    auto-retraction."""
    from engram.semantic_conflict import detect_semantic_conflicts
    facts = list(facts)
    live = [f for f in facts if not _attr(f, "superseded_by")]
    kw: dict[str, object] = {"min_cosine": min_cosine}
    if cosine_fn is not None:
        kw["cosine_fn"] = cosine_fn
    con: set[str] = set()
    for f in live:
        fid = str(_attr(f, "id", "") or "")
        for w in detect_semantic_conflicts(f, live, judge, **kw):  # type: ignore[arg-type]
            if getattr(w, "kind", "") == "semantic_conflict":
                con.add(fid)
                other = getattr(w, "other_fact_id", "")
                if other:
                    con.add(str(other))
    return sorted(con)


__all__ = ["Belief", "admit", "maintain", "propagate", "served",
           "justified_belief_integrity", "fact_to_belief", "audit_facts",
           "collect_contradicted_ids"]
