"""Cycle 139.SCALA — vertical stress lab.

Aurelio sfida 2026-05-18 'fammi vedere di cosa sei capace':
prendi il corpus production (1207 facts), replica 10x con id-suffix
per simulare scala 12k+, e misura:

  - cold cache build time (cycle 135 invariant)
  - hot recall latency p50/p95/p99 (cycle 135 cache claim)
  - mark_orphaned + cache_version bump latency (cycle 137 invariant)
  - anti-confab gate fast pass latency (cycle 138 invariant)
  - L2 scan_orphaned_facts on 12k corpus (cycle 132 invariant)

Read-only against the live corpus — replication happens on a temp
copy under ~/.engram_lab_scale.db. No mutation of the production
~/.verimem.
"""
from __future__ import annotations

import shutil
import sqlite3
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from verimem.anti_confab_gate import run_validation_gate
from verimem.anti_confabulation import scan_orphaned_facts
from verimem.semantic import SemanticMemory


class _AgentShim:
    def __init__(self, sm: SemanticMemory) -> None:
        self.semantic = sm


def _clone_corpus() -> Path:
    src = Path.home() / ".engram" / "semantic" / "semantic.db"
    if not src.exists():
        src = Path.home() / ".engram" / "semantic.db"
    dst = Path.home() / ".engram_lab_scale.db"
    if dst.exists():
        dst.unlink()
    shutil.copyfile(src, dst)
    return dst


def _replicate_10x(db: Path) -> int:
    """Duplicate every row 9 more times with id-suffix so the temp corpus
    becomes ~10x the original. Returns total post-replication."""
    with sqlite3.connect(str(db)) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        orig = conn.execute(
            "SELECT * FROM facts WHERE superseded_by IS NULL"
        ).fetchall()
        cols = [d[0] for d in conn.execute("SELECT * FROM facts LIMIT 1").description]
        id_idx = cols.index("id")
        created_at_idx = cols.index("created_at") if "created_at" in cols else None
        placeholders = ",".join("?" for _ in cols)
        sql = f"INSERT INTO facts ({','.join(cols)}) VALUES ({placeholders})"
        clones = 0
        for fact_row in orig:
            for k in range(1, 10):
                row = list(fact_row)
                row[id_idx] = f"{row[id_idx]}-clone{k}"
                if created_at_idx is not None and row[created_at_idx] is not None:
                    # Stagger so duplicates do not collapse to a single ts.
                    row[created_at_idx] = float(row[created_at_idx]) - k * 1e-6
                try:
                    conn.execute(sql, tuple(row))
                    clones += 1
                except sqlite3.IntegrityError:
                    continue
        conn.commit()
        n = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
    return int(n)


def _percentile(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    if not xs:
        return 0.0
    idx = min(len(xs) - 1, int(len(xs) * p))
    return xs[idx]


def main() -> int:
    db = _clone_corpus()
    print(f"Cloned corpus to {db}")
    try:
        n_total = _replicate_10x(db)
        print(f"Replicated 10x — total facts on disk: {n_total}")

        sm = SemanticMemory(db_path=db)
        agent = _AgentShim(sm)

        # ---- 1. cold cache build ----
        t0 = time.perf_counter()
        facts, matrix = sm._get_corpus_cache()  # noqa: SLF001 — internal
        cold_ms = (time.perf_counter() - t0) * 1000.0
        print()
        print(f"[1] cold cache build: {cold_ms:.1f}ms over {len(facts)} facts "
              f"(matrix {matrix.shape})")

        # ---- 2. hot recall p50/p95/p99 ----
        queries = [
            "Cycle anti-confab gate write",
            "memoria semantic recall cache O(1)",
            "Aurelio preferenze brevità italiano",
            "Tonegawa Nobel Prize 1987",
            "Anthropic Skills 2025",
            "SHIPPED commit reference",
        ] * 10
        lat: list[float] = []
        for q in queries:
            t0 = time.perf_counter()
            _ = sm.recall(q, k=5)
            lat.append((time.perf_counter() - t0) * 1000.0)
        print(f"[2] hot recall N={len(lat)}: p50={_percentile(lat,.5):.2f}ms "
              f"p95={_percentile(lat,.95):.2f}ms p99={_percentile(lat,.99):.2f}ms "
              f"mean={statistics.mean(lat):.2f}ms max={max(lat):.2f}ms")

        # ---- 3. anti-confab gate fast pass on full 12k ----
        with sm._connect() as conn:  # noqa: SLF001
            rows = conn.execute(
                "SELECT proposition, verified_by, topic FROM facts "
                "WHERE superseded_by IS NULL"
            ).fetchall()
        gate_lat: list[float] = []
        action_counts = Counter()
        import json as _json
        t_total = time.perf_counter()
        for r in rows:
            vb: list[str] = []
            if r[1]:
                try:
                    parsed = _json.loads(r[1])
                    if isinstance(parsed, list):
                        vb = [str(x) for x in parsed]
                except Exception:
                    pass
            t0 = time.perf_counter()
            g = run_validation_gate(
                proposition=r[0] or "",
                verified_by=vb,
                topic=r[2],
                agent=agent,
                validate="fast",
                gate_mode="downgrade",
            )
            gate_lat.append((time.perf_counter() - t0) * 1000.0)
            action_counts[g.action] += 1
        total_s = time.perf_counter() - t_total
        print(f"[3] gate fast N={len(rows)}: "
              f"total {total_s:.2f}s ({total_s/len(rows)*1000:.3f}ms/fact) "
              f"p50={_percentile(gate_lat,.5):.3f}ms "
              f"p99={_percentile(gate_lat,.99):.3f}ms — "
              f"actions={dict(action_counts)}")

        # ---- 4. L2 scan_orphaned_facts on 12k ----
        with sm._connect() as conn:  # noqa: SLF001
            corpus_rows = conn.execute("SELECT * FROM facts").fetchall()
        corpus_facts = [sm._row(rr) for rr in corpus_rows]  # noqa: SLF001
        t0 = time.perf_counter()
        report = scan_orphaned_facts(corpus_facts)
        scan_ms = (time.perf_counter() - t0) * 1000.0
        per_cat = {k: len(v) for k, v in report.items()}
        print(f"[4] L2 scan_orphaned_facts: {scan_ms:.1f}ms over "
              f"{len(corpus_facts)} facts — per category {per_cat}")

        # ---- 5. mark_orphaned + cache invalidation latency ----
        # Find a real candidate to flip and back-out (idempotent test).
        ship_ids = [fid for fid, _ in (report.get("shipped") or [])][:1]
        if ship_ids:
            fid = ship_ids[0]
            t0 = time.perf_counter()
            sm.mark_orphaned(fid, reason="lab_scale stress probe")
            mark_ms = (time.perf_counter() - t0) * 1000.0
            # Cache should be invalidated; first recall after rebuilds.
            t0 = time.perf_counter()
            sm._get_corpus_cache()  # noqa: SLF001
            rebuild_ms = (time.perf_counter() - t0) * 1000.0
            print(f"[5] mark_orphaned({fid}): {mark_ms:.2f}ms + cache rebuild "
                  f"{rebuild_ms:.1f}ms (cycle 137 invariant: cache_version bumped)")
        else:
            print("[5] mark_orphaned: skipped (no shipped candidates in corpus)")
    finally:
        try:
            db.unlink()
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
