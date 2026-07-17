"""Decisive validation: does the bge-reranker hold at n=300 HARD (paired McNemar)?
Same rigor that refuted centering. Baseline = plain recall (centering OFF, since
refuted). READ-ONLY (copy). Reuses the sister's bench_recall_self machinery.
"""
import os
import sys

# Force the ENTIRE stack (e5 embedder + bge cross-encoder) onto CPU. The 8GB GPU
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

from verimem.cross_encoder_rerank import rerank_candidates  # noqa: E402
from verimem.semantic import SemanticMemory  # noqa: E402

dst = _copy_live_db()
sm = SemanticMemory(db_path=dst)
facts = _sample_facts(dst)
probes = [(_make_query_hard(p, fid), fid) for fid, p in facts]
sm.recall("warm up the encoder and corpus cache", k=5)

from sentence_transformers import CrossEncoder  # noqa: E402

ce = CrossEncoder("BAAI/bge-reranker-v2-m3", trust_remote_code=True, max_length=512, device="cpu")


def scorer(pairs):
    return list(ce.predict(pairs))


b_r1h, r_r1h, b_r10h, r_r10h = [], [], [], []
b_mrr = r_mrr = 0.0
total = len(probes)
for i, (q, gold) in enumerate(probes, 1):
    ids = [f.id for f, *_ in sm.recall(q, k=50)]
    br = ids.index(gold) + 1 if gold in ids else 0
    rr = rerank_candidates(q, ids, semantic_db=dst, scorer=scorer, top_n=50)
    rids = [fid for fid, _ in rr]
    rk = rids.index(gold) + 1 if gold in rids else 0
    b_r1h.append(1 if br == 1 else 0)
    r_r1h.append(1 if rk == 1 else 0)
    b_r10h.append(1 if 1 <= br <= 10 else 0)
    r_r10h.append(1 if 1 <= rk <= 10 else 0)
    b_mrr += (1.0 / br) if 1 <= br <= 10 else 0.0
    r_mrr += (1.0 / rk) if 1 <= rk <= 10 else 0.0
    if i % 25 == 0 or i == total:
        print(f"... {i}/{total} probes", flush=True)

n = len(probes)
rate = lambda h: sum(h) / n  # noqa: E731
b1 = sum(1 for o, x in zip(b_r1h, r_r1h, strict=False) if o == 1 and x == 0)
c1 = sum(1 for o, x in zip(b_r1h, r_r1h, strict=False) if o == 0 and x == 1)
s1, p1 = _mcnemar(b1, c1)
verdict = "SIGNIFICATIVO" if p1 < 0.05 else "non significativo"
lines = [
    f"=== RERANKER n={n} HARD (recall vs recall+bge-reranker, paired) ===",
    f"R@1  base={rate(b_r1h):.3f} rerank={rate(r_r1h):.3f}  delta={rate(r_r1h)-rate(b_r1h):+.3f}",
    f"     McNemar b(base+/rr-)={b1} c(base-/rr+)={c1} chi2={s1:.2f} p={p1:.5f} -> {verdict}",
    f"R@10 base={rate(b_r10h):.3f} rerank={rate(r_r10h):.3f}  delta={rate(r_r10h)-rate(b_r10h):+.3f}",
    f"MRR  base={b_mrr/n:.3f} rerank={r_mrr/n:.3f}  delta={(r_mrr-b_mrr)/n:+.3f}",
]
out = "\n".join(lines)
print(out, flush=True)
# Durable verdict (survives any stdout-capture quirk of the background wrapper).
with open(os.path.expanduser("~/Desktop/ProgettiAI/SIS-out-5-rerank-verdict.txt"), "w", encoding="utf-8") as fh:
    fh.write(out + "\n")
