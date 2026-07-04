"""G4 (RELEASE_GATE): one entrypoint to reproduce every headline number.

Registry of the numbers Verimem publishes (README/STATE), each mapped to the
exact command that regenerates it and the results artifact that backs it.

    python -m benchmark.repro_all --list          # what's claimed, where
    python -m benchmark.repro_all --verify        # every claim has its artifact
    python -m benchmark.repro_all --show <key>    # command + current artifact value
    python -m benchmark.repro_all --run <key>     # actually rerun (some need claude -p)

--verify is the release-gate check: a claim whose artifact is missing FAILS
loudly (that number must then be removed from the docs or re-run). Costs are
declared per entry (local = free/deterministic; claude-p = paced serial LLM).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

_R = Path(__file__).resolve().parent / "results"

#: key -> {claim, artifact, jsonpath (dot keys), command, cost}
REGISTRY: dict[str, dict] = {
    "gate-auroc": {
        "claim": "write-path source⊢fact grounding AUROC 0.971 (SNLI)",
        "artifact": "fact_grounding.json",
        "value_at": ["auroc_faithful_vs_confab"],
        "command": "python -m benchmark.fact_grounding_bench --out benchmark/results/fact_grounding.json",
        "cost": "claude-p",
    },
    "moat-downstream": {
        "claim": "downstream hallucination 95.9% -> 12.2% with gate ON (seed 7)",
        "artifact": "halumem_moat_fixedpair.json",
        "value_at": [],
        "command": "python -m benchmark.halumem_writepath_moat --noise-mode same-topic --seed 7 --out benchmark/results/halumem_moat_fixedpair.json",
        "cost": "claude-p",
    },
    "lme-recall": {
        "claim": "LongMemEval-S recall@5 0.8745 fusion ON (full 500)",
        "artifact": "lme_s_fusionON_n500_clean.json",
        "value_at": [],
        "command": "python -m benchmark.lme_retrieval_bench --fusion on --n 500 --out benchmark/results/lme_s_fusionON_n500_clean.json",
        "cost": "local",
    },
    "updating-severe-oof": {
        "claim": "HaluMem updating severe accuracy 0.3286 (selector v3, out-of-fold)",
        "artifact": "halumem_selector_v3.json",
        "value_at": ["policies", "v3_oof_abstain0.0", "accuracy"],
        "command": "python -m benchmark.halumem_selector_v3 --dump benchmark/results/halumem_updating_full20_dump.json --out benchmark/results/halumem_selector_v3.json",
        "cost": "local",
    },
    "updating-judge": {
        "claim": "HaluMem updating judge-corrected 0.2867 (61-item Claude-judge pass)",
        "artifact": "halumem_updating_v3_judged.json",
        "value_at": ["judge_corrected_accuracy"],
        "command": "python -m benchmark.halumem_updating_judge_pass --results benchmark/results/halumem_updating_v3_selections.json --per-class 30 --out benchmark/results/halumem_updating_v3_judged.json",
        "cost": "claude-p",
    },
    "qa-cho": {
        "claim": "HaluMem QA C/H/O: correct 0.408 / hallucination 0.233 (n=120, strict)",
        "artifact": "halumem_qa_cho_n120.json",
        "value_at": ["correct_rate"],
        "command": "python -m benchmark.halumem_qa_bench --users 8 --q-per-user 15 --seed 7 --out benchmark/results/halumem_qa_cho_n120.json",
        "cost": "claude-p",
    },
    "extraction-f1": {
        "claim": "HaluMem Extraction F1 0.6499 gate ON (60 sessions)",
        "artifact": "halumem_extraction_f1_u10s6.json",
        "value_at": ["on", "f1"],
        "command": "python -m benchmark.halumem_extraction_f1 --users 10 --sessions 6 --out benchmark/results/halumem_extraction_f1_u10s6.json",
        "cost": "claude-p",
    },
    "interference": {
        "claim": "HaluMem interference TPR ~0.70 contradiction / low control FPR (ts fix, seed 7)",
        "artifact": "halumem_score_ts_seed7.json",
        "value_at": ["tpr_contradiction"],
        "command": "python -m benchmark.halumem_interference_stage + judge workflow + halumem_interference_score (see docs/BENCHMARKS.md pipeline)",
        "cost": "claude-p",
    },
}


def _dig(obj, keys):
    """keys is a LIST — artifact keys may themselves contain dots
    (e.g. 'v3_oof_abstain0.0'), so dotted-string paths are unusable."""
    for k in keys:
        obj = obj[k]
    return obj


def cmd_list() -> int:
    for k, e in REGISTRY.items():
        print(f"{k:22s} [{e['cost']:8s}] {e['claim']}")
    return 0


def cmd_verify() -> int:
    missing = []
    for k, e in REGISTRY.items():
        p = _R / e["artifact"]
        if not p.exists():
            missing.append((k, e["artifact"]))
            print(f"FAIL {k}: artifact missing -> {e['artifact']}")
            continue
        note = ""
        if e["value_at"]:
            try:
                v = _dig(json.loads(p.read_text(encoding="utf-8")), e["value_at"])
                note = f" (current value: {v})"
            except Exception as exc:  # noqa: BLE001 — report, don't crash the audit
                missing.append((k, f"{e['artifact']}::{e['value_at']}"))
                print(f"FAIL {k}: cannot read {e['value_at']}: {exc}")
                continue
        print(f"ok   {k}{note}")
    print(f"\n{len(REGISTRY) - len(missing)}/{len(REGISTRY)} claims backed by artifacts")
    return 1 if missing else 0


def cmd_show(key: str) -> int:
    e = REGISTRY[key]
    print(json.dumps(e, indent=2))
    p = _R / e["artifact"]
    if p.exists() and e["value_at"]:
        print("current:", _dig(json.loads(p.read_text(encoding="utf-8")), e["value_at"]))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true")
    g.add_argument("--verify", action="store_true")
    g.add_argument("--show", metavar="KEY")
    g.add_argument("--run", metavar="KEY")
    a = ap.parse_args(argv)
    if a.list:
        return cmd_list()
    if a.verify:
        return cmd_verify()
    if a.show:
        return cmd_show(a.show)
    if a.run:
        import subprocess
        import sys
        e = REGISTRY[a.run]
        print(f"[{e['cost']}] {e['command']}")
        return subprocess.call([sys.executable, "-m"] + e["command"].split()[2:])
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
