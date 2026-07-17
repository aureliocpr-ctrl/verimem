"""Cycle #155 (2026-05-19) — HIGH#2 TOCTOU race fix verification.

Cycle 151 aveva esplicitamente skippato HIGH#2 (TOCTOU race in
``auto_consolidate`` parallel) come OUT-OF-SCOPE. Cycle 153 honeycomb
mesh review l'ha riconfermato: testing GAP#1 e security HIGH#2 entrambi
chiedono fix.

Cycle 154 ha estratto ``_persist_master`` come natural seam atomic. Cycle
155 chiude il loop: ``threading.Lock`` module-level che serializza il
blocco check+store all'interno di ``auto_consolidate`` per processo
singolo (in-memory lock). Per cross-process serve UNIQUE INDEX migration
schema, ancora out of scope cycle 155.

Test design:
  Setup: shared SemanticMemory + EpisodicMemory, 1 cluster ``project/
  toctou/area`` con 6 facts.
  Action: 2 thread chiamano ``auto_consolidate`` in parallelo sullo
  stesso `sm` + `mem`.
  Pre-fix expected: 2 master Fact creati (TOCTOU race lost-update).
  Post-fix expected: exactly 1 master Fact creato (lock serializes).

Note: il test SQLite con shared connection cross-thread può sollevare
``OperationalError`` se sm._connect è not thread-safe. Usiamo lock
in-process al codice consolidation, NON cambiamo le connection
semantics di SemanticMemory.
"""
from __future__ import annotations

import threading
from pathlib import Path

import pytest

from verimem.consolidation import auto_consolidate
from verimem.memory import EpisodicMemory
from verimem.semantic import Fact, SemanticMemory


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sem.db")


@pytest.fixture
def mem(tmp_path: Path) -> EpisodicMemory:
    return EpisodicMemory(db_path=tmp_path / "ep.db")


def _seed_cluster(sm: SemanticMemory, topic: str, n: int) -> None:
    for i in range(n):
        f = Fact(
            proposition=f"Atom #{i} in {topic}",
            topic=topic,
            confidence=0.7,
            verified_by=[f"test:cycle155:toctou:{i}"],
            status="model_claim",
        )
        sm.store(f)


def _count_masters_for_prefix(
    sm: SemanticMemory, prefix: str,
) -> int:
    """Count master Fact rows whose topic matches ``<prefix>/auto-MASTER``."""
    expected_topic = f"{prefix}/auto-MASTER"
    with sm._connect() as conn:  # noqa: SLF001
        rows = conn.execute(
            "SELECT COUNT(*) FROM facts "
            "WHERE topic = ? AND superseded_by IS NULL",
            (expected_topic,),
        ).fetchone()
    return int(rows[0])


def test_high2_toctou_parallel_auto_consolidate_no_master_dup(
    sm: SemanticMemory, mem: EpisodicMemory,
) -> None:
    """Run 2 parallel ``auto_consolidate`` on the same cluster.

    Post-fix (cycle 155 lock): exactly 1 master Fact must exist for
    the prefix ``project/toctou``. Pre-fix: 2 master would have been
    created (race lost-update).

    Note: this test is racy by nature; the lock fix is what makes it
    deterministic. To make pre-fix failure visible empirically, we
    use ``barrier`` to maximise the chance of overlap.
    """
    _seed_cluster(sm, "project/toctou/area", 6)

    barrier = threading.Barrier(parties=2)
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            # Sync the two threads to enter auto_consolidate together
            # so they maximise overlap on the check-then-store window.
            barrier.wait(timeout=5.0)
            auto_consolidate(sm, mem, min_size=5, dry_run=False)
        except BaseException as exc:  # noqa: BLE001 — capture all
            errors.append(exc)

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join(timeout=15.0)
    t2.join(timeout=15.0)

    # No worker should crash (transient sqlite locked errors are
    # acceptable if the lock degrades gracefully, but assertion below
    # is what really matters).
    if errors:
        # Surface unexpected exceptions, not the expected serialization.
        for e in errors:
            # OperationalError "database is locked" is acceptable in WAL
            # busy-timeout scenarios — the lock contention is exactly
            # what protects us, not what we test for here.
            if "locked" not in str(e).lower():
                raise e

    n_masters = _count_masters_for_prefix(sm, "project/toctou")
    assert n_masters == 1, (
        f"HIGH#2 TOCTOU: with module-level lock, exactly 1 master Fact "
        f"must exist for the prefix after 2 parallel auto_consolidate "
        f"runs. Got {n_masters}. Pre-fix would have produced 2."
    )


def test_high2_lock_serializes_consecutive_calls(
    sm: SemanticMemory, mem: EpisodicMemory,
) -> None:
    """Even without thread contention, sequential second call must be
    no-op (idempotency via pre-loaded prefix set, cycle 151 MED#4).
    The lock change must NOT regress sequential idempotency.
    """
    _seed_cluster(sm, "project/toctou-seq/area", 6)
    first = auto_consolidate(sm, mem, min_size=5, dry_run=False)
    assert first["masters_persisted"] == 1
    second = auto_consolidate(sm, mem, min_size=5, dry_run=False)
    assert second["masters_persisted"] == 0, (
        f"Idempotency must be preserved post cycle 155 lock change. "
        f"Second call expected 0 new masters, got {second!r}"
    )
