"""Cycle #138 (2026-05-18) — anti-confabulation gate on write.

Project decision (2026-05-18): the gate acts on WRITE. Wraps the L1 family
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

# 2026-07-28: relations a fact asserts and its source does not (cause, completed
# state, certainty, computed quantity). The CE scores these HIGH — every word of
# the source is there, only the link is invented — so they never fall in the
# escalation band and the judge that could read them is never asked.
from .evidence_hint import hint_for

# 2026-08-05: il router di provenienza, per lo sweep sui quattordici layer che
# vivono qui (finora era applicato solo ai tre detector in semantic.py).
from .gate_router import attribution_question as _gr_attribution_question
from .gate_router import classify_provenance as _gr_classify_provenance
from .gate_router import l1x_applies as _gr_l1x_applies

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

# 2026-08-04: la PORTATA di una negazione, in un modulo solo. Il lessico non e'
# qui ne' la' — resta `quantity_match._NEGATOR_RE`, undici lingue.
from .negation_scope import e_un_claim_negativo as _e_un_claim_negativo
from .negation_scope import tutte_le_occorrenze_sono_negate
from .relation_claim import unverified_relation

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


def _graded_admission() -> bool:
    """Env switch ``ENGRAM_GRADED_ADMISSION`` (DEFAULT OFF — design bf5d322
    step 1). When ON, a grounding SHORTFALL (CE/judge score below the write
    threshold, or the CE review band with no adjudicator) no longer hard-
    quarantines a write that DECLARED a source: the fact persists as a
    low-confidence model_claim and the receipt records the shortfall
    (``L4-grounding-graded`` / ``L4-review-graded`` — non-escalating layers).
    Quarantine stays reserved for injection and active contradiction, which
    escalate independently. Rationale (measured, HaluMem external A/B at the
    shipped cut 40): the hard reject loses 33% of CLEAN facts while noise
    rejection is achievable on the READ side by weighting low-conf items —
    the pre-registered A/B for that flip lives with the design doc."""
    v = os.environ.get("ENGRAM_GRADED_ADMISSION", "").strip().lower()
    return v in ("1", "true", "on", "yes", "enforce")


def _l1_domain_precision() -> bool:
    """Env ``ENGRAM_L1_DOMAIN_PRECISION`` — **DEFAULT ON** (flipped 2026-07-22 by
    project decision: cures ship ENABLED; explicit opt-out restores the legacy
    always-escalate via "0"/"false"/"off"/"no").

    When on, the L1 keyword escalation is suppressed PER FACT for propositions
    the subject classifier reads as third-party professional facts (see
    ``verimem.subject_extract.is_domain_professional``). Surgical alternative to
    the reverted global L1 flip (d15e4ca): an agent's own software self-claim
    STILL escalates — the carve-out is content-based, not a global disarm.
    Relaxes only L1; L3/L4/injection are untouched. Promotion gates that earned
    the flip: vertical corpus FP 86.7%→0.0%, critic claim_holds (8f6d0ec5 +
    cb26737b), 463-test blast, full suite 7704/0, flip-delta audit (numeric-head
    fail-safe closed pre-flip)."""
    v = os.environ.get("ENGRAM_L1_DOMAIN_PRECISION", "").strip().lower()
    return v not in ("0", "false", "off", "no")


def _is_domain_professional_fact(proposition: str) -> bool:
    """Thin, fail-soft wrapper: a classifier import/logic fault must never crash
    a write — it degrades to 'not domain' (L1 keeps escalating, the safe side)."""
    try:
        from .subject_extract import is_domain_professional
        return bool(is_domain_professional(proposition))
    except Exception:  # noqa: BLE001 — classifier must not break the gate
        return False


def advisory_eligible(warnings: Iterable[dict] | None) -> bool:
    """True iff EVERY warning is from the L1 lexical family.

    P0 evidence-before-belief relaxes a KEYWORD screen, never a semantic one:
    an outside witness does not dissolve a contradiction (L3) nor supply the
    entailment L4 failed to find. So independent evidence may only speak when
    L1 is the whole story — the invariant that keeps evidence-before-belief
    from degenerating into evidence-instead-of-belief.
    """
    ws = [w for w in (warnings or []) if isinstance(w, dict)]
    if not ws:
        return False
    return all(str(w.get("layer", "")).upper().startswith("L1") for w in ws)


def _p0_independence_enforced() -> bool:
    """ENGRAM_P0_INDEPENDENCE — DEFAULT OFF (observe-first).

    Off: the rule is evaluated and its verdict recorded on the receipt, but
    the outcome is byte-identical to before. On: independent evidence keeps
    an L1-only escalation advisory. The flip waits on a measured false-block
    delta, per the 0.8 method — no default changes on a hunch.
    """
    return os.environ.get("ENGRAM_P0_INDEPENDENCE", "").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _l1_domain_advisory() -> bool:
    """SERVER-SIDE, deployment-level switch (env ``ENGRAM_L1_DOMAIN_ADVISORY``,
    default OFF). When ON, the L1.x keyword anti-confabulation detectors run and
    surface their warnings but do NOT escalate to quarantine.

    Rationale (measured 2026-07-21: 86.7% of legitimate lawyer/engineer/
    clinician facts quarantined; design memos kimi+glm, verified on source):
    the L1.x family polices an AGENT confabulating about its OWN code work
    ('it works', 'deployed', 'tests pass'). A deployment that stores CUSTOMER
    domain facts has no such agent, so those detectors are category-error there.

    It is an ENV switch, NOT a per-write ``add()`` argument, on purpose: a
    per-write flag is ``writer_role`` without a token — spoofable by an injected
    prompt (the exact hole the trusted-hook bypass had to token-gate at
    :882). A deployment operator sets this once, server-side; a write payload
    can never assert it.

    SCOPE (verified 2026-07-21, kimi review): it relaxes ONLY the L1* keyword
    family — every ``startswith("L1")`` layer (bare L1, L1.5 diagnosis, L1.7
    task-state, L1.8–L1.21), all of which are keyword detectors. The L3
    (contradiction) and L4 (grounding) gates carry ``L3``/``L4`` labels that
    ``startswith("L1")`` does NOT match, so they stay fail-closed.

    DELIBERATELY UNCONDITIONAL (glm review a-1, resolved by measurement): the
    two neighbouring suppressors ``_personal_fp``/``_world_fp`` defer to
    ``_no_dev`` because they are per-fact CONTENT guesses. This one is an
    operator's DEPLOYMENT declaration — higher authority than a keyword guess,
    so it does NOT defer to ``_has_dev_context`` (measured: gating on it
    re-quarantines 3/30 legitimate engineering/clinical facts — 'tested to 400
    kilonewtons', 'the bridge was deployed' — because that heuristic is itself
    keyword-blind, the very disease this cures). The fail-open is bounded: an
    ungrounded dev self-claim in this mode still hits L4 when a grounding judge
    is configured (test_advisory_dev_claim_still_hits_L4_grounding)."""
    v = os.environ.get("ENGRAM_L1_DOMAIN_ADVISORY", "").strip().lower()
    return v in ("1", "true", "on", "yes")


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
    #: OLD facts a same-source EVOLUTION supersedes (ENGRAM_SUPERSEDE_SAME_SOURCE
    #: enforce): the new write is ADMITTED and these are retired — distinct from
    #: contradicting_fact_ids, which quarantines the NEW write. Empty by default. The
    #: caller must only act on these when ``action == "persist"`` (a new write
    #: quarantined for another reason must not retire the old value).
    supersede_fact_ids: list[str] = field(default_factory=list)
    advice: str = ""
    #: L4 source⊢fact entailment score (0-100) WHEN computed (source + grounding_llm +
    #: ENGRAM_GROUNDING_WRITE), else None. Previously discarded after the pass/fail
    #: decision; now surfaced so the caller can PERSIST it on the fact and condition
    #: retrieval/answering on it (the moonshot 2026-06-20: a write-time trust signal no
    #: competitor has). None = not computed (default fast path).
    grounding_score: float | None = None
    #: v17 (2026-08-08) LA PROVA della verifica: la porzione di `source` che
    #: sostiene la proposizione. `grounding_score` dice QUANTO, questa DA COSA.
    #: Prima della cura del fatto restava solo un'impronta sha256, quindi davanti
    #: a un voto 98 non si poteva piu' rivedere su cosa fosse stato dato.
    #: None quando non c'e' una fonte (e allora non c'e' nemmeno un punteggio).
    grounding_span: str | None = None
    #: judge-of-record: WHICH judge scored L4 ('local' CE, or 'claude'/
    #: 'interactive' injected llm), or None when no entailment judge ran.
    #: Surfaced so a provider swap is auditable, never a silent drift.
    judge: str | None = None
    #: the admission cut the score was compared to (judge-scale-consistent),
    #: or None when no numeric judge ran. score - threshold = the margin.
    threshold: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "warnings": list(self.warnings),
            "contradicting_fact_ids": list(self.contradicting_fact_ids),
            "supersede_fact_ids": list(self.supersede_fact_ids),
            "grounding_score": self.grounding_score,
            "judge": self.judge,
            "threshold": self.threshold,
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


def _semantic_conflict_mode() -> str:
    """Mode of the opt-in NLI semantic-contradiction moat (L3-semantic): one of
    ``"off"`` / ``"observe"`` / ``"enforce"`` from ``ENGRAM_SEMANTIC_CONFLICT``.

    - unset → **auto**: ``"enforce"`` iff the local NLI model is already
      installed (``local_relation.local_nli_available()``, filesystem-only);
      otherwise ``"off"`` — a fresh install without the model pays nothing.
    - 0 / off / false / no → ``"off"``: the detector is NOT called; the
      lexical default path (~13ms, no judge) is unchanged, zero cost.
    - observe / log / shadow → ``"observe"``: the detector runs (llm-free, on the
      local NLI cross-encoder when no ``agent.llm`` is present) and SURFACES a
      contradiction as an advisory warning, but does NOT quarantine the write — so
      the false-block rate is measurable on real tenants before enforcing (the same
      observe→enforce discipline as the CE band + source_trust).
    - 1 / on / true / yes / enforce → ``"enforce"``: a contradiction quarantines the
      write (downgrade), as before.
    """
    import os
    v = os.environ.get("ENGRAM_SEMANTIC_CONFLICT", "").strip().lower()
    if v in ("observe", "log", "shadow"):
        return "observe"
    if v in ("1", "on", "true", "yes", "enforce"):
        return "enforce"
    if v in ("0", "off", "false", "no"):
        return "off"
    # UNSET → AUTO (0.7.0): the tier enforces iff the local NLI model is
    # already installed (pure-filesystem check, no load) — shipped capability
    # = enabled capability. A fresh install without the model pays nothing.
    if v == "":
        from . import local_relation as _lr
        if _lr.local_nli_available():
            return "enforce"
    return "off"


def _semantic_conflict_on() -> bool:
    """Back-compat: the L3-semantic moat is active (observe OR enforce)."""
    return _semantic_conflict_mode() != "off"


def _l3_subject_filter() -> bool:
    """ENGRAM_L3_SUBJECT_FILTER — **DEFAULT ON** (flipped 2026-07-22 with the
    SAFE rule converged by GLM-5.2 + Kimi-K3): before the NLI judge, skip ONLY
    same-head + both-sided disjoint-modifier siblings (the measured FP class,
    'payments team' vs 'design team'). A head mismatch NEVER skips — it is the
    alias signature (35.2% FN measured on Wikidata altLabels with the naive
    different-subject skip, refuted by both external reviewers as an
    attacker-steerable poisoning vector). "0"/"false"/"off"/"no" opts out to
    the unfiltered judge."""
    import os
    v = os.environ.get("ENGRAM_L3_SUBJECT_FILTER", "").strip().lower()
    return v not in ("0", "false", "off", "no")


def _puo_essere_una_evoluzione(nuovo: str, vecchio: str) -> bool:
    """Due fatti possono essere l'uno l'aggiornamento dell'altro?

    LA TERZA GUARDIA, misurata su data dir VERGINE con dieci fatti veri e
    scorrelati scritti dall'SDK senza un flag: **sei ritirati su dieci**, a
    catena — ogni fatto che porta un numero mangiava il precedente::

        RITIRATO ... Il grafo delle entita contiene 8625 nodi.
        RITIRATO ... La quarantena trattiene 528 fatti.
        RITIRATO ... Il repository ha 113 commit fuori da main.
        RITIRATO ... La CLI espone 24 comandi.
        RITIRATO ... Il corpus contiene 6682 fatti.
        RITIRATO ... La prima fetta della suite ha riportato 2698 passed.

    Chi scrive dieci misure ne ritrova quattro, in silenzio: il recall non
    serve piu' i ritirati e `Memory.get()` non espone nemmeno `superseded_by`.

    LA CLASSE ERA GIA' NOTA QUI, per un caso particolare. `both_machine_checked`
    nacque da nove relazioni OEIS e la descrive cosi': «two DISTINCT true
    properties of the same sequences read as "same subject, different
    numbers"». E' questo difetto — ma quella guardia protegge solo chi porta un
    `verified_by` deterministico, cioe' nessuno di chi scrive dall'SDK.

    IL CRITERIO, senza soglie e senza modelli: i nomi e i numeri dicono DI COSA
    si parla, le altre parole dicono COSA se ne dice. Due frasi che non
    condividono NESSUNA parola di contenuto non asseriscono la stessa
    grandezza, quindi la seconda non puo' essere un valore nuovo della prima.
    Misurato su dodici coppie prima di scrivere una riga:

        sei finte (ritirate davvero) -> 0 parole condivise, tutte e sei
        sei evoluzioni legittime     -> da 3 a 5 parole condivise, tutte e sei

    Restringe cosa puo' CHIAMARSI evoluzione: non tocca il knob, non promuove
    nessuno stato, non rende nulla immune. Un testo vuoto non da' opinione —
    decidono gli strati che c'erano gia'.

    DUE CONDIZIONI IN OR, e nessuna delle due regge da sola — misurato su 18
    coppie, comprese tre evoluzioni legittime scritte con un complemento in
    apertura::

        una sola parola condivisa   -> 1 sbagliata (basta «fatti», generica
                                       in un prodotto che parla di fatti)
        sola testa nominale         -> 3 sbagliate sulle evoluzioni VERE
                                       («Nel piano annuale il prezzo e' 100»)
        testa OPPURE >= 2 parole    -> 0 sbagliate su 18

    Il DUE non e' una soglia scelta: e' «piu' di una», cioe' la differenza fra
    un incrocio e una coincidenza. `_copula_parse` sarebbe stata la strada
    esatta e non e' percorribile: su questo corpus restituisce None ovunque
    (5 frasi copulari su 4854).

    IL LIMITE CHE RESTA, e mi e' capitato addosso mentre scrivevo questa
    funzione: due misure DIVERSE dello stesso soggetto — un conteggio e una
    mediana, stessa fonte, scritte a due secondi di distanza — hanno la stessa
    testa e molte parole in comune, e la seconda ha ritirato la prima. Per
    separarle serve sapere QUALE grandezza si misura, non quali parole si
    usano. Nessuna delle due condizioni qui lo sa.
    """
    from .validate_claim import (
        _SOGLIA_SIMILARITA,
        _parole_di_contenuto,
        _polarita,
        _testa_nominale,
        leggibile_a_maiuscole,
        similarita_semantica,
    )

    if not (nuovo or "").strip() or not (vecchio or "").strip():
        return True
    # SE IL CRITERIO NON SA LEGGERE LA FRASE, NON DECIDE. Riconoscere i nomi
    # propri dalla maiuscola e' una convenzione tipografica e non e'
    # universale: in tedesco ogni sostantivo e' maiuscolo, quindi finiscono
    # tutti fra i nomi e cio' che resta come «contenuto» e' scarto
    # grammaticale — misurato, «Der Server ist ein Produktionsknoten» e «Die
    # Datenbank ist ein Postgres Cluster» danno entrambe ['ein','ist'] e testa
    # 'ist', e questa funzione rispondeva True. Due fatti scorrelati, il
    # secondo ritirava il primo, e chi scrive dieci misure ne ritrovava una.
    # E DOVE LE LISTE NON LEGGONO, DECIDE IL MODELLO CHE PARLA CENTO LINGUE.
    # Tacere era meglio che sbagliare e restava un servizio in meno: due fatti
    # tedeschi che SONO l'uno l'aggiornamento dell'altro rimanevano separati
    # per sempre. `intfloat/multilingual-e5-base` e' gia' installato e gia' in
    # uso — sul corpus reale tutti i 6972 fatti hanno il vettore
    # persistito — quindi il confronto e' un coseno, senza liste da scrivere.
    # Soglia MISURATA su dodici coppie in de/pt/pl/tr: vere 0.9349-0.9682,
    # false 0.8121-0.8674. Il fast-path lessicale resta primo: l'italiano e
    # l'inglese non pagano un encode, ed e' su quel comportamento che gira
    # tutto il corpus.
    if not (leggibile_a_maiuscole(nuovo) and leggibile_a_maiuscole(vecchio)):
        return similarita_semantica(nuovo, vecchio) >= _SOGLIA_SIMILARITA
    # POLARITA' DIVERSA, NESSUNA EVOLUZIONE. Una frase e la sua negazione
    # hanno le stesse parole di contenuto e la stessa testa nominale —
    # verificato: «Il gate NON gira sul canale MCP» e «Il gate gira sul canale
    # MCP» danno entrambe ['canale','gate','gira','sul'] e testa «gate» —
    # quindi per le due condizioni qui sotto sono lo stesso fatto aggiornato,
    # e la seconda ritira la prima mentre dice il CONTRARIO.
    # La causa e' che «non» sta fra le parole vuote (per l'italiano soltanto:
    # `not`, `no`, `mai`, `senza`, `never`, `without` no). Rimetterle nel
    # conteggio e' stato provato e misurato PEGGIORE — 228 -> 229 evoluzioni
    # sulle 260 coppie corte, e la coppia in piu' e' un falso positivo — quindi
    # la negazione si confronta come POLARITA', dove non gonfia nessuna
    # intersezione.
    if _polarita(nuovo) != _polarita(vecchio):
        return False
    a = _parole_di_contenuto(nuovo)
    b = _parole_di_contenuto(vecchio)
    if not a or not b:
        return True
    testa = _testa_nominale(nuovo)
    if testa and testa == _testa_nominale(vecchio):
        return True
    # IL CONTEGGIO BASTA SULLE FRASI CORTE, NON SULLA PROSA. Le dodici coppie
    # con cui `>= 2` fu misurato (sopra) sono frasi brevi: fra 0 parole
    # condivise delle finte e 3-5 delle vere, due sta comodo. Ma il corpus e'
    # fatto di prosa, e due prose da 800 caratteri condividono due parole per
    # caso. Misurato 2026-08-03 su un campione di 200 fatti:
    #
    #     prosa lunga (>400 char)  4005 coppie  1830 «puo' essere» (45.7%)
    #                              quota condivisa mediana 0.0588
    #     frasi corte (<=200)       528 coppie    94 «puo' essere» (17.8%)
    #                              quota condivisa mediana 0.8000
    #
    # Quasi una coppia di prose su due passava, condividendo il 5.9% delle
    # proprie parole: un ordine di grandezza sotto le frasi corte per cui il
    # criterio era tarato. Esempi veri presi dal corpus, quota 0.026:
    # «reale»+«strutturale» fra un fatto su quantity_match e uno su una
    # architettura a spazio di stati; «loop»+«reali» fra un selftest di driver
    # e un bench MMLU. Il vecchio veniva RITIRATO.
    #
    # Le evoluzioni che i test presidiano stanno a quota 0.667-1.000, quindi
    # la soglia 0.15 gia' misurata in `quantity_match._shared_enough` (stessa
    # famiglia, stessa env) sta in mezzo con margine da entrambi i lati. Si
    # RIUSA quella: una superficie sola, una sola manopola.
    #
    # Il conteggio resta ACCANTO al rapporto e non viene sostituito: sulle
    # frasi corte e' lui a lavorare, ed e' misurato.
    from .quantity_match import _shared_enough
    return len(a & b) >= 2 and _shared_enough(a, b)


def _supersede_same_source_on() -> bool:
    """When a clash is a same-source EVOLUTION (the source restating its own value with a
    newer valid-time), ADMIT the new write and retire the OLD — instead of quarantining
    the new. **Default ON (2026-07-19):** evolving memory that retires a stale same-source
    value is the product's core promise, not an opt-in.

    Safety without source authentication (verimem has none — ``verified_by`` is caller-
    controlled, even the ``actor:`` prefix is a bare string): (a) the TENANCY isolation
    boundary blocks cross-tenant writes; (b) cross-source clashes never reach this path
    (they classify as 'conflict' → quarantined, not superseded), so the griefing surface
    is intra-tenant only; (c) a single-agent-per-tenant assumption (the sole agent
    superseding its OWN values is the intended feature) holds for the common deployment.
    A multi-agent-per-tenant deployment that cannot trust its own writers sets
    ``ENGRAM_SUPERSEDE_SAME_SOURCE=0`` until per-agent auth (the intra-tenant gap) ships.

    OPEN RISK (independent red-team audit, 2026-07-20): the architecture-A thin tier
    makes assumption (c) FALSE BY CONSTRUCTION where it is used — N agent sessions behind
    one shared server authenticate with ONE tenant key, so they are many writers in one
    tenant, and a single compromised session can retire another's true values (spoofable
    ``verified_by`` + caller-controlled ``asserted_at`` → same-source "evolution"). The
    default is deliberately left ON pending an explicit product decision; a shared-server
    deployment that cannot trust every session sets ``ENGRAM_SUPERSEDE_SAME_SOURCE=0``.
    Documented rather than silently flipped: changing a shipped default is a product
    call, not an audit side effect."""
    import os
    _explicit = os.environ.get("ENGRAM_SUPERSEDE_SAME_SOURCE")
    if _explicit is not None and _explicit.strip() != "":
        # An operator who knows their writers stays in control, both ways.
        return _explicit.strip().lower() not in ("0", "off", "false", "no")
    # No explicit setting: the default FOLLOWS the assumption it rests on.
    # A shared server (architecture A) has N agent sessions behind ONE tenant
    # key -> many writers in one tenant -> premise (c) is false by
    # construction, so the safe default THERE is off. An embedded
    # single-agent store keeps it on: retiring its own stale value is the
    # product's core promise, and the sole writer cannot grief itself.
    _shared = os.environ.get("VERIMEM_MULTI_WRITER", "").strip().lower()
    if _shared not in ("", "0", "off", "false", "no"):
        return False
    return True


def _route_evolutions(agent: Any, verified_by: Any, asserted_at: float | None,
                      ids: list[str], supersede_ids: list[str],
                      new_status: str | None = None,
                      claimant: str | None = None,
                      proposition: str | None = None) -> list[str]:
    """Partition contradicting OLD fact ids into EVOLUTIONS (same canonical source +
    later valid-time + at least as trusted → appended to ``supersede_ids``, retired) and
    genuine CONFLICTS (returned, to quarantine the new write). This gives contradictions
    caught by the LEXICAL L3 (numeric / version / date — the most common evolutions) the
    same handling as the NLI layer. Fetches each old fact from the agent's store.

    RANK FLOOR (anti-confab): a weaker new write never supersedes a STRONGER old one — an
    unverified ``model_claim`` contradicting a ``verified`` fact is a suspect
    confabulation, not an evolution, so it stays a CONFLICT (quarantined), protecting the
    verified fact. Any miss OR a cross-source clash also stays a conflict (griefing guard)."""
    import time as _t
    import types as _ty

    from .semantic import _STATUS_RANK
    from .supersession_policy import classify_write_relation
    sm = getattr(agent, "semantic", None) if agent is not None else None
    if sm is None:
        return list(ids)
    # ⚠️ IL CANDIDATO PORTAVA TRE CAMPI, E CHI LO GIUDICA NE LEGGE DI PIU'.
    # `writer_principal` mancava, quindi il cancello sull'identita' di chi
    # scrive — che `is_same_source` interroga — vedeva sempre `None` su questo
    # lato e non poteva scattare MAI. Il valore c'era gia' e arrivava fin qui
    # accanto: `run_validation_gate` lo riceve come `claimant`, la porta SDK lo
    # passa (`claimant=principal or self._principal`, client.py:293) e si
    # fermava una chiamata prima.
    #
    # Il costo di non passarlo, misurato sul multi-utente: in una
    # memoria di team il fatto di bruno ARCHIVIA quello di anna, e anna che
    # chiede del proprio magazzino riceve quello di un collega.
    #
    # 🔑 E' anche il caso di scuola del perche' una cura si misura END-TO-END:
    # con `is_same_source` gia' corretta e venti test verdi, il banco end-to-end
    # restava a «1 vivo su 2» — la funzione sapeva distinguere, il chiamante non
    # le passava di che.
    cand = _ty.SimpleNamespace(verified_by=verified_by, created_at=_t.time(),
                               asserted_at=asserted_at,
                               writer_principal=claimant,
                               proposition=proposition or "")
    _nr = _STATUS_RANK.get(new_status or "model_claim", 2)
    conflicts: list[str] = []
    for cid in ids:
        # NO reference guard on THIS path, deliberately. Adversarial review
        # 2026-07-25 (glm-5.2 + deepseek-v4-pro, convergent 2/2): applying it here
        # broke the legitimate case — "CORREZIONE del fatto X: il valore e' 200"
        # against a stored "il valore e' 100" names X, so the guard kept the stale
        # 100 alive beside its own correction. This path's conflicts are found by
        # the DETERMINISTIC detectors (year-disjoint, numeric, version, date,
        # negation); when one of those fires there IS a concrete clash and citing
        # an id must not excuse it. The guard belongs only where the judgement is
        # a model's opinion — see the semantic path below.
        try:
            old = sm.get(cid)
        except Exception:  # noqa: BLE001 — a lookup miss is treated as a conflict
            old = None
        # ⚠️ LA TERZA USCITA: COESISTENZA. Fino al 2026-08-05 questo ciclo ne
        # aveva DUE, e perdono entrambe:
        #     evolution -> ritira il VECCHIO      conflict -> quarantina il NUOVO
        # Nessuna tiene in vita tutti e due, quindi qualunque criterio messo qui
        # dentro sceglie soltanto CHI perde. E' il motivo per cui otto criteri su
        # otto erano caduti nel distinguere un catalogo da un aggiornamento:
        # non sbagliavano la soglia, rispondevano a una domanda le cui due
        # risposte sono entrambe una perdita.
        #
        # Misurato sul caso reale (due colleghi, due magazzini diversi):
        #     senza l'identita'   anna ARCHIVIATO · bruno vivo        1 vivo su 2
        #     con l'identita'     anna vivo · bruno QUARANTINED       1 vivo su 2
        # La perdita si sposta e non sparisce — lo stesso esito della cura sulla
        # «capienza uno», ritirata perche' cambiava il NOME della perdita.
        #
        # DUE AUTORI DICHIARATI E DIVERSI NON SI RITIRANO A VICENDA: nessuno dei
        # due e' la versione aggiornata dell'altro, e il disaccordo fra due
        # persone e' un DATO, non un errore da risolvere cancellando. Restano
        # entrambi vivi e `recall` li serve entrambi, quindi il disaccordo e'
        # visibile per costruzione.
        #
        # ⚠️ IL PERIMETRO E' STRETTO E VOLUTO: serve che ENTRAMBI dichiarino
        # un'identita' non anonima. Sul corpus di casa i quattro principal sono
        # tutti anonimi (`cli:local`, `mcp:unbound`, `sdk:local`, NULL), quindi
        # qui non cambia una virgola; morde solo in una memoria multi-utente.
        if old is not None and _entita_diverse(cand, old):
            continue
        if (old is not None
                and classify_write_relation(cand, old) == "evolution"
                and _STATUS_RANK.get(getattr(old, "status", "model_claim"), 2) <= _nr):
            if cid not in supersede_ids:
                supersede_ids.append(cid)
        else:
            conflicts.append(cid)
    return conflicts


#: Parole che introducono un RECORD: il numero che le segue è un'ETICHETTA
#: (quale issue, quale porta, quale riga), non una grandezza che può cambiare.
#: La lista è LESSICALE e il suo limite è dichiarato: copre le parole dei casi
#: misurati, non l'italiano e l'inglese interi. Estenderla è additivo — ogni
#: voce nuova va aggiunta con il suo caso in
#: ``tests/test_everyday_memory_survives.py``.
_ETICHETTE_RECORD = frozenset({
    "issue", "ticket", "message", "msg", "porta", "port", "riga", "line",
    "day", "giorno", "pr", "build", "run", "pid", "record", "slot", "task",
})

#: ``<parola> <intero>`` dove l'intero è SEMPLICE: il lookahead scarta
#: ``versione 0.7.0`` e ``porta 8080.5``, che non sono etichette di record.
_ETICHETTA_NUM_RE = re.compile(
    r"\b([A-Za-zÀ-ÿ]+)\s+(\d+)\b(?!\s*[.,]\d)(?![.\-]\d)")


def _record_numerati(testo: str) -> dict[str, set[str]]:
    """``{etichetta: {numeri}}`` per le sole parole di :data:`_ETICHETTE_RECORD`."""
    out: dict[str, set[str]] = {}
    for parola, numero in _ETICHETTA_NUM_RE.findall(testo or ""):
        chiave = parola.casefold()
        if chiave in _ETICHETTE_RECORD:
            out.setdefault(chiave, set()).add(numero)
    return out


def _record_numerati_diversi(pa: str, pb: str) -> bool:
    """Le due frasi numerano lo STESSO tipo di record con numeri DISGIUNTI.

    «issue 41 … » contro «issue 42 … »: identiche in tutto tranne l'etichetta,
    quindi parlano di due record, non di un valore che si aggiorna. È lo stesso
    argomento del ramo DATE qui sopra — *un registro non è un valore che si
    aggiorna, è una serie* — applicato al numero che identifica la riga del
    registro invece che al giorno.

    ⚠️ SERVE L'ETICHETTA SU ENTRAMBI I LATI, come per i codici: con una sola
    non si sa nulla e il comportamento resta quello di prima. E i numeri devono
    essere DISGIUNTI su OGNI etichetta condivisa — «issue 41 è aperta» contro
    «issue 41 è chiusa» è lo stesso record, e lì il secondo aggiorna il primo.

    ⛔ IL LIMITE, dichiarato: un intero preceduto da una parola non in elenco
    resta invisibile a questo asse (`sprint 3`, `lotto 7`). Non è un difetto
    silenzioso — è il comportamento di prima, e si allarga aggiungendo la parola
    con il suo caso di prova.
    """
    ea, eb = _record_numerati(pa), _record_numerati(pb)
    comuni = set(ea) & set(eb)
    return bool(comuni) and all(not (ea[k] & eb[k]) for k in comuni)


def _entita_diverse(a: Any, b: Any) -> bool:
    """I due fatti nominano record DIVERSI: non c'è un codice in comune.

    ⚠️ QUESTO ASSE HA SOSTITUITO QUELLO DELL'AUTORE, e la ragione è una
    regressione misurata sulla cura precedente, poche ore dopo:

        caso                        vivi  atteso  esito
        un autore,  due entità        1      2    ✗  il buco storico
        due autori, due entità        2      2    ✅ la cura sull'autore
        un autore,  aggiornamento     1      1    ✅ presidio
        due autori, aggiornamento     2      1    🔴 REGRESSIONE

    anna scrive «Il paziente Rossi pesa 70 chilogrammi», bruno corregge «78», e
    con l'asse autore restavano vivi ENTRAMBI: in un'organizzazione la
    correzione di un collega smetteva di sovrascrivere il dato sbagliato — il
    caso più comune che esista.

    🔑 «Autori diversi» non implica «cose diverse». Due persone che parlano
    dello STESSO paziente parlano della stessa cosa: l'autore era un proxy
    debole per l'asse che conta davvero, cioè L'ENTITÀ.

    ⚠️ E SO PERCHÉ QUESTO CRITERIO PUÒ REGGERE OGGI, mentre il 2026-08-04 era
    stato scritto, misurato e RITIRATO (`test_venticinque_schede_un_fatto_vivo`,
    xfail strict): allora l'unica alternativa a `evolution` era `conflict`,
    cioè la QUARANTENA, e la perdita cambiava solo nome. Oggi c'è la terza
    uscita — coesistenza, né ritiro né quarantena — che allora non esisteva.
    La stessa cura su una manopola con una posizione in più.

    Servono i codici su ENTRAMBI i lati: con un codice su un lato solo non si
    sa nulla e il comportamento resta quello di prima. È lo stesso principio
    del presidio in `hidden_records`.

    🔑 E DAL 2026-08-05 NON SOLO I CODICI: anche LE ENTITÀ DEL GRAFO, ed è così
    che si è chiusa LA CELLA 6 — «un autore, due entità SENZA codice»
    (Rossi/Bianchi), il buco storico su cui erano caduti SEI criteri lessicali
    in una notte (i nomi propri via `_CAPS_RE`, l'ancoraggio, l'allargamento di
    `codes_in` alla coda alfabetica).

    La risposta era in casa dal principio, ed e' emersa misurando::

        «DC-Nord e DC-Sud il prodotto li distingue GIÀ, senza nessun criterio
         lessicale: il grafo li estrae come due entità [proper] separate, nello
         stesso add() che archivia il fatto.»

    `extract_entities_lite` è la funzione che alimenta il grafo
    (`semantic.py:3101`) ed è PURA: chiamarla qui usa la stessa superficie, non
    una copia che divergerà.

    ⚠️ SI CONFRONTANO I `proper`, NON TUTTE LE ENTITÀ, e senza questo la cura
    non funzionerebbe sul caso che l'ha motivata::

        DC-Nord -> [{'DC','acronym'}, {'Nord','proper'}]
        DC-Sud  -> [{'DC','acronym'}, {'Sud','proper'}]

    condividono l'acronimo `DC`. Un ACRONIMO è un TIPO di cosa (`GB`, `RAM`,
    `DC`), un `proper` è un'ISTANZA — ed è l'istanza che distingue due record.
    Lo stesso motivo per cui «Il server ha 64 GB di RAM» e «…128 GB…» NON
    devono coesistere: condividono `GB` e `RAM`, che sono tipi, e non hanno
    nessun proper che li distingua.

    I numeri sulle 104 coppie ordinarie del corpus vero::

        42 entità CONDIVISE        -> il veto lascia passare  (il presidio)
        31 DISGIUNTE               -> il veto salva           (il buco chiuso)
        31 senza entità da un lato -> non coperto             (comportamento vecchio)
    """
    from .entity_extract_lite import extract_entities_lite
    from .hidden_records import codes_in
    from .temporal_context import date_menzionate

    pa = getattr(a, "proposition", "") or ""
    pb = getattr(b, "proposition", "") or ""
    ca, cb = codes_in(pa), codes_in(pb)
    if ca and cb and not (ca & cb):
        return True
    # LA DATA DISTINGUE DUE EVENTI, e questo ramo toglie all'inglese un
    # privilegio che aveva per accidente ortografico. Misurato scrivendo tre
    # consegne in tre date, stesso topic:
    #     ISO «2026-03-12/04-20/05-30»            scritti 3 -> VIVI 1
    #     mese IT «12 marzo/20 aprile/30 maggio»  scritti 3 -> VIVI 1
    #     mese EN «12 March/20 April/30 May»      scritti 3 -> VIVI 3
    # I tre inglesi sopravvivevano perche' `March`/`April` sono MAIUSCOLI e
    # finiscono fra i `proper` qui sotto; `marzo`/`aprile` no, e una data ISO
    # non ha nemmeno una parola. Un registro di consegne non e' un valore che
    # si aggiorna: e' una serie di eventi, e perderne due e' perdere il
    # registro (il nodo «catalogare tre cose ne perde due»).
    # ⚠️ Solo date DIVERSE: con la stessa data si parla dello stesso momento e
    # un valore nuovo lo aggiorna, altrimenti «avere una data» diventerebbe un
    # lasciapassare per non essere mai superseduti.
    da, db = date_menzionate(pa), date_menzionate(pb)
    if da and db and not (da & db):
        return True
    # IL NUMERO CHE IDENTIFICA LA RIGA DI UN REGISTRO, gemello del ramo DATE:
    # «issue 41» / «issue 42» sono due record, non un valore aggiornato. Sei
    # casi d'uso ordinari cadevano qui — issue, message, porta, day, riga —
    # e nessuno dei quattro assi precedenti li vede: un numero non è un codice,
    # non è una data, e `41` non è un `proper`.
    if _record_numerati_diversi(pa, pb):
        return True

    def _proper(testo: str) -> set[str]:
        return {e["name"].casefold() for e in extract_entities_lite(testo)
                if e.get("type") == "proper"}

    ea, eb = _proper(pa), _proper(pb)
    return bool(ea and eb and not (ea & eb))


#: statuses that are OUT of trusted recall — a new write must NOT be flagged as
#: contradicting one of these (it was already retired), and they must not cost a
#: judge call. Mirrors SemanticMemory.live_topic_siblings' SQL exclusion set.
_NON_LIVE_STATUSES = frozenset({"orphaned", "quarantined", "user_belief"})


def _live_topic_siblings(sm: Any, topic: str | None, *, limit: int = 200) -> list:
    """Same-topic, LIVE facts to compare a new write against for semantic
    contradiction. Prefer the store's indexed ``live_topic_siblings`` (bounded SQL);
    fall back to scanning ``all()`` for duck-typed / older stores, applying the SAME
    exclusions in memory. Excluding already-superseded / quarantined facts is
    correctness (a contradiction against a retired value is a false positive); using
    the indexed query is what keeps the opt-in moat off the O(store) ``all()`` path."""
    t = topic or ""
    getter = getattr(sm, "live_topic_siblings", None)
    if callable(getter):
        try:
            return list(getter(t, limit=limit))
        except Exception:  # noqa: BLE001 — any store error → fall back to the scan
            pass
    out: list = []
    for f in sm.all():
        if getattr(f, "topic", None) != t:
            continue
        if getattr(f, "superseded_by", None):
            continue
        if getattr(f, "status", None) in _NON_LIVE_STATUSES:
            continue
        out.append(f)
        if len(out) >= limit:
            break
    return out


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
    topic: str | None = None,
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
    # Il terzo elemento sono gli argomenti che SOLO quel detector accetta.
    # L1 dal 2026-08-04 guarda anche il topic per capire se il claim riguarda
    # un artefatto software; gli altri due non ne hanno bisogno, e passarglielo
    # per uniformita' significherebbe aggiungere un parametro che nessuno
    # legge. Esplicito qui, invece che con una firma finta la' dentro.
    for layer, detect, extra in (
        ("L1", detect_unsupported_shipped_claim, {"topic": topic}),
        ("L1.5", detect_unsupported_diagnosis_claim, {}),
        ("L1.7", detect_unsupported_task_state_claim, {}),
    ):
        reason = detect(proposition=proposition, verified_by=vb_list, **extra)
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
    # LA SMENTITA NON E' IL CLAIM (2026-08-04). Nove detector su dodici
    # leggevano «Il modulo NON funziona in produzione» come la dichiarazione
    # che funziona: la parola c'era, il «non» davanti non veniva guardato da
    # nessuno. Per un gate anti-confabulazione e' il verso sbagliato — punisce
    # chi documenta un limite noto e lascia passare chi tace.
    #
    # LA GUARDIA STA QUI, NON NEI NOVE DETECTOR. Copiarla in ognuno sarebbe la
    # seconda classe ricorrente di questo progetto (una copia invece della
    # superficie unica) e le copie divergerebbero, come sono gia' divergiate le
    # due liste di negatori trovate il 2026-08-03. Applicata dove i warning si
    # raccolgono vale per i detector di oggi E per quelli scritti domani.
    #
    # Emerso misurando la cura precedente su L1.15: era
    # giusta e riguardava un detector solo.
    if out:
        out = [w for w in out if not _e_una_smentita(proposition, w)]
    return out


#: Le famiglie il cui warning e' una DICHIARAZIONE DI STATO, che la negazione
#: puo' ribaltare. Restano fuori i layer quantitativi: negare un numero non lo
#: rende meno inventato, e «la latenza NON e' scesa del 40%» contiene comunque
#: una cifra da giustificare.
_NEGABILI = frozenset({
    "L1", "L1.5", "L1.7", "L1.8", "L1.10", "L1.11", "L1.12", "L1.13",
    "L1.14", "L1.15", "L1.16", "L1.17", "L1.18", "L1.20", "L1.21",
})
#: La parola scatenante, che i detector scrivono fra apici nel `reason`
#: («Works/confirmed claim 'funziona' lacks runtime evidence»). I piu' recenti
#: la espongono anche come campo: si prova prima quello.
_PAROLA_NEL_REASON = re.compile(r"'([^']{1,80})'")


def _e_una_smentita(proposition: str, warning: dict[str, Any]) -> bool:
    """Il warning nasce da una parola che nel testo e' NEGATA?"""
    if str(warning.get("layer", "")) not in _NEGABILI:
        return False
    parola = (warning.get("keyword") or warning.get("matched_text") or "")
    if not parola:
        m = _PAROLA_NEL_REASON.search(str(warning.get("reason", "")))
        parola = m.group(1) if m else ""
    return tutte_le_occorrenze_sono_negate(proposition, str(parola))


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
    # 2026-08-04: le superfici del prodotto mancavano tutte. Trovate mentre
    # questa lista diventava il secondo asse del detector L1 (prima girava
    # solo per i fatti personali): «il nuovo comando e' stato cablato nella
    # CLI» non aveva UN segnale dev, e nemmeno un topic come project/x/cli.
    r"CLI|SDK|MCP|comando|comandi|subcomando|modifica|modifiche|"
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


def _advisory_l4_skipped() -> dict[str, str]:
    """L'avviso che finisce nella provenance di un write sourced NON giudicato.

    Diceva sempre «il modello locale non e' installato», e per il server MCP era
    FALSO: li' il modello c'e' e sta caricando su un thread di sfondo, quindi
    per i primi ~45 secondi ogni write sourced veniva ammesso con un avviso che
    mandava a scaricare un file gia' presente (misurato 2026-07-30, riprodotto
    con l'env del server). Quell'avviso resta scritto sul fatto per sempre, e
    una diagnosi confidente-e-sbagliata e' precisamente cio' che questo prodotto
    esiste per impedire — a maggior ragione quando la scrive lui.

    Lo stato lo dice ``local_grounding.judge_state()``, uno solo per tutte le
    superfici. Il write resta AMMESSO in ogni caso (regola della provenance da
    fonte), etichettato onestamente «entailment NOT verified»: mai spacciato per
    verificato, mai saltato in silenzio.
    """
    from .local_grounding import judge_state
    stato = judge_state()
    if stato == "warming":
        return {
            "layer": "L4-skipped",
            "reason": "source provided but the grounding judge was still "
                      "loading - entailment NOT verified for THIS write",
            "advice": "the local CE judge is warming on a background thread "
                      "(delegate-only mode keeps the ~30s cold load off the "
                      "request thread). It is NOT missing: re-writing after it "
                      "lands, or writing through the CLI, gets the moat verdict.",
        }
    if stato == "failed":
        return {
            "layer": "L4-skipped",
            "reason": "source provided but the grounding judge failed to load - "
                      "entailment NOT verified",
            "advice": "the local model is on disk but could not be loaded in "
                      "this process (the failure is cached for its lifetime). "
                      "Run `verimem doctor` for the reason, or pass "
                      "Memory(llm=...) to use an injected judge instead.",
        }
    return {
        "layer": "L4-skipped",
        "reason": "source provided but no grounding judge is available - "
                  "entailment NOT verified",
        "advice": "the local grounding model is not installed and no llm was "
                  "passed. Run `verimem warmup` to fetch the free multilingual "
                  "CE judge, or pass Memory(llm=...) — either turns the "
                  "source-entailment moat on.",
    }


#: Quanto della fonte conservare come PROVA della verifica (v17, 2026-08-08).
#: 400 caratteri: due o tre righe di un verbale, cioe' la porzione che un umano
#: rileggerebbe per controllare. Costo su disco misurato sul corpus di casa: i
#: fatti con fonte sono 2514, e a 400 char fanno ~1 MB su 90,6 — poco piu'
#: dell'1%. Non e' una soglia di comportamento: alzarlo conserva piu' contesto,
#: abbassarlo meno, e nessun verdetto si muove in nessuno dei due casi.
_GROUNDING_SPAN_BUDGET = int(os.environ.get("VERIMEM_GROUNDING_SPAN_BUDGET", "400"))


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
    narrative_l1_skip: bool = False,
    #: 2026-08-05 — abilita il routing di provenienza (gate_router) sui layer
    #: L1.x. SOLO superfici in-process: vedi il commento esteso al punto d'uso.
    provenance_trusted: bool = False,
    hook_token: str | None = None,
    repo_root: Any = None,
    source: str | None = None,
    grounding_llm: Any = None,
    ground_write: bool | None = None,
    asserted_at: float | None = None,
    status: str | None = None,
    claimant: str | None = None,
    documents: Any = None,
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

    # Continuity narrative lane (2026-07-23, adversarial design glm+deepseek):
    # a retrospective session checkpoint naturally reads like the self-claims
    # the L1.x family polices ("shipped", "works", "tests pass") — category
    # error on a declared chronicle. narrative_l1_skip suppresses ONLY that
    # family (and its evidence-existence companion below); the injection
    # screen, L3 contradiction and L4 grounding still run, and the fact is
    # stamped meta_narrative=1 so every listing can tell chronicle from
    # screened claim. SECURITY: this kwarg is for IN-PROCESS surfaces only
    # (SDK/CLI — callers who could anyway open the SQLite file, and who can
    # already pass validate="off", a strictly stronger lever). It must NEVER
    # be wired from network arguments: the MCP/gateway handlers keep
    # forwarding client meta_narrative only into the token-gated path above
    # (fail-closed), never into this one — guarded by tests
    # (test_mcp_arguments_meta_narrative_does_not_skip_l1,
    # test_gateway_ignores_body_meta_narrative_and_lineage).
    # PROVENIENZA (2026-08-05) — lo sweep che al router mancava. Il mandato del
    # 10/07 («ma questo tocca a me o a qualcuno di voi?») e' cablato in
    # gate_router e applicato in semantic.py:2836 a TRE detector; i quattordici
    # layer L1.8-L1.21 che vivono qui non ci passavano, e questa funzione
    # riceveva gia' writer_role usandolo solo per il bypass dei trusted-hook.
    # Il difetto che l'ha fatto emergere: «Hanno firmato Neri e Gialli», un
    # verbale, quarantinato da L1.16 col moat a 99,93 — il gate chiedeva una
    # prova di approvazione formale a un testo che RIPORTA una firma altrui.
    #
    # ⚠️ verified_by e' un Iterable e classify_provenance lo scorre: senza
    # materializzarlo qui, un generatore arriverebbe CONSUMATO a _l1_warnings.
    # E' la trappola che _l1_warnings documenta nella propria docstring.
    #
    # 🛡️ IN-PROCESS ONLY, e il perche' l'ha insegnato il presidio che questa
    # cura ha fatto cadere alla prima stesura
    # (test_attacker_with_user_role_cannot_bypass): gate_router argomenta che
    # writer_role e' spoofabile «BECAUSE the only privilege external_content
    # grants is skipping a warning-only heuristic» — vero per un chiamante
    # in-process, FALSO sul canale MCP, dove writer_role e' un argomento del
    # CLIENT: un attaccante scriveva writer_role='user' e si comprava il salto
    # di L1. Quindi il privilegio non pende da writer_role, che arriva dalla
    # rete, ma da questo kwarg che solo SDK/CLI passano — la stessa forma con
    # cui narrative_l1_skip protegge meta_narrative dieci righe piu' su, e per
    # la stessa ragione. I gestori MCP/gateway non devono inoltrarlo MAI.
    # Tutto il resto (screen delle iniezioni, admission gate, hard-gate dei
    # refs, source-trust, moat L4) gira identico per ogni provenienza.
    _vb_list = None if verified_by is None else [str(x) for x in verified_by]
    _l1_ha_giurisdizione = (
        not provenance_trusted
        or _gr_l1x_applies(_gr_classify_provenance(writer_role, _vb_list)))
    warnings = ([] if narrative_l1_skip or not _l1_ha_giurisdizione
                else _l1_warnings(proposition, _vb_list))
    verified_by = _vb_list
    contradicting_ids: list[str] = []
    supersede_ids: list[str] = []
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
    if (repo_root is not None and not warnings and verified_by is not None
            and not narrative_l1_skip):  # companion of the L1 family above
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
            ev = [str(x) for x in (r.get("evidence_facts") or [])]
            advice = str(r.get("advice", ""))
            # Same-source EVOLUTION routing (ENGRAM_SUPERSEDE_SAME_SOURCE): a lexically-
            # caught contradiction (numeric/version/date) against the SAME source's earlier
            # value is an evolution — retire the old, admit the new — not a quarantine.
            _conflicts = ev
            _sup_prima = len(supersede_ids)
            if _supersede_same_source_on() and ev:
                _conflicts = _route_evolutions(agent, verified_by, asserted_at, ev,
                                               supersede_ids, status,
                                               claimant=claimant,
                                               proposition=proposition)
            if _conflicts:
                warnings.append({
                    "layer": "L3",
                    "reason": "validate_claim verdict=contradicted",
                    "advice": advice,
                })
                contradicting_ids = _conflicts
            elif ev and len(supersede_ids) > _sup_prima:
                # ogni contraddizione era un'evoluzione della stessa fonte →
                # si ammette il nuovo e si ritira il vecchio
                warnings.append({
                    "layer": "L3-supersession",
                    "reason": "a newer same-source value supersedes a stored fact",
                    "advice": "this write updates an earlier value from the same source; "
                              "the older value is superseded.",
                })
            elif ev:
                # ⚠️ IL MESSAGGIO DICHIARAVA UN'AZIONE CHE NON ERA AVVENUTA.
                # Trovato dal critic avversariale (job 2635e23b, worker
                # counterexample) sulla cura della coesistenza: quando TUTTE le
                # coppie escono dalla terza uscita, `_conflicts` e' vuoto e si
                # cadeva qui, annunciando «the older value is superseded» con
                # `supersede_ids` INTATTO. Nulla era stato ritirato.
                #
                # Per un prodotto che vende memoria verificata, un avviso che
                # racconta una supersessione mai avvenuta e' la stessa classe di
                # difetto che il gate esiste per fermare — solo che stavolta a
                # confabulare era il gate.
                warnings.append({
                    "layer": "L3-coexistence",
                    "reason": "a contradiction was found but both facts are kept",
                    "advice": "the clashing facts come from DIFFERENT declared "
                              "authors: neither is an update of the other, so both "
                              "stay servable and recall returns them together.",
                })

    # L3-SEMANTIC (NLI moat): the lexical L3 (validate_claim, "puramente lessicale")
    # misses conflicts where the WORDS differ but the MEANING contradicts a stored
    # fact. detect_semantic_conflicts adds the entailment-model trigger (timestamp-
    # aware: supersession over time is NOT a contradiction). Opt-in
    # (ENGRAM_SEMANTIC_CONFLICT) so the default path is unchanged (no judge call).
    # When ON, the judge is the injected ``agent.llm`` if present, else the local NLI
    # cross-encoder (llm-free, Phase 1.1) — so the moat works subscription-free /
    # offline. observe mode surfaces without quarantining; enforce quarantines. Never
    # crashes the write (fail-soft to no warning).
    _sc_mode = _semantic_conflict_mode()
    if level == "full" and _sc_mode != "off":
        _sm = getattr(agent, "semantic", None) if agent is not None else None
        if _sm is not None:
            try:
                import time as _t
                import types as _ty

                from .semantic_conflict import (
                    LLMRelationJudge,
                    detect_semantic_conflicts,
                )
                _judge_llm = getattr(agent, "llm", None) if agent is not None else None
                if _judge_llm is not None:
                    _judge = LLMRelationJudge(_judge_llm)
                else:
                    # llm-free fallback: the local NLI cross-encoder (no claude -p).
                    # Fail-soft — classify() returns NEUTRAL if the model can't load,
                    # so a missing model degrades to "no warning", never a crash.
                    from .local_relation import get_local_relation_judge
                    _judge = get_local_relation_judge()
                # `writer_principal` anche qui: e' il GEMELLO del candidato di
                # `_route_evolutions`, e curare uno solo dei due lascia intatto
                # il difetto — la lezione «dopo ogni cura chiedi: chi ALTRO fa
                # la stessa cosa?». Misurato: col solo percorso lessicale curato
                # il fatto di anna veniva ritirato lo stesso, da QUI.
                _new = _ty.SimpleNamespace(
                    id="__candidate__", proposition=proposition,
                    topic=topic, created_at=_t.time(), verified_by=verified_by,
                    asserted_at=asserted_at, writer_principal=claimant,
                )
                _sibs = _live_topic_siblings(_sm, topic, limit=200)
                if _l3_subject_filter():
                    # P2 subject pre-filter (default ON, SAFE rule — see
                    # _l3_subject_filter): drop ONLY same-head-disjoint-
                    # modifier siblings; a head mismatch always reaches the
                    # judge (alias signature). Fail-soft to keep: a matcher
                    # error must never hide a real conflict.
                    def _keep(s) -> bool:
                        try:
                            from .subject_extract import nli_prefilter_skip
                            return not nli_prefilter_skip(
                                proposition, getattr(s, "proposition", ""))
                        except Exception:  # noqa: BLE001
                            return True
                    _sibs = [s for s in _sibs if _keep(s)]
                _sib_by_id = {getattr(f, "id", None): f for f in _sibs}
                _observe = _sc_mode == "observe"
                from .proof_evidence import both_machine_checked
                from .semantic import _STATUS_RANK
                from .supersession_policy import (
                    classify_write_relation,
                    references_fact,
                )
                _supersede_on = _supersede_same_source_on()
                _new_rank = _STATUS_RANK.get(status or "model_claim", 2)
                for _w in detect_semantic_conflicts(_new, _sibs, _judge):
                    if getattr(_w, "kind", "") != "semantic_conflict":
                        continue
                    _oid = getattr(_w, "other_fact_id", "")
                    # provenance+time split: a same-source NEWER value is an EVOLUTION
                    # (the source superseding itself), not a cross-source contradiction —
                    # the deterministic fix for the local NLI's measured temporal
                    # over-flag (2026-07-19). Cross-source stays 'conflict' (griefing guard).
                    _old = _sib_by_id.get(_oid)
                    # DIARY GUARD (precision, 2026-07-19): two statements
                    # indexing DIFFERENT events of the same kind ("On day 4
                    # ..." vs "On day 5 ...") are distinct entries, not one
                    # value evolving — the NLI over-flags them. Skip entirely:
                    # no supersession, no quarantine, no observe noise.
                    # (Found live: 12 diary adds collapsed under auto-NLI and
                    # count() dropped below ground truth.)
                    _rel_pre = ("conflict" if _old is None
                                else classify_write_relation(_new, _old))
                    from .quantity_match import (
                        distinct_event_indices,
                        indexed_vs_unindexed,
                    )
                    _old_prop = getattr(_old, "proposition", "")
                    if (_old is not None and distinct_event_indices(
                            proposition, _old_prop)):
                        continue
                    # SPECIFIC-vs-GENERIC GUARD (2026-07-25, dogfooding): one
                    # statement names indexed subjects, the other names none, so
                    # they have no subject in common to contradict. The case that
                    # forced it: a service note "a stray note that is not a
                    # relation" RETIRED a verified OEIS relation, because the NLI
                    # read "is NOT a relation" against "verified relation" as a
                    # contradiction. Precision guard on a model's opinion, like
                    # the two above — the deterministic path keeps its verdicts.
                    if (_old is not None
                            and indexed_vs_unindexed(proposition, _old_prop)):
                        continue
                    # PROOF-BEATS-OPINION (2026-07-25, dogfooding). Both sides
                    # carry machine-checkable evidence — the very kind L1.15
                    # accepts as support for a "verified" claim — and the only
                    # thing calling them contradictory is this NLI verdict. A
                    # proof the gate can inspect outranks a cross-encoder's
                    # opinion, so neither is retired. The case: 9 OEIS relations
                    # verified by exact integer check, 2 survived, because two
                    # DISTINCT true properties of the same sequences read as
                    # "same subject, different numbers". Measured on that pair:
                    # every deterministic detector returns None.
                    # Scope: no status is promoted and nothing becomes immune —
                    # a deterministic clash never reaches this code and still
                    # retires the old value.
                    if (_old is not None and both_machine_checked(
                            verified_by, getattr(_old, "verified_by", None))):
                        continue
                    # REFERENCE GUARD (2026-07-25, found by dogfooding on my own
                    # writes): a write that NAMES the stored fact's id is citing
                    # it. The memory protocol's own advice — pair a long fact with
                    # a short lure so recall can find it — had the lure SUPERSEDE
                    # the fact, leaving a pointer to something recall would no
                    # longer return. Same treatment as the diary guard: skip, keep
                    # both, let lineage record the order.
                    #
                    # SCOPE, narrowed after an adversarial review that was right
                    # (glm-5.2 + deepseek-v4-pro, convergent 2/2). The guard lives
                    # ONLY here, where the verdict is a model's OPINION, and only
                    # for a same-source 'evolution' — never on the deterministic
                    # lexical path, and never on a cross-source conflict:
                    #   * a numeric/version/date clash is a concrete fact, and
                    #     citing an id must not excuse it (their case: "CORREZIONE
                    #     del fatto X: il valore e' 200" must still retire the
                    #     stored 100 — the first version of this guard kept it);
                    #   * restricting to 'evolution' keeps a DIFFERENT source from
                    #     shielding someone else's fact by naming its id.
                    # Residual, documented not hidden: a hostile writer on the
                    # SAME source can quote an id to mute the NLI verdict on that
                    # one pair. That writer can already do worse — this module
                    # states the shared-tenant risk at _supersede_same_source_on —
                    # and the alternative (an NLI opinion silently deleting a true
                    # fact) is the error this store exists to avoid.
                    if (_oid and _rel_pre == "evolution"
                            and references_fact(proposition, _oid)):
                        continue
                    # TERZA GUARDIA (2026-08-01): due fatti che non condividono
                    # nessuna parola di CONTENUTO non sono l'uno l'evoluzione
                    # dell'altro. Sta qui, accanto alle altre due, per lo stesso
                    # motivo dichiarato sopra — questo e' il punto in cui il
                    # verdetto e' l'OPINIONE di un modello — e generalizza la
                    # guardia OEIS, che riconosce lo stesso errore ma solo per
                    # chi porta un `verified_by` deterministico. Su store
                    # vergine erano SEI fatti veri ritirati su dieci: vedi
                    # `_puo_essere_una_evoluzione` per la misura.
                    if (_rel_pre == "evolution" and not _puo_essere_una_evoluzione(
                            proposition, getattr(_old, "proposition", ""))):
                        continue
                    # LA TERZA USCITA anche su questo percorso — vedi
                    # `_route_evolutions` per il perche' e per i numeri. Due
                    # autori dichiarati e diversi non si ritirano a vicenda e
                    # non si quarantinano a vicenda: restano entrambi vivi.
                    if _old is not None and _entita_diverse(_new, _old):
                        continue
                    _rel = _rel_pre
                    if _observe:
                        # observe: surface but do NOT act, so the FP rate is measurable.
                        if _rel == "evolution":
                            warnings.append({
                                "layer": "L3-supersession-observe",
                                "reason": "a newer same-source value supersedes a stored "
                                          "fact (observe mode: logged, NOT applied)",
                                "advice": "this write updates an earlier value from the "
                                          "same source; in enforce mode the older value "
                                          "would be superseded, not flagged a conflict.",
                                "other_fact_id": _oid,
                            })
                        else:
                            warnings.append({
                                "layer": "L3-semantic-observe",
                                "reason": "NLI judge: contradiction with a stored fact "
                                          "(observe mode: logged, NOT quarantined)",
                                "advice": "a stored memory semantically contradicts this "
                                          "claim; set ENGRAM_SEMANTIC_CONFLICT=1 to enforce.",
                                "other_fact_id": _oid,
                            })
                    elif (_rel == "evolution" and _supersede_on and _old is not None
                          and _STATUS_RANK.get(getattr(_old, "status", "model_claim"), 2)
                          <= _new_rank):
                        # enforce + ENGRAM_SUPERSEDE_SAME_SOURCE: the same source updated
                        # its own value with an at-least-as-trusted claim → ADMIT the new
                        # (does not escalate) and retire the OLD via supersede_ids. The
                        # rank floor keeps a weak new from retiring a stronger old (an
                        # unverified claim never supersedes a verified fact — anti-confab).
                        # The handler applies it ONLY when the new write is ultimately
                        # admitted (action=='persist').
                        warnings.append({
                            "layer": "L3-supersession",
                            "reason": "a newer same-source value supersedes a stored fact",
                            "advice": "this write updates an earlier value from the same "
                                      "source; the older value is superseded.",
                            "other_fact_id": _oid,
                        })
                        if _oid:
                            supersede_ids.append(_oid)
                    else:
                        # cross-source conflict, OR evolution with supersede OFF: the
                        # conservative default — quarantine the new claim.
                        warnings.append({
                            "layer": "L3-semantic",
                            "reason": "NLI judge: contradiction with a stored fact",
                            "advice": "a stored memory semantically contradicts this "
                                      "claim (not a lexical/numeric clash).",
                            "other_fact_id": _oid,
                        })
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
    # judge-of-record for this write (set below IFF the L4 numeric judge scored)
    _judge_of_record: str | None = None
    _threshold_of_record: float | None = None
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
        warnings.append(_advisory_l4_skipped())

    # v17: la PROVA della verifica esiste solo se esiste una fonte. Inizializzata
    # QUI e non dentro il ramo: senza, ogni scrittura priva di fonte moriva su un
    # NameError — ed e' il caso piu' comune del prodotto (4279 fatti su 6425 nel
    # corpus di casa). Preso dal banco al primo giro, sulla popolazione opposta.
    _gspan: str | None = None
    if source and _ground_on and _have_judge:
        # score and cut resolved for the SAME judge (local CE vs claude scales differ —
        # the 2026-07-02 critic caught the calibrated cut not reaching this L4 site).
        from .grounding_gate import (
            NoGroundingJudge,
            _ce_band_enforced,
            _ce_band_tau_hi,
            fact_grounding_score_ex,
            resolve_write_threshold_for,
        )
        try:
            gscore, _judge_used = fact_grounding_score_ex(grounding_llm, source, proposition)
            # v17: la PROVA accanto al voto. `select_relevant_span` e' pura e
            # deterministica (nessun modello, 0,046 ms su 500 chiamate contro i
            # 32.800 del giudice) e NON tocca `gscore`: i verdetti di ammissione
            # non si muovono di un decimale. Fallire qui non deve mai impedire
            # una scrittura — la prova e' un di piu', il voto e' il gate.
            try:
                from .grounding_gate import select_relevant_span
                _gspan = select_relevant_span(
                    source, proposition, budget=_GROUNDING_SPAN_BUDGET) or None
            except Exception:      # pragma: no cover — degrada, non blocca
                _gspan = None
        except (FileNotFoundError, OSError, ImportError, NoGroundingJudge):
            # ONLY "the judge isn't really reachable" is tolerated here (missing /
            # unloadable model). A DEDICATED NoGroundingJudge — not the whole
            # RuntimeError family — so a real ML fault (torch shape mismatch, CUDA
            # OOM: also RuntimeError) PROPAGATES instead of being laundered into a
            # silent admission (opus review 2026-07-18, findings D + B).
            gscore, _judge_used = None, None
        if gscore is None:
            # The CE was advertised present but could not score → treat as "no
            # judge" RIGHT HERE. The `elif` below is unreachable once this `if`
            # was taken, so emitting the advisory there was dead code (that was
            # the silent fail-open opus caught).
            _emit_l4_skipped()
        else:
            grounding_val = float(gscore)  # persist the score even when it PASSES
            _judge_of_record = _judge_used
            _threshold_of_record = resolve_write_threshold_for(_judge_used)
            # L4.1 — IL CONTROLLO DETERMINISTICO CHE MANCAVA, e sta QUI perché
            # qui la fonte c'è. Misurato a fonte e giudice invariati:
            #
            #   A  inventa un'ENTITÀ (fornitore Verdi)  ammessi 0/4  il moat li ferma
            #   B  DETTAGLIO non detto su entità VERA   ammessi 5/5  con g 97,1–99,5
            #        «L'ordine 77 conteneva 40 pezzi.»          g=97.1
            #        «Bianchi ha partecipato per 45 minuti»     g=98.7
            #        «L'ordine 77 vale 1200 euro.»              g=98.0
            #
            # (B) è la forma in cui un LLM allucina davvero — non inventa un
            # fornitore inesistente, inventa la durata e l'importo — ed entra
            # col punteggio più alto del sistema.
            #
            # 🔑 La diagnosi: «nessun rilevatore L1 riceve la fonte, il
            # confronto claim↔fonte esiste in UN SOLO posto, dentro il
            # cross-encoder, che è esattamente quello che sbaglia su questa
            # classe». E il numero che la rende strutturale: il 91,8%
            # dei verdetti sta agli estremi (1324 su 1673 sopra 99) — NESSUNA
            # SOGLIA PUÒ SEPARARE, perché il giudice dà lo stesso punteggio a
            # un fatto vero e a un dettaglio inventato.
            #
            # ⚠️ Non sostituisce il moat e non lo contraddice: si affianca. Il
            # moat dice «la fonte lo implica», questo dice «questo NUMERO nella
            # fonte non c'è» — che è la domanda a cui un modello di entailment
            # non risponde («sa dire questo CONTRADDICE la fonte, non sa
            # dire questo NON C'È nella fonte»).
            # L4.1-bis — I NUMERI CHE NON ABBIAMO POTUTO MISURARE LO DICONO.
            # Il fatto ENTRA: questo non è un veto, è un avviso, e la differenza
            # è la regola di casa «un avviso non ha bisogno della popolazione
            # opposta, un veto sì».
            # ⚠️ Senza questa riga la cura di `_PUNTO_AMBIGUO` sposta il difetto
            # invece di chiuderlo: prima «45.000 euro» contro «45 euro» veniva
            # AMMESSO da un confronto falso, dopo viene ammesso da NESSUN
            # confronto — e per chi legge il fatto le due cose sono identiche.
            # L'ha imposta una verifica indipendente, smentendo la prima
            # proposta: «togliere l'accusa
            # non distingue le due popolazioni, i falsi negativi nascono
            # convertendo i veri positivi in silenzio».
            from .quantity_match import numeri_ambigui
            _ambigui = numeri_ambigui(proposition)
            if _ambigui:
                _aa = ", ".join(_ambigui[:4])
                warnings.append({
                    "layer": "L4.1-ambiguo",
                    "reason": (f"il claim contiene numeri che NON sono stati "
                               f"verificati contro la fonte: {_aa}"),
                    "advice": ("il punto puo' essere separatore decimale o delle "
                               "migliaia e le due letture differiscono di mille "
                               "volte: riscrivi il numero senza separatori "
                               "(45000) per farlo verificare"),
                    "matched_text": _aa,
                })
            from .valore_non_nella_fonte import (
                assenti_che_la_fonte_scrive_a_parole,
                valori_non_nella_fonte,
            )
            _assenti = valori_non_nella_fonte(proposition, source)
            # LA FONTE LO DICE, SOLO A PAROLE. Misurato il 16/08 usando il
            # prodotto: fonte «SEI combinazioni», claim «6 combinazioni», tre
            # casi con `withheld_despite_judge=True` e grounding 99,3-99,9 —
            # il layer tratteneva un fatto VERO mentre il giudice era contento.
            # Qui il numero nella fonte c'e': cambia la forma in cui e' scritto.
            # ⚖️ DECLASSA, non ammette: il valore esce dal veto ed entra in un
            # AVVISO col suo nome, perche' l'equivalenza cifra-parola non e'
            # certa come quella di «nessun X» (`sei` e' anche il verbo essere).
            # E' la regola dichiarata a L4.1-bis qui sopra — «un avviso non ha
            # bisogno della popolazione opposta, un veto si'» — ed e' cio' che
            # permette di tenere dentro le parole ambigue: un omonimo costa un
            # avviso in piu' su un fatto che entra, non un numero che passa.
            _a_parole = assenti_che_la_fonte_scrive_a_parole(_assenti, source)
            if _a_parole:
                _pp = ", ".join(
                    (f"{v.come_scritto()} {v.unita}".strip())
                    for v in _a_parole[:4])
                warnings.append({
                    "layer": "L4.1-a-parole",
                    "reason": (f"la fonte non scrive questi valori in cifra ma "
                               f"contiene il numerale corrispondente: {_pp}"),
                    "advice": ("il numero sembra esserci, scritto a parole: "
                               "verifica che sia lo stesso e non un omonimo "
                               "(«sei» e' anche il verbo essere)"),
                    "matched_text": _pp,
                })
                _assenti = [a for a in _assenti if a not in _a_parole]
            if _assenti:
                # ⚠️ `come_scritto()` E NON `f"{v.valore:g}"`: quel formato tiene
                # sei cifre significative e ARROTONDA, quindi il gate nominava
                # una cifra che l'utente non aveva scritto — «2607.26760» usciva
                # come «2607.27», e «1706.03762» come «1706.04». Caso reale
                # incontrato usando il prodotto (id=21b5710c46f5), su un
                # claim che citava la propria fonte verbatim.
                # Per un gate che esiste per fermare i numeri inventati, era il
                # difetto peggiore possibile: non diceva «non capisco», diceva
                # con precisione una cosa falsa.
                _vv = ", ".join(
                    (f"{v.come_scritto()} {v.unita}".strip()) for v in _assenti[:4])
                warnings.append({
                    "layer": "L4.1",
                    "reason": (f"il claim afferma un valore che la fonte non "
                               f"contiene: {_vv}"),
                    "advice": ("un numero che la fonte non dice non e' un "
                               "numero verificato: correggi il valore, oppure "
                               "passa la fonte che lo contiene"),
                    "matched_text": _vv,
                })
            # L4.2 — L'ALTRA META' DELLO STESSO BUCO, misurata sulla cura
            # qui sopra: «14 valvole» entrava a 100.0 perche' la fonte diceva
            # «14 operai». L4.1 chiede se il VALORE c'e'; questo chiede se
            # parla della STESSA COSA. Cifra riusata: fermati 0/3 prima.
            # Non si sovrappongono: valori_riusati_da_altro_contesto salta per
            # costruzione i valori assenti, che sono il perimetro di L4.1.
            from .vicinato_del_valore import valori_riusati_da_altro_contesto
            _riusati = valori_riusati_da_altro_contesto(proposition, source)
            if _riusati:
                _rr = "; ".join(
                    f"{r.valore:g} qui e' «{r.nel_claim}», nella fonte "
                    f"«{r.nella_fonte}»" for r in _riusati[:3])
                warnings.append({
                    "layer": "L4.2",
                    "reason": (f"il claim riusa un numero della fonte "
                               f"riferendolo a un'altra grandezza: {_rr}"),
                    "advice": ("la cifra compare nella fonte ma parla d'altro: "
                               "correggi la grandezza, oppure passa la fonte "
                               "che sostiene questo valore"),
                    "matched_text": _rr,
                })
            # L4-negazione — NON un verdetto, una DICHIARAZIONE, e solo quando
            # il moat ha gia' deciso di bocciare. Il giudice e' un
            # cross-encoder di ENTAILMENT e non ha l'assunzione di mondo
            # chiuso: «il fornitore Verdi non era presente» non e' implicato da
            # un elenco che semplicemente non lo nomina, quindi cade a 1.38
            # anche quando e' VERA (8 su 12 in quattro lingue, con la
            # stessa simmetria — segno che e' il modello, non il lessico).
            # L'unica negazione che passa e' quella la cui assenza la fonte
            # ENUNCIA («l'ordine 91 resta in sospeso» -> ammessa a 90), ed e'
            # per questo che l'avviso indica quella uscita.
            #
            # ⚠️ Nessuna soglia puo' separare qui: e' misurato che il 91,8%
            # dei verdetti sta agli estremi (1324 su 1673 sopra 99). Il gate
            # non puo' sapere se la negazione sia vera; puo' smettere di far
            # sparire il fatto senza dire che il giudizio non era affidabile.
            # E' anche il motivo per cui questa cura non ha bisogno della
            # popolazione opposta, che per un veto sarebbe indispensabile:
            # l'avviso e' vero tanto per una negazione vera quanto per una
            # falsa. La guardia gemella sui detector L1 esiste dal 04/08
            # (negation_scope, riga ~1138) e al moat non era mai arrivata.
            if gscore < _threshold_of_record and _e_un_claim_negativo(
                    proposition):
                warnings.append({
                    "layer": "L4-negazione",
                    "reason": ("il claim afferma un'ASSENZA e il giudice non "
                               "sa verificarla: un modello di entailment non "
                               "assume mondo chiuso, quindi una negazione vera "
                               "che la fonte non enuncia esplicitamente cade "
                               "come una falsa — questo punteggio non separa "
                               "le due"),
                    "advice": ("se la negazione e' vera, passa una fonte che "
                               "ENUNCI l'assenza («l'ordine 91 resta in "
                               "sospeso») invece di una che la lasci dedurre "
                               "da un elenco: su quella forma il giudizio "
                               "torna affidabile"),
                    "matched_text": proposition[:120],
                })
            if gscore < _threshold_of_record:
                if _graded_admission():
                    # GRADED ADMISSION (design bf5d322 step 1, env-gated,
                    # DEFAULT OFF): "not proven enough" is not "malicious".
                    # Measured at the shipped cut 40 (HaluMem external A/B):
                    # hard-reject here loses 33% of CLEAN facts. With the env
                    # ON the write persists as a low-confidence model_claim and
                    # the receipt says so; quarantine stays reserved for
                    # injection / active contradiction (they escalate below
                    # regardless). Layer name deliberately NOT "L4-grounding"
                    # so the escalation equality check does not fire.
                    warnings.append({
                        "layer": "L4-grounding-graded",
                        # `.1f` e non `.0f`: con `.0f` un grounding di 0.3651
                        # si legge «grounding 0», che e' il valore che questo
                        # prodotto usa per dire «nessun punteggio». Chi legge
                        # non distingue un giudizio bassissimo da un giudizio
                        # assente — la distinzione che tutto il resto difende.
                        "reason": f"graded admission: grounding {gscore:.1f} below "
                                  f"threshold {_threshold_of_record:.0f} — admitted "
                                  "as low-confidence, NOT verified "
                                  "(ENGRAM_GRADED_ADMISSION)",
                        "advice": "the declared source does not entail this claim; "
                                  "it is stored as an unproven low-confidence "
                                  "memory. Unset ENGRAM_GRADED_ADMISSION to "
                                  "restore hard quarantine.",
                        "grounding_score": gscore,
                    })
                else:
                    # WHICH part the source misses. "the source does not
                    # support this proposition" is true and unactionable: a
                    # 190-char sentence asserts three things, the source
                    # carries two, and the writer guesses. Measured on myself
                    # 2026-07-29: three consecutive rejections of one
                    # checkpoint, each removing a different piece.
                    #
                    # Only with the LOCAL judge: it is free, so re-scoring a
                    # handful of clauses costs ~0.4s each on the REJECT path
                    # (18% of writes, measured over 22). With an llm judge this
                    # would be N extra inferences per rejection, which is not a
                    # price an advisory may charge.
                    _pointer = ""
                    try:
                        from .unsupported_span import split_claim_clauses
                        _n_claims = len(split_claim_clauses(proposition))
                    except Exception:  # noqa: BLE001 — advisory only
                        _n_claims = 1
                    if _n_claims > 1:
                        _pointer = (
                            f" This proposition makes {_n_claims} separate "
                            f"assertions and the moat judges them as ONE — a "
                            f"single unproven piece sinks the rest. Split it "
                            f"and save the parts this source actually proves; "
                            f"give the others their own source."
                        )
                    warnings.append({
                        "layer": "L4-grounding",
                        # `.1f` come sopra: «grounding 0» su un valore di 0.37
                        # confonde un giudizio bassissimo con uno assente.
                        "reason": f"source does not entail the proposition "
                                  f"(grounding {gscore:.1f} below threshold)",
                        "advice": "the source does not support this proposition — likely a "
                                  "confabulated inference, not a stated fact." + _pointer,
                        "grounding_score": gscore,
                    })
                    advice = advice or "Source does not entail the claim (semantic grounding)."
            elif (_judge_used == "local" and _ce_band_enforced()
                  and (gscore < _ce_band_tau_hi()
                       or unverified_relation(source, proposition))):
                # The band catches what the CE DOUBTS. It never catches what the
                # CE gets confidently wrong, and those are one class: relations
                # between the source's facts — a cause, a completed state, a
                # certainty, a computed quantity — where every word is present
                # and only the link is invented. Measured 2026-07-28 across five
                # domains: the CE's three misses scored 88, 100 and 100, i.e.
                # ABOVE tau_hi, so the safety net hung under them. A write whose
                # fact announces a relation its source never announces now
                # escalates whatever the score. Routing, not rejecting: with no
                # judge reachable escalate_band returns None and the write lands
                # exactly as before.
                # BAND ESCALATION (0.7.0): before parking the write for review,
                # ask an AVAILABLE llm judge to adjudicate the CE's uncertain
                # sliver -- auto-discovered claude CLI (subscription, no key)
                # when no llm was injected. Fail-soft: None -> held for review
                # exactly as before; an unreadable verdict never admits.
                _esc = None
                if grounding_llm is None:
                    from . import band_escalation as _be
                    _esc = _be.escalate_band(source, proposition)
                if _esc is not None:
                    _esc_score, _esc_judge = _esc
                    grounding_val = float(_esc_score)
                    _judge_of_record = _esc_judge   # local-band / claude-band
                    _threshold_of_record = resolve_write_threshold_for("claude")
                    if _esc_score < _threshold_of_record:
                        if _graded_admission():
                            # coherence with the main sub-threshold branch: a
                            # grounding shortfall admits as low-confidence
                            # under graded admission, whoever scored it.
                            warnings.append({
                                "layer": "L4-grounding-graded",
                                "reason": f"graded admission: band judge "
                                          f"({_esc_judge}) scored {_esc_score:.0f} "
                                          "below threshold — admitted as "
                                          "low-confidence, NOT verified",
                                "advice": "the llm adjudicated the source does not "
                                          "entail this claim; stored as an unproven "
                                          "low-confidence memory.",
                                "grounding_score": _esc_score,
                            })
                        else:
                            warnings.append({
                                "layer": "L4-grounding",
                                "reason": f"band escalation ({_esc_judge}): llm judge scored "
                                          f"{_esc_score:.0f} below the claude-scale "
                                          f"threshold {_threshold_of_record:.0f}",
                                "advice": "the CE was unsure and the llm judge "
                                          "adjudicated NOT entailed -- likely a "
                                          "confabulated inference, not a stated fact.",
                                "grounding_score": _esc_score,
                            })
                            advice = advice or ("Source does not entail the claim "
                                                "(band llm adjudication).")
                    # else: llm adjudicated entailed -> admitted clean,
                    # judge-of-record 'claude-band' on the receipt.
                else:
                    if _graded_admission():
                        # no adjudicator available: under graded admission the
                        # borderline write persists as low-confidence instead
                        # of being held — otherwise a BETTER score (band) would
                        # fare WORSE than a sub-threshold one (admitted above).
                        warnings.append({
                            "layer": "L4-review-graded",
                            "reason": f"graded admission: borderline grounding "
                                      f"({gscore:.0f}) in the CE review band — "
                                      "admitted as low-confidence, NOT verified",
                            "advice": "the local CE is not confident the source "
                                      "entails this claim; stored as an unproven "
                                      "low-confidence memory.",
                            "grounding_score": gscore,
                        })
                    elif gscore >= _ce_band_tau_hi():
                        # Il ramo scatta per DUE motivi diversi (la condizione
                        # dell'`elif` sopra): il punteggio SOTTO la banda, oppure
                        # una RELAZIONE che la fonte non enuncia. Il secondo non
                        # puo' trattenere da solo, e la ragione e' misurata il
                        # 19/08 su entrambe le popolazioni:
                        #   riformulati VERI  2 trattenuti su 3 — «Sono stati
                        #     spediti 45 colli» su una fonte che dice «la consegna
                        #     e' stata effettuata ... con 45 colli», g=99.98
                        #   confabulazioni    3 prese su 3, MA due di quelle tre
                        #     le ferma gia' il moat da solo (g=2.81 e g=5.50)
                        # ⇒ il veto aggiunge qualcosa una volta e sbaglia due, e
                        # il riformulato e' il caso NORMALE: nessuno ricopia la
                        # fonte, la riscrive con parole sue. Un criterio che
                        # sbaglia il doppio di quanto serve non e' un veto.
                        #
                        # Resta come AVVISO, che e' la stessa forma scelta per
                        # L4.2 poco piu' sotto e per la stessa ragione: dichiara
                        # e lascia decidere. ⚠️ Il costo e' dichiarato e non
                        # nascosto: la confabulazione che il moat NON ferma (nel
                        # banco, «il pagamento e' stato effettuato» su una fonte
                        # che dice «in lavorazione», g=93.95) ora ENTRA — con
                        # questo avviso addosso, non in silenzio.
                        #
                        # La banda NON cambia: sotto tau_hi si trattiene come
                        # prima, ed e' il ramo `else` qui sotto.
                        _rel = unverified_relation(source, proposition)
                        warnings.append({
                            "layer": "L4-relazione",
                            "reason": f"the claim announces a {_rel or 'relation'} "
                                      f"the source never states, but the CE scored "
                                      f"{gscore:.0f} — admitted WITH this notice, "
                                      f"not verified as a stated fact",
                            "advice": "check that the source really states this "
                                      "link and not only its parts; pass "
                                      "Memory(llm=...) to have it adjudicated.",
                            "grounding_score": gscore,
                        })
                    else:
                        warnings.append({
                            "layer": "L4-review",
                            "reason": f"borderline grounding ({gscore:.0f}) in the CE review "
                                      f"band [{_threshold_of_record:.0f}, "
                                      f"{_ce_band_tau_hi():.0f}) - held for review, not admitted",
                            "advice": "the local CE is not confident the source entails this "
                                      "claim; pass Memory(llm=...) to adjudicate the borderline "
                                      "zone, or review the held fact.",
                            "grounding_score": gscore,
                        })
    elif source and not _have_judge:
        _emit_l4_skipped()

    # An L1 detector answers "no evidence in verified_by; add one of ...". Often
    # the writer HAS it and put it in the sentence: "Wave 72 done, last commit
    # ff2aaa3e". Measured on the live corpus 2026-07-28: 174 of 509 quarantined
    # facts (34.2%) name a commit, a file:line, a test result or a PR in their
    # own prose. The verdict stays exactly as it is — a SHA inside prose is an
    # assertion, the same SHA in verified_by is something provenance_validator
    # can CHECK with git rev-parse — but the gate can SEE the reference it is
    # asking for, and quoting it back turns a generic refusal into one the
    # writer can act on.
    _hint = hint_for(proposition)
    if _hint:
        for _w in warnings:
            if str(_w.get("layer", "")).startswith("L1") and _w.get("advice"):
                _w["advice"] = f"{_w['advice']} NOTE: {_hint}."

    # Decision tree.
    has_l3_contradict = any(w.get("layer") == "L3" for w in warnings)
    has_l3_semantic = any(w.get("layer") == "L3-semantic" for w in warnings)
    # L4.1 tratta come un fallimento del moat, e deve: un numero che la fonte
    # non contiene NON è un numero verificato, e questa è l'unica classe di
    # allucinazione che il giudice non prende (misurata 5/5 ammessi a 97-99).
    # Sta con `L4-grounding` e non fra i layer L1 perché il verdetto viene dal
    # confronto con la FONTE, non dalle parole del claim.
    # ⚠️ L4.2 NON e' qui, ed e' una scelta MISURATA. Come veto costerebbe il
    # 20% di falsi positivi sui riformulati veri (banco lingue, 1/5: «300
    # pallet» contro una fonte che dice «300 bancali» cambia sia il verbo sia
    # il sostantivo, e nessuno dei due lati coincide). Il riformulato E' il
    # caso normale, e una cura che rompe un presidio verde scritto da un altro
    # non si consegna. Resta come AVVISO: dichiara che il numero e' riusato da
    # un altro contesto e lascia decidere — la forma di hidden_records,
    # quarantined_by, floor_applied_by, ranking.
    has_grounding_fail = any(w.get("layer") in ("L4-grounding", "L4.1")
                             for w in warnings)
    has_l4_review = any(w.get("layer") == "L4-review" for w in warnings)
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
    # SERVER-SIDE domain-advisory mode (measured 2026-07-21: 86.7% vertical FP):
    # a deployment that stores customer domain facts, not an agent's self-claims
    # about code, declares ENGRAM_L1_DOMAIN_ADVISORY — L1 keyword warnings are
    # still computed and surfaced but do not escalate to quarantine. Env-only,
    # never a per-write flag (that would be spoofable); relaxes ONLY L1 — the
    # L3/L4 semantic gates below are untouched.
    _domain_advisory = _l1_domain_advisory()
    # PER-FACT domain-precision carve-out (design (d), env ENGRAM_L1_DOMAIN_
    # PRECISION, DEFAULT OFF). Unlike _domain_advisory (which disarms L1 for the
    # WHOLE deployment), this suppresses the L1 escalation ONLY for a fact the
    # subject classifier reads as a third-party professional fact — an agent's
    # self-claim about its OWN software ('the migration is complete') is NOT
    # domain and still escalates. Content-based, not a spoofable field; the
    # subject HEAD (not the ambiguous verb) is the discriminator. Relaxes ONLY
    # L1 — L3/L4/injection escalate independently below.
    _domain_precision_fp = (has_l1 and _l1_domain_precision()
                            and _is_domain_professional_fact(proposition))
    # A declared source is caller-controlled and unverified (spoofable like the
    # writer_role the trusted-hook bypass had to token-gate). It therefore does
    # NOT downgrade an L1 hit: the gate stays fail-closed and quarantines a
    # shape-confab regardless of an attached source. The honest recovery path
    # for a real documental fact is a grounding JUDGE (L4), which verifies
    # source-entailment; the L4-skipped advisory above says so when none is set.
    l1_escalates = (has_l1 and not _personal_fp and not _world_fp
                    and not _domain_advisory and not _domain_precision_fp)
    if _domain_precision_fp and not _personal_fp and not _world_fp \
            and not _domain_advisory:
        # Record the per-fact stand-down (``*-observe``: surfaced, never a block
        # reason nor a ledger credit). Only when precision is the reason L1 did
        # not escalate — if a carve-out or the global switch already did, that
        # marker owns it.
        warnings.append({
            "layer": "L1-domain-precision-observe",
            "reason": "ENGRAM_L1_DOMAIN_PRECISION active: the subject reads as a "
                      "third-party professional fact, so the L1 keyword hit was "
                      "kept advisory rather than escalated",
            "advice": "unset ENGRAM_L1_DOMAIN_PRECISION to restore L1 keyword "
                      "escalation for this write",
        })
    if _domain_advisory and has_l1 and not _personal_fp and not _world_fp:
        # Critic probe 3 on e41991e (2026-07-21): the switch used to leave NO
        # trace — a disarmed-L1 deployment's receipts were indistinguishable
        # from an armed one's, and a mid-process env mutation disarmed the
        # layer fleet-wide with no audit record. Record the STAND-DOWN on the
        # receipt (``*-observe`` convention: surfaced, never owns a block
        # reason nor a ledger credit). Guarded on exactly the term the switch
        # flips in ``l1_escalates`` — an L1 hit no carve-out suppressed. Under
        # force_persist or an L3/L4 co-fire the final outcome is the same with
        # or without the switch (critic 2026-07-21, probe c): the marker still
        # stamps there, and its reason text stays literally true — L1 was kept
        # advisory by the switch; it just wasn't the deciding factor.
        warnings.append({
            "layer": "L1-domain-advisory-observe",
            "reason": "ENGRAM_L1_DOMAIN_ADVISORY active: an L1 keyword hit "
                      "that would have escalated was kept advisory by the "
                      "deployment-wide switch",
            "advice": "unset ENGRAM_L1_DOMAIN_ADVISORY to restore L1 keyword "
                      "escalation",
        })
    # P0 EVIDENCE-BEFORE-BELIEF (ciclo 2b, 2026-07-25) — observe-first.
    # The note above says a DECLARED source cannot downgrade an L1 hit: it is
    # caller-controlled, so trusting it would be the writer_role mistake again.
    # This is the verified form of that recovery path — not what the caller
    # SAYS, but who the server STAMPED: a fact whose cited document was indexed
    # by a different principal, over a channel that authenticates, is not a
    # self-claim laundering itself. Gated on `advisory_eligible` so it can only
    # ever speak about the lexical family, and on a server-stamped `claimant`
    # (never a tool argument). Default OFF: the verdict is recorded, the
    # outcome unchanged, so the false-block delta is MEASURED before any flip.
    if l1_escalates and documents is not None and advisory_eligible(warnings):
        from .evidence_independence import independence_verdict
        _iv = independence_verdict(verified_by=list(verified_by or []),
                                   claimant=claimant, store=documents)
        if _iv.independent:
            if _p0_independence_enforced():
                l1_escalates = False
                warnings.append({
                    "layer": "P0_INDEPENDENCE",
                    "matched_text": _iv.ref or "",
                    "reason": _iv.reason,
                    "advice": "the L1 keyword hit was kept ADVISORY: the cited "
                              "evidence was indexed by a different principal "
                              "over a trusted channel (unset "
                              "ENGRAM_P0_INDEPENDENCE to restore escalation)",
                })
            else:
                warnings.append({
                    "layer": "P0_INDEPENDENCE-observe",
                    "matched_text": _iv.ref or "",
                    "reason": _iv.reason,
                    "advice": "observe mode: this write WOULD have been kept "
                              "advisory instead of quarantined (independent "
                              f"witness {_iv.author}) — set "
                              "ENGRAM_P0_INDEPENDENCE=1 to enforce",
                })
    def _attribuzione_da_suggerire(ws: list) -> str:
        """La strada che il gate CONOSCE e non diceva a chi ne ha bisogno.

        Il router (10/07) esporta tre funzioni: `classify_provenance` e
        `l1x_applies` decidono, `attribution_question` lo SPIEGA a chi scrive —
        e quella terza era chiamata solo in semantic.py, mai qui. Il caso che
        l'ha fatta emergere: «Hanno firmato Neri e Gialli» quarantinata da
        L1.16 con l'advice «Add approval:<id>_signed / pr:<n>_approved», che
        per un verbale d'assemblea non ha nessuna uscita.

        ⚠️ NON SEMPRE, o e' rumore: su «ho fixato il bug» la provenienza non
        c'entra, e un advice che compare ovunque non si legge piu'. Il segnale
        che isola il caso vero e' la CONTRADDIZIONE INTERNA del gate — L1
        trattiene MENTRE il moat ha approvato la fonte. Li' il gate dice due
        cose incompatibili, e quella sbagliata e' la seconda: il testo non e'
        dell'agente.
        """
        if grounding_val is None or grounding_val < _threshold_of_record:
            return ""  # il moat non ha approvato: nessuna contraddizione
        if not any(str(w.get("layer", "")).startswith("L1") for w in ws):
            return ""
        if _gr_classify_provenance(writer_role, verified_by) != "agent_claim":
            return ""  # gia' dichiarata: dirglielo sarebbe rumore
        return _gr_attribution_question("agent_claim")

    def _mk(action: GateAction, *, advice_: str = advice,
            warnings_: list | None = None) -> GateResult:
        # Every gate outcome carries the judge-of-record + threshold, so the
        # write receipt classifies the evidence honestly (no silent verdicts).
        # dedup (order-preserving): the lexical L3 and the NLI layer can both flag the
        # same pair, so an id could otherwise appear twice (a spurious duplicate in the
        # receipt + a harmless-but-noisy second supersede attempt).
        _sup = list(dict.fromkeys(supersede_ids))
        _sup_set = set(_sup)
        _ws = warnings if warnings_ is None else warnings_
        _attr = _attribuzione_da_suggerire(_ws)
        if _attr:
            advice_ = f"{advice_} {_attr}".strip() if advice_ else _attr
            for _w in _ws:
                if str(_w.get("layer", "")).startswith("L1"):
                    _w["advice"] = f"{_w.get('advice', '')} {_attr}".strip()
        return GateResult(
            action=action,
            warnings=_ws,
            contradicting_fact_ids=[c for c in dict.fromkeys(contradicting_ids)
                                    if c not in _sup_set],
            supersede_fact_ids=_sup,
            advice=advice_,
            grounding_score=grounding_val,
            grounding_span=_gspan,
            judge=_judge_of_record,
            threshold=_threshold_of_record,
        )
    if force_persist:
        # Caller demands persist; we still surface warnings.
        return _mk("persist")
    if (has_l3_contradict or has_l3_semantic or has_grounding_fail) and mode == "reject":
        return _mk("reject", advice_=advice or "Claim contradicted by existing memory.")
    if (has_l3_contradict or has_l3_semantic or has_grounding_fail
            or has_l4_review or l1_escalates):
        return _mk("downgrade")
    if warnings:
        # L1 false positives on personal/non-dev text: keep the fact recallable, surface
        # the detectors as advisory only (no quarantine).
        return _mk("persist")
    return _mk("persist", warnings_=[])


__all__ = [
    "GateResult",
    "GateAction",
    "GateMode",
    "ValidateLevel",
    "TRUSTED_HOOKS",
    "run_validation_gate",
]
