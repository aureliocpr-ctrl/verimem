"""Decisive validation, FAST variant: does a small deployable cross-encoder
(mmarco-mMiniLMv2-L12-H384-v1, ~5x smaller than bge-reranker-v2-m3) hold at
n=300 HARD (paired McNemar)? The bge run was ~30s/probe on CPU (~2.5h total,
never finished). Here: smaller model + rerank pool 20 (not 50) -> deployable.

Same rigor that refuted centering. Baseline = plain recall k=50 (centering OFF,
since refuted) — IDENTICAL to bench_rerank_n300.py, so numbers stay comparable.
READ-ONLY (copy). Reuses the sister's bench_recall_self machinery.

Delta vs bench_rerank_n300.py (declared, nothing else changed):
  1. CE model: cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 (IT-capable, ~117M).
  2. Rerank pool = top-20 of recall (ids[:20], top_n=20). NB: rerank_candidates
     scores ALL pairs it receives — top_n only caps the RETURNED list — so the
     real speedup requires slicing the candidate list, not just passing top_n.
  3. Wall-clock + s/probe measured (a "fast" claim needs a number).
  4. Durable verdict file: SIS-out-6-rerank-fast-verdict.txt (don't clobber
     the bge slot SIS-out-5).
"""
import os
import sys
import time

# Force the ENTIRE stack (e5 embedder + cross-encoder) onto CPU. The 8GB GPU
# OOMs when recall's e5 model and the reranker both grab CUDA (prior run: EXIT=1
# cudaErrorMemoryAllocation). Hiding the device process-wide is the robust fix.
# NB: "-1" (not "") is the reliable sentinel -- empty string leaves CUDA visible
# on this torch/CUDA build (verified torch.cuda.is_available() still True with "").
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ.setdefault("HIPPO_RECALL_ENCODE_BUDGET_S", "60")
os.environ["ENGRAM_RECALL_CENTERING"] = "0"  # centering refuted -> baseline = plain recall
os.environ["ENGRAM_RECALL_RERANK"] = "0"  # CE default-ON since 2026-06-10 — baseline arm must stay bi-encoder
sys.path.insert(0, os.path.expanduser("~/Code/HippoAgent/scripts"))
from bench_recall_self import (  # noqa: E402
    _copy_live_db,
    _make_query_hard,
    _mcnemar,
    _sample_facts,
)

from engram.cross_encoder_rerank import rerank_candidates  # noqa: E402
from engram.semantic import SemanticMemory  # noqa: E402

RERANK_POOL = 20  # CE scores the top-20 first-stage candidates (was 50 with bge)

dst = _copy_live_db()
sm = SemanticMemory(db_path=dst)
facts = _sample_facts(dst)
probes = [(_make_query_hard(p, fid), fid) for fid, p in facts]
sm.recall("warm up the encoder and corpus cache", k=5)

from sentence_transformers import CrossEncoder  # noqa: E402

ce = CrossEncoder("cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
                  trust_remote_code=True, max_length=512, device="cpu")


def scorer(pairs):
    return list(ce.predict(pairs))


b_r1h, r_r1h, b_r10h, r_r10h = [], [], [], []
b_mrr = r_mrr = 0.0
total = len(probes)
t0 = time.time()
for i, (q, gold) in enumerate(probes, 1):
    ids = [f.id for f, *_ in sm.recall(q, k=50)]
    br = ids.index(gold) + 1 if gold in ids else 0
    rr = rerank_candidates(q, ids[:RERANK_POOL], semantic_db=dst,
                           scorer=scorer, top_n=RERANK_POOL)
    rids = [fid for fid, _ in rr]
    rk = rids.index(gold) + 1 if gold in rids else 0
    b_r1h.append(1 if br == 1 else 0)
    r_r1h.append(1 if rk == 1 else 0)
    b_r10h.append(1 if 1 <= br <= 10 else 0)
    r_r10h.append(1 if 1 <= rk <= 10 else 0)
    b_mrr += (1.0 / br) if 1 <= br <= 10 else 0.0
    r_mrr += (1.0 / rk) if 1 <= rk <= 10 else 0.0
    if i % 25 == 0 or i == total:
        el = time.time() - t0
        print(f"... {i}/{total} probes  ({el:.0f}s, {el/i:.2f}s/probe)", flush=True)

dt = time.time() - t0
n = len(probes)
rate = lambda h: sum(h) / n  # noqa: E731
b1 = sum(1 for o, x in zip(b_r1h, r_r1h, strict=False) if o == 1 and x == 0)
c1 = sum(1 for o, x in zip(b_r1h, r_r1h, strict=False) if o == 0 and x == 1)
s1, p1 = _mcnemar(b1, c1)
verdict = "SIGNIFICATIVO" if p1 < 0.05 else "non significativo"
lines = [
    f"=== RERANKER FAST n={n} HARD (recall k=50 vs recall+mmarco-mMiniLMv2-L12 pool=20, paired) ===",
    f"R@1  base={rate(b_r1h):.3f} rerank={rate(r_r1h):.3f}  delta={rate(r_r1h)-rate(b_r1h):+.3f}",
    f"     McNemar b(base+/rr-)={b1} c(base-/rr+)={c1} chi2={s1:.2f} p={p1:.5f} -> {verdict}",
    f"R@10 base={rate(b_r10h):.3f} rerank={rate(r_r10h):.3f}  delta={rate(r_r10h)-rate(b_r10h):+.3f}",
    f"MRR  base={b_mrr/n:.3f} rerank={r_mrr/n:.3f}  delta={(r_mrr-b_mrr)/n:+.3f}",
    f"tempo: {dt:.0f}s totali, {dt/n:.2f}s/probe (recall+CE, CPU)",
]
out = "\n".join(lines)
print(out, flush=True)
# Durable verdict (survives any stdout-capture quirk of the background wrapper).
with open(os.path.expanduser("~/Desktop/ProgettiAI/SIS-out-6-rerank-fast-verdict.txt"), "w", encoding="utf-8") as fh:
    fh.write(out + "\n")
