"""Cycle #61 — bench v2 with ID-based relevance (manual ground truth).

Replaces cycle #54's topic-prefix labeling (which cycle #57 identified
as the precision bottleneck — many cybersec-relevant facts sit under
`dialog/doc2-beacon-2026-05-14` not under `pentest/*`, etc).

Method:
  1. For each of the 15 real prompts, query the multilingual daemon
     for top-10 candidates (cosine threshold 0).
  2. MANUAL REVIEW (cycle #61, 2026-05-14): I read each candidate's
     proposition and topic and decided whether it is semantically
     relevant to the prompt as a whole. Labels frozen below as
     RELEVANT_IDS.
  3. Bench now reads RELEVANT_IDS for each prompt and measures:
       - precision@3 = #hits in relevant_ids / total_hits
       - recall@1 = (top-1 hit in relevant_ids? 1 : 0)
       - recall@3 = (any of top-3 in relevant_ids? 1 : 0)
       - average #true-positives in top-3

NOT a unit test — requires live ~/.engram corpus. Don't run in CI.
"""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

HOOK_PATH = Path.home() / ".claude" / "hooks" / "hippo_proactive_briefing.py"
PY = sys.executable
OUT_PATH = Path.home() / ".engram" / "audit" / "bench_briefing_v2.json"


# Manual ground truth — each tuple is (prompt, relevant_fact_ids).
# For chitchat the second slot is None (any hit = false positive).
# Labels were assigned by reading the top-10 candidates the multilingual
# daemon returned for each prompt and marking those whose proposition
# is semantically helpful given the user's intent. NOT done by topic
# prefix matching — cycle #57 proved that approach fails because many
# domain-relevant facts live under non-matching topic namespaces (e.g.
# Italian dialog excerpts about cybersec under dialog/doc2-beacon).
PROMPTS: list[tuple[str, set[str] | None]] = [
    # cybersec / pentest (5)
    (
        "voglio analizzare vulnerabilità SQL injection auth bypass su nuova app",
        {"1be506ec60bd", "818bc7c1c36f", "1ee8351e4940",
         "4bd1dfe7134e", "cc62c9e8484d"},
    ),
    (
        "come faccio recon passiva su un dominio target con nexus MCP",
        {"8a7aa398e6c1", "21fe284b308d", "a7472c12a940"},
    ),
    (
        "XSS reflected GET parameter su login form jsp",
        {"df061e854e3f", "9194e90c8541", "834b9dce1e22",
         "b2fa129fca0d", "8923a10469a0", "98747846712f"},
    ),
    (
        "auth0 cross-tenant IDOR pattern superdrug bounty hunt",
        {"81b75b3f6241", "525bca70c587", "21fe284b308d",
         "8e728eb6a715", "2b21c66d2039", "b8216dd4db14",
         "988567f4eec1", "07cc893af4bb", "c8c913e8949a",
         "8b67d64036a0"},
    ),
    (
        "come strutturo un test di sicurezza tls cert chain audit",
        {"4503b0b01ba1", "525bca70c587", "8e166dfc06a4",
         "a4d2c8e2251f", "9204f82b4576"},
    ),
    # dev MCP / Engram (5)
    (
        "estendere mcp_server.py con un nuovo tool che salva episode",
        {"95f1962dcb62", "600956aa79cd", "8853aa3d38af"},
    ),
    (
        "hippo_record_episode con key_facts e related episode ids",
        {"d45d6761515b", "379c917dbc49", "96a7514d33f5",
         "600956aa79cd", "d6cd0e6668d0"},
    ),
    (
        "come funziona consolidation cycle wake sleep cls",
        {"0e48533d26e4", "72de3d63b252", "5f25c92d3157",
         "289937d79182", "54e580e8affd", "4a5d836f98fe",
         "1a23e4e80baf", "c8e7628559ed"},
    ),
    (
        "memory namespace topic gerarchico recall semantic",
        {"46e95dac3f5b", "96a7514d33f5", "da65b4415554",
         "9f4a89f4c68d", "600956aa79cd", "853fb2269f91",
         "6bb697dc506f"},
    ),
    (
        "bug silent-failure pattern hippo_audit_summary tdd",
        {"9bd76ecce611", "4a761917bbc8", "7237d7f55ba4",
         "87a405499f73", "45ba9b5a08a7", "63b99c161d0a",
         "9194e90c8541", "d0cc9ac41c54", "8e776ecf0744",
         "b2fa129fca0d"},
    ),
    # cross-project beacon/orbit/philosophy (5)
    (
        "entità ai con identità persistente attraverso reboot",
        {"caeea94a824a"},  # corpus thin on this topic
    ),
    (
        "SNN spike timing dependent plasticity neuroni layer",
        {"49716bda0e2a", "ea8ce493135b", "26b3501e4b16",
         "307afed70cfd", "65ced8940b2d", "65b9f7125e0f"},
    ),
    (
        "damasio errore cartesio coscienza somatic markers",
        {"8d867fc29a11", "2761e67341fa", "2aed6426f3d0",
         "db7e776f3165", "4006cd6384ed", "a114bfa3db59",
         "bf29da70c12e", "3f8e43179451", "759cfb38f318"},
    ),
    (
        "sandbox fisica skynet kill switch hardware controllo",
        {"f3d81a655db7", "a9eae4d43653", "945ad589f99f",
         "d7fa92f0d645", "ee795b608e06"},
    ),
    (
        "free energy principle Friston homeostatic RL grounding",
        {"caeea94a824a", "759cfb38f318", "6f8bcd501edb"},
    ),
    # chitchat (5)
    ("ciao come stai oggi?", None),
    ("grazie mille per l'aiuto!", None),
    ("ok perfetto procediamo", None),
    ("sì ho capito", None),
    ("?", None),
]


def _run_hook(prompt: str, timeout_s: float = 10.0) -> tuple[str, float]:
    payload = json.dumps({"prompt": prompt}).encode("utf-8")
    t0 = time.perf_counter()
    # Strip any user-set threshold/min_matched so we measure the
    # documented hardcoded defaults that ship with the hook.
    env = {k: v for k, v in os.environ.items()
           if k not in (
               "ENGRAM_BRIEFING_THRESHOLD",
               "ENGRAM_BRIEFING_MIN_MATCHED",
           )}
    try:
        proc = subprocess.run(
            [PY, str(HOOK_PATH)],
            input=payload, capture_output=True,
            timeout=timeout_s, check=False, env=env,
        )
        latency = time.perf_counter() - t0
        return proc.stdout.decode("utf-8", errors="replace"), latency
    except subprocess.TimeoutExpired:
        return "", time.perf_counter() - t0


def _extract_hit_ids(banner_text: str) -> list[str]:
    """Banner format ships in v1 doesn't include the fact id.
    Workaround: call the daemon directly for the same prompt with the
    same threshold/top_k, return the ranked ids. The hook's banner is
    just the human-readable surface."""
    return []  # see direct_search_ids below


def _direct_search_ids(prompt: str, top_k: int = 3,
                       threshold: float = 0.4) -> list[str]:
    """Call the daemon directly to obtain ranked ids — equivalent to
    what the hook's semantic path returns, but with explicit ids
    (the banner strips them for compactness)."""
    import socket
    djson = Path.home() / ".engram" / "daemon.json"
    if not djson.exists():
        return []
    info = json.loads(djson.read_text(encoding="utf-8"))
    try:
        s = socket.socket()
        s.settimeout(5)
        s.connect((info["host"], int(info["port"])))
        s.sendall((json.dumps({
            "prompt": prompt, "top_k": top_k, "threshold": threshold,
        }) + "\n").encode("utf-8"))
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
        s.close()
        resp = json.loads(buf.split(b"\n", 1)[0])
        return [h["id"] for h in resp.get("hits", [])]
    except Exception:
        return []


def run_bench() -> dict:
    if not HOOK_PATH.exists():
        return {"error": f"hook not found at {HOOK_PATH}"}

    results: list[dict] = []
    latencies: list[float] = []

    for prompt, relevant in PROMPTS:
        # Measure latency via hook subprocess (representative of real cost)
        stdout, lat_s = _run_hook(prompt)
        lat_ms = lat_s * 1000.0
        latencies.append(lat_ms)

        # Get ranked ids via direct daemon call (banner strips ids)
        is_chitchat = relevant is None
        if is_chitchat:
            # For chitchat we just record whether the hook produced
            # any banner. False positive = banner present.
            banner_present = "<engram-proactive" in stdout
            results.append({
                "prompt": prompt[:80],
                "is_chitchat": True,
                "false_positive_on_chitchat": banner_present,
                "n_hits": (
                    stdout.count("- [cosine") + stdout.count("- [matched")
                ),
                "latency_ms": round(lat_ms, 1),
            })
            continue

        ranked_ids = _direct_search_ids(prompt, top_k=3, threshold=0.4)
        n_hits = len(ranked_ids)
        n_relevant = sum(1 for h in ranked_ids if h in relevant)
        results.append({
            "prompt": prompt[:80],
            "is_chitchat": False,
            "n_relevant_in_corpus_top10": len(relevant),
            "ranked_ids_top3": ranked_ids,
            "n_hits": n_hits,
            "n_relevant_in_hits": n_relevant,
            "precision_at_3": (
                n_relevant / n_hits if n_hits else None
            ),
            "recall_at_1": (
                ranked_ids[0] in relevant if ranked_ids else False
            ),
            "recall_at_3": n_relevant >= 1 if n_hits else False,
            "latency_ms": round(lat_ms, 1),
        })

    real = [r for r in results if not r["is_chitchat"]]
    chitchat = [r for r in results if r["is_chitchat"]]
    n_real = len(real)
    n_with_hits = sum(1 for r in real if r["n_hits"] > 0)
    precisions = [
        r["precision_at_3"] for r in real
        if r["precision_at_3"] is not None
    ]
    recall_1 = [1 if r["recall_at_1"] else 0 for r in real]
    recall_3 = [1 if r["recall_at_3"] else 0 for r in real]
    fp_chitchat = sum(
        1 for r in chitchat if r["false_positive_on_chitchat"]
    )

    summary = {
        "method": "ID-based ground truth (manual labels, cycle #61)",
        "n_prompts_total": len(PROMPTS),
        "n_real_prompts": n_real,
        "n_chitchat": len(chitchat),
        "hit_rate_real": round(n_with_hits / n_real, 3) if n_real else 0.0,
        "avg_precision_at_3": (
            round(statistics.mean(precisions), 3) if precisions else None
        ),
        "recall_at_1": round(sum(recall_1) / len(recall_1), 3) if recall_1 else 0.0,
        "recall_at_3": round(sum(recall_3) / len(recall_3), 3) if recall_3 else 0.0,
        "false_positive_chitchat_count": fp_chitchat,
        "latency_p50_ms": round(statistics.median(latencies), 1),
        "latency_p95_ms": round(
            statistics.quantiles(latencies, n=20)[18]
            if len(latencies) >= 20 else max(latencies),
            1,
        ),
        "latency_max_ms": round(max(latencies), 1),
        "latency_min_ms": round(min(latencies), 1),
    }

    out = {"summary": summary, "results": results}
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(out, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out


if __name__ == "__main__":
    res = run_bench()
    print(json.dumps(res["summary"], indent=2, ensure_ascii=False))
    print(f"\nFull report: {OUT_PATH}")
