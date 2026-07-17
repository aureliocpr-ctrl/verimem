"""Write-repair A/B on HaluMem GT (heldout users only) — FALSIFICATION HARNESS.

VERDICT (2026-07-02, run on the shipped local v2 gate): the write-repair idea
("on reject, replace the candidate fact with the most-anchored VERBATIM source
unit and re-gate that") is **FALSIFIED as a recovery lever, NOT wired**. Two
reasons, both in benchmark/results/write_repair_ab.json:

  * P1 obsolete premise: the local v2 gate's clean-admit on HaluMem heldout is
    already 0.924 — the documented "30-39% over-rejection" was the CLAUDE judge at
    θ=40, which v2 already closed. Repair recovers only +7.6pp (< the +10pp bar).
  * P2 tautology: re-gating a span⊆source against that source is trivially entailed
    (the CE saturates at ~99.97, threshold 99.64), so repair is a UNIVERSAL pass:
    interference (assistant-injected false memories) admission rose 0.051 → 0.994
    (+94.3pp). The lexical coverage guard τ only changes HOW MANY candidates, not
    their validity (at τ=0.5 interference still 0.949). It launders negatives.

Kept as a self-contained, re-runnable falsification (repair logic inlined below so
no production module has to carry dead code). PRE-REGISTERED PREDICTIONS, both
FAILED:
  P1: clean effective-admit >= baseline +10pp.
  P2: interference/foreign admission must NOT rise by more than +2pp.

Setup mirrors the v2 recipe exactly (same seed pipeline, same split): pairs from
``local_gate_eval.build_pairs(seed=11, n_clean=300, n_interference=300,
n_foreign=100, budget=1500, speakers=True)``; ``split_by_user(seed=11)``; ONLY the
heldout half is measured. Judge = the SHIPPED local v2 backend
(ENGRAM_GROUNDING_BACKEND=local); the injected llm is a tripwire that RAISES, so a
model-load failure aborts loudly instead of silently benchmarking claude. Zero
claude -p in the whole run.

    python -m benchmark.write_repair_ab --out benchmark/results/write_repair_ab.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

# --- inlined repair logic (falsified; deliberately NOT a production module) ------
_WORD = re.compile(r"[a-z0-9]+")
_STOP = frozenset((
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "to",
    "of", "in", "on", "at", "for", "and", "or", "but", "with", "that", "this",
    "these", "those", "it", "its", "as", "by", "from", "about", "has", "have",
    "had", "do", "does", "did", "not", "no", "he", "she", "they", "them", "his",
    "her", "their", "i", "you", "we", "my", "your", "our", "me", "us", "who",
    "which", "what", "when", "user", "assistant",
))
DEFAULT_MIN_COVERAGE = 0.25
DEFAULT_TOP_K = 3


def _stem(t: str) -> str:
    prev = None
    while t != prev:
        prev = t
        for suf in ("ing", "ed", "es", "s"):
            if t.endswith(suf) and len(t) - len(suf) >= 3:
                t = t[: len(t) - len(suf)]
                break
        if len(t) >= 4 and t[-1] == t[-2]:
            t = t[:-1]
    return t


def _content_tokens(text: str) -> set[str]:
    return {_stem(t) for t in _WORD.findall((text or "").lower())
            if len(t) > 2 and t not in _STOP}


def _units(source: str) -> list[str]:
    units = [u.strip() for u in (source or "").split("\n") if u.strip()]
    if len(units) <= 1:
        units = [u.strip() for u in re.split(r"(?<=[.!?])\s+", source or "")
                 if u.strip()]
    return units


def repair_candidates(source: str, fact: str, *, top_k: int = DEFAULT_TOP_K,
                      min_coverage: float = DEFAULT_MIN_COVERAGE) -> list[str]:
    ft = _content_tokens(fact)
    if not ft:
        return []
    scored = []
    for i, u in enumerate(_units(source)):
        cov = len(_content_tokens(u) & ft) / len(ft)
        if cov >= min_coverage:
            scored.append((cov, i, u))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [u for _c, _i, u in scored[: max(0, int(top_k))]]


class TripwireLLM:
    """Injected-llm stand-in that must NEVER be reached: the bench measures the
    LOCAL judge only. Reaching this means the local model failed to load and the
    gate tried to fail over — abort loudly, do not silently benchmark claude."""

    def complete(self, *_a, **_k):  # pragma: no cover - tripwire
        raise RuntimeError(
            "local gate backend unavailable — the bench refuses to fall back to "
            "the claude judge; fix ENGRAM_LOCAL_GATE_MODEL / the v2 model dir")


def _rate(k: int, n: int) -> float | None:
    return round(k / n, 3) if n else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--halumem",
                    default=str(Path.home() / ".cache/halumem/HaluMem-Medium.jsonl"))
    ap.add_argument("--seed", type=int, default=11)      # v2 recipe pipeline
    ap.add_argument("--budget", type=int, default=1500)  # v2 recipe span budget
    ap.add_argument("--taus", default="0.2,0.25,0.35,0.5")
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--max-per-kind", type=int, default=0,
                    help="cap heldout items per kind (0 = all; use for quick runs)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    # Local backend ONLY (set before any gate import path resolves it).
    os.environ["ENGRAM_GROUNDING_BACKEND"] = "local"

    from benchmark.local_gate_eval import build_pairs, split_by_user
    from verimem.grounding_gate import should_store_fact
    from verimem.local_grounding import get_local_judge

    def repair_store(span, fact, *, top_k, min_coverage):
        """Gate; on reject try the most-anchored source unit. Returns
        (store?, stored_fact, score, repaired?, orig_score)."""
        ok, score = should_store_fact(llm, span, fact)
        if ok:
            return True, fact, score, False, score
        for cand in repair_candidates(span, fact, top_k=top_k,
                                      min_coverage=min_coverage):
            c_ok, c_score = should_store_fact(llm, span, cand)
            if c_ok:
                return True, cand, c_score, True, score
        return False, fact, score, False, score

    judge = get_local_judge()
    judge_thr = judge.threshold
    if judge_thr is None:
        raise SystemExit("local model ships no calibrated threshold — refuse to "
                         "bench against an uncalibrated cut")

    pairs = build_pairs(a.halumem, seed=a.seed, n_clean=300, n_interference=300,
                        n_foreign=100, budget=a.budget, speakers=True)
    _calib, held = split_by_user(pairs, seed=a.seed)
    by_kind: dict[str, list[dict]] = {"clean": [], "interference": [], "foreign": []}
    for p in held:
        by_kind.setdefault(p["kind"], []).append(p)
    if a.max_per_kind:
        for k in by_kind:
            by_kind[k] = by_kind[k][: a.max_per_kind]

    llm = TripwireLLM()
    t0 = time.time()

    # ---- arm A: plain gate (baseline) -------------------------------------
    base: dict[str, list[bool]] = {}
    for kind, items in by_kind.items():
        base[kind] = [should_store_fact(llm, p["span"], p["fact"])[0] for p in items]

    taus = [float(t) for t in a.taus.split(",") if t.strip()]
    sweep: dict[str, dict] = {}
    examples: list[dict] = []

    # ---- arm B: gate + repair, per tau ------------------------------------
    for tau in taus:
        row: dict[str, dict] = {}
        for kind, items in by_kind.items():
            n = len(items)
            eff_admit = 0
            repaired = 0
            for i, p in enumerate(items):
                store, sfact, sscore, was_rep, oscore = repair_store(
                    p["span"], p["fact"], top_k=a.top_k, min_coverage=tau)
                if store:
                    eff_admit += 1
                    if was_rep:
                        repaired += 1
                        if (kind == "clean" and tau == 0.25
                                and len(examples) < 6):
                            examples.append({
                                "original": p["fact"],
                                "original_score": oscore,
                                "repaired": sfact,
                                "score": sscore,
                            })
            base_admit = sum(base[kind])
            row[kind] = {
                "n": n,
                "admit_base": _rate(base_admit, n),
                "admit_effective": _rate(eff_admit, n),
                "repaired_in": _rate(repaired, n),
            }
        sweep[str(tau)] = row

    # ---- verdict against the pre-registered predictions --------------------
    d = sweep.get("0.25") or sweep[str(taus[0])]
    clean_delta = (d["clean"]["admit_effective"] or 0) - (d["clean"]["admit_base"] or 0)
    neg_delta = max(
        (d[k]["admit_effective"] or 0) - (d[k]["admit_base"] or 0)
        for k in ("interference", "foreign") if d.get(k, {}).get("n"))
    res = {
        "judge": {"backend": "local", "model_dir": str(judge.model_dir),
                  "threshold": judge_thr, "focus_budget": judge.focus_budget},
        "heldout_counts": {k: len(v) for k, v in by_kind.items()},
        "top_k": a.top_k,
        "sweep": sweep,
        "repaired_examples_tau_0.25": examples,
        "wall_s": round(time.time() - t0, 1),
        "verdict": {
            "P1_clean_recovery_pp": round(clean_delta * 100, 1),
            "P1_met_(>=+10pp)": clean_delta >= 0.10,
            "P2_worst_negative_rise_pp": round(neg_delta * 100, 1),
            "P2_met_(<=+2pp)": neg_delta <= 0.02,
        },
    }
    print(json.dumps(res, indent=2))
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
