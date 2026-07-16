"""engram.Memory — the turnkey SDK: add()/search() in a few lines, WITH the moat on.

mem0/Zep expose ``add(messages)`` / ``search(query)`` and store whatever the extractor
emits. Engram's ``add()`` routes every write through the anti-confabulation gate (L1
lexical + optional L3 contradiction + optional L4 source-entailment) — so a fact that
isn't supported is downgraded/refused, not silently stored — and ``search()`` returns
the per-fact PROVENANCE (status, grounding_score) so the caller can trust-condition.
That gate is the capability no competitor's SDK has.

    from engram import Memory
    mem = Memory()
    mem.add("The deployment uses PostgreSQL 16.")          # L1 lexical screen (always)
    hits = mem.search("which database?")                    # [{text, status, grounding_score, score}]

    mem.add(fact, source=src, ground=True)                  # + L4 source⊢fact entailment

Local SQLite, subscription/offline by default (no external key). The L1 lexical
screen runs on every add(); the L4 entailment moat (AUROC 0.971) runs per-call
when you pass ``source=`` and ``ground=True`` (needs a grounding_llm or the
local distilled CE, ENGRAM_GROUNDING_BACKEND=local).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .anti_confab_gate import run_validation_gate
from .flow_events import emit_flow as _emit_flow
from .semantic import Fact, SemanticMemory

#: Gate presets (packaging 2026-07-08): the gate's knobs existed for months
#: (validate off/fast/full, gate_mode downgrade/reject, ground L4) but you had
#: to know them. Three declarative modes; ``balanced`` = the historic default,
#: byte-identical. Any explicit per-call parameter always wins over the preset.
_GATE_PRESETS: dict[str, dict[str, Any]] = {
    "strict":     {"validate": "full", "gate_mode": "reject",    "ground": True},
    "balanced":   {"validate": "fast", "gate_mode": None,        "ground": False},
    "permissive": {"validate": "off",  "gate_mode": None,        "ground": False},
}

#: Grounding-verified answering (asse madre, anti-hallucination read-path). The
#: generator answers ONLY from retrieved facts; a local cross-encoder then
#: verifies the answer is entailed by one of them and abstains otherwise.
_ANSWER_SYSTEM = (
    "Answer the question using ONLY the provided facts. Be concise: just the "
    "answer, no preamble. If the facts do not contain the answer, reply exactly: "
    "NO ANSWER.")
#: Case-B resolution prompt (trust-conditioned answering). Measured on the
#: well-grounded-distractor bench (sonnet-5, 2026-07-16, n=12 + 2 unresolvable):
#: bare facts C=0.17/H=0.33 → tagged facts C=0.92/H=0.08, and it abstained 2/2
#: on same-metadata conflicts. Wording = the bench's resolution prompt PLUS one
#: trailing no-facts→NO ANSWER sentence (inert on the bench — every case's
#: answer IS in a fact — kept for parity with the v1 prompt's contract; critic
#: 2026-07-16 flagged the earlier "EXACTLY the bench's" comment as imprecise).
#: The verbose tie-rule variant measurably regressed (described the conflict
#: instead of the bare NO ANSWER), so don't "improve" this without re-measuring.
_ANSWER_TRUST_SYSTEM = (
    "Answer the question using ONLY the provided facts. Each fact is tagged "
    "[when | source | status]. If facts conflict, resolve by metadata: a "
    "'verified' fact beats an unverified one; a more recent fact beats an older "
    "one; a first-hand source beats hearsay. If the conflict cannot be resolved "
    "by the metadata, reply exactly: NO ANSWER. Be concise: just the answer. If "
    "the facts do not contain the answer, reply exactly: NO ANSWER.")


def _fact_trust_line(h: dict[str, Any]) -> str:
    """One tagged fact line for the trust-conditioned answer prompt:
    ``[when | source | status] text``. Honest formatting: the date comes from
    ``asserted_at`` (event time) falling back to ``created_at`` (always real);
    the source is the first source episode, else the verifiers, else the
    explicit word "unrecorded" — never an invented provenance."""
    import time as _time
    ts = h.get("asserted_at") or h.get("created_at")
    when = _time.strftime("%Y-%m-%d", _time.gmtime(float(ts))) if ts else "undated"
    src = h.get("source") or ", ".join(h.get("verified_by") or []) or "unrecorded"
    return f"[{when} | {src} | {h.get('status', 'model_claim')}] {h['text']}"
#: CE score above which the answer counts as fact-supported. Distinct from the
#: WRITE gate's 99.64 (Youden on source⊢fact hard negatives): the probe
#: 2026-07-16 measured answering-facts ~91-94 vs distractors ~1-3, so any cut in
#: (3, 90) separates; 40 mirrors WRITE_DEFAULT_THRESHOLD. Recalibrate on the bench.
_ANSWER_VERIFY_THRESHOLD = 40.0


class Memory:
    """Turnkey persistent-memory client. Wraps SemanticMemory + the anti-confab gate."""

    def __init__(self, path: str | Path | None = None, *, grounding_llm: Any = None,
                 llm: Any = None, preset: str = "balanced") -> None:
        if preset not in _GATE_PRESETS:
            raise ValueError(
                f"unknown gate preset {preset!r} — one of: "
                f"{', '.join(sorted(_GATE_PRESETS))}")
        self.preset = preset
        self._preset_defaults = _GATE_PRESETS[preset]
        self.semantic = SemanticMemory(db_path=Path(path) if path else None)
        #: trust odometer: persistent counters of what the gate did (admitted /
        #: quarantined / rejected / abstained) — same DB file, fail-open, no PII.
        from .trust_ledger import TrustLedger
        self._ledger = TrustLedger(self.semantic.db_path)
        self.grounding_llm = grounding_llm
        #: extraction LLM for ``add(messages)`` — anything with
        #: ``.complete(system, messages, **kw)``; optional otherwise.
        self.llm = llm

    # ---- write -------------------------------------------------------------
    def add(
        self, content: str | list[dict], *, topic: str = "user",
        source: str | None = None,
        verified_by: list[str] | None = None, validate: str | None = None,
        ground: bool | None = None, gate_mode: str | None = None,
        asserted_at: float | None = None, conversation_id: str | None = None,
        user_name: str | None = None,
    ) -> dict[str, Any]:
        """Store ``text`` AFTER the anti-confab gate. Returns
        ``{stored, id?, status, grounding_score, warnings, advice}``.

        Two gate layers, honest about what runs by default:

        * **L1 lexical screen — always on.** Unsupported "it works / verified /
          completed" self-claims are downgraded to ``quarantined`` (hidden from
          default recall) with no LLM call (~13 ms).
        * **L4 source⊢fact entailment — the moat, opt-in per call.** Pass a
          ``source`` and ``ground=True`` (or set ``ENGRAM_GROUNDING_WRITE=1``)
          and the write is admitted only if the source actually *entails* the
          fact — catching confabulated *inferences* L1 can't. Needs a judge:
          the ``grounding_llm`` you built ``Memory`` with, or the local
          distilled CE (``ENGRAM_GROUNDING_BACKEND=local``). Without a source
          or a judge, L4 is skipped and ``grounding_score`` is ``None``.

        ``gate_mode='reject'`` makes a below-threshold write return
        ``stored=False`` (default ``'downgrade'`` stores it quarantined).

        ``content`` may also be a **conversation** (``list`` of
        ``{"role","content"}`` messages): it is routed through the gated
        conversation ingestion — atomic extraction + consolidation, every fact
        through the gate, conversation provenance. Needs the ``llm`` the
        client was built with. ``asserted_at`` (epoch seconds) stamps the
        EVENT time (bi-temporal v13: when it was said/true — drives
        reconciliation age-gaps and answer-with-history)."""
        if isinstance(content, list):
            if self.llm is None:
                raise ValueError(
                    "add(messages) needs an extraction llm: Memory(..., llm=...)")
            from .conversation_ingest import ingest_conversation
            res = ingest_conversation(
                self.semantic, content, llm=self.llm,
                conversation_id=conversation_id or "sdk",
                topic=topic if topic != "user" else "conversational/ingested",
                asserted_at=asserted_at, embed="sync",
                user_name=user_name)
            # Review 2026-07-09 #1: the ingest path was INVISIBLE to the trust
            # odometer while its facts showed up in the store — ledger and
            # store contradicted each other inside one /v1/stats response.
            # Count from the facts' FINAL stored status (post store-screens).
            self._ledger_ingest_result(res, topic=topic)
            return res
        text = (content or "").strip()
        if not text:
            return {"stored": False, "status": "empty", "warnings": [], "advice": "empty text"}
        # preset defaults fill only what the call left unspecified (None):
        # an explicit per-call parameter always wins over the preset.
        if validate is None:
            validate = self._preset_defaults["validate"]
        if gate_mode is None:
            gate_mode = self._preset_defaults["gate_mode"]
        if ground is None:
            ground = self._preset_defaults["ground"]
        gate = run_validation_gate(
            proposition=text, verified_by=verified_by, topic=topic, agent=self,
            validate=validate, source=source, grounding_llm=self.grounding_llm,
            ground_write=ground or None, gate_mode=gate_mode,
        )
        warnings = list(gate.warnings)
        action = gate.action
        # Source-trust consultation (task #17, behind ENGRAM_SOURCE_TRUST=1,
        # default OFF): a source whose persisted two-channel trust sits below
        # the floor gets QUARANTINED (never rejected — quarantine is
        # rehabilitable, and the consistency channel must be able to fish the
        # source back out; TRUST_CORE.md guard-rail).
        from . import source_trust as _st
        if _st.enabled() and action == "persist":
            _src = _st.canonical_source(verified_by)
            _t = self._source_trust_book().trust(_src)
            if _t < _st.threshold():
                action = "downgrade"
                warnings.append({
                    "layer": "SOURCE_TRUST",
                    "matched_text": _src,
                    "advice": (
                        f"source '{_src}' trust {_t:.2f} is below "
                        f"{_st.threshold():.2f} — stored quarantined pending "
                        "corroboration (confirmations by independent sources "
                        "rehabilitate it)"),
                })
        _layers = sorted({str(w.get("layer", "")) for w in warnings if w.get("layer")})
        if action == "reject":
            self._record_trust("rejected", layers=_layers, topic=topic)
            _emit_flow("flow.write", stored=False, status="rejected",
                       fact_id="", topic=str(topic), layers=_layers)
            return {"stored": False, "status": "rejected", "warnings": warnings,
                    "advice": gate.advice, "grounding_score": gate.grounding_score}
        fact = Fact(proposition=text, topic=topic, verified_by=verified_by or [],
                    grounding_score=gate.grounding_score, asserted_at=asserted_at)
        if action == "downgrade":
            fact.status = "quarantined"
        self.semantic.store(fact, embed="sync")
        # Review 2026-07-09 #2/#3: count AFTER store, from the fact's FINAL
        # status — screens inside store() (injection screen: default ON) can
        # flip a gate-persisted fact to quarantined, and the odometer must
        # report what HAPPENED, not the gate's intention. Layer attribution
        # only when a layer actually ACTED: gate downgrade -> its layers;
        # store-screen flip -> "store-screen"; clean admit -> none (advisory
        # warnings are in the add() response, not in by_layer).
        if fact.status == "quarantined":
            _hit_layers = _layers if action == "downgrade" else ["store-screen"]
            self._record_trust("quarantined", layers=_hit_layers, topic=topic)
        else:
            _hit_layers = []
            self._record_trust("admitted", layers=None, topic=topic)
        # layers in the flow event = which defense actually ACTED (same
        # attribution as the ledger): the Live Engine Room lights the real
        # stage, not a generic box. Metadata only, never fact content.
        _emit_flow("flow.write", stored=True, status=str(fact.status),
                   fact_id=str(fact.id), topic=str(topic), layers=_hit_layers)
        return {
            "stored": True, "id": fact.id, "status": fact.status,
            "grounding_score": gate.grounding_score,
            "warnings": warnings, "advice": gate.advice,
        }

    # ---- read --------------------------------------------------------------
    def search(self, query: str, k: int = 5, *, deep: bool = False,
               as_of: float | str | None = None,
               with_history: bool | str = False,
               include_beliefs: bool = False) -> list[dict[str, Any]]:
        """Recall the top-k facts for ``query``, each with its provenance — the
        differentiator: ``status`` + write-time ``grounding_score`` so a caller can
        prefer/assert grounded facts and hedge low-trust ones.

        * ``deep`` — archaeology: also search dormant memories the freshness
          half-life hides from the default view (integrity guards stay).
        * ``as_of`` (epoch seconds) — time travel: what was CURRENT at that
          moment (asserted by then, not yet superseded). No competitor has it.
          ``as_of="auto"`` routes per query: an explicit retrospective anchor
          in the question ("as of / on / by <date>") activates time travel at
          that date; without one the live recall is byte-identical. Measured
          (routed_asof_ab.json): 10/31 previously-wrong anchored questions
          flip correct, abstention 21/21 intact — the live "[current]" story
          on as-of questions was drowning the answer in future facts.
        * ``with_history`` — each hit carries its transition story
          (``history: [{text, asserted_date, until}]``) from the supersession
          chain: "changed from X to Y on <date>". ``"auto"`` routes per query
          (``wants_history``): temporal wording gets the story (+16pp measured
          on transition questions), plain lookups keep the lean context whose
          abstention on trap questions is pure (1.000 vs 0.949 — the measured
          price of always-on history, docs/TRUST_MAINTENANCE.md).
        * ``include_beliefs`` (anti-sycophancy read-side) — opt unverified USER
          assertions (``status='user_belief'``, produced by the ingest's
          ``tag_beliefs``) back into the result. They are OUT of the default
          view so the memory never serves an uncorroborated user claim back as
          truth; a caller opting in sees ``status`` on each hit and must caveat
          accordingly. Narrow: un-hides beliefs only."""
        if with_history == "auto":
            from .temporal_context import wants_history
            with_history = wants_history(query)
        if as_of == "auto":
            from .temporal_context import extract_as_of
            as_of = extract_as_of(query)
        if as_of is not None:
            from .temporal_context import recall_as_of
            hits = recall_as_of(self.semantic, query, when=float(as_of), k=k,
                                include_beliefs=include_beliefs)
        else:
            hits = self.semantic.recall(query, k=k, deep=deep,
                                        include_beliefs=include_beliefs)
        out: list[dict[str, Any]] = []
        for f, score, *_rest in [h if len(h) >= 2 else (h[0], 0.0) for h in hits]:
            item = {
                "text": getattr(f, "proposition", ""),
                "score": round(float(score), 4),
                "status": getattr(f, "status", "model_claim"),
                "grounding_score": getattr(f, "grounding_score", None),
                "topic": getattr(f, "topic", ""),
                "id": getattr(f, "id", ""),
                # per-fact provenance for trust-conditioned answering (case-B
                # wire, measured 2026-07-16): event time, transaction time,
                # first source episode, and who verified. Raw values — the
                # caller formats; None == genuinely unknown, never invented.
                "asserted_at": getattr(f, "asserted_at", None),
                "created_at": getattr(f, "created_at", None),
                "source": (getattr(f, "source_episodes", None) or [None])[0],
                "verified_by": list(getattr(f, "verified_by", None) or []),
            }
            if with_history:
                from .temporal_context import _event_ts, _iso, fact_history
                item["history"] = [
                    {"text": getattr(p, "proposition", ""),
                     "asserted_date": _iso(_event_ts(p)),
                     "until": getattr(p, "superseded_at", None)}
                    for p in fact_history(self.semantic, item["id"])
                ]
            out.append(item)
        _emit_flow("flow.recall", kind="search", n=len(out),
                   best=round(max((float(i.get("score") or 0.0)
                                   for i in out), default=0.0), 4))
        return out

    def count(self, *, query: str | None = None, topic: str | None = None,
              topic_prefix: str | None = None) -> int:
        """Set-size, NOT top-k — the honest primitive for aggregation queries.

        F1 surface map (retrieval-vs-set-algebra): ``search`` is similarity
        top-k, so "how many times did I mention X?" undercounts (recall k=5
        saw 5 of 12 real mentions). ``count`` SCANS the store instead, so it
        sees the WHOLE matching set:

        * ``query``        — keyword scan; every fact whose proposition
                             contains all query tokens (case-insensitive),
                             optionally within ``topic`` / ``topic_prefix``;
        * ``topic``        — exact-topic scan;
        * ``topic_prefix`` — scoped scan (e.g. one tenant);
        * none             — the whole live corpus (excludes superseded).

        Live facts only (superseded excluded), matching ``search``'s default
        view. This is the primitive; routing a natural-language counting query
        to it is a separate intent step (gateway/F2)."""
        if query is not None:
            return len(self.semantic.search_facts(
                query, limit=1_000_000, require_all_tokens=True,
                topic=topic, topic_prefix=topic_prefix))
        if topic_prefix is not None:
            return len(self.semantic.search_facts(
                "", limit=1_000_000, topic_prefix=topic_prefix))
        if topic is not None:
            return len(self.semantic.list_facts(topic=topic, limit=1_000_000))
        return self.semantic.count()

    def answer(self, query: str, *, llm: Any, k: int = 8,
               verify_threshold: float | None = None,
               trust_conditioning: bool = True) -> dict[str, Any]:
        """Grounding-verified answering — the anti-hallucination read-path.

        Generate an answer from the top-``k`` retrieved facts, then a LOCAL
        cross-encoder (no LLM) checks the answer is ENTAILED by one of those
        facts. If no retrieved fact supports it, abstain (``NO ANSWER``) rather
        than serve a probable hallucination — the memory FINDS the fact
        (recall@30 0.96) but a flat answerer gets fooled by distractors
        (Hallucination 0.167); this closes that gap at answer time.

        ``trust_conditioning`` (default ON) additionally tags every fact with
        the provenance the store already holds — ``[when | source | status]`` —
        and instructs the model to resolve conflicts by metadata (verified >
        unverified, recent > old, first-hand > hearsay; unresolvable → abstain).
        This is the CASE-B lever, measured on the well-grounded-distractor bench
        (sonnet-5, 2026-07-16, 12 cases where BOTH facts pass the grounding gate
        at 76-100 so grounding cannot separate them): bare answer C=0.17/H=0.33
        → trust-conditioned C=0.92/H=0.08, abstaining 2/2 on same-metadata
        conflicts. ``False`` restores the bare v1 prompt byte-identically.

        Returns ``{answer, grounded, support_score, support_fact, raw_answer,
        reason}``. ``raw_answer`` always carries what the model produced (a caught
        hallucination is reported, never silently dropped). Fail-open only when
        the local CE is unavailable (``reason='ce_unavailable_failopen'``) — the
        one honest hole, logged not hidden.

        HONEST SCOPE: the CE post-verify catches an answer NOT supported by ANY
        retrieved fact (inventing beyond memory) — it does NOT separate a wrong
        fact that is ITSELF in memory (the CE serves it as support, measured
        ce_served≈97 on the bench). That separation is exactly what the
        trust-conditioning above buys (0.17→0.92), and its own honest residue is
        a well-grounded distractor whose METADATA also dominates (newer AND
        verified but false) — indistinguishable in principle without an audit.
        """
        hits = self.search(query, k=k)
        if not hits:
            return {"answer": "NO ANSWER", "grounded": False, "reason": "no_facts",
                    "support_score": None, "support_fact": None, "raw_answer": None}
        facts = [h["text"] for h in hits]
        if trust_conditioning:
            lines = [_fact_trust_line(h) for h in hits]
            system = _ANSWER_TRUST_SYSTEM
        else:
            lines = [f"- {t}" for t in facts]
            system = _ANSWER_SYSTEM
        user = "Facts:\n" + "\n".join(lines) + f"\n\nQuestion: {query}"
        resp = llm.complete(system,
                            [{"role": "user", "content": user}], max_tokens=64)
        raw = (getattr(resp, "text", "") or "").strip()

        from .grounding_gate import _is_abstention
        if _is_abstention(raw):
            return {"answer": "NO ANSWER", "grounded": True,
                    "reason": "model_abstained", "support_score": None,
                    "support_fact": None, "raw_answer": raw}

        # local-CE post-verification: is the answer entailed by any retrieved fact?
        from .local_grounding import try_local_score
        thr = (_ANSWER_VERIFY_THRESHOLD if verify_threshold is None
               else float(verify_threshold))
        best_ce, best_fact = -1.0, None
        for t in facts:
            r = try_local_score(t, raw)
            if r is None:  # CE model unavailable -> can't verify; fail-open, logged
                return {"answer": raw, "grounded": True,
                        "reason": "ce_unavailable_failopen", "support_score": None,
                        "support_fact": None, "raw_answer": raw}
            if r[0] > best_ce:
                best_ce, best_fact = r[0], t
        grounded = best_ce >= thr
        return {"answer": raw if grounded else "NO ANSWER", "grounded": grounded,
                "support_score": round(best_ce, 1),
                "support_fact": best_fact if grounded else None, "raw_answer": raw,
                "reason": "grounded" if grounded else "unsupported_by_facts"}

    def ask(self, query: str, *, k: int = 5,
            topic_prefix: str | None = None) -> dict[str, Any]:
        """Intent-routed query — the read-path twin of the write-path
        provenance router (surface-map thesis: classify before acting).

        A cardinality question ("how many times did I discuss X?") routes to a
        full-corpus SCAN/count, not top-k recall (which undercounts — F1 saw
        5/12). Enumeration ("list all X") returns the whole matching set.
        Everything else is FIND: ordinary semantic recall, unchanged. Returns
        ``{"intent", ...}`` — ``count`` for COUNT, ``results`` otherwise — so
        the caller always knows which operation ran.

        FIND is the safe default: a misclassified query behaves exactly like
        ``search`` today. This is the dispatcher; the classifier lives in
        engram.query_intent (lexical, EN+IT)."""
        from .query_intent import (
            COUNT,
            EXCLUDE,
            FIND,
            LIST_ALL,
            classify_query_intent,
            content_terms,
        )
        intent = classify_query_intent(query)
        if intent == COUNT:
            terms = content_terms(query)
            n = (self.count(query=terms, topic_prefix=topic_prefix)
                 if terms else self.count(topic_prefix=topic_prefix))
            return {"intent": COUNT, "terms": terms, "count": n}
        if intent == LIST_ALL:
            terms = content_terms(query)
            rows = self.semantic.search_facts(
                terms, limit=1000, require_all_tokens=bool(terms),
                topic_prefix=topic_prefix)
            return {"intent": LIST_ALL, "terms": terms,
                    "results": [{"text": f.proposition, "id": f.id,
                                 "topic": f.topic} for f in rows]}
        if intent == EXCLUDE:
            # Set-difference: the scoped corpus MINUS the facts matching the
            # excluded terms. Embeddings ignore "not"; this executes it as a
            # scan + removal (F1 negation fall). Base is the whole scope so a
            # generic subject never zeroes the set.
            from .query_intent import split_exclude
            _subj, excluded = split_exclude(query)
            base = (self.semantic.search_facts("", limit=10000,
                                               topic_prefix=topic_prefix)
                    if topic_prefix else self.semantic.list_facts(limit=10000))
            excl_ids: set[str] = set()
            if excluded:
                excl_ids = {f.id for f in self.semantic.search_facts(
                    excluded, limit=10000, require_all_tokens=True,
                    topic_prefix=topic_prefix)}
            results = [f for f in base if f.id not in excl_ids]
            return {"intent": EXCLUDE, "excluded": excluded,
                    "results": [{"text": f.proposition, "id": f.id,
                                 "topic": f.topic} for f in results]}
        return {"intent": FIND, "results": self.search(query, k=k)}

    def explain(self, query: str, k: int = 5, *, deep: bool = False,
                as_of: float | None = None,
                min_relevance: float | str | None = None) -> dict[str, Any]:
        """The evidence dossier behind an answer — the trust gate made atomic:
        per fact the full chain of custody (provenance, writer, status,
        verified_by, grounding, the two clocks, what it replaced, declared
        disputes) or an EXPLICIT abstention with its reason. Judge-grade
        "how do you know?" for any query.

        ``min_relevance`` (default 0.0 = off) applies a retrieval floor so a
        query with no relevant fact abstains without an LLM.
        ``min_relevance="auto"`` lets the STORE calibrate the floor itself
        (scrambled-probe noise quantile, engram.relevance_floor): measured on
        external data (HaluEval dev n=100, 2026-07-10) the self-calibrated
        floor landed at 0.7987 vs 0.80 hand-picked from the labeled curve —
        false_answer 1.0→0.04 at 0.10 over-abstention. A fixed default cannot
        do this: e5 scores live in [0.73, 0.95], so any constant is wrong for
        some store/embedder pair. Estimation (~32 probe recalls) is cached
        for 5 minutes. The resolved value is reported as
        ``report["min_relevance"]``.

        ``min_relevance=None`` (the default) reads the ``ENGRAM_MIN_RELEVANCE`` env —
        the single switch to turn read-path abstention ON across every surface
        (``auto`` | ``<float>`` | ``off``); unset → 0.0 (permissive, backward-compat)."""
        if min_relevance is None:
            from .relevance_floor import env_floor
            min_relevance = env_floor()
        if min_relevance == "auto":
            min_relevance = self._auto_relevance_floor()
        from .trust_report import build_trust_report
        report = build_trust_report(self.semantic, query, k=k, deep=deep,
                                    as_of=as_of, min_relevance=min_relevance)
        report["min_relevance"] = float(min_relevance)
        # task #20a: dossier transparency — with source-trust on, every fact
        # shows its SOURCE's two-channel trust, not just its own status.
        from . import source_trust as _st
        if _st.enabled():
            book = self._source_trust_book()
            for e in report.get("facts") or []:
                src = _st.canonical_source(e.get("verified_by"))
                e["source_trust"] = {"source": src,
                                     "trust": round(book.trust(src), 4)}
        if report.get("abstained"):
            # honest-"I don't know" counter — the read-path half of the odometer
            self._record_trust("abstained")
        _emit_flow("flow.recall", kind="explain",
                   n=len(report.get("facts") or []),
                   abstained=bool(report.get("abstained")))
        return report

    # ---- source trust (task #17, behind ENGRAM_SOURCE_TRUST) ----------------

    def _source_trust_book(self):
        """The process-shared per-path book (the store-side supersession hook
        mutates the SAME object — a private cache here would diverge)."""
        from .source_trust import get_book
        return get_book(self.semantic.db_path)

    def source_trust_observe(self, *, confirmation: list[str] | None = None,
                             contradiction: str | None = None,
                             outcome: tuple[str, bool, float] | None = None,
                             reports: dict[str, dict[str, str]] | None = None,
                             audited_false: tuple[str, str] | None = None,
                             ) -> None:
        """Feed the per-source book and persist it. ``confirmation`` = ≥2
        distinct sources asserted the same accepted value; ``contradiction``
        = this source contradicted an accepted value; ``outcome`` =
        (source, good, weight) — weight<1 attenuates stale blame (task #18).

        ``reports`` = {source: {key: value}} that each confirmer asserted — the
        independence substrate: with ENGRAM_SOURCE_INDEPENDENCE=1 the confirmation
        needs ≥2 INDEPENDENT clusters, so copies/colluders of one feed (identical
        report vectors) collapse to one witness instead of self-confirming.
        ``audited_false`` = (key, value) an audit revealed FALSE — the do-operator
        anchor for ENGRAM_SOURCE_INDEPENDENCE_DECONFOUND (P88): colluders co-admit
        it, honest sources do not, so honest agreement is no longer false-merged.

        RETROACTIVE DEMOTION (judge finding, seeds 12-13): reputation crosses
        the floor only after a few contradictions, so a liar's EARLY writes
        were staying admitted. When an observation sinks a source BELOW the
        floor (crossing, not every update), its already-stored facts are
        re-evaluated: quarantined — rehabilitable, never deleted (guard-rail).
        Flag-gated like the rest of the wiring."""
        from .source_trust import (
            enabled,
            independence_deconfounded,
            independence_enabled,
            save_book,
            threshold,
        )
        book = self._source_trust_book()
        if audited_false:
            book.mark_false(*audited_false)
        watched = {s for s in (contradiction,
                               outcome[0] if outcome else None) if s}
        pre = {s: book.trust(s) for s in watched}
        # trust BEFORE this observation for every source it touches (confirmers
        # included) — the recovery crossing-up is read against these.
        pre_all = {s: book.trust(s)
                   for s in set(watched) | set(confirmation or [])}
        if confirmation:
            for src_id, kv in (reports or {}).items():
                for k, v in (kv or {}).items():
                    book.record_report(src_id, k, v)
            book.observe_confirmation(
                confirmation, require_independent=independence_enabled(),
                deconfounded=independence_deconfounded())
        if contradiction:
            book.observe_contradiction(contradiction)
        if outcome:
            src, good, weight = outcome
            book.observe_outcome(src, good=good, weight=weight)
        save_book(self.semantic.db_path, book)
        if enabled():
            thr = threshold()
            for s in watched:
                if pre.get(s, 1.0) >= thr and book.trust(s) < thr:
                    self._retro_demote_source(s)          # crossing DOWN
        # crossing UP: a recovered source's OWN source-trust demotions reverse
        # (guard-rail rehabilitation path). confirmations are the recovery.
        if enabled() and confirmation:
            thr = threshold()
            for s in confirmation:
                if pre_all.get(s, 0.0) < thr <= book.trust(s):
                    self._rehabilitate_source(s)

    def report_outcome(self, fact_id: str, *, good: bool,
                       weight: float = 1.0) -> bool:
        """The OUTCOME channel's application entry point: report that a stored fact
        succeeded or FAILED in use. Feeds the source's outcome reputation and — on a
        FAILURE — marks the fact's (topic, proposition) audit-revealed FALSE. That
        anchor is the do-operator that lets the deconfounded independence tell a copy
        cartel of LIARS apart from honest sources who merely agree on the truth — the
        second channel the write-path alone cannot supply (benchmark/
        independence_dense_honest.py). Returns False if the fact is unknown.

        No flag of its own: the reputation update is inert unless the gate consults it
        (ENGRAM_SOURCE_TRUST) and the audit anchor unless deconfound is on."""
        fact = self.semantic.get(fact_id)
        if fact is None:
            return False
        from .source_trust import canonical_source
        source = canonical_source(getattr(fact, "verified_by", None))
        topic = (getattr(fact, "topic", "") or "").strip()
        prop = (getattr(fact, "proposition", "") or "").strip()
        audited = (topic, prop) if (not good and topic and prop) else None
        self.source_trust_observe(outcome=(source, good, weight),
                                  audited_false=audited)
        return True

    _SOURCE_REF_PREFIXES = ("source-doc", "source", "src", "doc", "file")
    _DEMOTE_TABLE = ("CREATE TABLE IF NOT EXISTS source_trust_demotions ("
                     "fact_id TEXT PRIMARY KEY, source TEXT NOT NULL)")

    def _retro_demote_source(self, source: str) -> None:
        """Quarantine every non-quarantined fact citing ``source`` — the
        write-time gate only stops FUTURE lies; the crossing re-evaluates the
        past ones. Each demoted id is RECORDED so recovery can restore exactly
        these (never an L1/L4 quarantine). Best-effort."""
        import sqlite3 as _sq
        clauses = " OR ".join(["verified_by LIKE ?"] * len(self._SOURCE_REF_PREFIXES))
        params = [f'%"{p}:{source}:%' for p in self._SOURCE_REF_PREFIXES]
        try:
            with _sq.connect(str(self.semantic.db_path)) as conn:
                conn.execute(self._DEMOTE_TABLE)
                rows = conn.execute(
                    f"SELECT id FROM facts WHERE status != 'quarantined' "
                    f"AND ({clauses})", params).fetchall()
        except _sq.Error:
            return
        for (fid,) in rows:
            try:
                if self.semantic.quarantine_fact(
                    fid, reason=(f"source '{source}' trust sank below the "
                                 "floor — retroactive demotion")):
                    with _sq.connect(str(self.semantic.db_path)) as conn:
                        conn.execute(
                            "INSERT OR REPLACE INTO source_trust_demotions "
                            "(fact_id, source) VALUES (?, ?)", (fid, source))
                        conn.commit()
            except Exception:  # noqa: BLE001 — best-effort per fact
                continue

    def _rehabilitate_source(self, source: str) -> None:
        """Restore ONLY the facts THIS source-trust demoted (recorded ids) —
        an L1/L4 quarantine is never touched. The reverse of the crossing."""
        import sqlite3 as _sq
        try:
            with _sq.connect(str(self.semantic.db_path)) as conn:
                conn.execute(self._DEMOTE_TABLE)
                rows = conn.execute(
                    "SELECT fact_id FROM source_trust_demotions WHERE source=?",
                    (source,)).fetchall()
        except _sq.Error:
            return
        for (fid,) in rows:
            try:
                self.semantic.restore_fact(
                    fid, reason=f"source '{source}' recovered above the floor")
            except Exception:  # noqa: BLE001 — best-effort per fact
                pass
        try:
            with _sq.connect(str(self.semantic.db_path)) as conn:
                conn.execute(
                    "DELETE FROM source_trust_demotions WHERE source=?",
                    (source,))
                conn.commit()
        except _sq.Error:
            pass

    # ---- decision chain (task #15) ------------------------------------------

    def _decisions(self):
        """Lazy DecisionStore on a sibling DB (decisions.db next to
        semantic.db — the documents.py sibling-path pattern). Built on first
        WRITE so a pure read never creates the file."""
        ds = getattr(self, "_decision_store", None)
        if ds is None:
            from pathlib import Path as _P

            from .decision_chain import DecisionStore
            ds = self._decision_store = DecisionStore(
                _P(self.semantic.db_path).with_name("decisions.db"))
        return ds

    def _decisions_ro(self):
        """Read-only handle: None if no decisions.db exists yet (a why/list
        must not materialise the store)."""
        from pathlib import Path as _P
        if getattr(self, "_decision_store", None) is not None:
            return self._decision_store
        if _P(self.semantic.db_path).with_name("decisions.db").exists():
            return self._decisions()
        return None

    def record_decision(self, decision: str, *,
                        alternatives: list[str] | None = None,
                        evidence: list[str] | None = None,
                        expected: str = "", revisit_at: float | None = None,
                        topic: str = "decisions/general") -> str:
        """Record a decision as a first-class cited record — the choice, the
        alternatives rejected, the evidence (fact ids) considered, the
        expected outcome. Answerable later via ``why_decision``."""
        return self._decisions().record(
            decision=decision, alternatives=alternatives, evidence=evidence,
            expected=expected, revisit_at=revisit_at, topic=topic)

    def decision_outcome(self, decision_id: str, outcome: str, *,
                         verified_by: list[str]) -> bool:
        """Attach the MEASURED outcome to a decision — requires evidence
        (guard-rail), updates only the record, never the cited sources."""
        return self._decisions().record_outcome(
            decision_id, outcome, verified_by=verified_by)

    def why_decision(self, question: str, *, limit: int = 5) -> list[dict]:
        """"Why did we choose X?" → matching decisions with their cited
        evidence ids. Empty list when nothing was ever recorded."""
        ds = self._decisions_ro()
        if ds is None:
            return []
        return [{"id": d.id, "decision": d.decision, "topic": d.topic,
                 "alternatives": d.alternatives, "evidence": d.evidence,
                 "expected": d.expected, "outcome": d.outcome,
                 "outcome_verified_by": d.outcome_verified_by}
                for d in ds.why(question, limit=limit)]

    def source_trust(self, source: str) -> float:
        """Combined (min-of-observed-channels) trust for ``source``."""
        return self._source_trust_book().trust(source)

    def consistency_trust(self, source: str) -> float:
        return self._source_trust_book().consistency(source)

    _FLOOR_CACHE_TTL_S = 300.0

    def _auto_relevance_floor(self) -> float:
        """Resolve the self-calibrated floor, cached per client for the TTL —
        estimation costs ~32 probe recalls, which must not be paid per query."""
        import time as _time
        cached = getattr(self, "_floor_cache", None)
        now = _time.time()
        if cached and now - cached[0] < self._FLOOR_CACHE_TTL_S:
            return cached[1]
        from .relevance_floor import estimate_relevance_floor
        val = estimate_relevance_floor(self.semantic)
        self._floor_cache = (now, val)
        return val

    def _record_trust(self, action: str, layers: list[str] | None = None,
                      topic: str = "") -> None:
        """Ledger write that can never cost the caller anything — defence in
        depth on top of the ledger's own fail-open (a buggy or replaced
        ledger must still not break add/explain)."""
        try:
            self._ledger.record(action, layers=layers, topic=topic)
        except Exception:
            pass

    def _ledger_ingest_result(self, res: dict, *, topic: str) -> None:
        """Count a conversation-ingest batch in the trust odometer, from the
        FINAL stored status of each fact (screens inside store() included).
        Fail-open: counting must never break the ingest that just succeeded."""
        try:
            ids = list(res.get("fact_ids") or [])
            by_status: dict[str, int] = {}
            if ids:
                qmarks = ",".join("?" * len(ids))
                with sqlite3.connect(str(self.semantic.db_path)) as con:
                    for status, n in con.execute(
                            f"SELECT status, COUNT(*) FROM facts "
                            f"WHERE id IN ({qmarks}) GROUP BY status", ids):
                        by_status[str(status)] = int(n)
            n_quar = by_status.pop("quarantined", 0)
            n_admitted = sum(by_status.values())
            if n_quar:
                self._ledger.record_many("quarantined", n_quar,
                                         layers=["ingest"], topic=topic)
            if n_admitted:
                self._ledger.record_many("admitted", n_admitted, topic=topic)
            n_rej = int(res.get("rejected") or 0)
            if n_rej:
                self._ledger.record_many("rejected", n_rej,
                                         layers=["ingest"], topic=topic)
        except Exception:
            pass

    def trust_stats(self) -> dict[str, Any]:
        """The trust odometer: what the gate DID on this store, live.

        ``ledger`` — persistent per-action counters (admitted / quarantined /
        rejected / abstained), counted from each fact's FINAL stored status
        (store-screens included) and covering the conversation-ingest path
        too; ``by_layer`` attributes only layers that actually ACTED (advisory
        warnings stay in the add() response). ``store`` — a SNAPSHOT of the
        live facts by status (a quarantined fact later deleted leaves the
        snapshot but stays in the cumulative ledger — different questions,
        both honest). ``abstained`` counts explain() abstention EVENTS (not
        deduped by query; plain search() misses are not abstentions).
        ``ledger_write_failures`` — events this process dropped because the
        ledger itself failed (fail-open stays, but visibly)."""
        out = self._ledger.stats()
        store: dict[str, int] = {}
        try:
            with sqlite3.connect(str(self.semantic.db_path)) as con:
                for status, n in con.execute(
                        "SELECT status, COUNT(*) FROM facts "
                        "WHERE superseded_by IS NULL GROUP BY status"):
                    store[str(status)] = int(n)
        except Exception:
            pass
        out["store"] = store
        out["ledger_write_failures"] = int(
            getattr(self._ledger, "write_failures", 0) or 0)
        return out

    def quarantine_log(self, *, limit: int = 50) -> list[dict[str, Any]]:
        """The blocked-claims log: live QUARANTINED facts, newest first.

        The odometer says HOW MANY the gate stopped; this says WHAT — each
        unsupported claim the gate downgraded, with topic and timestamp, so a
        human can audit the stops (and rescue a false positive via
        ``verified_by`` + update). Read-only; deleted/superseded quarantined
        facts drop out of this view but stay counted in the ledger."""
        rows: list[dict[str, Any]] = []
        try:
            with sqlite3.connect(str(self.semantic.db_path)) as con:
                con.row_factory = sqlite3.Row
                for r in con.execute(
                        "SELECT id, proposition, topic, created_at, status "
                        "FROM facts WHERE status = 'quarantined' "
                        "AND superseded_by IS NULL "
                        "ORDER BY created_at DESC LIMIT ?",
                        (max(1, int(limit)),)):
                    rows.append(dict(r))
        except Exception:
            pass  # read-only view: an unreadable store shows empty, not 500
        return rows

    #: ``recall`` is the same operation as ``search`` (HippoAgent naming).
    recall = search

    @staticmethod
    def _fact_view(f: Any, *, fact_id: str = "") -> dict[str, Any]:
        """One fact as the SDK dict — the SAME provenance surface everywhere
        (audit mod.8: get/get_all lacked the fields search exposes, so a
        trust-conditioning caller lost verified_by the moment it re-fetched)."""
        return {
            "id": getattr(f, "id", fact_id),
            "text": getattr(f, "proposition", ""),
            "status": getattr(f, "status", "model_claim"),
            "grounding_score": getattr(f, "grounding_score", None),
            "topic": getattr(f, "topic", ""),
            "asserted_at": getattr(f, "asserted_at", None),
            "created_at": getattr(f, "created_at", None),
            "source": (getattr(f, "source_episodes", None) or [None])[0],
            "verified_by": list(getattr(f, "verified_by", None) or []),
        }

    def get(self, fact_id: str) -> dict[str, Any] | None:
        """Fetch one stored fact by id (with its provenance), or None."""
        f = self.semantic.get(fact_id)
        if f is None:
            return None
        return self._fact_view(f, fact_id=fact_id)

    def delete(self, fact_id: str, *, purge_history: bool = False) -> bool:
        """Forget a fact by id (privacy / GDPR). True iff at least a row was removed.

        ``purge_history=True`` — the GDPR-grade delete (probe-confirmed defect
        2026-07-06: a plain delete removes ONE row while superseded predecessors
        carrying the SAME sensitive datum survive and RESURFACE via deep recall
        and ``as_of`` time travel). It removes the whole supersession chain —
        predecessors (recursive) and forward successors — plus their
        unresolved-dispute ledger entries. Default False = single-row delete,
        behaviour unchanged."""
        if not purge_history:
            return self.semantic.delete(fact_id)
        ids: set[str] = set()
        # forward: the live successors this fact was replaced by
        try:
            for f in self.semantic.get_supersession_chain(fact_id):
                ids.add(getattr(f, "id", ""))
        except Exception:  # noqa: BLE001 — best-effort walk, delete goes on
            ids.add(fact_id)
        # backward: EVERY predecessor generation (full closure, all branches —
        # a partial purge would leave sensitive rows resurrectable via as_of)
        frontier = list(ids)
        while frontier:
            nxt: list[str] = []
            for fid in frontier:
                try:
                    for p in self.semantic.direct_predecessors(fid, limit=1000):
                        pid = getattr(p, "id", "")
                        if pid and pid not in ids:
                            ids.add(pid)
                            nxt.append(pid)
                except Exception:  # noqa: BLE001
                    continue
            frontier = nxt
        removed = False
        for fid in ids:
            try:
                removed = self.semantic.delete(fid) or removed
            except Exception:  # noqa: BLE001 — one failed row must not stop the purge
                continue
        # scrub the dispute ledger referencing purged facts (best-effort)
        try:
            import sqlite3

            from .contradiction import ContradictionStore
            cs = ContradictionStore(self.semantic.db_path)
            with sqlite3.connect(str(cs.db_path if hasattr(cs, "db_path")
                                     else self.semantic.db_path)) as con:
                qmarks = ",".join("?" for _ in ids)
                con.execute(
                    f"DELETE FROM contradictions WHERE fact_a_id IN ({qmarks}) "
                    f"OR fact_b_id IN ({qmarks})", (*ids, *ids))
                con.commit()
        except Exception:  # noqa: BLE001 — ledger scrub is best-effort
            pass
        return removed

    def get_all(self, *, topic: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """List stored facts (with provenance), newest-relevant first. mem0/Zep parity."""
        return [self._fact_view(f)
                for f in self.semantic.list_facts(limit=limit, topic=topic)]

    def update(self, fact_id: str, text: str, *, topic: str | None = None) -> dict[str, Any]:
        """Revise a fact. Engram facts are immutable + auditable, so an update STORES a new
        fact (through the gate) and SUPERSEDES the old one — the old version stays in the
        provenance chain (see :meth:`history`), it is not destroyed. Returns the add result
        plus ``supersedes``."""
        old = self.semantic.get(fact_id)
        if old is None:
            return {"updated": False, "reason": "not found"}
        res = self.add(text, topic=topic or getattr(old, "topic", "user"))
        if res.get("stored") and res.get("id"):
            try:
                self.semantic.supersede(fact_id, res["id"], reason="sdk update")
            except Exception as exc:  # noqa: BLE001
                return {**res, "updated": True, "supersedes": fact_id, "supersede_warning": str(exc)}
        return {**res, "updated": bool(res.get("stored")), "supersedes": fact_id}

    def history(self, fact_id: str) -> list[dict[str, Any]]:
        """The FULL supersession trail of the lineage containing ``fact_id`` —
        the provenance trail no cosine-only store has:
        ``[{id, text, status, superseded_by}, …]`` oldest→newest.

        Any id in the chain returns the same trail (audit mod.8, reproduced
        2026-07-17): the walk was forward-only, so the id a caller most
        naturally holds — the CURRENT fact, e.g. from ``search`` — returned a
        1-entry "trail" while the oldest id returned the whole story. Now the
        walk first rewinds to the lineage root (``direct_predecessors``,
        following the primary — most recently retired — predecessor at each
        step; a multi-predecessor MERGE keeps its side branches reachable via
        their own ids), then plays forward as before."""
        start = self.semantic.get(fact_id)
        if start is None:
            return []
        # rewind to the lineage root (cycle-guarded like the forward walk)
        root = start
        back_seen = {getattr(start, "id", "")}
        while True:
            try:
                preds = self.semantic.direct_predecessors(
                    getattr(root, "id", ""), limit=1)
            except Exception:  # noqa: BLE001 — degrade to the forward-only view
                break
            if not preds or getattr(preds[0], "id", "") in back_seen:
                break
            root = preds[0]
            back_seen.add(getattr(root, "id", ""))
        chain: list[dict[str, Any]] = []
        seen: set[str] = set()
        cur = root
        while cur is not None and getattr(cur, "id", None) not in seen:
            cid = getattr(cur, "id", "")
            seen.add(cid)
            nxt = getattr(cur, "superseded_by", None)
            chain.append({"id": cid, "text": getattr(cur, "proposition", ""),
                          "status": getattr(cur, "status", ""), "superseded_by": nxt})
            cur = self.semantic.get(nxt) if nxt else None
        return chain


#: Alias for users who expect a ``Client`` name (mem0/Zep ergonomics).
Client = Memory

__all__ = ["Memory", "Client"]
