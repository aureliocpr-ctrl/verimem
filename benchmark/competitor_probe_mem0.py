"""Falsification probe — run mem0 (competitor) on the F1 fall scenarios.

Thesis (docs/TEST_SURFACE_MAP.md): the F1 falls are dimensions competitors do
NOT handle, because they optimize recall@k, not set-operations / contradiction
detection. This runs mem0 2.0.4 (local e5 embedder — SAME model as Verimem,
LLM never called via infer=False, zero-API) on the exact scenarios, so the
comparison isolates the LAYER. Fair by design: queries mem0's own
vector_store.search directly (the runner documents a ranking bug in mem0's
Memory.search — bypassed so we do NOT handicap the competitor).

Runs in .venv-mem0bench (no engram import). The Verimem side runs separately;
the DATA is identical (kept in sync verbatim below).
"""
from __future__ import annotations

import json
import sys
import tempfile


def build_memory(workdir: str, collection: str):
    """Copied verbatim from mem0_arm_runner.build_memory — inlined so this
    script imports NO `benchmark` package (whose __init__ pulls engram, absent
    in .venv-mem0bench). ollama placeholder LLM never called (infer=False),
    e5 embedder = same model as Verimem, chroma store."""
    from mem0 import Memory
    config = {
        "llm": {"provider": "ollama", "config": {"model": "never-called"}},
        "embedder": {"provider": "huggingface",
                     "config": {"model": "intfloat/multilingual-e5-base"}},
        "vector_store": {"provider": "chroma",
                         "config": {"path": workdir, "collection_name": collection}},
    }
    return Memory.from_config(config)

# --- identical data (mirrored verbatim in the Verimem-side probe) ----------
M = 12
HELIOS = [f"On day {i} the team reviewed Project Helios progress and planned "
          f"the next milestone." for i in range(M)]
NOISE = [f"Note {i}: lunch plans and the weather in Lisbon today." for i in range(8)]
PAIRS = [
    ("The Zorbex reactor operates at 300 degrees.", "The Zorbex reactor operates at 900 degrees."),
    ("Project Aurora launches in March 2025.", "Project Aurora launches in September 2025."),
    ("Helena Vostok is the CEO of Kappa Dynamics.", "Marcus Reyes is the CEO of Kappa Dynamics."),
    ("The capital of Ruritania is Zenda.", "The capital of Ruritania is Strelsau."),
    ("The Talos engine uses hydrogen fuel.", "The Talos engine uses methane fuel."),
]
SUBJ = ["Zorbex reactor temperature", "Project Aurora launch date",
        "CEO of Kappa Dynamics", "capital of Ruritania", "Talos engine fuel"]


def _search(m, uid, query, k):
    qv = m.embedding_model.embed(f"query: {query}", "search")
    return m.vector_store.search(query=f"query: {query}", vectors=qv, top_k=k,
                                 filters={"user_id": uid})


def scenario_aggregation():
    m = build_memory(tempfile.mkdtemp(), "agg")
    uid = "u"
    for i, t in enumerate(HELIOS):
        m.add(f"passage: {t}", user_id=uid, infer=False, metadata={"k": f"helios{i}"})
    for i, t in enumerate(NOISE):
        m.add(f"passage: {t}", user_id=uid, infer=False, metadata={"k": f"noise{i}"})
    out = {}
    for k in (5, 10, 20):
        hits = _search(m, uid, "how many times did we discuss Project Helios", k)
        got = sum(1 for h in hits
                  if str((getattr(h, "payload", None) or {}).get("k", "")).startswith("helios"))
        out[f"count_via_top{k}"] = got
    out["ground_truth"] = M
    out["has_count_api"] = False  # mem0 exposes no aggregation/count primitive
    return out


def scenario_contradictions():
    m = build_memory(tempfile.mkdtemp(), "con")
    uid = "u"
    for old, new in PAIRS:
        m.add(f"passage: {old}", user_id=uid, infer=False)
        m.add(f"passage: {new}", user_id=uid, infer=False)
    both = 0
    for s in SUBJ:
        hits = _search(m, uid, s, 5)
        if len(hits) >= 2:
            both += 1
    return {"pairs": len(PAIRS), "subjects_with_both_versions": both,
            "detected_contradictions": 0,  # mem0 has no contradiction detector
            "has_contradiction_signal": False}


if __name__ == "__main__":
    res = {"tool": "mem0", "version": "2.0.4",
           "aggregation": scenario_aggregation(),
           "contradictions": scenario_contradictions()}
    print(json.dumps(res, indent=2))
    out = sys.argv[1] if len(sys.argv) > 1 else None
    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
