"""G3 crash-injection (RELEASE_GATE): a REAL child process killed mid-write.

What this proves (and its declared limit): TerminateProcess/SIGKILL at an
arbitrary point of a write burst — the "agent process dies / OOM-killed"
failure — must lose ZERO committed writes, leave the DB uncorrupted
(integrity_check ok), and the store must reopen and accept new writes.
A true OS-crash/power-loss cannot be simulated in userspace: with
synchronous=NORMAL a committed-but-uncheckpointed write may be lost there
BY DESIGN; `ENGRAM_SQLITE_SYNCHRONOUS=FULL` closes that window with
per-commit fsync (see engram/_sqlite_pragma.py). That residual window is
documented, not tested here.

The worker acks each fact id on stdout ONLY AFTER store() returns (= the
per-operation connection committed); every acked id must be present after
the kill.
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from engram.semantic import Fact, SemanticMemory

_WORKER = r"""
import sys, time
from pathlib import Path
from engram.semantic import Fact, SemanticMemory

db = Path(sys.argv[1])
mem = SemanticMemory(db_path=db)
for i in range(500):
    f = Fact(proposition=f"crash burst fact {i}", topic="t/crash")
    mem.store(f, embed="defer")
    print(i, flush=True)  # ack AFTER store() returned (committed)
    time.sleep(0.005)  # pace the burst so the parent's kill lands MID-burst
"""


def _run_worker_and_kill(db: Path, kill_after_acks: int) -> list[int]:
    proc = subprocess.Popen(
        [sys.executable, "-c", _WORKER, str(db)],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        cwd=str(Path(__file__).resolve().parents[1]))
    acked: list[int] = []
    try:
        for line in proc.stdout:  # type: ignore[union-attr]
            acked.append(int(line.strip()))
            if len(acked) >= kill_after_acks:
                proc.kill()  # TerminateProcess mid-burst
                break
    finally:
        proc.stdout.close()  # type: ignore[union-attr]
        proc.wait(timeout=30)
    return acked


def test_kill_mid_burst_loses_no_committed_write(tmp_path) -> None:
    db = tmp_path / "semantic" / "semantic.db"
    db.parent.mkdir(parents=True)
    SemanticMemory(db_path=db)  # create schema before the worker starts

    acked = _run_worker_and_kill(db, kill_after_acks=25)
    assert len(acked) >= 25, "worker died before reaching the kill point"

    conn = sqlite3.connect(db)
    try:
        (integ,) = conn.execute("PRAGMA integrity_check").fetchone()
        assert integ == "ok"
        rows = conn.execute(
            "SELECT proposition FROM facts WHERE topic='t/crash'").fetchall()
    finally:
        conn.close()
    stored = {r[0] for r in rows}
    # the kill must have landed MID-burst — a worker that finished all 500
    # before the kill would make this a no-op test, not an injection
    assert len(stored) < 500, "worker completed the burst; nothing was injected"
    missing = [i for i in acked
               if f"crash burst fact {i}" not in stored]
    assert not missing, f"acked-but-lost after kill: {missing}"


def test_store_reopens_and_accepts_writes_after_kill(tmp_path) -> None:
    db = tmp_path / "semantic" / "semantic.db"
    db.parent.mkdir(parents=True)
    SemanticMemory(db_path=db)
    _run_worker_and_kill(db, kill_after_acks=10)

    mem = SemanticMemory(db_path=db)  # boot over the killed store (WAL recovery)
    mem.store(Fact(proposition="post-crash write lands",
                   topic="t/crash-after"), embed="defer")
    conn = sqlite3.connect(db)
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE topic='t/crash-after'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert n == 1


def test_journal_entry_survives_worker_kill_and_replays_on_boot(tmp_path) -> None:
    """Deferred-path crash: the journal entry is written, the process dies
    before the background store lands — the next boot must replay it."""
    import engram.semantic as semantic_mod

    db = tmp_path / "semantic" / "semantic.db"
    db.parent.mkdir(parents=True)
    SemanticMemory(db_path=db)

    orphan = Fact(proposition="journaled then killed", topic="t/crash-journal")
    jpath = semantic_mod._journal_path_for(db)
    worker = (
        "import json, sys, time\n"
        "from pathlib import Path\n"
        "jpath, payload = Path(sys.argv[1]), sys.argv[2]\n"
        "with jpath.open('a', encoding='utf-8') as fh:\n"
        "    fh.write(payload + '\\n')\n"
        "    fh.flush()\n"
        "print('journaled', flush=True)\n"
        "time.sleep(300)  # background store never lands\n"
    )
    payload = json.dumps({"kind": "fact", "fact": asdict(orphan),
                          "store_kwargs": {"embed": "defer"}})
    proc = subprocess.Popen(
        [sys.executable, "-c", worker, str(jpath), payload],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    try:
        assert proc.stdout.readline().strip() == "journaled"  # type: ignore[union-attr]
        proc.kill()
    finally:
        proc.stdout.close()  # type: ignore[union-attr]
        proc.wait(timeout=30)

    SemanticMemory(db_path=db)  # boot triggers _replay_pending_facts
    conn = sqlite3.connect(db)
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE topic='t/crash-journal'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert n == 1
    assert not jpath.exists(), "journal must be consumed after replay"
