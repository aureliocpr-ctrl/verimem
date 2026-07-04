#!/usr/bin/env python
"""FAIR hybrid-recall bench: fluent paraphrase queries vs vector-only (paired).

WHY a separate bench: the existing HARD suite (bench_recall_self) builds
queries as shuffled content-words OF THE FACT ITSELF — the same provenance
``recall_hybrid`` mines for its kw-overlap signal (trigger_keywords +
applicable_when are derived from the fact). Measuring hybrid on that regime
would inflate it artificially (shared-provenance confound). Here the queries
are FLUENT human-style paraphrases (hand-written, new wording), stored in a
JSON so the bench is reproducible, with an automated anti-leak guard: any
query sharing a verbatim >=4-word n-gram with its source fact is counted and
reported (and can be excluded with --strict).

Two modes:
  --dump   sample N_TARGET facts (seed 4242) from a COPY of the live corpus
           and write bench_hybrid_fair_facts.json for the paraphrase author.
  (none)   load bench_hybrid_fair_queries.json [{fact_id, query}], join with
           the facts present in a fresh COPY, run paired vector-vs-hybrid
           (k=50), report R@1/R@10/MRR + McNemar on R@1 and R@10, and write
           the durable verdict file.

Safety: every run works on a COPY of ~/.engram (never --live). Flags under
test: NONE — ENGRAM_RECALL_CENTERING=0 (refuted) and ENGRAM_RECALL_RERANK
unset (wired but not under test here). CPU-forced.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# CPU-force BEFORE any engram import (8GB GPU OOMs with e5 resident; "-1" is
# the reliable sentinel on this torch build, "" leaves CUDA visible).
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ.setdefault("HIPPO_RECALL_ENCODE_BUDGET_S", "60")
os.environ["ENGRAM_RECALL_CENTERING"] = "0"   # refuted -> baseline plain
os.environ["ENGRAM_RECALL_RERANK"] = "0"      # not under test (default ON since 2026-06-10 — pin OFF explicitly)

sys.path.insert(0, os.path.expanduser("~/Code/HippoAgent/scripts"))
from bench_recall_self import _copy_live_db, _mcnemar  # noqa: E402

from engram.semantic import SemanticMemory  # noqa: E402

SEED = 4242
N_TARGET = 120
MIN_WORDS = 10
K_DEEP = 50
SAMPLE_STATUSES = ("verified", "model_claim", "provisional")
HERE = Path(__file__).resolve().parent
FACTS_JSON = HERE / "bench_hybrid_fair_facts.json"
QUERIES_JSON = HERE / "bench_hybrid_fair_queries.json"
VERDICT_TXT = Path(os.path.expanduser(
    "~/Desktop/ProgettiAI/SIS-out-7-hybrid-fair-verdict.txt"))


def _sample(dst: Path) -> list[tuple[str, str]]:
    import random
    import sqlite3
    placeholders = ",".join("?" for _ in SAMPLE_STATUSES)
    conn = sqlite3.connect(str(dst))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        f"SELECT id, proposition FROM facts "
        f"WHERE superseded_by IS NULL AND status IN ({placeholders})",
        SAMPLE_STATUSES,
    ).fetchall()
    conn.close()
    pool = [(r["id"], r["proposition"]) for r in rows
            if r["proposition"] and len(r["proposition"].split()) >= MIN_WORDS]
    rng = random.Random(SEED)
    rng.shuffle(pool)
    return pool[:N_TARGET]


def _ngram_leak(query: str, prop: str, n: int = 4) -> bool:
    """True if query shares a verbatim n-gram (n words, casefolded) with prop."""
    def grams(text: str) -> set[tuple[str, ...]]:
        toks = [w.strip(".,;:()[]{}\"'`").lower() for w in text.split()]
        toks = [t for t in toks if t]
        return {tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)}
    return bool(grams(query) & grams(prop))


def cmd_dump() -> int:
    dst = _copy_live_db()
    facts = _sample(dst)
    FACTS_JSON.write_text(
        json.dumps([{"fact_id": fid, "proposition": p} for fid, p in facts],
                   ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"dumped {len(facts)} facts -> {FACTS_JSON}")
    return 0


def _rank(ids: list[str], gold: str) -> int:
    return ids.index(gold) + 1 if gold in ids else 0


def cmd_bench(strict: bool) -> int:
    t0 = time.time()
    if not QUERIES_JSON.exists():
        print(f"missing {QUERIES_JSON} — write the paraphrases first")
        return 1
    queries = json.loads(QUERIES_JSON.read_text(encoding="utf-8"))
    dst = _copy_live_db()
    sm = SemanticMemory(db_path=dst)

    # Join with the facts actually present in this copy (corpus drift safety)
    import sqlite3
    conn = sqlite3.connect(str(dst))
    conn.row_factory = sqlite3.Row
    present = {r["id"]: r["proposition"] for r in conn.execute(
        "SELECT id, proposition FROM facts WHERE superseded_by IS NULL")}
    conn.close()

    probes: list[tuple[str, str]] = []
    leaks = 0
    for row in queries:
        fid, q = row["fact_id"], (row["query"] or "").strip()
        if not q or fid not in present:
            continue
        if _ngram_leak(q, present[fid]):
            leaks += 1
            if strict:
                continue
        probes.append((q, fid))
    n = len(probes)
    if n == 0:
        print("no usable probes")
        return 1

    sm.recall("warm up the encoder and the corpus cache please", k=5)
    v1 = v10 = h1 = h10 = 0
    v_mrr = h_mrr = 0.0
    pv1, ph1, pv10, ph10 = [], [], [], []
    for i, (q, gold) in enumerate(probes, 1):
        rv = _rank([f.id for f, *_ in sm.recall(q, k=K_DEEP)], gold)
        rh = _rank([f.id for f, *_ in sm.recall_hybrid(q, k=K_DEEP)], gold)
        v1 += rv == 1; h1 += rh == 1                       # noqa: E702
        v10 += 1 <= rv <= 10; h10 += 1 <= rh <= 10          # noqa: E702
        v_mrr += (1.0 / rv) if 1 <= rv <= 10 else 0.0
        h_mrr += (1.0 / rh) if 1 <= rh <= 10 else 0.0
        pv1.append(1 if rv == 1 else 0); ph1.append(1 if rh == 1 else 0)  # noqa: E702
        pv10.append(1 if 1 <= rv <= 10 else 0); ph10.append(1 if 1 <= rh <= 10 else 0)  # noqa: E702
        if i % 20 == 0 or i == n:
            print(f"... {i}/{n} ({time.time()-t0:.0f}s)", flush=True)

    def _pairs(a: list[int], b: list[int]) -> tuple[int, int]:
        x = sum(1 for o, w in zip(a, b, strict=True) if o == 1 and w == 0)
        y = sum(1 for o, w in zip(a, b, strict=True) if o == 0 and w == 1)
        return x, y

    b1, c1 = _pairs(pv1, ph1)
    s1, p1 = _mcnemar(b1, c1)
    b10, c10 = _pairs(pv10, ph10)
    s10, p10 = _mcnemar(b10, c10)
    dt = time.time() - t0

    if (h1 > v1 or h10 > v10) and (p1 < 0.05 or p10 < 0.05):
        verdict = "HYBRID WIN (fair regime)"
    elif (h1 < v1 or h10 < v10) and (p1 < 0.05 or p10 < 0.05):
        verdict = "HYBRID HARMFUL (fair regime)"
    else:
        verdict = "non significativo"

    lines = [
        f"=== HYBRID FAIR n={n} (parafrasi fluenti, paired vector vs recall_hybrid, k={K_DEEP}) ===",
        f"anti-leak 4-gram: {leaks} query flaggate"
        + (" (ESCLUSE, --strict)" if strict else " (INCLUSE, dichiarate)"),
        f"R@1  vector={v1/n:.3f} hybrid={h1/n:.3f}  delta={h1/n-v1/n:+.3f}"
        f"   McNemar b={b1} c={c1} chi2={s1:.2f} p={p1:.5f}",
        f"R@10 vector={v10/n:.3f} hybrid={h10/n:.3f}  delta={h10/n-v10/n:+.3f}"
        f"   McNemar b={b10} c={c10} chi2={s10:.2f} p={p10:.5f}",
        f"MRR  vector={v_mrr/n:.3f} hybrid={h_mrr/n:.3f}  delta={(h_mrr-v_mrr)/n:+.3f}",
        f"tempo: {dt:.0f}s ({dt/n:.2f}s/probe, 2 recall a probe)",
        f"VERDETTO-HYBRID: R@1 {v1/n:.3f}->{h1/n:.3f} R@10 {v10/n:.3f}->{h10/n:.3f}"
        f" p(R@1)={p1:.5f} p(R@10)={p10:.5f} -> {verdict}",
    ]
    out = "\n".join(lines)
    print(out, flush=True)
    VERDICT_TXT.write_text(out + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    if "--dump" in sys.argv:
        raise SystemExit(cmd_dump())
    raise SystemExit(cmd_bench(strict="--strict" in sys.argv))
