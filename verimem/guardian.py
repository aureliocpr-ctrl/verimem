"""Guardian at the read-path — ACCEPT / CORRECT / ABSTAIN (cortex transfer).

The cortex lab measured the pattern (guardian.correct: 0 false answers over
2000 queries, accuracy 0.507→0.844 on its rule world): when the store CONTAINS
a better-guaranteed truth, don't just block the wrong candidate — SERVE the
truth, with both sides cited. This is the product incarnation on copula facts:

  * ACCEPT   — the top hit stands (no rival on the same subject);
  * CORRECT  — a rival fact about the SAME subject carries a strictly better
               epistemic guarantee (proven > unbeaten > unlabeled; refuted is
               disqualified outright) → answer with the winner, cite both;
  * ABSTAIN  — a real conflict with no epistemic winner (never pick silently:
               the conflict is shown), or no support at all.

Scope, honest: subject matching is the composer's copula parse — the same
world-bound v1 as composition (no copula structure → the guardian simply
ACCEPTs like today's read-path). Refuted facts are never served, even when
recall ranks them first.

user_belief awareness (Giro 2 §3.4): the guardian is the ONE reader that opts
into beliefs (``include_beliefs=True``), because its job is to correct them —
an unverified USER assertion participates in conflict DETECTION but can never
WIN: a corroborated rival is served with the belief cited as ``uncorroborated``
("previously asserted, not corroborated"); a subject supported ONLY by beliefs
is an ABSTAIN, never an answer. Every verdict carries an ``uncorroborated``
list (empty when none) so callers get a stable schema.
"""
from __future__ import annotations

from typing import Any

from .composer import _copula_parse, subject_key
from .epistemic import guarantee_rank

__all__ = ["correct_read"]


def _rank(fact: Any) -> int:
    # epistemic.guarantee_rank, not a local table: the active probe compares the
    # same two facts and reached the OPPOSITE conclusion while this ordering
    # lived only here (2026-07-28). An unknown/foreign kind is UNLABELED there
    # too, never a KeyError on the read-path (audit mod.3).
    return guarantee_rank(getattr(fact, "epistemic", None))


def _is_belief(fact: Any) -> bool:
    return getattr(fact, "status", "") == "user_belief"


def _value(fact: Any) -> str:
    return (_copula_parse(fact.proposition) or ("", "", ""))[1]


def _risolvi_pavimento(mem: Any, min_relevance: float | str | None) -> tuple[float, bool]:
    """``(pavimento, chiesto_e_non_ottenuto)``.

    ``"auto"`` lo fa calcolare allo store (che lo tiene in cache: la stima costa
    ~32 sonde e non si paga per query).

    ⚠️ Il secondo valore esiste perché ZERO ha DUE significati che questa
    funzione restituiva identici, e il chiamante non poteva distinguerli:

        min_relevance=None / 0 / "off"   -> zero VOLUTO, il pavimento e' spento
        min_relevance="auto" -> 0.0      -> zero NON voluto: la calibrazione
                                            non ha prodotto una soglia

    Il secondo caso capita su un corpus troppo piccolo per calibrare —
    misurato: 1 fatto -> 0.0, 6 fatti -> 0.9166 — cioè **sul primo fatto di un
    tenant nuovo**, che è il primo momento di ogni cliente. Serviti identici,
    il guardiano non poteva sapere se stava rispettando una scelta o subendo
    una resa: `if pavimento > 0.0` saltava il controllo in entrambi i casi, e
    la misura scritta più sotto dice cosa comporta servire senza pavimento
    (10 risposte false su 10).

    Il ritorno resta un numero + un flag invece di ``None``: un pavimento
    assente e un pavimento nullo si comportano allo stesso modo, e cambiare il
    tipo avrebbe spostato la decisione su ogni sito di chiamata.
    """
    if min_relevance is None:
        return 0.0, False
    if min_relevance == "auto":
        try:
            calibrato = float(mem._auto_relevance_floor())
        except Exception:      # noqa: BLE001 — un read-path non cade mai per
            return 0.0, True   # colpa della calibrazione: si degrada a «off».
        return calibrato, calibrato <= 0.0
    try:
        return max(0.0, float(min_relevance)), False
    except (TypeError, ValueError):
        return 0.0, False


def correct_read(mem: Any, query: str, *, k: int = 5,
                 min_relevance: float | str | None = None) -> dict[str, Any]:
    """Come ``_correct_read``, e in più DICE quando il pavimento chiesto non c'era.

    ⚠️ Involucro invece di una riga dentro ciascun ``return``: la lettura
    guardata ha nove punti di uscita, e annotarli uno per uno lascia scoperto il
    decimo che nascerà. Qui la nota si aggiunge una volta sola, e vale anche per
    gli esiti che oggi non esistono.

    ``floor_note`` compare SOLO quando la risposta è stata servita senza il
    pavimento che era stato chiesto: su un'astensione non ha senso, perché nulla
    è stato servito.

    Quello che questa nota NON fa: scegliere una soglia. Su un corpus troppo
    piccolo per calibrarsi, servire troppo e astenersi troppo sono due prodotti
    diversi e la scelta non è tecnica. Ciò che era tecnico — e mancava — è che
    la risposta non distinguesse «pavimento spento» da «pavimento chiesto e non
    ottenuto»: al chiamante arrivavano identiche.
    """
    _, senza_calibrazione = _risolvi_pavimento(mem, min_relevance)
    esito = _correct_read(mem, query, k=k, min_relevance=min_relevance)
    if senza_calibrazione and esito.get("verdict") != "ABSTAIN":
        esito["floor_note"] = "relevance_floor_requested_but_uncalibrated"
    return esito


def _correct_read(mem: Any, query: str, *, k: int = 5,
                 min_relevance: float | str | None = None) -> dict[str, Any]:
    """One gated read with correction. Returns
    ``{verdict, answer, served_id, evidence, uncorroborated, reason}``.

    ``min_relevance`` is the abstention floor, forwarded to ``mem.search``:
    ``"auto"`` (the store self-calibrates), a float, or ``None`` for the old
    permissive behaviour.

    PERCHE' ESISTE (2026-08-04, trovato usando l'API HTTP da utente).
    Stesso store, stessa domanda senza risposta, tre rotte:

        GET /v1/search   2 hit, top «La riunione settimanale e' il martedi'» 0.8227
        GET /v1/explain  abstained=TRUE, n_facts=0
        GET /v1/correct  verdict=ACCEPT, answer=«La riunione ... alle 10.»
                         <- a una domanda sul LOGO aziendale

    Il retrieval era lo stesso: a mancare era il pavimento.
    ``min_relevance=_gateway_min_relevance()`` compariva UNA SOLA VOLTA in tutto
    ``gateway.py``, sulla rotta ``explain``, e qui non c'era nemmeno il
    parametro da passare. La rotta esplicitamente chiamata *guardian* era
    l'unica lettura che non applicava l'astensione che il prodotto vende — il
    docstring di ``_gateway_min_relevance`` la chiama «the point of a TRUST
    product».

    ⚠️ IL PAVIMENTO DECIDE SE SERVIRE, NON SE VEDERE — e la prima stesura di
    questa cura sbagliava proprio qui. Passarlo a ``mem.search`` sembrava la
    cosa ovvia e ha rotto ``test_correct_abstains_on_real_conflict``: quando
    due fatti si contraddicono, questo endpoint si astiene MOSTRANDO ENTRAMBI
    I LATI, e col filtro davanti al retrieval i due contendenti sparivano prima
    di essere visti. L'astensione restava, ma l'utente perdeva l'informazione
    piu' preziosa che il guardiano possa dargli: *ci sono due fatti in
    conflitto, eccoli*. Un'astensione cieca e una motivata non sono la stessa
    risposta.

    Quindi si recupera SENZA filtro e si controlla il punteggio migliore prima
    di servire: sotto il pavimento si abbandona con ``below_relevance_floor``,
    portandosi dietro gli id di cio' che c'era.

    Costo e beneficio, misurati su entrambe le popolazioni (10 domande
    con risposta, 10 senza): senza pavimento 10/10 servite e 10/10 false
    servite; con pavimento 9/10 servite e 0/10 false. Una risposta vera persa
    su dieci contro dieci risposte inventate bloccate su dieci.
    """
    hits = mem.search(query, k=k, include_beliefs=True)
    if not hits:
        return {"verdict": "ABSTAIN", "answer": None, "served_id": None,
                "evidence": [], "uncorroborated": [], "reason": "no_support"}
    pavimento, _ = _risolvi_pavimento(mem, min_relevance)
    if pavimento > 0.0:
        migliore = max((float(h.get("score") or 0.0) for h in hits), default=0.0)
        if migliore < pavimento:
            # C'era qualcosa, ma niente di abbastanza pertinente. Si dice cosa
            # c'era: un'astensione motivata vale piu' di una muta.
            return {"verdict": "ABSTAIN", "answer": None, "served_id": None,
                    "evidence": [h.get("id", "") for h in hits],
                    "uncorroborated": [], "reason": "below_relevance_floor"}
    facts = [f for f in (mem.semantic.get(h.get("id", "")) for h in hits) if f]
    if not facts:
        # hits existed but every row is gone (delete race): degrade to the
        # honest abstention — a read-path never crashes (audit mod.3).
        return {"verdict": "ABSTAIN", "answer": None, "served_id": None,
                "evidence": [], "uncorroborated": [], "reason": "no_support"}
    # group the copula facts by subject; non-copula hits pass through untouched.
    # The key is composer.subject_key — the SHARED definition of "same subject".
    # Grouping on the raw parse hid every conflict where the two sides spelled
    # the subject differently ("Rex" vs "The Rex"): the guardian ACCEPTed and
    # served an answer the active probe considered refuted (2026-07-28, banco 4).
    contenders: dict[str, list[Any]] = {}
    for f in facts:
        parsed = _copula_parse(f.proposition)
        if parsed:
            contenders.setdefault(subject_key(parsed[0]), []).append(f)

    top = facts[0]
    top_parsed = _copula_parse(top.proposition)
    rivals = contenders.get(subject_key(top_parsed[0]), [top]) if top_parsed else [top]
    # a refuted fact never gets served — drop it from contention entirely
    live = [f for f in rivals if _rank(f) >= 0] or []
    if not live:
        return {"verdict": "ABSTAIN", "answer": None, "served_id": None,
                "evidence": [f.id for f in rivals], "uncorroborated": [],
                "reason": "all_refuted"}

    # beliefs detect conflicts but never win; a beliefs-only subject abstains
    beliefs = [f for f in live if _is_belief(f)]
    servable = [f for f in live if not _is_belief(f)]
    if not servable:
        return {"verdict": "ABSTAIN", "answer": None, "served_id": None,
                "evidence": [f.id for f in rivals],
                "uncorroborated": [f.id for f in beliefs],
                "reason": "only_unverified_user_assertion"}

    values = {_value(f) for f in servable}
    if len(values) <= 1:                     # agreement (or single voice)
        winner = max(servable, key=_rank)
        overridden = [f for f in beliefs if _value(f) != _value(winner)]
        if overridden:
            # the sycophancy correction: the user asserted X, the store holds
            # a corroborated Y — serve Y, cite X as previously-asserted.
            return {"verdict": "CORRECT", "answer": winner.proposition,
                    "served_id": winner.id, "evidence": [f.id for f in rivals],
                    "uncorroborated": [f.id for f in overridden],
                    "reason": "user assertion not corroborated — "
                              "the corroborated fact wins"}
        # "unchallenged" is a CLAIM — the store holds nothing against this
        # answer — and the guardian may only make it where it could actually
        # look. Rivals are gathered through the copula parse, so a non-copula
        # top hit has no contenders to gather and the fact is returned alone.
        # Measured on the real corpus (2026-07-28): 0 of 4208 live facts are
        # copula (median proposition 814 chars of prose), so on real queries
        # this branch was answering "unchallenged" every time, through the
        # production endpoint, without ever having compared anything. The
        # verdict is unchanged — there is no better answer available — but the
        # two cases stop sharing one word.
        return {"verdict": "ACCEPT", "answer": winner.proposition,
                "served_id": winner.id, "evidence": [f.id for f in rivals],
                "uncorroborated": [],
                "reason": ("unchallenged" if top_parsed else
                           "served as-is: not comparable — no copula structure "
                           "to gather rivals by, so no conflict search ran")}

    # dominance is per-VALUE, not per-fact (audit mod.3): two proven facts
    # AGREEING on "labrador" must beat a lone unlabeled "poodle" — comparing
    # against the agreeing twin made MORE corroboration produce MORE
    # abstention. A value's guarantee is the best rank among its facts.
    by_value: dict[str, list[Any]] = {}
    for f in servable:
        by_value.setdefault(_value(f), []).append(f)
    value_rank = {v: max(_rank(f) for f in fs) for v, fs in by_value.items()}
    best_value = max(value_rank, key=value_rank.get)  # type: ignore[arg-type]
    best = max(by_value[best_value], key=_rank)
    uncorroborated = [f.id for f in beliefs if _value(f) != best_value]
    if all(value_rank[best_value] > r for v, r in value_rank.items()
           if v != best_value):
        # CORRECT whenever a real conflict was resolved by the label — never
        # dependent on which side recall happened to rank first (that order is
        # not deterministic w.r.t. content, the verdict must be).
        label = (best.epistemic or {}).get("kind", "unlabeled")
        return {"verdict": "CORRECT", "answer": best.proposition,
                "served_id": best.id, "evidence": [f.id for f in rivals],
                "uncorroborated": uncorroborated,
                "reason": f"conflict resolved by epistemic rank: {label} wins"}
    # a tie between conflicting guarantees is a REAL conflict — show, don't pick
    return {"verdict": "ABSTAIN", "answer": None, "served_id": None,
            "evidence": [f.id for f in live],
            "uncorroborated": [f.id for f in beliefs],
            "reason": "conflict_without_epistemic_winner"}
