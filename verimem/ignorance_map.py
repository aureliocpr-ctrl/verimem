"""The ignorance map — "I don't know" upgraded to "here is WHAT I'm missing".

Vivarium P83 / cortex cognition, via the handoff: diagnosing WHICH
sub-competence is missing made acquiring it ~6.2× cheaper than blind
exploration, and the lab's ignorance map motivated all six of its world-bound
abstentions. Product incarnation: for each query the store cannot (or should
not) answer, name the ignorance CLASS and what would cure it —

  * ``no_evidence``       — nothing relevant in the store at all;
  * ``below_floor``       — hits exist but none clears the abstention floor τ
                            (the honest-uncertainty band);
  * ``quarantined_only``  — evidence EXISTS but every piece of it is
                            quarantined: the cure is a supporting source or a
                            quarantine review, not more retrieval;
  * ``conflict``          — live facts about the same subject disagree with no
                            epistemic winner: the cure is an independent
                            source or an audit;
  * ``answerable``        — not ignorance (counted for the honest denominator).

Read-only: the map never writes. It is the daemon's future work-list — every
class maps to a concrete acquisition action.
"""
from __future__ import annotations

import re
from typing import Any

from .composer import _copula_parse, subject_key

__all__ = ["ignorance_map"]

_WORD = re.compile(r"[a-zA-ZÀ-ɏ0-9]{3,}")
def _stopwords() -> frozenset[str]:
    """Le parole vuote del percorso LESSICALE, non una copia.

    Qui c'era una lista di 19 parole INGLESI — the, and, for, with, what,
    which, who, how, why, does, is, are, was, were, this, that, from, into,
    about — mentre `bm25_rank._QUERY_STOPWORDS` ne ha 104 EN+IT ed e' usata dal
    percorso lessicale dal 2026-07-07. Due copie divergono, e questa lo aveva
    gia' fatto: `_WORD` chiede 3+ caratteri, quindi «il»/«la»/«di» erano fuori
    da soli, ma le funzionali LUNGHE — della, per, con, del, alla, sul — che
    nessuna lista inglese puo' contenere passavano come parole di contenuto.

    Due danni misurati il 2026-08-02:

    1. `what_would_help` («a source about: …») elencava parole vuote: 5 termini
       su 31 in otto domande, TUTTI italiani; le inglesi uscivano pulite.
    2. Peggio, `_quarantined_overlap(min_shared=2)` decide la classe
       `quarantined_only` — «l'evidenza ESISTE ed e' in quarantena, la cura e'
       una fonte, non altro retrieval». Bastavano due funzionali condivise:

           'come si configura il backup della macchina per la produzione'
           vs «La ricetta della nonna per il pane e nel quaderno.»
              overlap 2 su ['della', 'per']  -> quarantined_only

       Le stesse frasi in inglese: overlap 0. Il prodotto mandava l'utente
       italiano a cercare una fonte per un fatto che parla di un gatto, e
       quello inglese no.

    L'unione e non la sostituzione: le 19 storiche restano anche se un domani
    la lista condivisa cambiasse, cosi' la cura non puo' togliere copertura.
    """
    from .bm25_rank import _QUERY_STOPWORDS
    return _STOP_STORICHE | _QUERY_STOPWORDS


_STOP_STORICHE = frozenset(
    "the and for with what which who how why does is are was "
    "were this that from into about".split())
_STOP = _stopwords()


def _keywords(text: str) -> set[str]:
    return {w.lower() for w in _WORD.findall(text or "")
            if w.lower() not in _STOP}


def _quarantined_overlap(semantic: Any, query: str, *, min_shared: int = 2) -> bool:
    """Does QUARANTINED evidence share >= min_shared content words with the
    query? Linear scan, declared v1 (the map is an offline diagnostic)."""
    qk = _keywords(query)
    if not qk:
        return False
    for fact in semantic.all():
        if fact.status != "quarantined":
            continue
        if len(qk & _keywords(fact.proposition)) >= min_shared:
            return True
    return False


def _classify(mem: Any, query: str, *, floor: float, k: int,
              noise_floor: float = 0.0) -> dict[str, Any]:
    hits = mem.search(query, k=k)
    top = hits[0].get("score", 0.0) if hits else None
    row: dict[str, Any] = {"query": query, "top_score": top}
    # CONFLICT dominates the floor: when the retrieved facts CONTRADICT each
    # other about one subject, that is the deepest reason the query is
    # unanswerable — a low top score is the symptom, not the diagnosis (the
    # compressed e5 band routinely puts real conflicts under τ).
    by_subject: dict[str, dict[str, list[str]]] = {}
    for h in hits:
        fact = mem.semantic.get(h.get("id", ""))
        if not fact:
            continue
        parsed = _copula_parse(fact.proposition)
        if not parsed:
            continue
        subj = subject_key(parsed[0])
        by_subject.setdefault(subj, {}).setdefault(parsed[1], []).append(fact.id)
    qk = _keywords(query)
    for subj, values in by_subject.items():
        # pertinence guard: an off-topic query can retrieve a conflicting pair
        # as mere nearest-neighbour noise — the conflict only explains THIS
        # query's ignorance if the disputed subject is what the query asks about
        if len(values) > 1 and (_keywords(subj) & qk):
            ids = [i for ids_ in values.values() for i in ids_]
            row.update({"class": "conflict", "conflicting_ids": ids,
                        "what_would_help": f"an independent source (or an "
                        f"audit) to resolve '{subj}' — "
                        f"{len(values)} live values disagree"})
            return row
    # LA SOGLIA CHE DECIDE e' il pavimento dichiarato, e basta.
    #
    # Per qualche ora e' stata `max(floor, noise_floor)`, ed era SBAGLIATO —
    # misurato sul corpus vero lo stesso giorno, 2026-07-30, prima di lasciarlo
    # in piedi: con quella regola SETTE domande su otto che il corpus sa
    # rispondere (il moat, il grounding score, le regole di scrittura, la
    # pubblicazione su PyPI...) uscivano come ignoranza, e le `answerable`
    # erano ZERO. Una mappa dell'ignoranza che dice «non lo so» su tutto e'
    # inutile quanto una che dice «lo so» su tutto.
    #
    # L'errore concettuale: `estimate_relevance_floor` e' il 95o percentile dei
    # MASSIMI di sonde scramblate, e su un corpus grande qualche sonda casuale
    # becca sempre qualcosa — quel numero e' alto per costruzione (0.87 sul
    # corpus vero) e NON e' «il livello sotto cui non c'e' informazione». Usarlo
    # come soglia di risposta taglia via i match semantici veri: una domanda che
    # RIFORMULA un fatto vale ~0.78, e sta sotto.
    #
    # Il difetto che aveva fatto nascere quella cura resta vero e va risolto
    # altrimenti: quando il top sta sotto il rumore misurato, la risposta si da'
    # ma CON L'AVVERTENZA (sotto), invece di essere dichiarata rispondibile
    # senza riserve.
    soglia = float(floor)
    row["deciding_floor"] = soglia
    if not hits or (top or 0.0) < soglia:
        if _quarantined_overlap(mem.semantic, query):
            row.update({"class": "quarantined_only",
                        "what_would_help": "evidence exists but is quarantined "
                        "— provide a supporting source or review the quarantine"})
        elif not hits or (top or 0.0) <= noise_floor:
            # A hit at or below the store's own NOISE ceiling is not weak
            # evidence, it is a nearest neighbour with nothing to say. Calling
            # it below_floor changes the prescription from "find a source on
            # this topic" to "get stronger evidence" — pointing the operator at
            # a fact that was never about the question (measured 2026-07-28:
            # fourteen facts about servers turned a weather query from
            # no_evidence into below_floor without adding a word about weather).
            row.update({"class": "no_evidence",
                        "what_would_help": "a source about: "
                        + ", ".join(sorted(_keywords(query))[:5])})
        else:
            quale = ("measured noise floor" if soglia > float(floor)
                     else "declared floor")
            row.update({"class": "below_floor",
                        "what_would_help": f"stronger evidence — best hit "
                        f"{top:.2f} sits under the {quale} {soglia:.2f}"})
        return row
    row.update({"class": "answerable", "what_would_help": None})
    # Il top supera il pavimento dichiarato ma sta sotto il RUMORE che lo store
    # ha misurato su se stesso: si risponde, e lo si dice. E' il difetto che
    # aveva fatto nascere (male) la soglia `max`: quella fascia usciva
    # `answerable` senza alcuna riserva, e per la misura dello store e' la zona
    # in cui un vicino qualsiasi vale quanto un match.
    if noise_floor and (top or 0.0) <= float(noise_floor):
        row["caveat"] = (
            f"best hit {top:.2f} sits at or below the store's own measured "
            f"noise level {float(noise_floor):.2f} — answerable, but this is "
            f"the band where a nearest neighbour scores like a real match")
    return row


def ignorance_map(mem: Any, queries: list[str], *, floor: float = 0.8,
                  k: int = 5, noise_floor: float | None = None) -> dict[str, Any]:
    """Classify every query; return ``{queries: [...], by_class: {...}}`` —
    every class counted, nothing silently dropped.

    ``noise_floor`` separates NOISE from weak evidence; None measures it from
    the store itself (``estimate_relevance_floor``: scrambled in-domain probes,
    0.0 when the store is too small to measure, in which case nothing changes).
    Estimated ONCE per call, not per query — it costs ~32 recalls. It is
    returned in the report because a number that decides a verdict has to be
    visible in it.
    """
    # WHERE the floor came from, because 0.0 means three different things and a
    # bare 0.0 in the report told them apart in none: the store was too small to
    # measure (estimate_relevance_floor's deliberate answer — a floor guessed
    # from nothing is worse than none), the measurement CRASHED, or the caller
    # asked for it. At 0.0 the noise guard is inert and every weak hit is
    # classified below_floor again, so an operator has to be able to tell a
    # disabled guard from a measured one.
    if noise_floor is not None:
        source = "caller"
    else:
        from .relevance_floor import estimate_relevance_floor
        try:
            noise_floor = estimate_relevance_floor(mem.semantic)
            source = "unmeasurable" if not noise_floor else "measured"
        except Exception:            # noqa: BLE001 — a diagnostic never crashes
            noise_floor = 0.0        # behave as before, but SAY so
            source = "failed"
    rows = [_classify(mem, q, floor=floor, k=k, noise_floor=noise_floor)
            for q in queries]
    by_class: dict[str, int] = {}
    for r in rows:
        by_class[r["class"]] = by_class.get(r["class"], 0) + 1
    return {"queries": rows, "by_class": by_class, "floor": floor,
            "noise_floor": noise_floor, "noise_floor_source": source,
            # Quale soglia ha deciso — resta esposta anche ora che coincide
            # col floor dichiarato: e' il numero che un lettore deve poter
            # verificare senza leggere il codice.
            "deciding_floor": float(floor),
            "n": len(rows)}
