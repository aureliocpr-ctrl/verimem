"""Cycle #64 — Robustness bench. Tests retrieval invariance under
paraphrase: same RELEVANT_IDS as cycle #61, but each prompt is
rewritten in TWO additional forms:

  - EN: English translation (tests multilingual encoder robustness)
  - BRIEF: keyword-only form, no natural language structure
           (tests whether ranking depends on linguistic surface)

If recall@1 stays within 5pp of the IT baseline across all 3 forms,
the system is robust. If EN or BRIEF crashes >10pp, we have identified
a fragility (e.g. multilingual encoder under-performs on EN, or the
ranking is over-fit to sentence-shape).

This is NOT a tuning bench. We are validating cycle #63 generalises
beyond the exact prompts whose ages were used to calibrate grace=2.0.

Output: per-variant precision@3, recall@1, recall@3 + delta vs IT.
"""
from __future__ import annotations

import json
import socket
import statistics
import time
from pathlib import Path

# 15 prompts × 3 forms (IT/EN/BRIEF). RELEVANT_IDS frozen from cycle #61
# manual ground truth — they describe SEMANTIC relevance, so they apply
# to all 3 forms of the same prompt.
PROMPTS: list[tuple[str, dict[str, str], set[str]]] = [
    (
        "p1_sql_injection",
        {
            "IT": "voglio analizzare vulnerabilità SQL injection auth bypass su nuova app",
            "EN": "I want to analyze SQL injection auth bypass vulnerabilities on a new app",
            "BRIEF": "sql injection auth bypass app",
        },
        {"1be506ec60bd", "818bc7c1c36f", "1ee8351e4940",
         "4bd1dfe7134e", "cc62c9e8484d"},
    ),
    (
        "p2_recon_nexus",
        {
            "IT": "come faccio recon passiva su un dominio target con nexus MCP",
            "EN": "how do I do passive reconnaissance on a target domain using nexus MCP",
            "BRIEF": "recon passiva nexus MCP target",
        },
        {"8a7aa398e6c1", "21fe284b308d", "a7472c12a940"},
    ),
    (
        "p3_xss_jsp",
        {
            "IT": "XSS reflected GET parameter su login form jsp",
            "EN": "XSS reflected GET parameter on JSP login form",
            "BRIEF": "XSS reflected jsp login",
        },
        {"df061e854e3f", "9194e90c8541", "834b9dce1e22",
         "b2fa129fca0d", "8923a10469a0", "98747846712f"},
    ),
    (
        "p4_idor_auth0",
        {
            "IT": "auth0 cross-tenant IDOR pattern superdrug bounty hunt",
            "EN": "find IDOR pattern in multi-tenant auth0 setup during a bug bounty",
            "BRIEF": "auth0 IDOR cross-tenant superdrug",
        },
        {"81b75b3f6241", "525bca70c587", "21fe284b308d",
         "8e728eb6a715", "2b21c66d2039", "b8216dd4db14",
         "988567f4eec1", "07cc893af4bb", "c8c913e8949a",
         "8b67d64036a0"},
    ),
    (
        "p5_tls_audit",
        {
            "IT": "come strutturo un test di sicurezza tls cert chain audit",
            "EN": "how do I structure a security test for tls certificate chain audit",
            "BRIEF": "tls cert chain audit security test",
        },
        {"4503b0b01ba1", "525bca70c587", "8e166dfc06a4",
         "a4d2c8e2251f", "9204f82b4576"},
    ),
    (
        "p6_extend_mcp",
        {
            "IT": "estendere mcp_server.py con un nuovo tool che salva episode",
            "EN": "extend mcp_server.py with a new tool that saves an episode",
            "BRIEF": "mcp_server.py nuovo tool salva episode",
        },
        {"95f1962dcb62", "600956aa79cd", "8853aa3d38af"},
    ),
    (
        "p7_record_episode_facts",
        {
            "IT": "hippo_record_episode con key_facts e related episode ids",
            "EN": "record an episode with key facts and related episode ids",
            "BRIEF": "record_episode key_facts related_episode_ids",
        },
        {"d45d6761515b", "379c917dbc49", "96a7514d33f5",
         "600956aa79cd", "d6cd0e6668d0"},
    ),
    (
        "p8_consolidation_cycle",
        {
            "IT": "come funziona consolidation cycle wake sleep cls",
            "EN": "how does the consolidation cycle wake sleep cls work",
            "BRIEF": "consolidation wake sleep cls cycle",
        },
        {"0e48533d26e4", "72de3d63b252", "5f25c92d3157",
         "289937d79182", "54e580e8affd", "4a5d836f98fe",
         "1a23e4e80baf", "c8e7628559ed"},
    ),
    (
        "p9_namespace_recall",
        {
            "IT": "memory namespace topic gerarchico recall semantic",
            "EN": "hierarchical topic namespace for semantic memory recall",
            "BRIEF": "namespace topic gerarchico recall",
        },
        {"46e95dac3f5b", "96a7514d33f5", "da65b4415554",
         "9f4a89f4c68d", "600956aa79cd", "853fb2269f91",
         "6bb697dc506f"},
    ),
    (
        "p10_silent_failure_tdd",
        {
            "IT": "bug silent-failure pattern hippo_audit_summary tdd",
            "EN": "silent failure bug pattern hippo_audit_summary test driven development",
            "BRIEF": "silent failure audit_summary tdd",
        },
        {"9bd76ecce611", "4a761917bbc8", "7237d7f55ba4",
         "87a405499f73", "45ba9b5a08a7", "63b99c161d0a",
         "9194e90c8541", "d0cc9ac41c54", "8e776ecf0744",
         "b2fa129fca0d"},
    ),
    (
        "p11_ai_persistent_identity",
        {
            "IT": "entità ai con identità persistente attraverso reboot",
            "EN": "AI entity with persistent identity across reboots",
            "BRIEF": "identità persistente reboot AI",
        },
        {"caeea94a824a"},
    ),
    (
        "p12_snn_stdp",
        {
            "IT": "SNN spike timing dependent plasticity neuroni layer",
            "EN": "SNN spike timing dependent plasticity neurons layer",
            "BRIEF": "SNN spike timing plasticity neuroni",
        },
        {"49716bda0e2a", "ea8ce493135b", "26b3501e4b16",
         "307afed70cfd", "65ced8940b2d", "65b9f7125e0f"},
    ),
    (
        "p13_damasio_consciousness",
        {
            "IT": "damasio errore cartesio coscienza somatic markers",
            "EN": "damasio descartes error consciousness somatic markers",
            "BRIEF": "damasio cartesio coscienza somatic",
        },
        {"8d867fc29a11", "2761e67341fa", "2aed6426f3d0",
         "db7e776f3165", "4006cd6384ed", "a114bfa3db59",
         "bf29da70c12e", "3f8e43179451", "759cfb38f318"},
    ),
    (
        "p14_skynet_killswitch",
        {
            "IT": "sandbox fisica skynet kill switch hardware controllo",
            "EN": "physical sandbox skynet kill switch hardware control",
            "BRIEF": "sandbox skynet kill switch hardware",
        },
        {"f3d81a655db7", "a9eae4d43653", "945ad589f99f",
         "d7fa92f0d645", "ee795b608e06"},
    ),
    (
        "p15_free_energy",
        {
            "IT": "free energy principle Friston homeostatic RL grounding",
            "EN": "Friston's free energy principle homeostatic RL grounding",
            "BRIEF": "free energy Friston homeostatic RL",
        },
        {"caeea94a824a", "759cfb38f318", "6f8bcd501edb"},
    ),
]


def _direct_search_ids(prompt: str, top_k: int = 3,
                        threshold: float = 0.4) -> tuple[list[str], float]:
    djson = Path.home() / ".engram" / "daemon.json"
    if not djson.exists():
        return [], 0.0
    info = json.loads(djson.read_text(encoding="utf-8"))
    t0 = time.perf_counter()
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
        lat_ms = (time.perf_counter() - t0) * 1000.0
        return [h["id"] for h in resp.get("hits", [])], lat_ms
    except Exception:
        return [], (time.perf_counter() - t0) * 1000.0


def run_variant(variant_name: str) -> dict:
    results = []
    latencies = []
    for slug, forms, relevant in PROMPTS:
        prompt = forms[variant_name]
        ranked, lat = _direct_search_ids(prompt, top_k=3, threshold=0.4)
        latencies.append(lat)
        n_relevant = sum(1 for h in ranked if h in relevant)
        results.append({
            "slug": slug,
            "prompt": prompt,
            "ranked_top3": ranked,
            "n_relevant": n_relevant,
            "precision_at_3": (
                n_relevant / len(ranked) if ranked else None
            ),
            "recall_at_1": (ranked[0] in relevant) if ranked else False,
            "recall_at_3": n_relevant >= 1 if ranked else False,
        })
    n = len(results)
    precisions = [r["precision_at_3"] for r in results
                  if r["precision_at_3"] is not None]
    summary = {
        "variant": variant_name,
        "n": n,
        "hit_rate": round(
            sum(1 for r in results if r["ranked_top3"]) / n, 3),
        "avg_precision_at_3": (
            round(statistics.mean(precisions), 3) if precisions else None
        ),
        "recall_at_1": round(
            sum(1 for r in results if r["recall_at_1"]) / n, 3),
        "recall_at_3": round(
            sum(1 for r in results if r["recall_at_3"]) / n, 3),
        "latency_p50_ms": round(statistics.median(latencies), 1),
    }
    return {"summary": summary, "results": results}


def main() -> dict:
    print("=== Cycle #64 — Robustness bench ===")
    print("15 prompts × 3 forms (IT/EN/BRIEF) = 45 queries")
    print("Ground truth: same RELEVANT_IDS as bench v2 cycle #61")
    print()

    out = {}
    for variant in ("IT", "EN", "BRIEF"):
        print(f"--- {variant} ---")
        res = run_variant(variant)
        out[variant] = res
        s = res["summary"]
        print(f"  recall@1     = {s['recall_at_1']*100:.1f}%")
        print(f"  precision@3  = "
              f"{(s['avg_precision_at_3'] or 0)*100:.1f}%")
        print(f"  recall@3     = {s['recall_at_3']*100:.1f}%")
        print(f"  hit_rate     = {s['hit_rate']*100:.1f}%")
        print(f"  P50 latency  = {s['latency_p50_ms']:.0f}ms")
        print()

    print("=== ROBUSTNESS DELTA (vs IT baseline) ===")
    baseline = out["IT"]["summary"]["recall_at_1"]
    for v in ("EN", "BRIEF"):
        delta = out[v]["summary"]["recall_at_1"] - baseline
        verdict = (
            "ROBUST" if abs(delta) <= 0.05
            else "DEGRADED" if delta < -0.10
            else "MARGINAL"
        )
        print(f"  recall@1 {v} delta: "
              f"{delta*100:+.1f}pp  → {verdict}")

    out_path = Path.home() / ".engram" / "audit" / "bench_v3_robustness.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    print(f"\nFull report: {out_path}")
    return out


if __name__ == "__main__":
    main()
