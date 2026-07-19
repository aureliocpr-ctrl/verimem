"""Evolution-moat benchmark — Verimem 0.7.0 vs mem0 2.0.4, same-source value updates.

The scenario every long-lived agent hits: a source it trusts UPDATES one of its own
facts (300°->900°, March->September, one CEO->another). A memory layer without a
contradiction moat keeps BOTH the stale and the current value and will happily recall
the stale one — a confabulation. Verimem's default moat RETIRES the stale value
(superseded_by), so default recall serves only the current one.

Fairness — this isolates the LAYER, nothing else:
  * identical data, identical subjects, identical top-k retrieval;
  * SAME embedder family — mem0 uses intfloat/multilingual-e5-base, Verimem uses the
    same e5 encoder;
  * mem0 runs 100% local, ZERO external API (infer=False, no LLM call) — a fair, real run
    of the competitor, not a strawman;
  * three Verimem arms so the honest boundary is visible: DEFAULT (deterministic lexical
    L3 — numeric/version/date/negation) and +NLI (ENGRAM_SEMANTIC_CONFLICT=1, the opt-in
    semantic tier that also catches entity substitutions).

Metrics, per arm, over the 5 same-source updates:
  stale_leak     — subjects whose RETIRED old value still returns in default recall (lower=better; the confab risk)
  current_served — subjects whose NEW value returns (must stay 5/5 — never lose the truth)
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

# (subject, old, new, stale_token, current_token, kind)
# SET A — a realistic mixed update stream (1 numeric, 1 month-name date, 3 entity
# substitutions). The 3 entity cases are, by design, the NLI tier's job (the README
# scopes the zero-config lexical detector to numeric/version/date/negation), so this
# set is where the opt-in +NLI arm earns its keep.
PAIRS_MIXED = [
    ("Zorbex reactor temperature",
     "The Zorbex reactor operates at 300 degrees.",
     "The Zorbex reactor operates at 900 degrees.", "300", "900", "numeric"),
    ("Project Aurora launch date",
     "Project Aurora launches in March 2025.",
     "Project Aurora launches in September 2025.", "March", "September", "month"),
    ("CEO of Kappa Dynamics",
     "Helena Vostok is the CEO of Kappa Dynamics.",
     "Marcus Reyes is the CEO of Kappa Dynamics.", "Helena Vostok", "Marcus Reyes", "entity"),
    ("capital of Ruritania",
     "The capital of Ruritania is Zenda.",
     "The capital of Ruritania is Strelsau.", "Zenda", "Strelsau", "entity"),
    ("Talos engine fuel",
     "The Talos engine uses hydrogen fuel.",
     "The Talos engine uses methane fuel.", "hydrogen", "methane", "entity"),
]
# SET B — the zero-config lexical moat's DESIGN TARGET: numeric / version /
# numeric-date / negation changes (what a plain Memory() catches with no model load,
# no opt-in). This is the honest picture of the DEFAULT differentiator vs a no-moat store.
PAIRS_LEXICAL = [
    ("subscription monthly price",
     "The subscription costs 100 euros per month.",
     "The subscription costs 150 euros per month.", "100", "150", "numeric"),
    ("reserve tank capacity in liters",
     "The reserve tank holds 500 liters.",
     "The reserve tank holds 900 liters.", "500", "900", "numeric"),
    ("shipped release version",
     "Orion ships on version 2.3.1.",
     "Orion ships on version 4.0.0.", "2.3.1", "4.0.0", "version"),
    ("audit calendar date",
     "The compliance audit is on 2025-03-06.",
     "The compliance audit is on 2025-09-20.", "2025-03-06", "2025-09-20", "numdate"),
    ("contract signature state",
     "The vendor contract is signed.",
     "The vendor contract is not signed.", "is signed", "not signed", "negation"),
]
TOPK = 5


def _tally(rows: list[dict]) -> dict:
    return {
        "stale_leak": sum(1 for r in rows if r["stale_present"]),
        "current_served": sum(1 for r in rows if r["current_present"]),
        "n": len(rows),
        "by_subject": rows,
    }


def run_mem0(pairs: list) -> dict:
    """mem0 2.0.4, local e5 + chroma, infer=False (no LLM, zero external API)."""
    from mem0 import Memory as M0
    cfg = {
        "llm": {"provider": "ollama", "config": {"model": "never-called"}},
        "embedder": {"provider": "huggingface",
                     "config": {"model": "intfloat/multilingual-e5-base"}},
        "vector_store": {"provider": "chroma",
                         "config": {"path": tempfile.mkdtemp(),
                                    "collection_name": f"evo{id(pairs) & 0xffff}"}},
    }
    m = M0.from_config(cfg)
    uid = "u"
    rows = []
    for subj, old, new, st, cur, kind in pairs:
        m.add(f"passage: {old}", user_id=uid, infer=False)
        m.add(f"passage: {new}", user_id=uid, infer=False)
        qv = m.embedding_model.embed(f"query: {subj}", "search")
        hits = m.vector_store.search(query=f"query: {subj}", vectors=qv, top_k=TOPK,
                                     filters={"user_id": uid})
        texts = [str((getattr(h, "payload", None) or {}).get("data", "")) for h in hits]
        blob = " ".join(texts)
        rows.append({"subject": subj, "kind": kind,
                     "stale_present": st in blob, "current_present": cur in blob})
    return _tally(rows)


def run_verimem(pairs: list, nli: bool) -> dict:
    """Verimem 0.7.0 Memory(). Same source for old+new of each subject (the source
    updates its own value → same-source evolution). nli=True = the DEFAULT on a warmed
    machine (env UNSET → auto-enforce, the model is installed here); nli=False = the
    explicit lexical-only opt-out (ENGRAM_SEMANTIC_CONFLICT=0)."""
    os.environ.pop("ENGRAM_SUPERSEDE_SAME_SOURCE", None)  # rely on the 0.7.0 default (ON)
    if nli:
        os.environ.pop("ENGRAM_SEMANTIC_CONFLICT", None)  # UNSET = auto → enforce here
    else:
        os.environ["ENGRAM_SEMANTIC_CONFLICT"] = "0"      # explicit opt-out
    from verimem.client import Memory
    mem = Memory(Path(tempfile.mkdtemp()) / "evo.db")
    rows = []
    superseded_total = 0
    for i, (subj, old, new, st, cur, kind) in enumerate(pairs):
        src = [f"source-doc:{i}"]                       # SAME source for old + new
        mem.add(old, topic=f"evo/{i}", verified_by=src)
        r2 = mem.add(new, topic=f"evo/{i}", verified_by=src)
        superseded_total += len(r2.get("superseded") or [])
        hits = mem.search(subj, k=TOPK)
        texts = [str(h.get("text", "")) for h in hits]
        blob = " ".join(texts)
        rows.append({"subject": subj, "kind": kind,
                     "stale_present": st in blob, "current_present": cur in blob,
                     "superseded": r2.get("superseded") or []})
    out = _tally(rows)
    out["superseded_total"] = superseded_total
    return out


def _fmt(name: str, r: dict) -> str:
    return (f"  {name:<26} stale_leak={r['stale_leak']}/{r['n']}   "
            f"current_served={r['current_served']}/{r['n']}"
            + (f"   superseded={r.get('superseded_total')}" if "superseded_total" in r else ""))


def _report_set(label: str, pairs: list) -> dict:
    block = {
        "mem0": run_mem0(pairs),
        "verimem_lexical_only_optout": run_verimem(pairs, nli=False),
        "verimem_default_auto_nli": run_verimem(pairs, nli=True),
    }
    print(f"\n--- {label} (n={len(pairs)}) ---")
    print(_fmt("mem0 (no moat)", block["mem0"]))
    print(_fmt("verimem lexical-only (=0)", block["verimem_lexical_only_optout"]))
    print(_fmt("verimem DEFAULT (auto-NLI)", block["verimem_default_auto_nli"]))
    print("  per-subject stale leak (LEAK = stale value still recalled):")
    for arm in ("mem0", "verimem_lexical_only_optout", "verimem_default_auto_nli"):
        marks = " ".join(
            f"{r['kind'][:4]}:{'LEAK' if r['stale_present'] else 'ok'}"
            for r in block[arm]["by_subject"])
        print(f"    {arm:<26} {marks}")
    return block


_SETS = {
    "A": ("set_A_mixed",
          "SET A — realistic mixed stream (numeric + month-name date + 3 entity subs)",
          PAIRS_MIXED),
    "B": ("set_B_lexical_target",
          "SET B — the zero-config lexical moat's design target (numeric/version/numdate/negation)",
          PAIRS_LEXICAL),
}

if __name__ == "__main__":
    import sys
    # One set per PROCESS: loading e5 (x2) + the NLI cross-encoder for BOTH sets in a
    # single process exhausts RAM; a fresh process per set releases the models on exit.
    which = [a for a in sys.argv[1:] if a in _SETS] or ["A", "B"]
    print("\n=== EVOLUTION-MOAT BENCHMARK: Verimem 0.7.0 vs mem0 2.0.4 ===")
    print("  scenario: same-source value update (old -> new), default recall top-5")
    print("  embedder (both): intfloat/multilingual-e5-base   mem0: local infer=False (zero external API)")
    print("  metric: stale_leak = subjects whose RETIRED old value still returns (lower=better)")
    outdir = Path("benchmark/results")
    outdir.mkdir(parents=True, exist_ok=True)
    for key in which:
        json_key, label, pairs = _SETS[key]
        block = _report_set(label, pairs)
        (outdir / f"evolution_moat_vs_mem0_{key}.json").write_text(
            json.dumps({"scenario": "same-source value update, default recall top-5",
                        "embedder": "intfloat/multilingual-e5-base (both)",
                        "mem0_mode": "local infer=False (zero external API)",
                        json_key: block}, indent=2), encoding="utf-8")
        print(f"  saved: {outdir / f'evolution_moat_vs_mem0_{key}.json'}")
