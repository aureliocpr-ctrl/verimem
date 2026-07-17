"""Cycle 158 (2026-05-20) — cross-process empirical test for the
partial UNIQUE INDEX cycle 157 created.

ROADMAP §4 (`docs/ROADMAP-2026-05-19.md` line 50-59): cycle 156 design
doc §5.2 step 2 required a ``subprocess.Popen × 2`` test proving that
two HippoAgent processes racing on the same DB cannot both persist a
master fact for the same topic. The test was deferred from cycle 157
because Windows subprocess + db_path coordination needed setup care.

Cycle 157 already pins the single-connection invariant
(test_consolidation_unique_index.py:55). This file extends to a real
multi-process race using ``subprocess.Popen`` with ``sys.executable``
and synchronized via an on-disk barrier file (avoids assumptions about
multiprocessing semantics on Windows where spawn — not fork — is the
default).

Falsification design: without the partial UNIQUE INDEX
(``idx_facts_auto_master_unique``), two parallel workers calling
``auto_consolidate`` on a freshly-seeded cluster would each insert a
distinct master row and the post-condition (``COUNT(*) WHERE topic =
... AND superseded_by IS NULL`` == 1) would fail with a count of 2.
With the index live, the second writer either hits ``IntegrityError``
(handled gracefully — cycle 157 §6) or is silently REPLACED-into the
same row via ``INSERT OR REPLACE`` (cycle 157 §5.2 step 2 trade-off).
Either way the at-rest invariant holds.

Stability notes (Windows-specific gotchas, addressed):
  - ``subprocess.Popen`` uses spawn on Windows — children must import
    ``engram`` from scratch; we pass a ``-c`` inline script and rely
    on the parent's interpreter (``sys.executable``).
  - SQLite WAL mode opens fine cross-process; ``sm._connect()`` uses
    a 10 s busy timeout (semantic.py default).
  - We sync the two workers via a barrier file so both reach
    ``auto_consolidate`` within milliseconds of each other.
  - Test timeout 60 s — generous, but the workers should finish in <5 s.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests._real_model import requires_real_model
from verimem.semantic import Fact, SemanticMemory

# Subprocess workers spawn a fresh Python that loads the REAL model (no
# in-process stub); skip when it isn't cached (CI without a warmed HF cache).
pytestmark = requires_real_model

# How a worker subprocess gets invoked. Keep the script tiny so the
# parsing overhead is minimal — we don't want random imports to slow
# the worker spawn enough that one finishes before the other starts.
_WORKER_SCRIPT = r"""
import json, os, sys, time
from pathlib import Path
sem_path = Path(sys.argv[1])
ep_path = Path(sys.argv[2])
barrier = sys.argv[3]
out_path = sys.argv[4]

from verimem.semantic import SemanticMemory
from verimem.memory import EpisodicMemory
from verimem.consolidation import auto_consolidate

sm = SemanticMemory(db_path=sem_path)
mem = EpisodicMemory(db_path=ep_path)

# Spin until the parent flips the barrier file to 'GO'.
deadline = time.time() + 30
while time.time() < deadline:
    try:
        with open(barrier, 'r', encoding='utf-8') as f:
            if f.read().strip() == 'GO':
                break
    except FileNotFoundError:
        pass
    time.sleep(0.01)
else:
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({'error': 'barrier timeout'}, f)
    sys.exit(1)

stats = auto_consolidate(sm, mem, min_size=5, prefix_depth=2)
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(stats, f)
"""


def _seed_cluster(sem_path: Path, prefix: str, n: int = 7) -> None:
    """Insert ``n`` sub-facts under ``prefix/sub-K`` ready for an
    auto_consolidate pass to detect them as one cluster.

    NB: must use the parent's own ``SemanticMemory`` so the schema is
    materialised at v5 before the children attach.
    """
    sm = SemanticMemory(db_path=sem_path)
    for k in range(n):
        sm.store(Fact(
            proposition=f"sub fact #{k} for cluster {prefix}",
            topic=f"{prefix}/sub-{k}",
            confidence=0.7,
            source_episodes=[f"ep_seed_{k}"],
            status="model_claim",
        ))


def _spawn_worker(
    sem_path: Path, ep_path: Path, barrier: Path, out_path: Path,
) -> subprocess.Popen:
    """Spawn one worker subprocess with the inline _WORKER_SCRIPT."""
    return subprocess.Popen(
        [
            sys.executable, "-c", _WORKER_SCRIPT,
            str(sem_path), str(ep_path), str(barrier), str(out_path),
        ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


def test_two_processes_cannot_both_persist_master_for_same_topic(
    tmp_path: Path,
) -> None:
    """Cycle 158 ROADMAP §4 — the empirical cross-process race.

    Pre-fix (no partial UNIQUE INDEX, cycle 155 era only): the two
    workers each pre-load an empty ``consolidated_prefixes`` set,
    both pass the membership check, both reach ``_persist_master``,
    and both insert a master row for the same topic. Post-cycle-157
    (partial UNIQUE INDEX live): only one row stays live.

    We do NOT assert on ``masters_persisted`` from worker stats —
    the second-writer may report a successful local commit that gets
    silently REPLACED by the index (cycle 157 §5.2 trade-off), or
    may catch ``IntegrityError`` if the underlying ``sm.store`` path
    changes in future. The contract is at-rest: ≤1 live master per
    topic.
    """
    sem_path = tmp_path / "sem.db"
    ep_path = tmp_path / "ep.db"
    barrier = tmp_path / "barrier.txt"
    out_a = tmp_path / "out_a.json"
    out_b = tmp_path / "out_b.json"

    # Seed the cluster (7 sub-facts under one depth-2 prefix → 1 cluster).
    cluster_prefix = "cycle158/race"
    _seed_cluster(sem_path, cluster_prefix, n=7)

    # Spawn both workers. They will spin on the barrier file.
    proc_a = _spawn_worker(sem_path, ep_path, barrier, out_a)
    proc_b = _spawn_worker(sem_path, ep_path, barrier, out_b)

    # Tiny sleep so both processes are deep into their spin loops.
    time.sleep(0.5)

    # Flip the barrier — both workers fire at (approx) the same instant.
    barrier.write_text("GO", encoding="utf-8")

    # Collect results.
    try:
        proc_a.wait(timeout=60)
        proc_b.wait(timeout=60)
    except subprocess.TimeoutExpired:
        proc_a.kill()
        proc_b.kill()
        pytest.fail("Worker did not finish within 60 s")

    # Both should have exited 0 (graceful handling of any IntegrityError
    # is the consolidation.py contract; non-zero exit is a real bug).
    assert proc_a.returncode == 0, (
        f"Worker A failed: rc={proc_a.returncode}, "
        f"stderr={proc_a.stderr.read().decode(errors='replace')}"
    )
    assert proc_b.returncode == 0, (
        f"Worker B failed: rc={proc_b.returncode}, "
        f"stderr={proc_b.stderr.read().decode(errors='replace')}"
    )

    stats_a = json.loads(out_a.read_text(encoding="utf-8"))
    stats_b = json.loads(out_b.read_text(encoding="utf-8"))

    # Sanity: both workers detected the same cluster.
    assert stats_a.get("clusters_detected") == 1, stats_a
    assert stats_b.get("clusters_detected") == 1, stats_b

    # The at-rest invariant: ≤1 live master row for the cluster's topic.
    expected_topic = f"{cluster_prefix}/auto-MASTER"
    sm = SemanticMemory(db_path=sem_path)
    with sm._connect() as conn:  # noqa: SLF001
        live_masters = conn.execute(
            "SELECT COUNT(*) AS c FROM facts "
            "WHERE topic = ? AND superseded_by IS NULL "
            "  AND proposition LIKE 'AUTO-CLUSTER-MASTER%'",
            (expected_topic,),
        ).fetchone()
        n_live = int(live_masters["c"])

    assert n_live == 1, (
        f"Cross-process UNIQUE INDEX invariant broken: expected 1 live "
        f"master for topic {expected_topic!r}, got {n_live}. "
        f"Worker A stats: {stats_a}. Worker B stats: {stats_b}."
    )

    # At least one of the two workers should report a persisted master.
    # (Both can also report 1 each — the index either rejects or REPLACEs
    # the second insert; what matters is the at-rest invariant above.)
    total_workers_that_persisted = (
        int(stats_a.get("masters_persisted", 0)) +
        int(stats_b.get("masters_persisted", 0))
    )
    assert total_workers_that_persisted >= 1, (
        f"At least one worker must have persisted a master. "
        f"Got A={stats_a}, B={stats_b}."
    )


def test_two_processes_idempotent_when_master_already_exists(
    tmp_path: Path,
) -> None:
    """Regression guard: if a master is ALREADY live for a cluster,
    two parallel auto_consolidate calls must both no-op gracefully
    (no exception, no duplicate). This exercises the fast-path
    pre-load check in ``auto_consolidate`` line 365 + the slow-path
    fresh re-check at line 370 — both gated by the live UNIQUE INDEX.
    """
    sem_path = tmp_path / "sem.db"
    ep_path = tmp_path / "ep.db"
    barrier = tmp_path / "barrier.txt"
    out_a = tmp_path / "out_a.json"
    out_b = tmp_path / "out_b.json"

    cluster_prefix = "cycle158/preexisting"
    _seed_cluster(sem_path, cluster_prefix, n=7)

    # Pre-create the master (single-process, no race).
    from verimem.consolidation import auto_consolidate
    from verimem.memory import EpisodicMemory
    sm = SemanticMemory(db_path=sem_path)
    mem = EpisodicMemory(db_path=ep_path)
    initial = auto_consolidate(sm, mem, min_size=5, prefix_depth=2)
    assert initial["masters_persisted"] == 1

    # Now spawn two workers that should both detect "already consolidated".
    proc_a = _spawn_worker(sem_path, ep_path, barrier, out_a)
    proc_b = _spawn_worker(sem_path, ep_path, barrier, out_b)
    time.sleep(0.5)
    barrier.write_text("GO", encoding="utf-8")

    proc_a.wait(timeout=60)
    proc_b.wait(timeout=60)

    assert proc_a.returncode == 0
    assert proc_b.returncode == 0
    stats_a = json.loads(out_a.read_text(encoding="utf-8"))
    stats_b = json.loads(out_b.read_text(encoding="utf-8"))

    # Both must report 0 new masters (idempotency).
    assert stats_a.get("masters_persisted") == 0, stats_a
    assert stats_b.get("masters_persisted") == 0, stats_b

    # And the DB still has exactly 1 live master for the cluster.
    expected_topic = f"{cluster_prefix}/auto-MASTER"
    with sm._connect() as conn:  # noqa: SLF001
        n_live = int(conn.execute(
            "SELECT COUNT(*) FROM facts "
            "WHERE topic = ? AND superseded_by IS NULL "
            "  AND proposition LIKE 'AUTO-CLUSTER-MASTER%'",
            (expected_topic,),
        ).fetchone()[0])
    assert n_live == 1
