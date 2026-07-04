"""Cycle #54 — real bench of the proactive briefing hook.

Runs 20 stratified synthetic prompts through the hook (as a subprocess,
exactly like Claude Code would) against the LIVE corpus at
~/.engram/. Measures:
  - Latency P50 / P95 (ms)
  - Hit rate (% prompts with ≥1 hit)
  - Precision@3 (per prompt: fraction of returned hits in expected topics)
  - Recall@1 (per prompt: did at least one expected-topic hit appear?)
  - False-positive rate on chitchat prompts (should be 0)

Output JSON saved to ~/.engram/audit/bench_briefing.json.

NOT a unit test: requires live ~/.engram corpus. Don't run in CI.
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
OUT_PATH = Path.home() / ".engram" / "audit" / "bench_briefing.json"


# 20 stratified prompts.
# Each: (prompt, expected_topics OR None for chitchat).
# expected_topics: set of topic prefixes a "correct" hit should have.
PROMPTS: list[tuple[str, set[str] | None]] = [
    # --- cybersec / pentest (5) ---
    ("voglio analizzare vulnerabilità SQL injection auth bypass su nuova app",
     {"pentest/", "project/superdrug", "project/nexus", "lessons/hippoagent"}),
    ("come faccio recon passiva su un dominio target con nexus MCP",
     {"project/nexus", "project/superdrug_intigriti", "pentest/"}),
    ("XSS reflected GET parameter su login form jsp",
     {"pentest/testfire", "project/superdrug"}),
    ("auth0 cross-tenant IDOR pattern superdrug bounty hunt",
     {"project/superdrug_intigriti", "pentest/"}),
    ("come strutturo un test di sicurezza tls cert chain audit",
     {"project/nexus", "pentest/"}),
    # --- dev Engram / MCP (5) ---
    ("estendere mcp_server.py con un nuovo tool che salva episode",
     {"project/engram", "project/hippoagent", "lessons/mcp-server",
      "lessons/hippoagent"}),
    ("hippo_record_episode con key_facts e related episode ids",
     {"project/engram", "project/hippoagent", "decisions/architecture"}),
    ("come funziona consolidation cycle wake sleep cls",
     {"project/hippoagent", "lessons/hippoagent"}),
    ("memory namespace topic gerarchico recall semantic",
     {"project/engram", "preferences/aurelio"}),
    ("bug silent-failure pattern hippo_audit_summary tdd",
     {"project/engram", "project/hippoagent", "lessons/hippoagent"}),
    # --- cross-project Beacon / Orbit / philosophy (5) ---
    ("entità ai con identità persistente attraverso reboot",
     {"project/beacon", "dialog/doc2-beacon"}),
    ("SNN spike timing dependent plasticity neuroni layer",
     {"project/orbit", "dialog/doc2"}),
    ("damasio errore cartesio coscienza somatic markers",
     {"project/beacon", "dialog/doc2"}),
    ("sandbox fisica skynet kill switch hardware controllo",
     {"project/beacon", "dialog/doc2"}),
    ("free energy principle Friston homeostatic RL grounding",
     {"project/beacon", "dialog/doc2"}),
    # --- chitchat (5, expected NO hits) ---
    ("ciao come stai oggi?", None),
    ("grazie mille per l'aiuto!", None),
    ("ok perfetto procediamo", None),
    ("sì ho capito", None),
    ("?", None),
]


def _run_hook(prompt: str, timeout_s: float = 10.0
               ) -> tuple[str, float]:
    """Invoke the hook as subprocess. Returns (stdout_text, latency_s)."""
    payload = json.dumps({"prompt": prompt}).encode("utf-8")
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [PY, str(HOOK_PATH)],
            input=payload, capture_output=True,
            timeout=timeout_s, check=False,
        )
        latency = time.perf_counter() - t0
        return proc.stdout.decode("utf-8", errors="replace"), latency
    except subprocess.TimeoutExpired:
        return "", time.perf_counter() - t0


def _parse_banner_hits(output: str) -> list[dict[str, str]]:
    """Extract hits from the <engram-proactive> banner.
    Each line `- [matched ...] topic — excerpt` becomes a dict."""
    if "<engram-proactive" not in output:
        return []
    hits: list[dict[str, str]] = []
    for line in output.split("\n"):
        line = line.strip()
        if not line.startswith("- ["):
            continue
        # Try to extract the topic between "] " and " —"
        # Format: "- [matched X/Y kw (Z%), Nd ago] topic — excerpt"
        try:
            after_bracket = line.split("]", 1)[1].strip()
            if " — " in after_bracket:
                topic_part, excerpt = after_bracket.split(" — ", 1)
                hits.append({"topic": topic_part.strip(),
                             "excerpt": excerpt.strip()})
            else:
                # No topic (anonymous fact) — topic empty
                hits.append({"topic": "", "excerpt": after_bracket})
        except Exception:
            continue
    return hits


def _is_relevant(hit_topic: str, expected: set[str]) -> bool:
    if not expected:
        return False
    return any(hit_topic.startswith(prefix) for prefix in expected)


def _clear_session_state() -> None:
    """Reset session_seen so bench runs are isolated (no carry-over
    dedup between prompts)."""
    p = Path.home() / ".engram" / "audit" / "session_seen.json"
    try:
        p.unlink()
    except FileNotFoundError:
        pass


def run_bench() -> dict:
    if not HOOK_PATH.exists():
        return {"error": f"hook not found at {HOOK_PATH}"}

    results: list[dict] = []
    latencies: list[float] = []

    for prompt, expected in PROMPTS:
        # Reset per-prompt to get clean dedup state. (Real sessions
        # have dedup; bench wants per-prompt fairness.)
        _clear_session_state()
        stdout, lat_s = _run_hook(prompt)
        lat_ms = lat_s * 1000.0
        latencies.append(lat_ms)
        hits = _parse_banner_hits(stdout)

        is_chitchat = expected is None
        n_relevant = 0
        n_irrelevant = 0
        for h in hits:
            if is_chitchat:
                # ANY hit on chitchat = false positive
                n_irrelevant += 1
            else:
                if _is_relevant(h["topic"], expected):
                    n_relevant += 1
                else:
                    n_irrelevant += 1

        results.append({
            "prompt": prompt[:80],
            "expected_topics": (
                sorted(expected) if expected else None
            ),
            "n_hits": len(hits),
            "n_relevant": n_relevant,
            "n_irrelevant": n_irrelevant,
            "precision": (
                n_relevant / len(hits) if hits else None
            ),
            "recall_at_1": (
                n_relevant >= 1 if not is_chitchat else None
            ),
            "false_positive_on_chitchat": (
                len(hits) > 0 if is_chitchat else None
            ),
            "latency_ms": round(lat_ms, 1),
            "is_chitchat": is_chitchat,
        })

    # Aggregate
    real_prompts = [r for r in results if not r["is_chitchat"]]
    chitchat = [r for r in results if r["is_chitchat"]]
    n_real = len(real_prompts)
    n_with_hits = sum(1 for r in real_prompts if r["n_hits"] > 0)
    precisions = [r["precision"] for r in real_prompts if r["precision"] is not None]
    recalls = [r["recall_at_1"] for r in real_prompts]

    summary = {
        "n_prompts_total": len(PROMPTS),
        "n_real_prompts": n_real,
        "n_chitchat": len(chitchat),
        "hit_rate_real": round(n_with_hits / n_real, 3) if n_real else 0.0,
        "avg_precision": (
            round(statistics.mean(precisions), 3) if precisions else None
        ),
        "recall_at_1": (
            round(sum(recalls) / len(recalls), 3) if recalls else 0.0
        ),
        "false_positive_chitchat_count": sum(
            1 for r in chitchat if r["false_positive_on_chitchat"]
        ),
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
    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    return out


if __name__ == "__main__":
    res = run_bench()
    print(json.dumps(res["summary"], indent=2, ensure_ascii=False))
    print(f"\nFull report: {OUT_PATH}")
