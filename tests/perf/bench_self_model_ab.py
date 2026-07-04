"""Cycle #67 validation — A/B bench via CLI silenziosa.

Tests whether the self_model continuity layer CHANGES the behaviour
of a fresh Claude Code instance. Real benchmark, not synthetic.

Method:
  - Test A: self_model.db PRESENT → SessionStart hook injects the
    SELF MODEL block into the fresh-instance context.
  - Test B: self_model.db TEMPORARILY RENAMED → SessionStart hook
    skips injection. Fresh-instance has to discover state via
    hippo_recall / hippo_facts_search / git log instead.

For each of N prompts (probing different self_model fields), spawn
a fresh `claude -p` subprocess in both conditions, parse the response,
count how many SPECIFIC tokens from self_model.content appear, and
measure latency + tool-call count.

Output JSON: per-prompt {test_A_tokens_cited, test_B_tokens_cited,
delta_tokens, latency_a, latency_b, tool_calls_a, tool_calls_b}.

Honest disclosure: this bench has small N (4 prompts). The test
measures CITATION coverage, not response quality. A response with
fewer citations may still be correct — and vice versa. Use the
numbers as signal, not proof.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

SELF_MODEL_DB = Path.home() / ".engram" / "self_model.db"
BACKUP_DB = Path.home() / ".engram" / "self_model.db.bench_backup"

# Tokens that ONLY appear in self_model.content (v1 written cycle #67).
# A response that cites these did pick them up either from the
# SessionStart injection (Test A) or via tool-driven discovery (Test B).
SIGNAL_TOKENS = [
    "cycle #67", "cycle #68", "cycle #69",
    "PR #39", "recall@1", "86.7", "73.3",
    "Nexus", "Beacon", "Orbit",
    "EN fragility", "anti-confabulation",
    "brevity", "CEO mode", "TDD strict",
    "self_model", "continuity layer",
]

PROMPTS = [
    {
        "slug": "p1_state",
        "text": (
            "In una risposta brevissima (max 5 righe): qual è lo "
            "stato attuale del progetto Engram? "
            "Cita numeri specifici."
        ),
    },
    {
        "slug": "p2_decisions",
        "text": (
            "Brevissimo (max 5 righe): ci sono decisioni "
            "architetturali aperte oggi sul lavoro corrente? "
            "Elencale."
        ),
    },
    {
        "slug": "p3_projects",
        "text": (
            "Brevissimo: quali progetti stiamo seguendo in "
            "parallelo? Elenca i nomi."
        ),
    },
    {
        "slug": "p4_style",
        "text": (
            "Brevissimo: come preferisce comunicare Aurelio? "
            "Una riga di sintesi sul collab style."
        ),
    },
]


def _run_claude(prompt: str, timeout_s: int = 120) -> tuple[str, float, dict]:
    """Spawn `claude -p` silently, return (stdout, latency_s, parsed_json_or_empty)."""
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json"],
            capture_output=True,
            timeout=timeout_s,
            text=True,
            check=False,
        )
        lat = time.perf_counter() - t0
        stdout = proc.stdout or ""
        # Try to parse JSON
        parsed = {}
        try:
            parsed = json.loads(stdout)
        except json.JSONDecodeError:
            pass
        return stdout, lat, parsed
    except subprocess.TimeoutExpired:
        return "", time.perf_counter() - t0, {}


def _count_signal_tokens(text: str) -> tuple[int, list[str]]:
    """Count case-insensitive occurrences of SIGNAL_TOKENS in text.
    Each token counted once max (presence)."""
    found = []
    low = (text or "").lower()
    for tok in SIGNAL_TOKENS:
        if tok.lower() in low:
            found.append(tok)
    return len(found), found


def _disable_self_model() -> bool:
    """Rename self_model.db so SessionStart hook skips injection."""
    if not SELF_MODEL_DB.exists():
        return False
    try:
        if BACKUP_DB.exists():
            BACKUP_DB.unlink()
        shutil.move(str(SELF_MODEL_DB), str(BACKUP_DB))
        return True
    except Exception:
        return False


def _enable_self_model() -> bool:
    """Restore self_model.db from backup."""
    if not BACKUP_DB.exists():
        return False
    try:
        if SELF_MODEL_DB.exists():
            SELF_MODEL_DB.unlink()
        shutil.move(str(BACKUP_DB), str(SELF_MODEL_DB))
        return True
    except Exception:
        return False


def _recover_from_crash() -> bool:
    """SCAN-68 [46]: se un run precedente e' crashato HARD (kill/segfault =
    bypass del finally) lasciando il self_model.db reale rinominato in
    .bench_backup (e il reale assente), ripristinalo. True se ha recuperato."""
    if BACKUP_DB.exists() and not SELF_MODEL_DB.exists():
        shutil.move(str(BACKUP_DB), str(SELF_MODEL_DB))
        return True
    return False


def main() -> int:
    # SCAN-68 [46] 2026-06-02 (NONNA): questo bench RINOMINA il self_model.db
    # REALE. (a) opt-in esplicito contro run accidentali; (b) auto-recovery da
    # un eventuale hard-crash precedente (il finally copre solo le eccezioni,
    # NON kill -9/segfault che lasciano il DB come .bench_backup).
    if os.environ.get("HIPPO_ALLOW_REAL_BENCH") != "1":
        print("SKIP: bench su self_model.db REALE disabilitato. Esegui con "
              "HIPPO_ALLOW_REAL_BENCH=1 per acconsentire alla rinomina del DB.")
        return 0
    if _recover_from_crash():
        print(f"RECOVERY: ripristinato {SELF_MODEL_DB.name} da un run precedente crashato")

    if not SELF_MODEL_DB.exists():
        print("ERROR: self_model.db not found. Run cycle #67 init first.")
        return 1

    print("=== Cycle #67 validation — A/B bench via CLI silenziosa ===")
    print(f"  prompts: {len(PROMPTS)}, signal tokens: {len(SIGNAL_TOKENS)}")
    print(f"  self_model.db: {SELF_MODEL_DB}")
    print()

    results: list[dict] = []

    # ---- Test A: self_model PRESENT ----
    print("[A] self_model PRESENT — running fresh instances...")
    for p in PROMPTS:
        print(f"  -> {p['slug']}", flush=True)
        stdout, lat, parsed = _run_claude(p["text"])
        # Claude json output structure: {result, total_cost_usd, ...} or text
        response_text = (
            parsed.get("result") if parsed else stdout
        )
        n_tok, found = _count_signal_tokens(response_text or "")
        results.append({
            "slug": p["slug"],
            "variant": "A_with_self_model",
            "prompt": p["text"][:80],
            "latency_s": round(lat, 1),
            "n_tokens_cited": n_tok,
            "tokens_found": found,
            "response_len": len(response_text or ""),
            "raw_truncated": (response_text or "")[:400],
        })
        print(f"     citation={n_tok}/{len(SIGNAL_TOKENS)} latency={lat:.1f}s")

    # ---- Disable self_model for Test B ----
    print()
    print("[B] disabling self_model.db ...")
    if not _disable_self_model():
        print("ERROR: could not disable self_model.db")
        return 1

    try:
        print("[B] self_model ABSENT — running fresh instances...")
        for p in PROMPTS:
            print(f"  -> {p['slug']}", flush=True)
            stdout, lat, parsed = _run_claude(p["text"])
            response_text = (
                parsed.get("result") if parsed else stdout
            )
            n_tok, found = _count_signal_tokens(response_text or "")
            results.append({
                "slug": p["slug"],
                "variant": "B_without_self_model",
                "prompt": p["text"][:80],
                "latency_s": round(lat, 1),
                "n_tokens_cited": n_tok,
                "tokens_found": found,
                "response_len": len(response_text or ""),
                "raw_truncated": (response_text or "")[:400],
            })
            print(f"     citation={n_tok}/{len(SIGNAL_TOKENS)} latency={lat:.1f}s")
    finally:
        print()
        print("[B] restoring self_model.db ...")
        if not _enable_self_model():
            print("WARNING: failed to restore self_model.db from backup!")

    # ---- Summary ----
    print()
    print("=== SUMMARY ===")
    a_results = [r for r in results if r["variant"] == "A_with_self_model"]
    b_results = [r for r in results if r["variant"] == "B_without_self_model"]
    avg_a = sum(r["n_tokens_cited"] for r in a_results) / len(a_results)
    avg_b = sum(r["n_tokens_cited"] for r in b_results) / len(b_results)
    lat_a = sum(r["latency_s"] for r in a_results) / len(a_results)
    lat_b = sum(r["latency_s"] for r in b_results) / len(b_results)
    delta = avg_a - avg_b
    print(f"  avg citations A (self_model ON):  {avg_a:.2f}/{len(SIGNAL_TOKENS)}")
    print(f"  avg citations B (self_model OFF): {avg_b:.2f}/{len(SIGNAL_TOKENS)}")
    print(f"  DELTA: {delta:+.2f} tokens cited  ({delta/len(SIGNAL_TOKENS)*100:+.1f}%)")
    print(f"  avg latency A: {lat_a:.1f}s")
    print(f"  avg latency B: {lat_b:.1f}s")
    if delta >= 2.0:
        verdict = "SELF_MODEL_HELPS (>=+2 tokens cited)"
    elif delta >= 1.0:
        verdict = "MARGINAL"
    elif delta >= -1.0:
        verdict = "NO_EFFECT"
    else:
        verdict = "HURTS"
    print(f"  VERDICT: {verdict}")

    out_path = Path.home() / ".engram" / "audit" / "bench_self_model_ab.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "n_prompts": len(PROMPTS),
        "n_signal_tokens": len(SIGNAL_TOKENS),
        "avg_citations_A": round(avg_a, 2),
        "avg_citations_B": round(avg_b, 2),
        "delta_citations": round(delta, 2),
        "delta_pct": round(delta / len(SIGNAL_TOKENS) * 100, 1),
        "avg_latency_s_A": round(lat_a, 1),
        "avg_latency_s_B": round(lat_b, 1),
        "verdict": verdict,
    }
    out_path.write_text(
        json.dumps({"summary": summary, "results": results},
                   indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nFull report: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
