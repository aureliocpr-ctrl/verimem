"""Bench: DG cabling into EpisodicMemory — 3 dimensions.

Dichiarate prima di misurare:

  1. PAIRWISE TWIN SEPARATION (mean over 50 random twin pairs):
     With near-identical embeddings (cos_sum ≈ 0.995 by construction),
     the DG encoding amplifies the gap. Mean amplification (1 - cos_dg)
     / (1 - cos_sum) over 50 random twin pairs at the configured
     `dg_k_sparse` / `dg_d_expand` / `dg_seed` should be ≥ 2.0×.
     This is the headline pattern-separation measurement.

  2. RECALL PRESERVATION on a diverse corpus:
     With 10 episodes covering distinct domains (no twins) and 10
     paraphrase queries, DG-recall must keep the right episode in
     top-3 at a rate ≥ 0.80. The DG path must not BREAK retrieval for
     non-pathological corpora.

  3. STORAGE COST (sparse on-disk format):
     The new `dg_embedding` BLOB column should add ≤ 2× the bytes of
     `summary_embedding`. Default sparse format = 2 + 6k bytes = 482
     bytes for k=80 vs 1.5 KB summary → well under budget. Target:
     ≤ 2.0×.
"""
from __future__ import annotations

import gc
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engram.config import CONFIG
from engram.dentate_gyrus import dg_encode
from engram.episode import Episode, Trace
from engram.memory import EpisodicMemory, _global_dg_projection


def _ep(*, ep_id: str, text: str) -> Episode:
    return Episode(
        id=ep_id, task_id=text[:30], task_text=text,
        outcome="success", final_answer="ok",
        traces=[Trace(
            step=1, thought="x", action="x", action_input="{}", observation="x",
        )],
    )


def main() -> int:
    # ---- Dimension 1: pairwise twin separation -----------------------
    # Direct measurement of the DG primitive under the cabling-time
    # CONFIG values. Independent of recall pipeline / sentence
    # transformer noise.
    rng = np.random.default_rng(seed=20260508)
    W = _global_dg_projection()
    k = CONFIG.dg_k_sparse
    n_pairs = 50
    amps = []
    cos_sums = []
    cos_dgs = []
    for _ in range(n_pairs):
        base = rng.standard_normal(CONFIG.embedding_dim).astype(np.float32)
        base = base / np.linalg.norm(base)
        perturb = rng.standard_normal(CONFIG.embedding_dim).astype(np.float32) * 0.005
        twin = base + perturb
        twin = twin / np.linalg.norm(twin)
        cos_sum = float(np.dot(base, twin))
        dg_a = dg_encode(base, W, k_sparse=k)
        dg_b = dg_encode(twin, W, k_sparse=k)
        cos_dg = float(np.dot(dg_a, dg_b))
        cos_sums.append(cos_sum)
        cos_dgs.append(cos_dg)
        amps.append((1.0 - cos_dg) / max(1e-9, 1.0 - cos_sum))
    mean_amp = float(np.mean(amps))
    mean_cos_sum = float(np.mean(cos_sums))
    mean_cos_dg = float(np.mean(cos_dgs))

    # On Windows, SQLite WAL files retain a transient lock after close;
    # use mkdtemp + manual rmtree(ignore_errors=True) so the bench
    # doesn't crash on the cleanup path.
    tmp = Path(tempfile.mkdtemp(prefix="bench_dg_"))
    tmp2 = Path(tempfile.mkdtemp(prefix="bench_dg_"))
    try:
        mem = EpisodicMemory(db_path=tmp / "ep.db")
        # Just one episode to populate dg_embedding for storage measurement.
        mem.store(_ep(ep_id="storage-probe", text="storage measurement probe"))

        # ---- Dimension 2: recall preservation ----------------------
        diverse = [
            ("compute factorial of 10", "fact-10",
             "calculate factorial of n"),
            ("send email via smtp", "email",
             "deliver mail through smtp protocol"),
            ("parse json config file", "json-cfg",
             "read configuration from json"),
            ("connect to postgres database", "pg-conn",
             "establish connection with postgresql server"),
            ("render html template", "html-tpl",
             "generate web page from template engine"),
            ("upload file to s3 bucket", "s3-upload",
             "push artifact to amazon storage"),
            ("compress directory with tar", "tar-dir",
             "archive a folder using tar"),
            ("validate yaml schema", "yaml-val",
             "check yaml file conforms to schema"),
            ("rotate ssh key", "ssh-rot",
             "regenerate the ssh authentication key"),
            ("deploy lambda function", "lambda-dep",
             "publish a serverless function to aws"),
        ]

        mem2 = EpisodicMemory(db_path=tmp2 / "ep.db")
        for text, eid, _ in diverse:
            mem2.store(_ep(ep_id=eid, text=text))

        # Top-3 hit rate: lenient enough that legitimate paraphrase
        # matches don't fail just because k-WTA reshuffled mid-cosine
        # episodes within the top-3 window.
        base_hit = 0
        dg_hit = 0
        for _, eid, q in diverse:
            b = mem2.recall(q, k=3, use_dg=False, track_access=False)
            d = mem2.recall(q, k=3, use_dg=True, track_access=False)
            if eid in {ep.id for ep, _ in b}:
                base_hit += 1
            if eid in {ep.id for ep, _ in d}:
                dg_hit += 1
        base_rate = base_hit / len(diverse)
        dg_rate = dg_hit / len(diverse)

        # ---- Dimension 3: storage cost -----------------------------
        with mem._connect() as c:  # noqa: SLF001
            row = c.execute(
                "SELECT length(summary_embedding), length(dg_embedding) "
                "FROM episodes LIMIT 1"
            ).fetchone()
        summary_bytes = int(row[0])
        dg_bytes = int(row[1])
        storage_ratio = dg_bytes / summary_bytes
    finally:
        # Drop the EpisodicMemory references so SQLite/WAL fully closes
        # before tempdir cleanup on Windows.
        mem = None  # type: ignore[assignment]  # noqa: F841
        mem2 = None  # type: ignore[assignment]  # noqa: F841
        gc.collect()
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(tmp2, ignore_errors=True)

    # ---- Report -----------------------------------------------------
    print()
    print("Bench: DG cabling into EpisodicMemory")
    print()
    print(f"  pairwise separation ({n_pairs} random twin pairs, "
          f"k={k}, d_expand={CONFIG.dg_d_expand}):")
    print(f"    mean cos_sum:       {mean_cos_sum:.4f}")
    print(f"    mean cos_dg:        {mean_cos_dg:.4f}")
    print(f"    mean amplification: {mean_amp:.2f}× "
          f"(target ≥ 2.0×)")
    print()
    print("  recall preservation (10 paraphrase queries, diverse corpus, top-3):")
    print(f"    baseline hit-rate:  {base_rate:.2f} ({base_hit}/{len(diverse)})")
    print(f"    DG hit-rate:        {dg_rate:.2f} ({dg_hit}/{len(diverse)})")
    print("    target:             dg ≥ 0.80")
    print()
    print("  storage cost per episode:")
    print(f"    summary_embedding:  {summary_bytes} B")
    print(f"    dg_embedding:       {dg_bytes} B "
          f"(k_sparse={CONFIG.dg_k_sparse}, d_expand={CONFIG.dg_d_expand})")
    print(f"    ratio dg/summary:   {storage_ratio:.3f}× "
          f"(target ≤ 2.0×)")
    print()
    print("Verdict (3 dimensions, declared up front):")
    d1 = mean_amp >= 2.0
    d2 = dg_rate >= 0.80
    d3 = storage_ratio <= 2.0
    print(f"  pairwise amp ≥ 2.0×:      {'+' if d1 else '!'}")
    print(f"  recall hit ≥ 0.80:        {'+' if d2 else '!'}")
    print(f"  storage ≤ 2× summary:     {'+' if d3 else '!'}")
    return 0 if (d1 and d2 and d3) else 1


if __name__ == "__main__":
    sys.exit(main())
