"""Epistemic labels — the GUARANTEE kind of a fact, orthogonal to provenance.

``status`` (verified/provisional/model_claim/...) says who vouches for a fact;
the epistemic label says what KIND of guarantee backs it:

  * ``proven``     — a declared machine-checkable proof ref (e.g. the
                     ``qa:exact_integer_check_..._PASS`` pattern the organism
                     used to earn admission through the anti-confab gate);
  * ``unbeaten``   — held against every probe up to a named ``bound``; the
                     bound only GROWS (monotone evidence accumulation);
  * ``refuted``    — a NAMED counterexample exists; ABSORBING (a counterexample
                     does not evaporate — correction happens by supersession,
                     never by relabeling).

Transfer origin (cortex handoff 2026-07-13, verified in the lab): coprime6→
deficient holds to 10^6 yet dies at 5391411025 — "unbeaten(1e6)" and "proven"
must never be conflated, and the composition layer must only build from labels
it can trust. Pure logic: no I/O; persistence lives in semantic.py (column
``epistemic``, schema v14, additive/nullable — None = unlabeled, the default
for ordinary facts).
"""
from __future__ import annotations

import json
from typing import Any

__all__ = ["KINDS", "can_transition", "make_proven", "make_refuted",
           "make_unbeaten", "parse", "serialize"]

KINDS = ("proven", "unbeaten", "refuted")


def make_proven(proof: str) -> dict[str, Any]:
    """A proof must be a non-empty machine-checkable reference, not a vibe."""
    if not (proof or "").strip():
        raise ValueError("proven requires a non-empty proof ref")
    return {"kind": "proven", "proof": proof.strip()}


def make_unbeaten(bound: float | int) -> dict[str, Any]:
    """``bound`` = the largest probe the fact survived; must be positive."""
    if not isinstance(bound, (int, float)) or isinstance(bound, bool) or bound <= 0:
        raise ValueError("unbeaten requires a positive numeric bound")
    return {"kind": "unbeaten", "bound": bound}


def make_refuted(counterexample: str) -> dict[str, Any]:
    """The counterexample is NAMED (the near-misses discipline: '144, 945',
    not 'a conflict was detected')."""
    if not (counterexample or "").strip():
        raise ValueError("refuted requires a named counterexample")
    return {"kind": "refuted", "counterexample": counterexample.strip()}


def parse(raw: str | None) -> dict[str, Any] | None:
    """Robust decode of a stored label; anything malformed -> None (unlabeled).
    Fail-open by design: a garbage label must never break recall."""
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or data.get("kind") not in KINDS:
        return None
    try:  # re-validate through the constructors so invariants hold on read too
        if data["kind"] == "proven":
            return make_proven(str(data.get("proof", "")))
        if data["kind"] == "unbeaten":
            return make_unbeaten(data.get("bound", 0))
        return make_refuted(str(data.get("counterexample", "")))
    except (ValueError, TypeError):
        return None


def serialize(label: dict[str, Any]) -> str:
    return json.dumps(label, sort_keys=True)


def can_transition(current: dict[str, Any] | None, new: dict[str, Any]) -> bool:
    """Monotone evidence rules — a transition must ADD information:

      None -> anything valid          (first labeling)
      unbeaten(b1) -> unbeaten(b2)    iff b2 > b1 (the bound grows, never shrinks)
      unbeaten -> proven | refuted    (upgrade / kill)
      proven -> proven | refuted      (new proof ref; or the honest reversal —
                                       a 'proof' can be found wrong)
      refuted -> refuted              (a different counterexample may replace)
      refuted -> proven | unbeaten    FORBIDDEN (absorbing)
      proven -> unbeaten              FORBIDDEN (silent downgrade; correct by
                                       supersession instead)
    """
    if new is None or new.get("kind") not in KINDS:
        return False
    if current is None:
        return True
    cur_k, new_k = current["kind"], new["kind"]
    if cur_k == "refuted":
        return new_k == "refuted"
    if cur_k == "proven":
        return new_k in ("proven", "refuted")
    # cur_k == "unbeaten"
    if new_k == "unbeaten":
        return new["bound"] > current["bound"]
    return True  # proven or refuted
