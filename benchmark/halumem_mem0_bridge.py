"""mem0 side of the HaluMem write-poisoning head-to-head (bridge).

Runs INSIDE .venv-mem0bench (mem0ai + chroma + HF e5) — NO engram/verimem
imports. Reads a candidates JSON produced by halumem_mem0_real_arm.py, ingests
every candidate text into a fresh mem0 store per user (infer=False: raw
storage, the zero-API mode — mem0 has NO write gate, it stores whatever is
emitted), retrieves top-k contexts per question, writes them to JSON. The
answering + judging happen on the verimem side so all arms share the SAME
answerer and judge (the comparison isolates the memory layer).

Config honesty (same as mem0_arm_runner / competitor_probe_mem0):
  * embedder intfloat/multilingual-e5-base = the SAME model verimem uses;
  * e5 parity: "passage: "/"query: " prefixes injected (the scheme e5 was
    trained with) — closes the "you handicapped mem0" objection;
  * vector_store.search direct (the runner documents a ranking bug in
    mem0's Memory.search — bypassed so we do NOT handicap the competitor).

  .venv-mem0bench/Scripts/python benchmark/halumem_mem0_bridge.py \
      --candidates c.json --out ctx.json --k 8
"""
from __future__ import annotations

import argparse
import json
import tempfile


def build_memory(workdir: str, collection: str):
    from mem0 import Memory
    config = {
        "llm": {"provider": "ollama", "config": {"model": "never-called"}},
        "embedder": {"provider": "huggingface",
                     "config": {"model": "intfloat/multilingual-e5-base"}},
        "vector_store": {"provider": "chroma",
                         "config": {"path": workdir, "collection_name": collection}},
    }
    return Memory.from_config(config)


def _search(m, uid, query, k):
    qv = m.embedding_model.embed(f"query: {query}", "search")
    return m.vector_store.search(query=f"query: {query}", vectors=qv, top_k=k,
                                 filters={"user_id": uid})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--k", type=int, default=8)
    a = ap.parse_args()

    data = json.load(open(a.candidates, encoding="utf-8"))
    out = {"k": a.k, "users": []}
    for u in data["users"]:
        uid = u["uid"]
        m = build_memory(tempfile.mkdtemp(prefix=f"halu_mem0_{uid}_"), f"halu_{uid}")
        for t in u["texts"]:
            m.add(f"passage: {t}", user_id=uid, infer=False)
        rows = []
        for q in u["questions"]:
            hits = _search(m, uid, q["question"], a.k)
            ctx = []
            for h in hits:
                payload = getattr(h, "payload", None) or {}
                txt = payload.get("data") or payload.get("memory") or ""
                if txt.startswith("passage: "):
                    txt = txt[len("passage: "):]
                if txt:
                    ctx.append(txt)
            rows.append({"question": q["question"], "ctx": ctx})
        out["users"].append({"uid": uid, "questions": rows})
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"mem0 bridge: {len(out['users'])} users done -> {a.out}")


if __name__ == "__main__":
    main()
