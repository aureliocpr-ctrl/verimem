"""Reasoning dossier — the multi-hop answer WITH its cited derivation.

``EntityStore.traced_paths`` yields the edge chain; this layer turns it into
a product-grade answer: it hydrates each hop with the real PROPOSITION behind
it (the fact that generated the edge) and composes a readable, citable
derivation — or an honest ABSTENTION when a hop is not grounded or its cited
fact has since vanished from the store.

This is the TrustReport of reasoning. Every memory system can (maybe) reach
"Acme" from "Alice"; none of them hands back *why*, as a chain of custody the
caller can audit — and none of them ABSTAINS when the chain has a gap rather
than fabricating the link. That is the whole point of Verimem, applied to the
graph.

Pure and deterministic: EntityStore reads + fact lookups, no model, no
network. ``semantic`` is anything exposing ``get(fact_id) -> obj|None`` with a
``.proposition`` (SemanticMemory satisfies it).
"""
from __future__ import annotations

from typing import Any


def _entity_name(store: Any, entity_id: str) -> str:
    try:
        ent = store.get(entity_id) if hasattr(store, "get") else None
    except Exception:  # noqa: BLE001
        ent = None
    name = getattr(ent, "canonical_name", None)
    return name or entity_id


def _dossier_for_path(store: Any, semantic: Any, src_id: str,
                      path: dict[str, Any]) -> dict[str, Any]:
    """Hydrate ONE traced path into a cited derivation or an abstention."""
    target = path["target"]
    answer_name = _entity_name(store, target)
    base = {
        "target": target,
        "min_weight": path.get("min_weight"),
        "path_weight": path.get("path_weight"),
    }

    # ungrounded hop: the edge cites no fact -> we cannot show why -> abstain
    ungrounded = [h for h in path["hops"] if not h.get("source_fact_id")]
    if ungrounded or not path.get("grounded", False):
        preds = ", ".join(h["predicate"] for h in ungrounded) or "a hop"
        return {**base, "abstained": True, "grounded": False, "answer": None,
                "reason": f"path to {answer_name} is not grounded "
                          f"({preds} has no source fact)"}

    # grounded: fetch the proposition behind each hop; a missing fact
    # (superseded/deleted) is an honest gap, not a place to invent text
    derivation: list[dict[str, Any]] = []
    for hop in path["hops"]:
        fid = hop["source_fact_id"]
        fact = None
        try:
            fact = semantic.get(fid)
        except Exception:  # noqa: BLE001
            fact = None
        prop = getattr(fact, "proposition", None)
        if not prop:
            return {**base, "abstained": True, "grounded": False,
                    "answer": None,
                    "reason": f"source fact {fid} for the "
                              f"'{hop['predicate']}' hop is no longer in the "
                              f"store — abstaining instead of fabricating"}
        derivation.append({
            "from_entity": _entity_name(store, hop["src_entity"]),
            "to_entity": _entity_name(store, hop["dst_entity"]),
            "predicate": hop["predicate"],
            "source_fact_id": fid,
            "weight": hop["weight"],
            "proposition": prop,
        })
    chain = " ⊕ ".join(
        f'[{s["proposition"]} ({s["source_fact_id"]})]' for s in derivation)
    return {**base, "abstained": False, "grounded": True,
            "answer": answer_name, "derivation": derivation,
            "chain": f"{answer_name} — derived from: {chain}"}


def reasoning_dossier(
    store: Any, semantic: Any, src_entity_id: str, *,
    target: str | None = None, max_hops: int = 2, k: int = 10,
) -> Any:
    """Multi-hop reasoning with a chain of custody.

    With ``target`` set: returns ONE dossier for the best path to that entity
    (or an abstention if unreachable / ungrounded / a cited fact is missing).
    Without ``target``: returns a LIST of dossiers, one per reachable entity,
    each already grounded-or-abstained. Shortest paths first (fewest links =
    most trust), via ``traced_paths``.
    """
    paths = store.traced_paths(src_entity_id, max_hops=max_hops, k=k)

    if target is not None:
        chosen = next((p for p in paths if p["target"] == target), None)
        if chosen is None:
            return {"target": target, "abstained": True, "grounded": False,
                    "answer": None,
                    "reason": f"no path from {_entity_name(store, src_entity_id)} "
                              f"to {_entity_name(store, target)} within "
                              f"{max_hops} hops (unreachable)"}
        return _dossier_for_path(store, semantic, src_entity_id, chosen)

    return [_dossier_for_path(store, semantic, src_entity_id, p) for p in paths]


__all__ = ["reasoning_dossier"]
