"""Build a SECOND VeriBench corpus from SQuAD v2 (offline, from the HF cache).

Reshapes SQuAD v2 into the same ``{knowledge, question}`` shape as the HaluEval
corpus — one answerable question per UNIQUE context paragraph — then cuts the
identical disjoint dev/heldout/unanswerable splits via
``external_readpath.make_samples`` under the ``squad_v2`` prefix. The unanswerable
probes are questions whose context is NEVER ingested (VeriBench's retrieval-
abstention notion), NOT SQuAD's reading-comprehension "impossible" label — the two
are different questions and only the former is what VeriBench measures.

    python -m benchmark.make_squad_corpus
"""
from __future__ import annotations

import json
import os
import random
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1")

from datasets import load_dataset  # noqa: E402

from benchmark.external_readpath import DATA_DIR, make_samples  # noqa: E402


def build(n_cap: int = 500, seed: int = 42) -> dict:
    ds = load_dataset("squad_v2", split="validation")
    seen: dict[str, str] = {}
    for ex in ds:
        # answerable = SQuAD marks it with a non-empty answer span
        if ex["answers"]["text"] and ex["context"] not in seen:
            seen[ex["context"]] = ex["question"]
    items = [{"knowledge": c, "question": q} for c, q in seen.items()]
    random.Random(seed).shuffle(items)
    items = items[:n_cap]

    raw = DATA_DIR / ".cache" / "squad_v2_raw.jsonl"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in items),
                   encoding="utf-8")
    info = make_samples(raw, DATA_DIR, prefix="squad_v2", seed=seed)
    info["unique_contexts"] = len(seen)
    return info


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
