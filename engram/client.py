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

from pathlib import Path
from typing import Any

from .anti_confab_gate import run_validation_gate
from .semantic import Fact, SemanticMemory


class Memory:
    """Turnkey persistent-memory client. Wraps SemanticMemory + the anti-confab gate."""

    def __init__(self, path: str | Path | None = None, *, grounding_llm: Any = None) -> None:
        self.semantic = SemanticMemory(db_path=Path(path) if path else None)
        self.grounding_llm = grounding_llm

    # ---- write -------------------------------------------------------------
    def add(
        self, text: str, *, topic: str = "user", source: str | None = None,
        verified_by: list[str] | None = None, validate: str = "fast",
        ground: bool = False, gate_mode: str | None = None,
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
        ``stored=False`` (default ``'downgrade'`` stores it quarantined)."""
        text = (text or "").strip()
        if not text:
            return {"stored": False, "status": "empty", "warnings": [], "advice": "empty text"}
        gate = run_validation_gate(
            proposition=text, verified_by=verified_by, topic=topic, agent=self,
            validate=validate, source=source, grounding_llm=self.grounding_llm,
            ground_write=ground or None, gate_mode=gate_mode,
        )
        if gate.action == "reject":
            return {"stored": False, "status": "rejected", "warnings": list(gate.warnings),
                    "advice": gate.advice, "grounding_score": gate.grounding_score}
        fact = Fact(proposition=text, topic=topic, verified_by=verified_by or [],
                    grounding_score=gate.grounding_score)
        if gate.action == "downgrade":
            fact.status = "quarantined"
        self.semantic.store(fact, embed="sync")
        return {
            "stored": True, "id": fact.id, "status": fact.status,
            "grounding_score": gate.grounding_score,
            "warnings": list(gate.warnings), "advice": gate.advice,
        }

    # ---- read --------------------------------------------------------------
    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Recall the top-k facts for ``query``, each with its provenance — the
        differentiator: ``status`` + write-time ``grounding_score`` so a caller can
        prefer/assert grounded facts and hedge low-trust ones."""
        out: list[dict[str, Any]] = []
        for f, score in self.semantic.recall(query, k=k):
            out.append({
                "text": getattr(f, "proposition", ""),
                "score": round(float(score), 4),
                "status": getattr(f, "status", "model_claim"),
                "grounding_score": getattr(f, "grounding_score", None),
                "topic": getattr(f, "topic", ""),
                "id": getattr(f, "id", ""),
            })
        return out

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

    def delete(self, fact_id: str) -> bool:
        """Forget one fact by id (privacy / GDPR). True iff a row was removed."""
        return self.semantic.delete(fact_id)

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
