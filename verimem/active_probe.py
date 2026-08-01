"""Active probes — the store builds the query that would falsify a fact
(Vivarium P87 / cortex ``active_real``: designed probes killed spurious
postulates in ~4 observations where passive observation left them in limbo
forever; the hypothesis trilemma became a budget line).

One probe pass over a copula fact:

  1. build the falsifying query from the fact itself ("<subject> is …" — what
     ELSE does the store assert about this subject?);
  2. counter-evidence = a LIVE fact, same subject, different value, from an
     INDEPENDENT non-engine source (P85: ``actor:*`` rivals never count —
     self-echo cannot refute the world);
  3. the verdict, by how the two guarantees compare:
     * rival STRICTLY better guaranteed → ``refuted(counterexample=…)`` through
       the monotone epistemic rules (set_epistemic — absorbing, auditable);
     * rival EQUALLY guaranteed → ``contested``: the rival is NAMED and nothing
       is labelled. Settling an even conflict with an irreversible label would
       decide it by probe ORDER, and would read specialisation as contradiction
       ("Rex is a dog" / "Rex is a labrador" are both true). The guardian
       already abstains and shows both sides on this input — one store, one
       verdict (2026-07-28);
     * every rival disqualified by a guard → ``inconclusive``: no falsification
       attempt could occur, so no survival is claimed;
     * no rival at all → ``survived``, and the ``unbeaten`` bound grows by one:
       bound semantics = NUMBER OF PROBES SURVIVED, declared here and in the
       label itself — which is why it is minted only when a probe was real.

Honest scope: probes the store against ITSELF (internal consistency made
active). Probing against external anchors (re-fetching a source, an API
ground-truth) plugs into the same outcome contract later.
"""
from __future__ import annotations

from typing import Any

from .composer import _copula_parse, subject_key
from .epistemic import guarantee_rank, make_refuted, make_unbeaten
from .self_provenance import is_self_ref
from .source_trust import canonical_source

__all__ = ["probe_fact"]


def probe_fact(mem: Any, fact_id: str, *, k: int = 8) -> dict[str, Any]:
    """One active-falsification pass. Returns ``{outcome, probe_query,
    counterexample_id? | rival_id? | bound?}`` with outcome in
    ``refuted_proposed | contested | inconclusive | survived | not_probeable |
    not_found``."""
    fact = mem.semantic.get(fact_id)
    if fact is None:
        return {"outcome": "not_found"}
    parsed = _copula_parse(fact.proposition)
    if not parsed:
        return {"outcome": "not_probeable",
                "reason": "no copula structure to falsify (world-bound v1)"}
    subj, obj_norm, _obj_raw = parsed
    probe_query = f"{subj} is"

    hits = mem.search(probe_query, k=k)
    contested: tuple[Any, str] | None = None
    disqualified = 0
    for h in hits:
        rid = h.get("id", "")
        if rid == fact.id:
            continue
        rival = mem.semantic.get(rid)
        # user_belief disqualified as a rival (Giro 2): an unverified user
        # assertion must never drive a falsification verdict against a fact.
        if rival is None or rival.superseded_by \
                or rival.status in ("quarantined", "orphaned", "user_belief"):
            continue
        rp = _copula_parse(rival.proposition)
        # subject_key, not a local normalisation: this rule had a second copy in
        # the guardian and the two disagreed (2026-07-28). Same behaviour as
        # before here — the divergence was on the guardian's side.
        if not rp or subject_key(rp[0]) != subject_key(subj):
            continue
        if rp[1] == obj_norm:
            continue                                   # agreement, not a rival
        # Past this line the row IS a same-subject disagreement. Every check
        # below REMOVES it from contention, so it is counted: a pass that faced
        # nothing but disqualified rivals did not survive a probe, it never had
        # one, and the ``unbeaten`` receipt must not claim otherwise.
        if any(is_self_ref(r) for r in (rival.verified_by or [])):
            # NOT counted as a disqualified rival. P85 says an ``actor:*`` row
            # is the engine quoting itself — it is not a voice that failed to
            # qualify, it is not a voice. Counting it would mean a fact can
            # never earn a bound once the composer has echoed it, and would let
            # anyone freeze another fact's bound forever by writing echoes.
            # The two cases below are different: a source revising ITSELF and
            # an unsourced row are real disagreements that fail a bar, and
            # "nothing withstood falsification" is the honest verdict there.
            # (2026-07-29: these three shared one counter, so two tests
            # contradicted each other and which one passed depended on whether
            # recall happened to retrieve the rival.)
            continue                                   # P85: self-echo can't refute
        # INDEPENDENCE (2026-07-27). The docstring promised counter-evidence
        # "from an INDEPENDENT source" and only "not the engine" was enforced —
        # two different claims. Since ``refuted`` is ABSORBING, a wrong one kills
        # a fact for good, so the rival must be at least as well-sourced as what
        # it destroys: it needs an identifiable source, and a source revising
        # ITSELF is supersession (that machinery already exists), not refutation.
        if not (rival.verified_by or []):
            disqualified += 1
            continue                                   # unsourced: too cheap to kill
        if canonical_source(rival.verified_by) == canonical_source(fact.verified_by):
            disqualified += 1
            continue                                   # same source correcting itself
        # GUARANTEE (2026-07-28). Refutation is irreversible, so it takes a
        # STRICTLY better guarantee — the same test the guardian applies when it
        # decides to CORRECT rather than abstain. An equal guarantee is a
        # conflict with no winner: reported, never settled by force.
        _rank_rival = guarantee_rank(rival.epistemic)
        _rank_fact = guarantee_rank(fact.epistemic)
        if _rank_rival < _rank_fact:
            disqualified += 1
            continue                                   # weaker guarantee cannot kill
        # Two axes, and the rival must be STRICTLY ahead on one without being
        # behind on the other: the epistemic guarantee, and provenance (it
        # already carries a source by the guard above — the fact may not). An
        # equal rival on both is a conflict with no winner.
        if _rank_rival > _rank_fact or not (fact.verified_by or []):
            label = make_refuted(f"{rival.id}: {rp[1]}")
            applied = mem.semantic.set_epistemic(fact.id, label)
            return {"outcome": "refuted_proposed", "probe_query": probe_query,
                    "counterexample_id": rival.id, "label_applied": applied}
        if contested is None:
            contested = (rival, rp[1])                 # keep looking for a winner

    if contested is not None:
        # An EVEN conflict. Applying the absorbing label here would settle it by
        # probe ORDER — probe the labrador and the labrador dies, probe the
        # poodle and the poodle dies — and would read specialisation as
        # contradiction ("Rex is a dog" vs "Rex is a labrador": both true, one
        # killed forever). The store says so instead, and NAMES the rival; this
        # is the verdict the guardian already reaches on the same input.
        rival, rival_value = contested
        return {"outcome": "contested", "probe_query": probe_query,
                "rival_id": rival.id, "rival_value": rival_value,
                "reason": "same subject, different value, equal guarantee — "
                          "no epistemic winner, so nothing is refuted"}
    if disqualified:
        # Rivals existed and every one was removed by a guard. Nothing was
        # falsified AND nothing withstood falsification: minting unbeaten here
        # would sell a survival that was structurally guaranteed.
        return {"outcome": "inconclusive", "probe_query": probe_query,
                "rivals_disqualified": disqualified,
                "reason": "every same-subject rival was disqualified — no "
                          "falsification attempt could take place"}

    # survived: the bound = probes survived so far, monotone by construction
    current = fact.epistemic if fact.epistemic else None
    bound = (current["bound"] + 1 if current and current["kind"] == "unbeaten"
             else 1)
    applied = mem.semantic.set_epistemic(fact.id, make_unbeaten(bound))
    return {"outcome": "survived", "probe_query": probe_query,
            "bound": bound, "label_applied": applied}
