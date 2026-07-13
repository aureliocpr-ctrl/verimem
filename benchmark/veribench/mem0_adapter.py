"""Run mem0 (the real, shipping competitor) on the VeriBench axis — OFFLINE.

The sharpest criticism of a self-built benchmark is "you only compared against a
strawman baseline you wrote yourself." This closes it: it drives **mem0's actual
retrieval stack** (its `Memory`, its Chroma vector store, its `search`) on the
same corpus, with the **same e5 embedder and the same e5 prefixes as verimem**, so
the only free variable is the one VeriBench is about — the abstention floor.

Fairness, stated:
  * mem0 gets `intfloat/multilingual-e5-base` (verimem's model) with `query:` /
    `passage:` prefixes, so its retrieval quality has parity — it is NOT
    handicapped by a worse embedder.
  * mem0's LLM fact-extraction (`infer=True`) needs an external key this project
    does not use, so memories are stored raw (`infer=False`). That does not touch
    the abstention question: with or without extraction, mem0's store returns a
    nearest neighbour for ANY query — including unanswerable ones.
  * `floor` bolts an abstention threshold onto mem0's own score scale. floor=0 is
    mem0 AS SHIPPED (its default `threshold=0.1` never abstains on real neighbours);
    a positive floor is the charitable "operator adds a floor" steelman.

Import-guarded: `mem0_available()` is False if mem0/chroma are missing, so the
suite degrades instead of breaking.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_MODEL = "intfloat/multilingual-e5-base"   # same as verimem (config._DEFAULT_EMBEDDING_MODEL)


def mem0_available() -> bool:
    try:
        import chromadb  # noqa: F401
        import mem0  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def _memory(store_dir: Path):
    """A fully-local mem0 Memory: e5 embedder + Chroma + an LLM config that is
    never called (infer=False on every add). No network, no API key."""
    os.environ.pop("OPENAI_API_KEY", None)
    from mem0 import Memory
    cfg = {
        "embedder": {"provider": "huggingface", "config": {"model": _MODEL}},
        "vector_store": {"provider": "chroma",
                         "config": {"path": str(store_dir),
                                    "collection_name": "veribench"}},
        "llm": {"provider": "ollama", "config": {"model": "llama3"}},
    }
    return Memory.from_config(cfg)


def build_mem0_store(items: list[dict], store_dir: Path):
    """Ingest each item's `knowledge` (e5 `passage:` prefix) into mem0's store,
    tagged with its index so a hit is id-decidable. Returns the Memory."""
    mem = _memory(store_dir)
    for i, item in enumerate(items):
        mem.add("passage: " + item["knowledge"], user_id="vb",
                metadata={"i": i}, infer=False)
    return mem


def _search(mem, query: str, *, k: int) -> list[dict[str, Any]]:
    r = mem.search("query: " + query, filters={"user_id": "vb"},
                   top_k=k, threshold=0.0)
    res = r.get("results", r) if isinstance(r, dict) else r
    return list(res or [])


def _top_score(hits: list[dict[str, Any]]) -> float:
    return max((float(h.get("score", 0.0)) for h in hits), default=0.0)


def eval_raw_mem0(mem, items: list[dict], questions: list[str], *, k: int):
    """Search ONCE per probe and record (hit, top_score) so any abstention floor
    can be applied post-hoc — the substrate for mem0's own floor sweep. Returns
    (answerable_raw, unanswerable_raw)."""
    ans_raw = []
    for i, item in enumerate(items):
        hits = _search(mem, item["question"], k=k)
        ans_raw.append({
            "retrieval_hit": any(int((h.get("metadata") or {}).get("i", -1)) == i
                                 for h in hits),
            "top_score": _top_score(hits), "has_hits": bool(hits)})
    unans_raw = [{"top_score": _top_score(h), "has_hits": bool(h)}
                 for h in (_search(mem, q, k=k) for q in questions)]
    return ans_raw, unans_raw


def rows_at_floor(ans_raw: list[dict], unans_raw: list[dict], *, floor: float):
    """Apply an abstention floor to cached raw rows → the (answerable, unanswerable)
    rows the outcome mapper consumes. floor=0 = mem0 as shipped (never abstains on a
    real neighbour)."""
    def _abst(r):
        return (not r["has_hits"]) or r["top_score"] < floor
    ans = [{"retrieval_hit": r["retrieval_hit"], "abstained": _abst(r)}
           for r in ans_raw]
    unans = [{"abstained": _abst(r)} for r in unans_raw]
    return ans, unans
