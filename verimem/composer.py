"""The minimal composition loop — the ORGANISM ring inside the product.

From pairs of LIVE facts that share a pivot term, derive a NEW candidate by
DECLARED substitution (v1: the copula syllogism — "X is a Y." + "A Y is a Z."
-> "X is a Z."), push it through the SAME anti-confab gate as every other
writer (L4 source⊢fact entailment where the source is the two parents — the
composer has NO privileges: the gate that quarantined the organism's first
machine write guards this one too), and admit survivors:

  * SIGNED   — ``actor:composer:<run>`` in verified_by (P85: the engine's own
               writes never testify, never earn reputation);
  * TRACED   — ``derives_from=[parent_a, parent_b]`` (P78: the answer is a
               chain you can audit, and justified-memory can retract it if a
               parent falls);
  * LABELED  — ``epistemic = proven("qa:l4_entail_parents_score<NN>_PASS")``
               (the label names EXACTLY which machine check passed, nothing
               more — the coprime6 discipline).

Few-but-zero-false: a candidate the judge does not entail stays quarantined
(rehabilitable, visible in the ledger), never silently admitted. Generation is
pure substitution over declared patterns — zero unverified creativity; the
creative half (LLM conjectures) plugs in later behind the same gate.

Honest scope (v1): composes only where the corpus has copula structure —
world-bound by design; on a corpus of scattered notes it derives little and
says so in the report. No scheduling here: this is the RING; the nightly
daemon that calls it is a separate, later piece.
"""
from __future__ import annotations

import re
import uuid
from typing import Any

__all__ = ["compose_once", "_copula_parse"]

#: A DERIVED fact needs more than the gate's minimum: the unreadable-verdict
#: fallback is a non-committal 50, which PASSES the claude-scale write cut
#: (40) — so a dead judge would silently flood the store with unverified
#: compositions. The composer floor sits ABOVE the fallback: anything the
#: judge cannot positively entail (>= 55) is quarantined, never live.
#: Env override: ENGRAM_COMPOSER_MIN_SCORE.
_MIN_SCORE_DEFAULT = 55.0


def _min_score() -> float:
    import os
    try:
        return float(os.environ.get("ENGRAM_COMPOSER_MIN_SCORE",
                                    str(_MIN_SCORE_DEFAULT)))
    except ValueError:
        return _MIN_SCORE_DEFAULT

_ARTICLES = ("a", "an", "the")
#: leading words that mark a NON-noun-phrase object ("is in Rome", "is over")
_NON_NP_LEADS = frozenset(
    "in on at from to of for with by about over under near into onto as".split())

_COPULA_RE = re.compile(
    r"^(?P<s>[A-Za-z][\w\s\-']{0,60}?)\s+is\s+(?P<o>[A-Za-z][\w\s\-']{1,60}?)\s*\.$")


def _strip_article(np: str) -> str:
    words = np.strip().split()
    if words and words[0].lower() in _ARTICLES:
        words = words[1:]
    return " ".join(words)


def _copula_match(text: str) -> re.Match | None:
    m = _COPULA_RE.match((text or "").strip())
    if not m:
        return None
    obj_words = m.group("o").strip().split()
    if not obj_words or obj_words[0].lower() in _NON_NP_LEADS:
        return None                      # "is in Rome" — locative, not a class NP
    if not _strip_article(m.group("o")):
        return None                      # bare article, no head noun
    return m


def _copula_parse(text: str) -> tuple[str, str, str] | None:
    """``"Rex is a labrador."`` -> ``("rex", "labrador", "a labrador")`` —
    (subject lowered as written, object head lowered WITHOUT article, object
    lowered WITH its article). None for anything that is not a clean
    copula-over-noun-phrase sentence. Pure; the contract the tests pin."""
    m = _copula_match(text)
    if not m:
        return None
    return (m.group("s").strip().lower(),
            _strip_article(m.group("o")).lower(),
            m.group("o").strip().lower())


def compose_once(mem: Any, *, topic: str | None = None, run_id: str | None = None,
                 max_candidates: int = 50) -> dict[str, Any]:
    """One composition pass over the live store. Returns an honest report:
    ``{eligible, candidates, admitted, rejected_gate, skipped_known,
    admitted_ids}`` — every bound and every skip is counted, never silent."""
    run = run_id or uuid.uuid4().hex[:8]
    facts = [f for f in mem.semantic.all()
             if not f.superseded_by
             # Giro 2: 'user_belief' excluded — composing over an unverified
             # user assertion would LAUNDER it: the derived fact carries the
             # belief's content without its low-trust label (worse than
             # serving the belief itself, the origin disappears).
             and f.status not in ("quarantined", "orphaned", "user_belief")
             and not (f.epistemic or {}).get("kind") == "refuted"]
    # parse the copula facts once; keep the ORIGINAL casing for candidate text
    parsed = []
    for f in facts:
        m = _copula_match(f.proposition)
        if m:
            parsed.append((f, m))
    known = {" ".join(f.proposition.lower().split()) for f in facts}

    report = {"eligible": len(facts), "copula_facts": len(parsed),
              "candidates": 0, "admitted": 0, "rejected_gate": 0,
              "rejected_noncommittal": 0, "skipped_known": 0,
              "admitted_ids": [], "run_id": run}
    for a, ma in parsed:
        pivot_a = _strip_article(ma.group("o")).lower()
        for b, mb in parsed:
            if a.id == b.id:
                continue
            # a parent never composes with its own derivative (trivial loops)
            if a.id in (b.derives_from or []) or b.id in (a.derives_from or []):
                continue
            if _strip_article(mb.group("s")).lower() != pivot_a:
                continue
            subj_a = ma.group("s").strip()
            obj_b = mb.group("o").strip()
            if _strip_article(subj_a).lower() == _strip_article(obj_b).lower():
                continue                             # X is X — vacuous
            candidate = f"{subj_a} is {obj_b}."
            if report["candidates"] >= max_candidates:
                report["truncated"] = True           # bound declared, not silent
                return report
            report["candidates"] += 1
            if " ".join(candidate.lower().split()) in known:
                report["skipped_known"] += 1
                continue
            res = mem.add(
                candidate,
                topic=topic or a.topic or "derived",
                source=f"{a.proposition} {b.proposition}",
                ground=True,
                verified_by=[f"actor:composer:{run}"],
            )
            if not res.get("stored") or res.get("status") == "quarantined":
                report["rejected_gate"] += 1
                continue
            fid = res.get("id")
            gs = res.get("grounding_score")
            if gs is None or float(gs) < _min_score():
                # the judge did not POSITIVELY entail (None = never ran; ~50 =
                # the unreadable-verdict fallback): a derived fact does not go
                # live on a shrug — quarantine, rehabilitable, visible.
                try:
                    mem.semantic.quarantine_fact(
                        fid, reason=(f"composer: judge score "
                                     f"{gs if gs is not None else 'None'} below "
                                     f"floor {_min_score():.0f} — a derived "
                                     "fact needs positive entailment"))
                except Exception:  # noqa: BLE001 — best-effort demotion
                    pass
                report["rejected_noncommittal"] += 1
                continue
            mem.semantic.set_derives_from(fid, [a.id, b.id])
            from .epistemic import make_proven
            mem.semantic.set_epistemic(fid, make_proven(
                f"qa:l4_entail_parents_score{int(gs)}_PASS"))
            known.add(" ".join(candidate.lower().split()))
            report["admitted"] += 1
            report["admitted_ids"].append(fid)
    return report
