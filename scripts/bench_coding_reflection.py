"""Cycle #142 (2026-05-18 sera) — real benchmark for coding_reflection.

Aurelio direttiva: 'test e bench reali, non empirica totale'. This script
seeds N=300 distinct coding errors into a fresh EpisodicMemory and
measures three real latencies:

    1. extract_error_signature      — pure regex / hash, no I/O.
    2. capture_coding_error         — write path (Episode.store + embed).
    3. recall_similar_errors        — read path (SQL scan + cosine).

Output is a single multi-line report on stdout. The script does NOT
mutate the production ``~/.engram`` corpus — every run uses a fresh
SQLite under tempdir.

Run:
    python scripts/bench_coding_reflection.py [--n N] [--k K]

Calibrated to fit comfortably in CI: with N=300 the wall clock on a
warm machine is < 60 s (signature ~5 ms total, capture ~30 s, recall
~10 s for 100 queries). Disable embedding to skip the network-free but
torch-CPU model warmup (overrides via env: ``HIPPO_EMBED_MODEL=stub``).
"""
from __future__ import annotations

import argparse
import statistics
import sys
import tempfile
import time
from pathlib import Path

# Ensure repo root on sys.path so this can run standalone.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verimem.coding_reflection import (
    capture_coding_error,
    extract_error_signature,
    recall_similar_errors,
)
from verimem.memory import EpisodicMemory

_ERROR_TEMPLATES: list[tuple[str, str]] = [
    ("TypeError", "unsupported operand type(s) for +: 'str' and 'int'"),
    ("ValueError", "invalid literal for int() with base 10: 'foo'"),
    ("KeyError", "'missing_key'"),
    ("AttributeError", "'NoneType' object has no attribute 'split'"),
    ("IndexError", "list index out of range"),
    ("ZeroDivisionError", "division by zero"),
    ("RuntimeError", "dictionary changed size during iteration"),
    ("ImportError", "cannot import name 'foo' from 'bar'"),
    ("FileNotFoundError", "[Errno 2] No such file or directory: 'data.csv'"),
    ("PermissionError", "[Errno 13] Permission denied: '/etc/passwd'"),
]


def _make_traceback(err_type: str, msg: str, file: str, line: int) -> str:
    return (
        f"Traceback (most recent call last):\n"
        f'  File "{file}", line {line}, in some_func\n'
        f"    do_something()\n"
        f"{err_type}: {msg}\n"
    )


def _percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    xs = sorted(xs)
    idx = min(len(xs) - 1, int(len(xs) * p))
    return xs[idx]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=300,
                        help="number of seed errors (default 300)")
    parser.add_argument("--k", type=int, default=100,
                        help="number of recall queries (default 100)")
    args = parser.parse_args()
    n_seed = int(args.n)
    k_recalls = int(args.k)

    # -- Step 1: pure signature extraction (no DB, no embed) -----------
    sig_lat: list[float] = []
    for i in range(1000):
        err_type, msg = _ERROR_TEMPLATES[i % len(_ERROR_TEMPLATES)]
        tb = _make_traceback(err_type, msg, f"/src/m{i % 13}.py", 10 + i % 200)
        t0 = time.perf_counter()
        extract_error_signature(tb)
        sig_lat.append((time.perf_counter() - t0) * 1000.0)
    print(f"[1] extract_error_signature × {len(sig_lat)}: "
          f"mean={statistics.mean(sig_lat):.4f}ms "
          f"p50={_percentile(sig_lat, .5):.4f}ms "
          f"p95={_percentile(sig_lat, .95):.4f}ms "
          f"p99={_percentile(sig_lat, .99):.4f}ms "
          f"max={max(sig_lat):.4f}ms")

    # -- Step 2: capture path (write Episode + embed) ------------------
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "bench.db"
        mem = EpisodicMemory(db_path=db)

        cap_lat: list[float] = []
        seeded_signatures: list[str] = []
        for i in range(n_seed):
            err_type, msg = _ERROR_TEMPLATES[i % len(_ERROR_TEMPLATES)]
            tb = _make_traceback(
                err_type, msg, f"/src/mod{i % 17}.py", 10 + (i * 7) % 500,
            )
            t0 = time.perf_counter()
            out = capture_coding_error(
                mem,
                task_text=f"bench task #{i} testing {err_type}",
                traceback_text=tb,
                correction=f"fix #{i}: handle {err_type} before call",
            )
            cap_lat.append((time.perf_counter() - t0) * 1000.0)
            seeded_signatures.append(out["signature"])
        print(f"[2] capture_coding_error × {n_seed} (real Episode + embed): "
              f"mean={statistics.mean(cap_lat):.2f}ms "
              f"p50={_percentile(cap_lat, .5):.2f}ms "
              f"p95={_percentile(cap_lat, .95):.2f}ms "
              f"p99={_percentile(cap_lat, .99):.2f}ms "
              f"max={max(cap_lat):.2f}ms")

        # -- Step 3: recall path -------------------------------------
        rec_lat: list[float] = []
        hit_counts: list[int] = []
        for i in range(k_recalls):
            sig = seeded_signatures[i % len(seeded_signatures)]
            t0 = time.perf_counter()
            hits = recall_similar_errors(mem, signature=sig, k=5)
            rec_lat.append((time.perf_counter() - t0) * 1000.0)
            hit_counts.append(len(hits))
        print(f"[3] recall_similar_errors × {k_recalls} (k=5 over "
              f"{n_seed} failures): "
              f"mean={statistics.mean(rec_lat):.2f}ms "
              f"p50={_percentile(rec_lat, .5):.2f}ms "
              f"p95={_percentile(rec_lat, .95):.2f}ms "
              f"p99={_percentile(rec_lat, .99):.2f}ms "
              f"max={max(rec_lat):.2f}ms "
              f"mean_hits={statistics.mean(hit_counts):.1f}/5")

        # -- Step 4: signature-as-query recall recall@1 ---------------
        # For each seeded ep, query its own signature: does it come back
        # in top-5? This is a sanity check, not a precision claim — many
        # episodes share the same template so top-5 is loose.
        hits_top1_correct = 0
        for sig in seeded_signatures[:k_recalls]:
            hits = recall_similar_errors(mem, signature=sig, k=5)
            if hits:
                # "Correct" = top-1 has same first signature component
                # (the ErrorType, which is the most discriminative axis).
                top_type = hits[0]["signature"].split(":", 1)[0]
                want_type = sig.split(":", 1)[0]
                if top_type == want_type:
                    hits_top1_correct += 1
        recall_at_1 = hits_top1_correct / max(1, k_recalls)
        print(f"[4] recall@1 (top-1 errortype match): "
              f"{hits_top1_correct}/{k_recalls} = {recall_at_1:.1%}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
