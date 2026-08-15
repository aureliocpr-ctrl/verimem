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


def _run_claude(prompt: str,
                timeout_s: int = 120) -> tuple[str, float, dict, str]:
    """Spawn `claude -p` silently, return (stdout, latency_s, parsed, fault).

    The model is explicit on purpose: the headless CLI does not inherit the
    calling session's model, and an A/B whose two arms silently ran on the CLI
    default measures the default, not the change (2026-07-25).

    ⚠️ `fault` added 2026-08-15, and here the discarded outcome was worse than
    on the two briefing benches. There a dead process looked FAST; here it
    manufactures a scientific conclusion:

      · dead in BOTH arms   -> 0 tokens either side -> delta 0.00 -> the
        `delta >= -1.0` branch prints **VERDICT: NO_EFFECT** and writes it to
        `~/.engram/audit/bench_self_model_ab.json`. A total failure produces
        the most publishable finding there is.
      · dead in ONE arm only (a rate limit landing halfway is enough) -> that
        arm averages 0 and the delta goes wide -> **SELF_MODEL_HELPS** or
        **HURTS**. A partial failure manufactures a POSITIVE result.

    ⇒ An A/B must refuse to conclude when an arm did not run. The verdict is
    withheld, not softened: `MEASUREMENT_INVALID` and the reason.
    """
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json",
             "--model", os.environ.get("BENCH_CLAUDE_MODEL", "claude-opus-4-8")],
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
        if proc.returncode != 0:
            tail = (proc.stderr or "")[-300:]
            return stdout, lat, parsed, f"rc={proc.returncode} stderr={tail!r}"
        return stdout, lat, parsed, ""
    except subprocess.TimeoutExpired:
        return "", time.perf_counter() - t0, {}, f"timeout after {timeout_s}s"
    except FileNotFoundError:
        # `claude` not on PATH: without this the bench would have reported
        # NO_EFFECT on a machine where it never ran at all.
        return "", time.perf_counter() - t0, {}, "`claude` not found on PATH"


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
        stdout, lat, parsed, fault = _run_claude(p["text"])
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
            "fault": fault,
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
            stdout, lat, parsed, fault = _run_claude(p["text"])
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
                "fault": fault,
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
    # ⚠️ Averages over the runs that ACTUALLY happened. A dead `claude` cites
    # zero tokens, so counting it drags its arm towards zero — and the delta,
    # which is the whole result, moves with it.
    a_valid = [r for r in a_results if not r["fault"]]
    b_valid = [r for r in b_results if not r["fault"]]
    faults = [r for r in results if r["fault"]]

    def _media(righe: list[dict], campo: str) -> float | None:
        return (sum(r[campo] for r in righe) / len(righe)) if righe else None

    avg_a = _media(a_valid, "n_tokens_cited")
    avg_b = _media(b_valid, "n_tokens_cited")
    lat_a = _media(a_valid, "latency_s")
    lat_b = _media(b_valid, "latency_s")
    delta = (avg_a - avg_b) if (avg_a is not None and avg_b is not None) else None
    def _mostra(x: float | None, cifre: int = 2) -> str:
        return "n/d" if x is None else f"{x:.{cifre}f}"

    print(f"  runs A: {len(a_valid)}/{len(a_results)} valid"
          f"   runs B: {len(b_valid)}/{len(b_results)} valid")
    print(f"  avg citations A (self_model ON):  "
          f"{_mostra(avg_a)}/{len(SIGNAL_TOKENS)}")
    print(f"  avg citations B (self_model OFF): "
          f"{_mostra(avg_b)}/{len(SIGNAL_TOKENS)}")
    if delta is None:
        print("  DELTA: n/d — an arm has no valid run")
    else:
        print(f"  DELTA: {delta:+.2f} tokens cited  "
              f"({delta/len(SIGNAL_TOKENS)*100:+.1f}%)")
    print(f"  avg latency A: {_mostra(lat_a, 1)}s")
    print(f"  avg latency B: {_mostra(lat_b, 1)}s")

    # 🔑 THE VERDICT IS WITHHELD, NOT SOFTENED. Before this, a `claude` that
    # died in both arms gave delta 0.00, which falls in the `>= -1.0` branch:
    # the bench printed NO_EFFECT and saved it. A failure must not be able to
    # produce a finding — least of all the most publishable one.
    if faults:
        verdict = (f"MEASUREMENT_INVALID — {len(faults)} of {len(results)} "
                   f"runs did not complete: {faults[0]['fault']}")
    elif delta >= 2.0:
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
        # First three on purpose: a reader who stops at the top of the report
        # still learns whether the run measured anything.
        "measurement_valid": not faults,
        "runs_that_did_not_complete": len(faults),
        "first_fault": faults[0]["fault"] if faults else None,
        "n_prompts": len(PROMPTS),
        "n_signal_tokens": len(SIGNAL_TOKENS),
        "n_valid_runs_A": len(a_valid),
        "n_valid_runs_B": len(b_valid),
        # `None` and not 0.0 when an arm has nothing valid: a zero would read
        # as a measured result instead of as an absent measurement.
        "avg_citations_A": None if avg_a is None else round(avg_a, 2),
        "avg_citations_B": None if avg_b is None else round(avg_b, 2),
        "delta_citations": None if delta is None else round(delta, 2),
        "delta_pct": (
            None if delta is None
            else round(delta / len(SIGNAL_TOKENS) * 100, 1)
        ),
        "avg_latency_s_A": None if lat_a is None else round(lat_a, 1),
        "avg_latency_s_B": None if lat_b is None else round(lat_b, 1),
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
