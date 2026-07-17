"""Standalone perf harness: measures P50/P95/P99 of HippoAgent hot paths.

Usage:
    python -m tests.perf.bench

Prints a Markdown table to stdout. Designed to be run twice — before and
after performance changes — and the output diffed.

Replaces sentence-transformers with the same hashing-trick stub used by the
unit tests, so runs are deterministic and offline-safe.
"""
from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path

import numpy as np

from tests.perf.seed_data import seed_all, stub_vector


def _install_embedding_stub() -> None:
    """Replace `verimem.embedding._model` with a deterministic stub."""
    from verimem import embedding

    class _StubModel:
        def encode(self, text, normalize_embeddings=True, show_progress_bar=False,
                   convert_to_numpy=True):
            if isinstance(text, str):
                return stub_vector(text)
            return np.stack([stub_vector(t) for t in text]).astype(np.float32)

    stub = _StubModel()
    embedding._model.cache_clear()  # type: ignore[attr-defined]
    embedding._model = lambda: stub  # type: ignore[assignment]


def _percentiles(samples: list[float]) -> dict[str, float]:
    s = sorted(samples)
    n = len(s)
    return {
        "p50": s[n // 2] * 1000,
        "p95": s[min(n - 1, int(n * 0.95))] * 1000,
        "p99": s[min(n - 1, int(n * 0.99))] * 1000,
        "mean": (sum(s) / n) * 1000,
        "n": n,
    }


def time_calls(label: str, fn, n: int = 10) -> tuple[str, dict[str, float]]:
    samples = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - t0)
    p = _percentiles(samples)
    p["label"] = label
    return label, p


def run_benchmarks(base: Path, seed_only: bool = False) -> dict[str, dict]:
    paths = seed_all(base)
    if seed_only:
        return {}
    _install_embedding_stub()

    # Patch CONFIG to point at seeded paths.
    from verimem.config import CONFIG
    object.__setattr__(CONFIG, "skills_dir", paths["skills_dir"])
    object.__setattr__(CONFIG, "skills_db", paths["skills_db"])
    object.__setattr__(CONFIG, "episodes_db", paths["episodes_db"])
    object.__setattr__(CONFIG, "semantic_db", paths["semantic_db"])

    from verimem.memory import EpisodicMemory
    from verimem.repomap import build_repomap, scan_repo
    from verimem.semantic import SemanticMemory
    from verimem.skill import SkillLibrary

    skills = SkillLibrary(dir_path=paths["skills_dir"], db_path=paths["skills_db"])
    memory = EpisodicMemory(db_path=paths["episodes_db"])
    semantic = SemanticMemory(db_path=paths["semantic_db"])

    results: dict[str, dict] = {}

    # Skill operations -------------------------------------------------------
    def _find_dups():
        skills.find_duplicates()

    def _cluster():
        skills.cluster_by_embedding()

    def _retrieve():
        skills.retrieve("optimize python performance bottleneck", k=5)

    def _all_skills():
        skills.all()

    # Warm-up: prime caches that the rest of the bench relies on. Without
    # this the first sample of every loop dominates the P95.
    skills.all()
    skills.find_duplicates()
    skills.cluster_by_embedding()
    label, p = time_calls("skill.find_duplicates (1k skills)", _find_dups, n=20)
    results[label] = p
    label, p = time_calls("skill.cluster_by_embedding (1k skills)", _cluster, n=20)
    results[label] = p
    label, p = time_calls("skill.retrieve (1k skills, k=5)", _retrieve, n=20)
    results[label] = p
    label, p = time_calls("skill.all (1k skills)", _all_skills, n=10)
    results[label] = p

    # Memory operations ------------------------------------------------------
    def _recall():
        memory.recall("debug python error", k=5)

    def _recall_filtered():
        memory.recall("debug python error", k=5, outcome_filter="success")

    def _cluster_eps():
        memory.cluster_similar(eps_threshold=0.55)

    # Warm up the recall index before benchmarking (it would otherwise
    # leak the build cost into the first sample's timing).
    memory._ensure_recall_index()
    label, p = time_calls("memory.recall (5k episodes, k=5)", _recall, n=30)
    results[label] = p
    label, p = time_calls("memory.recall (filtered, k=5)", _recall_filtered, n=20)
    results[label] = p
    # Vectorised cluster_similar — fast enough to bench at n=5
    memory.cluster_similar(eps_threshold=0.55)  # warm
    label, p = time_calls("memory.cluster_similar (5k episodes)", _cluster_eps, n=5)
    results[label] = p

    # Semantic recall --------------------------------------------------------
    def _facts_recall():
        semantic.recall("python optimization", k=5)

    label, p = time_calls("semantic.recall (500 facts, k=5)", _facts_recall, n=20)
    results[label] = p

    # Repomap ----------------------------------------------------------------
    def _repomap_cold():
        build_repomap(paths["repo_root"])

    def _scan_only():
        scan_repo(paths["repo_root"])

    # Cold — explicit no-cache to measure the raw scan path.
    def _scan_no_cache():
        scan_repo(paths["repo_root"], use_cache=False)
    label, p = time_calls("repomap.scan_repo (1k files cold/no-cache)", _scan_no_cache, n=5)
    results[label] = p

    # Warm — populate cache once, then time repeated scans.
    cache_warm = base / "rmap_warm_cache.json"
    scan_repo(paths["repo_root"], cache_path=cache_warm, use_cache=True)
    def _scan_warm():
        scan_repo(paths["repo_root"], cache_path=cache_warm, use_cache=True)
    label, p = time_calls("repomap.scan_repo (1k files warm)", _scan_warm, n=10)
    results[label] = p

    label, p = time_calls("repomap.build_repomap (1k files cold)", _repomap_cold, n=5)
    results[label] = p

    # Embedding encode (cached vs uncached) ----------------------------------
    from verimem import embedding
    sample_texts = [f"task example {i}" for i in range(20)]
    def _encode_repeats():
        for t in sample_texts:
            embedding.encode(t)
        # Re-encode the same texts (where caching would help)
        for t in sample_texts:
            embedding.encode(t)

    label, p = time_calls("embedding.encode (20 texts × 2 reps)", _encode_repeats, n=10)
    results[label] = p

    return results


def render_table(results: dict[str, dict]) -> str:
    rows = ["| benchmark | n | mean (ms) | P50 (ms) | P95 (ms) | P99 (ms) |",
            "|-----------|---:|---:|---:|---:|---:|"]
    for label, p in results.items():
        rows.append(
            f"| {label} | {p['n']} | {p['mean']:.2f} | "
            f"{p['p50']:.2f} | {p['p95']:.2f} | {p['p99']:.2f} |"
        )
    return "\n".join(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=None, help="JSON output path")
    parser.add_argument("--keep-data", action="store_true",
                        help="Don't delete the temp data directory after run")
    parser.add_argument("--base-dir", default=None,
                        help="Use this dir for seed data (don't create temp)")
    args = parser.parse_args()

    if args.base_dir:
        base = Path(args.base_dir)
        base.mkdir(parents=True, exist_ok=True)
        results = run_benchmarks(base)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            results = run_benchmarks(base)
            if args.keep_data:
                # Copy out before TemporaryDirectory cleanup
                pass

    print(render_table(results))
    if args.out:
        Path(args.out).write_text(
            json.dumps(results, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
