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
        _layers = sorted({str(w.get("layer", "")) for w in gate.warnings if w.get("layer")})
        if gate.action == "reject":
            self._record_trust("rejected", layers=_layers, topic=topic)
            return {"stored": False, "status": "rejected", "warnings": list(gate.warnings),
                    "advice": gate.advice, "grounding_score": gate.grounding_score}
        fact = Fact(proposition=text, topic=topic, verified_by=verified_by or [],
                    grounding_score=gate.grounding_score, asserted_at=asserted_at)
        if gate.action == "downgrade":
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
            self._record_trust(
                "quarantined",
                layers=_layers if gate.action == "downgrade" else ["store-screen"],
                topic=topic)
        else:
            self._record_trust("admitted", layers=None, topic=topic)
        return {
            "stored": True, "id": fact.id, "status": fact.status,
            "grounding_score": gate.grounding_score,
            "warnings": list(gate.warnings), "advice": gate.advice,
        }

    # ---- read --------------------------------------------------------------
    def search(self, query: str, k: int = 5, *, deep: bool = False,
               as_of: float | str | None = None,
               with_history: bool | str = False) -> list[dict[str, Any]]:
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
          price of always-on history, docs/TRUST_MAINTENANCE.md)."""
        if with_history == "auto":
            from .temporal_context import wants_history
            with_history = wants_history(query)
        if as_of == "auto":
            from .temporal_context import extract_as_of
            as_of = extract_as_of(query)
        if as_of is not None:
            from .temporal_context import recall_as_of
            hits = recall_as_of(self.semantic, query, when=float(as_of), k=k)
        else:
            hits = self.semantic.recall(query, k=k, deep=deep)
        out: list[dict[str, Any]] = []
        for f, score, *_rest in [h if len(h) >= 2 else (h[0], 0.0) for h in hits]:
            item = {
                "text": getattr(f, "proposition", ""),
                "score": round(float(score), 4),
                "status": getattr(f, "status", "model_claim"),
                "grounding_score": getattr(f, "grounding_score", None),
                "topic": getattr(f, "topic", ""),
                "id": getattr(f, "id", ""),
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
        return out

    def explain(self, query: str, k: int = 5, *, deep: bool = False,
                as_of: float | None = None,
                min_relevance: float = 0.0) -> dict[str, Any]:
        """The evidence dossier behind an answer — the trust gate made atomic:
        per fact the full chain of custody (provenance, writer, status,
        verified_by, grounding, the two clocks, what it replaced, declared
        disputes) or an EXPLICIT abstention with its reason. Judge-grade
        "how do you know?" for any query.

        ``min_relevance`` (default 0.0 = off) applies a retrieval floor so a
        query with no relevant fact abstains without an LLM — see
        ``build_trust_report`` for why it is opt-in (anisotropic bi-encoder)."""
        from .trust_report import build_trust_report
        report = build_trust_report(self.semantic, query, k=k, deep=deep,
                                    as_of=as_of, min_relevance=min_relevance)
        if report.get("abstained"):
            # honest-"I don't know" counter — the read-path half of the odometer
            self._record_trust("abstained")
        return report

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

    def get(self, fact_id: str) -> dict[str, Any] | None:
        """Fetch one stored fact by id (with its provenance), or None."""
        f = self.semantic.get(fact_id)
        if f is None:
            return None
        return {
            "id": getattr(f, "id", fact_id),
            "text": getattr(f, "proposition", ""),
            "status": getattr(f, "status", "model_claim"),
            "grounding_score": getattr(f, "grounding_score", None),
            "topic": getattr(f, "topic", ""),
        }

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
        return [{
            "id": getattr(f, "id", ""),
            "text": getattr(f, "proposition", ""),
            "status": getattr(f, "status", "model_claim"),
            "grounding_score": getattr(f, "grounding_score", None),
            "topic": getattr(f, "topic", ""),
        } for f in self.semantic.list_facts(limit=limit, topic=topic)]

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
        """The supersession chain from this fact forward — the provenance trail no
        cosine-only store has: ``[{id, text, status, superseded_by}, …]`` oldest→newest,
        so a caller can see what a fact became and whether it's still current."""
        chain: list[dict[str, Any]] = []
        seen: set[str] = set()
        cur = self.semantic.get(fact_id)
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
