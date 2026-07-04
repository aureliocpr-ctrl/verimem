#!/usr/bin/env python
"""FAIR-regime validation of the opt-in reranker: decide default-ON.

WHY: the reranker was validated n=300 on the HARD regime (shuffled
content-words of the fact itself -> R@1 0.52->0.81, commit a98c9c3) — the
SAME regime that had inflated recall_hybrid before the fair bench refuted
it (R@1 0.54->0.24, commit 2f92d9e). Before flipping ENGRAM_RECALL_RERANK
default-ON, the reranker must survive the fair regime too: fluent
paraphrase queries (bench_hybrid_fair_queries.json, n~120), paired, with
the anti-leak 4-gram guard declared.

Arms (paired, same probe, same process — the flag is read per-call):
  A baseline: SemanticMemory.recall(q, k=50), ENGRAM_RECALL_RERANK=0.
  B rerank:   SemanticMemory.recall(q, k=50), ENGRAM_RECALL_RERANK=1 —
              the EXACT production path (_rerank_stage2: mmarco-mMiniLMv2
              -L12-H384-v1, pool ENGRAM_RERANK_TOPN default 20, cosine
              kept as score). No bench-side reimplementation.

Decision rule (declared up front):
  rerank WIN  (p<0.05 on R@1 or R@10, delta>0) -> candidate default-ON.
  rerank HARM (p<0.05, delta<0)                -> stays opt-in OFF.
  otherwise                                     -> stays opt-in OFF
  (a default flip needs positive evidence, not absence of harm).

Safety: COPY of ~/.engram (never --live), CPU-forced, centering OFF
(refuted). Durable verdict: SIS-out-8-rerank-fair-verdict.txt.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# CPU-force BEFORE any engram import (8GB GPU OOMs with e5 + CE resident;
# "-1" is the reliable sentinel on this torch build, "" leaves CUDA visible).
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ.setdefault("HIPPO_RECALL_ENCODE_BUDGET_S", "60")
os.environ["ENGRAM_RECALL_CENTERING"] = "0"   # refuted -> baseline plain
os.environ["ENGRAM_RECALL_RERANK"] = "0"      # baseline arm OFF; flipped per-probe (default ON since 2026-06-10)

sys.path.insert(0, os.path.expanduser("~/Code/HippoAgent"))
sys.path.insert(0, os.path.expanduser("~/Code/HippoAgent/scripts"))
from bench_hybrid_fair import _ngram_leak  # noqa: E402
from bench_recall_self import _copy_live_db, _mcnemar  # noqa: E402

from engram.semantic import SemanticMemory  # noqa: E402

K_DEEP = 50
HERE = Path(__file__).resolve().parent
QUERIES_JSON = HERE / "bench_hybrid_fair_queries.json"
VERDICT_TXT = Path(os.path.expanduser(
    "~/Desktop/ProgettiAI/SIS-out-8-rerank-fair-verdict.txt"))


def _rank(ids: list[str], gold: str) -> int:
    return ids.index(gold) + 1 if gold in ids else 0


def main(strict: bool) -> int:
    t0 = time.time()
    if not QUERIES_JSON.exists():
        print(f"missing {QUERIES_JSON}")
        return 1
    queries = json.loads(QUERIES_JSON.read_text(encoding="utf-8"))
    dst = _copy_live_db()
    sm = SemanticMemory(db_path=dst)

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

    # Warm both arms BEFORE timing: encoder+corpus cache, then the CE load.
    sm.recall("warm up the encoder and the corpus cache please", k=5)
    os.environ["ENGRAM_RECALL_RERANK"] = "1"
    sm.recall("warm up the cross encoder reranker as well please", k=5)
    os.environ["ENGRAM_RECALL_RERANK"] = "0"

    b1 = b10 = r1 = r10 = 0
    b_mrr = r_mrr = 0.0
    pb1, pr1, pb10, pr10 = [], [], [], []
    t_base = t_rr = 0.0
    for i, (q, gold) in enumerate(probes, 1):
        os.environ["ENGRAM_RECALL_RERANK"] = "0"
        ta = time.time()
        rb = _rank([f.id for f, *_ in sm.recall(q, k=K_DEEP)], gold)
        t_base += time.time() - ta

        os.environ["ENGRAM_RECALL_RERANK"] = "1"
        ta = time.time()
        rr = _rank([f.id for f, *_ in sm.recall(q, k=K_DEEP)], gold)
        t_rr += time.time() - ta

        b1 += rb == 1; r1 += rr == 1                       # noqa: E702
        b10 += 1 <= rb <= 10; r10 += 1 <= rr <= 10          # noqa: E702
        b_mrr += (1.0 / rb) if 1 <= rb <= 10 else 0.0
        r_mrr += (1.0 / rr) if 1 <= rr <= 10 else 0.0
        pb1.append(1 if rb == 1 else 0); pr1.append(1 if rr == 1 else 0)  # noqa: E702
        pb10.append(1 if 1 <= rb <= 10 else 0); pr10.append(1 if 1 <= rr <= 10 else 0)  # noqa: E702
        if i % 20 == 0 or i == n:
            print(f"... {i}/{n} ({time.time()-t0:.0f}s)", flush=True)
    os.environ["ENGRAM_RECALL_RERANK"] = "0"

    def _pairs(a: list[int], b: list[int]) -> tuple[int, int]:
        x = sum(1 for o, w in zip(a, b, strict=True) if o == 1 and w == 0)
        y = sum(1 for o, w in zip(a, b, strict=True) if o == 0 and w == 1)
        return x, y

    d1, c1 = _pairs(pb1, pr1)
    s1, p1 = _mcnemar(d1, c1)
    d10, c10 = _pairs(pb10, pr10)
    s10, p10 = _mcnemar(d10, c10)
    dt = time.time() - t0

    win = (r1 > b1 and p1 < 0.05) or (r10 > b10 and p10 < 0.05)
    harm = (r1 < b1 and p1 < 0.05) or (r10 < b10 and p10 < 0.05)
    if win and not harm:
        verdict = "RERANK WIN (fair regime) -> candidato default-ON"
    elif harm:
        verdict = "RERANK HARMFUL (fair regime) -> resta opt-in OFF"
    else:
        verdict = "non significativo -> resta opt-in OFF"

    lines = [
        f"=== RERANK FAIR n={n} (parafrasi fluenti, paired recall vs recall+CE prod-path, k={K_DEEP}) ===",
        f"modello CE: produzione via flag (mmarco-mMiniLMv2-L12-H384-v1, pool TOPN={os.environ.get('ENGRAM_RERANK_TOPN', '20')})",
        f"anti-leak 4-gram: {leaks} query flaggate"
        + (" (ESCLUSE, --strict)" if strict else " (INCLUSE, dichiarate)"),
        f"R@1  base={b1/n:.3f} rerank={r1/n:.3f}  delta={r1/n-b1/n:+.3f}"
        f"   McNemar b={d1} c={c1} chi2={s1:.2f} p={p1:.5f}",
        f"R@10 base={b10/n:.3f} rerank={r10/n:.3f}  delta={r10/n-b10/n:+.3f}"
        f"   McNemar b={d10} c={c10} chi2={s10:.2f} p={p10:.5f}",
        f"MRR  base={b_mrr/n:.3f} rerank={r_mrr/n:.3f}  delta={(r_mrr-b_mrr)/n:+.3f}",
        f"latenza: base {t_base/n:.2f}s/probe, rerank {t_rr/n:.2f}s/probe (CPU)",
        f"tempo: {dt:.0f}s",
        f"VERDETTO-RERANK-FAIR: R@1 {b1/n:.3f}->{r1/n:.3f} R@10 {b10/n:.3f}->{r10/n:.3f}"
        f" p(R@1)={p1:.5f} p(R@10)={p10:.5f} -> {verdict}",
    ]
    out = "\n".join(lines)
    print(out, flush=True)
    VERDICT_TXT.write_text(out + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(strict="--strict" in sys.argv))
