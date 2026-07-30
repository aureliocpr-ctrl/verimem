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

__all__ = ["compose_once", "subject_key", "_copula_parse"]

#: A DERIVED fact needs more than the gate's minimum: the unreadable-verdict
#: fallback is a non-committal 50, which PASSES the claude-scale write cut
#: (40) — so a dead judge would silently flood the store with unverified
#: compositions. The composer floor sits ABOVE the fallback: anything the
#: judge cannot positively entail (>= 55) is quarantined, never live.
#: Env override: ENGRAM_COMPOSER_MIN_SCORE.
_MIN_SCORE_DEFAULT = 55.0


def _min_score() -> float:
    from .env_num import env_float
    return env_float("ENGRAM_COMPOSER_MIN_SCORE", _MIN_SCORE_DEFAULT)

#: Le QUATTRO LINGUE su cui il giudice del moat e' misurato (EN/IT/FR/ES). Fino
#: al 2026-07-30 la copula era ``\s+is\s+`` e basta: in italiano
#: ``_copula_parse`` restituiva None, quindi il guardian non vedeva MAI due
#: fatti come rivali e la contesa non veniva dichiarata da nessuna superficie.
#: Un prodotto che dichiara di giudicare in quattro lingue e riconosce
#: l'identita' del soggetto in una sola non protegge le altre tre.
#:
#: LA LINGUA LA DECIDE LA COPULA INCONTRATA, e ogni lingua porta i SUOI
#: articoli e le SUE preposizioni. Non e' pignoleria: «a» e' articolo in inglese
#: («is a labrador») e preposizione in italiano («e' a Roma»). Con le liste
#: mescolate, o si perde l'oggetto in inglese o si accetta un locativo italiano
#: come se fosse una classe — e un locativo scambiato per classe fa dichiarare
#: rivali due fatti che non lo sono.
_ARTICOLI_PER_LINGUA: dict[str, tuple[str, ...]] = {
    "en": ("a", "an", "the"),
    "it": ("il", "lo", "la", "i", "gli", "le", "un", "uno", "una"),
    "fr": ("le", "la", "les", "un", "une", "des"),
    "es": ("el", "la", "los", "las", "un", "una", "unos", "unas"),
}

#: parole che aprono un oggetto NON nominale ("is in Rome", "e' a Roma")
_NON_NP_PER_LINGUA: dict[str, frozenset[str]] = {
    "en": frozenset("in on at from to of for with by about over under near "
                    "into onto as".split()),
    "it": frozenset("in su a da di per con tra fra sotto sopra verso presso "
                    "dentro fuori".split()),
    "fr": frozenset("en sur a de du des dans pour avec par sous vers chez "
                    "entre".split()),
    "es": frozenset("en sobre a de del para con por bajo hacia entre desde "
                    "hasta".split()),
}

#: La copula -> la lingua. `est` prima di `es`, e `e'` prima di `es`: il regex
#: prova le alternative in ordine e la piu' lunga deve avere la precedenza.
_COPULE: dict[str, str] = {
    "is": "en", "è": "it", "e'": "it", "est": "fr", "es": "es",
}

#: Retrocompatibilita': l'inglese resta il default per chi importa il nome.
_ARTICLES = _ARTICOLI_PER_LINGUA["en"]
_NON_NP_LEADS = _NON_NP_PER_LINGUA["en"]

#: Tutti gli articoli, per ``subject_key``: li' la lingua non e' nota (si
#: normalizza un soggetto gia' estratto) e togliere un articolo di troppo e'
#: innocuo, mentre lasciarne uno fa divergere due chiavi che devono coincidere.
_ARTICOLI_TUTTI = frozenset(
    a for lista in _ARTICOLI_PER_LINGUA.values() for a in lista)

#: ``[^\W\d_]`` = una lettera qualsiasi, accenti compresi: con ``[A-Za-z]``
#: una frase che inizia per È o É non veniva nemmeno presa in esame.
_COPULA_RE = re.compile(
    r"^(?P<s>[^\W\d_][\w\s\-']{0,60}?)\s+(?P<c>is|est|è|e'|es)\s+"
    r"(?P<o>[^\W\d_][\w\s\-']{1,60}?)\s*\.$",
    re.UNICODE)


def _strip_article(np: str, lingua: str | None = None) -> str:
    """Toglie l'articolo iniziale. Con ``lingua`` usa SOLO gli articoli di
    quella lingua (l'oggetto di una copula: li' «a» inglese e «a» italiano
    vogliono trattamenti opposti); senza, usa l'unione — il caso di
    ``subject_key``, dove la lingua non e' nota."""
    words = np.strip().split()
    ammessi = (_ARTICOLI_PER_LINGUA.get(lingua, ()) if lingua
               else _ARTICOLI_TUTTI)
    if words and words[0].lower() in ammessi:
        words = words[1:]
    return " ".join(words)


def subject_key(subject: str) -> str:
    """The ONE definition of "the same subject", for every reader that groups
    rival facts — the guardian's conflict detection and the active probe's
    counter-evidence search.

    It existed twice and the copies disagreed (2026-07-28): the probe normalised
    the article, the guardian did not, so one store holding "Rex is a labrador."
    and "The Rex is a poodle." was a fatal contradiction for the probe (which
    applied its ABSORBING ``refuted``) and no contradiction at all for the
    guardian (which served "labrador" as unchallenged). The same evidence cannot
    be both. Subject identity is one question, so it gets one answer here.

    Deliberately shallow — article + case + surrounding space, the normalisation
    ``_copula_parse`` already performs on the OBJECT. It does not resolve
    pronouns, aliases or morphology: "Rexy" is not "Rex", and a reader must not
    infer that it is.
    """
    return _strip_article(subject or "").strip().lower()


def _copula_match(text: str) -> re.Match | None:
    m = _COPULA_RE.match((text or "").strip())
    if not m:
        return None
    lingua = _COPULE.get(m.group("c").lower(), "en")
    obj_words = m.group("o").strip().split()
    if not obj_words or obj_words[0].lower() in _NON_NP_PER_LINGUA[lingua]:
        return None                      # "is in Rome" / "e' a Roma" — locativo
    if not _strip_article(m.group("o"), lingua):
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
    lingua = _COPULE.get(m.group("c").lower(), "en")
    return (m.group("s").strip().lower(),
            _strip_article(m.group("o"), lingua).lower(),
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
            if subject_key(mb.group("s")) != pivot_a:   # the shared definition
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
