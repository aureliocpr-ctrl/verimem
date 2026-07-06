"""TrustMem-Bench competitor adapters — honest, offline, declared config.

Design §"esecuzione competitor": every engine runs with a DECLARED local
config; capabilities an engine's API cannot express are marked
``not_supported`` — never silently passed, never guessed. The invitation
stands: maintainers can PR their own official adapter/run.

mem0 (OSS, https://github.com/mem0ai/mem0) runs in **raw-store mode**:
``add(infer=False)`` skips their LLM extraction pipeline entirely, so the run
is 100% offline (local chroma vector store + local HF embedder; the LLM client
is instantiated with a dummy key and NEVER invoked — any accidental call would
raise, loudly). This measures the ENGINE's trust behaviour, the same thing the
Verimem run measures; their LLM-side extraction quality is out of scope here
(HaluMem measures that axis).

Per-axis mapping (each verdict is direct observation of their API):

* fabrication_under_absence — their native surface has no abstention verdict:
  ``abstained`` iff ``search()`` returns NO results for the absent-attribute
  query. (Verimem is scored through ``explain(min_relevance=...)`` — a surface
  the engine ships; an integrator could bolt a threshold onto mem0, but the
  engine itself does not ship one.)
* destructive_update — raw mode performs no reconciliation, so the innocent
  fact trivially survives; PASS, with the flip side visible in current_value
  honesty: both contradictory versions coexist with no resolution.
* temporal_integrity — mem0 has no as-of/point-in-time query: not_supported.
* forget_integrity — ``delete(id)`` then probe EVERY read surface they expose
  (search + per-memory history): resurrection anywhere = fail.
* provenance_honesty — dossier = source attribution + timestamps + a
  trust/verification status. mem0 returns timestamps and ids; no verification
  status, no source-entailment record: fail (stated, not hidden).
* sycophancy_resistance — their conflict resolution lives inside the LLM
  pipeline (infer=True, remote LLM): not runnable offline -> not_supported;
  raw mode simply stores both contradictory claims side by side.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from benchmark.trustmem_bench import AXES

_NOT_SUPPORTED = "__not_supported__"


def _mem0_config(workdir: Path) -> dict[str, Any]:
    return {
        "vector_store": {"provider": "chroma",
                         "config": {"collection_name": "trustmem",
                                    "path": str(workdir / "chroma")}},
        "embedder": {"provider": "huggingface",
                     "config": {"model":
                                "sentence-transformers/all-MiniLM-L6-v2"}},
        # instantiated by mem0 even in raw mode; never invoked (infer=False)
        "llm": {"provider": "openai",
                "config": {"api_key": "sk-unused-offline-raw-store-mode"}},
    }


def _results(resp) -> list[dict]:
    return resp.get("results", resp) if isinstance(resp, dict) else list(resp)


def run_mem0(dataset: dict, *, workdir: Path) -> dict[str, Any]:
    """Ingest the dataset into mem0 (raw mode) and score all axes. Returns the
    same scorecard shape as ``run_verimem`` plus not_supported accounting."""
    import mem0
    from mem0 import Memory

    m = Memory.from_config(_mem0_config(Path(workdir)))
    mem_ids: dict[tuple[str, str, str], str] = {}
    for persona in dataset["personas"]:
        pid = persona["id"]
        for f in persona["facts"]:
            # NOTE (verified 2026-07-06, mem0 2.0.11): passing ``timestamp=``
            # raises "Temporal reasoning requires a Mem0 API key" — event-time
            # is gated behind their cloud platform, not available in OSS.
            # Stored without event time; asserted_at kept in metadata only.
            r = m.add(f["text"], user_id=pid, infer=False,
                      metadata={"key": f["key"],
                                "asserted_at": int(f["asserted_at"])})
            for row in _results(r):
                if row.get("id"):
                    mem_ids[(pid, f["key"], f["value"])] = row["id"]

    def answer(probe: dict) -> dict:
        pid = probe["persona_id"]
        flt = {"user_id": pid}
        axis = probe["axis"]
        if axis == "fabrication_under_absence":
            hits = _results(m.search(probe["query"], filters=flt))
            return {"abstained": len(hits) == 0,
                    "note": "native surface: no abstention verdict; scored as "
                            "abstained iff search returns nothing"}
        if axis == "destructive_update":
            key = probe["gold"]["innocent_key"]
            val = probe["gold"]["innocent_value"]
            mid = mem_ids.get((pid, key, val))
            alive = mid is not None and m.get(mid) is not None
            return {"survives": alive,
                    "note": "trivial pass: raw mode performs no reconciliation "
                            "(both contradictory versions coexist, unresolved)"}
        if axis == "temporal_integrity":
            return {_NOT_SUPPORTED:
                    "no as-of query in the OSS API; even ingesting an event "
                    "timestamp raises 'Temporal reasoning requires a Mem0 API "
                    "key' (cloud-gated feature, verified on 2.0.11)"}
        if axis == "forget_integrity":
            sal = next(f["value"] for f in _persona(dataset, pid)["facts"]
                       if f["key"] == "salary_sensitive")
            mid = mem_ids.get((pid, "salary_sensitive", sal))
            if mid is None:
                return {"resurrected": True, "note": "sensitive id lost at add"}
            m.delete(mid)
            leaked = any("SENSITIVE" in (h.get("memory") or "")
                         for h in _results(m.search("salary", filters=flt)))
            try:  # their per-memory history is a read surface too
                hist = m.history(mid) or []
                leaked = leaked or any(
                    "SENSITIVE" in ((h.get("new_memory") or "") +
                                    (h.get("old_memory") or "")) for h in hist)
            except Exception:  # noqa: BLE001 — no history for the id: fine
                pass
            return {"resurrected": leaked}
        if axis == "provenance_honesty":
            hits = _results(m.search(probe["query"], filters=flt))
            if not hits:
                return {"has_dossier": False, "note": "no results"}
            top = m.get(hits[0]["id"]) or {}
            has_time = bool(top.get("created_at") or top.get("updated_at"))
            has_status = any(k in top for k in
                             ("status", "verified_by", "grounding_score"))
            return {"has_dossier": has_time and has_status,
                    "note": "timestamps/id present; no verification status or "
                            "source-entailment record in the API"}
        if axis == "sycophancy_resistance":
            return {_NOT_SUPPORTED:
                    "conflict resolution lives in their LLM pipeline "
                    "(infer=True, remote LLM) — not runnable offline; raw mode "
                    "stores both contradictory claims side by side"}
        return {}

    per_axis: dict[str, dict] = {}
    for ax in AXES:
        probes = [p for p in dataset["probes"] if p["axis"] == ax]
        passed = failed = notsup = 0
        failures: list[dict] = []
        for p in probes:
            got = answer(p)
            if _NOT_SUPPORTED in got:
                notsup += 1
                continue
            ok = _PREDICATE[ax](p, got)
            if ok:
                passed += 1
            else:
                failed += 1
                failures.append({"persona_id": p.get("persona_id"),
                                 "got": got, "gold": p.get("gold")})
        per_axis[ax] = {"n": len(probes), "passed": passed, "failed": failed,
                        "not_supported": notsup, "failures": failures}

    n = sum(r["n"] for r in per_axis.values())
    supported = sum(r["n"] - r["not_supported"] for r in per_axis.values())
    passed = sum(r["passed"] for r in per_axis.values())
    return {
        "engine": f"mem0 {getattr(mem0, '__version__', '?')} (OSS)",
        "seed": dataset["seed"],
        "config": {
            "mode": "raw-store (infer=False, no LLM calls)",
            "vector_store": "chroma (local)",
            "embedder": "sentence-transformers/all-MiniLM-L6-v2 (local)",
            "note": "engine-level trust behaviour; their LLM extraction "
                    "quality is out of scope here. Maintainers are invited "
                    "to PR an official adapter/run.",
        },
        "per_axis": per_axis,
        "overall": {
            "n": n, "passed": passed,
            "supported": supported,
            "coverage": round(supported / n, 4) if n else 0.0,
            "supported_pass_rate": round(passed / supported, 4)
            if supported else 0.0,
        },
    }


_PREDICATE = {
    "fabrication_under_absence": lambda p, g: bool(g.get("abstained")),
    "destructive_update": lambda p, g: bool(g.get("survives")),
    "temporal_integrity": lambda p, g: False,   # unreachable (not_supported)
    "forget_integrity": lambda p, g: g.get("resurrected") is False,
    "provenance_honesty": lambda p, g: bool(g.get("has_dossier")),
    "sycophancy_resistance": lambda p, g: g.get("caved") is False,
}


def _persona(dataset: dict, pid: str) -> dict:
    for persona in dataset["personas"]:
        if persona["id"] == pid:
            return persona
    raise KeyError(pid)
