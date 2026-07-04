"""Cycle #62 — offline evaluation of BAAI/bge-m3 against the same
ground truth defined manually in cycle #61.

NO daemon, NO deployment — just: load bge-m3, encode all 421 facts +
15 prompts, compute cosine, compare ranked top-3 vs RELEVANT_IDS.

Outputs precision@3, recall@1, recall@3 — directly comparable to the
cycle #61 multilingual numbers (precision 68.9%, recall@1 73.3%,
recall@3 86.7%).

If bge-m3 beats multilingual by ≥5pp on precision AND its cold-load
is tolerable, full swap may be worth a cycle. If not, multilingual
stays as documented baseline.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

os.environ.setdefault("HIPPO_OFFLINE", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

PROMPTS_RELEVANT: list[tuple[str, set[str]]] = [
    ("voglio analizzare vulnerabilità SQL injection auth bypass su nuova app",
     {"1be506ec60bd", "818bc7c1c36f", "1ee8351e4940", "4bd1dfe7134e", "cc62c9e8484d"}),
    ("come faccio recon passiva su un dominio target con nexus MCP",
     {"8a7aa398e6c1", "21fe284b308d", "a7472c12a940"}),
    ("XSS reflected GET parameter su login form jsp",
     {"df061e854e3f", "9194e90c8541", "834b9dce1e22", "b2fa129fca0d", "8923a10469a0", "98747846712f"}),
    ("auth0 cross-tenant IDOR pattern superdrug bounty hunt",
     {"81b75b3f6241", "525bca70c587", "21fe284b308d", "8e728eb6a715", "2b21c66d2039",
      "b8216dd4db14", "988567f4eec1", "07cc893af4bb", "c8c913e8949a", "8b67d64036a0"}),
    ("come strutturo un test di sicurezza tls cert chain audit",
     {"4503b0b01ba1", "525bca70c587", "8e166dfc06a4", "a4d2c8e2251f", "9204f82b4576"}),
    ("estendere mcp_server.py con un nuovo tool che salva episode",
     {"95f1962dcb62", "600956aa79cd", "8853aa3d38af"}),
    ("hippo_record_episode con key_facts e related episode ids",
     {"d45d6761515b", "379c917dbc49", "96a7514d33f5", "600956aa79cd", "d6cd0e6668d0"}),
    ("come funziona consolidation cycle wake sleep cls",
     {"0e48533d26e4", "72de3d63b252", "5f25c92d3157", "289937d79182",
      "54e580e8affd", "4a5d836f98fe", "1a23e4e80baf", "c8e7628559ed"}),
    ("memory namespace topic gerarchico recall semantic",
     {"46e95dac3f5b", "96a7514d33f5", "da65b4415554", "9f4a89f4c68d",
      "600956aa79cd", "853fb2269f91", "6bb697dc506f"}),
    ("bug silent-failure pattern hippo_audit_summary tdd",
     {"9bd76ecce611", "4a761917bbc8", "7237d7f55ba4", "87a405499f73",
      "45ba9b5a08a7", "63b99c161d0a", "9194e90c8541", "d0cc9ac41c54", "8e776ecf0744", "b2fa129fca0d"}),
    ("entità ai con identità persistente attraverso reboot",
     {"caeea94a824a"}),
    ("SNN spike timing dependent plasticity neuroni layer",
     {"49716bda0e2a", "ea8ce493135b", "26b3501e4b16", "307afed70cfd", "65ced8940b2d", "65b9f7125e0f"}),
    ("damasio errore cartesio coscienza somatic markers",
     {"8d867fc29a11", "2761e67341fa", "2aed6426f3d0", "db7e776f3165", "4006cd6384ed",
      "a114bfa3db59", "bf29da70c12e", "3f8e43179451", "759cfb38f318"}),
    ("sandbox fisica skynet kill switch hardware controllo",
     {"f3d81a655db7", "a9eae4d43653", "945ad589f99f", "d7fa92f0d645", "ee795b608e06"}),
    ("free energy principle Friston homeostatic RL grounding",
     {"caeea94a824a", "759cfb38f318", "6f8bcd501edb"}),
]

print("[1] loading bge-m3 ...", flush=True)
t0 = time.time()
import numpy as np  # noqa: E402  (deliberate: deferred load timing)
from sentence_transformers import SentenceTransformer  # noqa: E402

model = SentenceTransformer("BAAI/bge-m3")
print(f"    loaded in {time.time()-t0:.1f}s, dim={model.get_sentence_embedding_dimension()}", flush=True)

print("[2] loading 421 facts from semantic.db ...", flush=True)
t1 = time.time()
sem_db = Path.home() / ".engram" / "semantic" / "semantic.db"
if not sem_db.exists(): sem_db = Path.home() / ".engram" / "semantic.db"
conn = sqlite3.connect(str(sem_db))
rows = conn.execute("SELECT id, proposition, topic FROM facts").fetchall()
print(f"    {len(rows)} facts loaded in {time.time()-t1:.1f}s", flush=True)

print("[3] encoding facts ...", flush=True)
t2 = time.time()
fact_ids = [r[0] for r in rows]
fact_props = [r[1] or "" for r in rows]
fact_vecs = model.encode(fact_props, normalize_embeddings=True, show_progress_bar=False, convert_to_numpy=True, batch_size=32)
print(f"    encoded {len(fact_props)} facts in {time.time()-t2:.1f}s, shape={fact_vecs.shape}", flush=True)

print("[4] running 15 prompts ...", flush=True)
results = []
for prompt, relevant in PROMPTS_RELEVANT:
    t3 = time.perf_counter()
    qv = model.encode([prompt], normalize_embeddings=True, show_progress_bar=False, convert_to_numpy=True)[0]
    enc_ms = (time.perf_counter() - t3) * 1000.0

    t4 = time.perf_counter()
    sims = fact_vecs @ qv
    order = np.argsort(-sims)
    match_ms = (time.perf_counter() - t4) * 1000.0

    top3_ids = [fact_ids[i] for i in order[:3]]
    top3_sims = [float(sims[i]) for i in order[:3]]
    n_relevant = sum(1 for h in top3_ids if h in relevant)
    results.append({
        "prompt": prompt[:60],
        "top3_ids": top3_ids,
        "top3_sims": [round(s, 3) for s in top3_sims],
        "n_relevant_top3": n_relevant,
        "precision_at_3": n_relevant / 3,
        "recall_at_1": top3_ids[0] in relevant,
        "recall_at_3": n_relevant >= 1,
        "encode_ms": round(enc_ms, 1),
        "match_ms": round(match_ms, 2),
    })

n = len(results)
prec_at_3 = sum(r["precision_at_3"] for r in results) / n
recall_1 = sum(1 for r in results if r["recall_at_1"]) / n
recall_3 = sum(1 for r in results if r["recall_at_3"]) / n
avg_enc = sum(r["encode_ms"] for r in results) / n
avg_match = sum(r["match_ms"] for r in results) / n

summary = {
    "encoder": "BAAI/bge-m3",
    "dim": int(fact_vecs.shape[1]),
    "n_facts": len(fact_ids),
    "n_prompts": n,
    "avg_precision_at_3": round(prec_at_3, 3),
    "recall_at_1": round(recall_1, 3),
    "recall_at_3": round(recall_3, 3),
    "avg_encode_ms_per_prompt": round(avg_enc, 1),
    "avg_match_ms_per_prompt": round(avg_match, 3),
    "cold_load_s_model": round(time.time() - t0, 1),
}
print("\n=== SUMMARY ===")
print(json.dumps(summary, indent=2, ensure_ascii=False))

import tempfile  # noqa: E402  (late import: script body runs the eval above first)

_out_path = Path(tempfile.gettempdir()) / "bge_m3_eval_result.json"
with open(_out_path, "w", encoding="utf-8") as f:
    json.dump({"summary": summary, "results": results}, f, indent=2, ensure_ascii=False)
print(f"\nFull report: {_out_path}")
