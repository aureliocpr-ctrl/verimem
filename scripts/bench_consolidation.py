"""Cycle #144 (2026-05-18 sera) — real bench for auto-consolidation.

Clones the production semantic.db + episodes.db to a temp location
(production NEVER mutated) and runs auto_consolidate dry_run and apply,
reporting cluster + master + edge counts and durations.

Compares with the manual master node baseline created by the previous
session (6 verticali per-progetto + cluster minori ombrello).
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engram.consolidation import (
    auto_consolidate,
    detect_cluster_candidates,
)
from engram.memory import EpisodicMemory
from engram.semantic import SemanticMemory


def _clone_production(td: Path) -> tuple[Path, Path]:
    """Hot-copy production semantic + episodes DBs to tempdir."""
    src_sem = Path.home() / ".engram" / "semantic" / "semantic.db"
    src_ep = Path.home() / ".engram" / "episodes" / "episodes.db"
    dst_sem = td / "semantic.db"
    dst_ep = td / "episodes.db"
    # shutil.copy is fine here — production is local + WAL handles concurrent
    # reads. The clone is dead-end (temp), no risk of partial write to prod.
    shutil.copyfile(src_sem, dst_sem)
    shutil.copyfile(src_ep, dst_ep)
    return dst_sem, dst_ep


def main() -> int:
    with tempfile.TemporaryDirectory() as td_str:
        td = Path(td_str)
        sem_path, ep_path = _clone_production(td)
        print(f"[clone] sem={sem_path.stat().st_size//1024}KB "
              f"ep={ep_path.stat().st_size//1024}KB")
        sm = SemanticMemory(db_path=sem_path)
        mem = EpisodicMemory(db_path=ep_path)

        # [1] cluster detection, min_size 5 and 10
        for m in (5, 10):
            t0 = time.perf_counter()
            clusters = detect_cluster_candidates(sm, min_size=m, prefix_depth=2)
            ms = (time.perf_counter() - t0) * 1000.0
            print(f"[1] detect min_size={m}: {len(clusters)} clusters "
                  f"in {ms:.1f}ms — top5: "
                  f"{[(c['topic_prefix'], c['fact_count']) for c in clusters[:5]]}")

        # [2] dry_run on the clone — should not mutate
        with sm._connect() as conn:  # noqa: SLF001
            facts_before = int(conn.execute(
                "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL"
            ).fetchone()[0])
        with mem._connect() as conn:  # noqa: SLF001
            eps_before = int(conn.execute(
                "SELECT COUNT(*) FROM episodes"
            ).fetchone()[0])
            edges_before = int(conn.execute(
                "SELECT COUNT(*) FROM causal_edges"
            ).fetchone()[0])
        dry = auto_consolidate(sm, mem, min_size=5, dry_run=True)
        print(f"[2] dry_run: detected={dry['clusters_detected']} "
              f"proposed={dry['masters_proposed']} "
              f"persisted={dry['masters_persisted']} "
              f"edges={dry['edges_created']} "
              f"duration={dry['duration_ms']:.1f}ms")
        # invariant — no mutation
        with sm._connect() as conn:  # noqa: SLF001
            assert facts_before == int(conn.execute(
                "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL"
            ).fetchone()[0]), "dry_run must NOT change facts"

        # [3] apply on the clone — measure real impact
        t0 = time.perf_counter()
        apply = auto_consolidate(sm, mem, min_size=5, dry_run=False)
        apply_s = (time.perf_counter() - t0)
        with sm._connect() as conn:  # noqa: SLF001
            facts_after = int(conn.execute(
                "SELECT COUNT(*) FROM facts WHERE superseded_by IS NULL"
            ).fetchone()[0])
        with mem._connect() as conn:  # noqa: SLF001
            eps_after = int(conn.execute(
                "SELECT COUNT(*) FROM episodes"
            ).fetchone()[0])
            edges_after = int(conn.execute(
                "SELECT COUNT(*) FROM causal_edges"
            ).fetchone()[0])
        print(f"[3] apply: detected={apply['clusters_detected']} "
              f"proposed={apply['masters_proposed']} "
              f"persisted={apply['masters_persisted']} "
              f"edges={apply['edges_created']} "
              f"in {apply_s*1000:.0f}ms")
        print(f"    facts {facts_before}→{facts_after} (+{facts_after-facts_before})")
        print(f"    eps   {eps_before}→{eps_after} (+{eps_after-eps_before})")
        print(f"    edges {edges_before}→{edges_after} (+{edges_after-edges_before})")

        # [4] idempotency check — second apply must yield 0 new masters
        second = auto_consolidate(sm, mem, min_size=5, dry_run=False)
        print(f"[4] idempotency 2nd run: persisted={second['masters_persisted']} "
              f"(must be 0) ✓" if second["masters_persisted"] == 0
              else f"[4] idempotency 2nd run: persisted={second['masters_persisted']} ✗ FAIL")

    return 0


if __name__ == "__main__":
    sys.exit(main())
