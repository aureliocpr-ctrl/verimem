#!/usr/bin/env python
"""Re-embed stale rows to the ACTIVE embedding model (facts + skills).

Why this exists (and supersedes the hardcoded ``flip_embedding.py``):
the per-row embedding isolation (facts v9 / skills v2) EXCLUDES from recall any
row whose ``embedding_model`` != the active model OR whose vector byte-length !=
the active dim. Rows left at an old model are semantically unreachable (keyword
only). This brings them back by RE-ENCODING their source text with whatever
model is active *right now* — read from ``embedding.model_signature()``, never
hardcoded, so it stays correct across future model bumps.

Mutates ONLY the embedding + embedding_model columns. Mirrors the exact
store-side encode convention so re-embedded vectors match recall-time queries:
- facts:  ``embedding.encode(embedding.as_passage(proposition))``  (semantic.py:1105)
- skills: ``embedding.encode(f"{name}\\n{trigger}")``  (RAW, no prefix — skill.py:258)

Safety:
- DRY-RUN by default; ``--live`` required to write.
- A dimension guard probes the model first and ABORTS if the loaded model does
  not produce the expected dim (prevents corrupting the corpus with a wrong model).
- Chunked commits (default 200 rows) keep the SQLite write-lock held briefly
  (the contention root behind the historical save hang).
- ``--live`` makes a VACUUM INTO backup of each touched DB first.

Run dry:   python scripts/reembed_to_active_model.py
Run live:  python scripts/reembed_to_active_model.py --live
"""
from __future__ import annotations

import os
import sqlite3
import sys
import time
from pathlib import Path

# cached model + no accidental network. Do NOT set delegate-only: this batch
# job intentionally loads the model in-process.
os.environ.setdefault("HIPPO_OFFLINE", "1")

from engram import embedding  # noqa: E402
from engram.config import CONFIG  # noqa: E402

DATA = Path(os.environ.get("ENGRAM_DATA_DIR", "~/.engram")).expanduser()
SEM = DATA / "semantic" / "semantic.db"
SKI = DATA / "skills" / "skills_index.db"

ACTIVE = embedding.model_signature()
EXPECT_DIM = int(CONFIG.embedding_dim)
EXPECT_BYTES = EXPECT_DIM * 4


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def _probe_or_abort() -> None:
    """Load the active model and verify it yields EXPECT_DIM, else abort."""
    t0 = time.time()
    vec = embedding.encode(embedding.as_passage("probe di calibrazione"))
    dt = time.time() - t0
    dim = int(vec.shape[-1])
    print(f"[probe] model={ACTIVE!r} loaded+encoded in {dt:.1f}s -> dim={dim} (expect {EXPECT_DIM})")
    if dim != EXPECT_DIM:
        print(f"FATAL: model produced dim {dim} != expected {EXPECT_DIM}; ABORT (no writes).")
        raise SystemExit(3)


def _backup(db: Path) -> None:
    bdir = DATA / "backups" / "manual"
    bdir.mkdir(parents=True, exist_ok=True)
    dst = bdir / f"{db.stem}.pre-reembed-{ACTIVE.split('/')[-1]}.db"
    con = sqlite3.connect(db)
    try:
        con.execute("VACUUM INTO ?", (str(dst),))
    finally:
        con.close()
    print(f"[backup] {db.name} -> {dst.name} ({dst.stat().st_size // 1024}KB)")


def _open_rw(db: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db, timeout=60.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=60000")
    con.execute("PRAGMA journal_mode=WAL")
    return con


def reembed_facts(live: bool, batch: int = 64, commit_every: int = 200) -> int:
    con = _open_rw(SEM)
    try:
        rows = con.execute(
            "SELECT id, proposition FROM facts "
            "WHERE COALESCE(embedding_model,'') != ? OR length(embedding) != ?",
            (ACTIVE, EXPECT_BYTES),
        ).fetchall()
        todo = [(r["id"], r["proposition"]) for r in rows if (r["proposition"] or "").strip()]
        skipped = len(rows) - len(todo)
        print(f"[facts] stale={len(rows)}  to_embed={len(todo)}  skipped_empty_prop={skipped}")
        if not live or not todo:
            return 0
        done = pending = 0
        for chunk in _chunks(todo, batch):
            texts = [embedding.as_passage(p) for _, p in chunk]
            embs = embedding.encode(texts)
            if embs.ndim == 1:
                embs = embs.reshape(1, -1)
            assert embs.shape[1] == EXPECT_DIM, f"batch dim {embs.shape[1]} != {EXPECT_DIM}"
            for (fid, _), vec in zip(chunk, embs, strict=True):
                con.execute(
                    "UPDATE facts SET embedding=?, embedding_model=? WHERE id=?",
                    (embedding.serialize(vec), ACTIVE, fid),
                )
                done += 1
                pending += 1
                if pending >= commit_every:
                    con.commit()
                    pending = 0
                    print(f"  ...facts committed {done}/{len(todo)}")
        con.commit()
        print(f"[facts] re-embedded {done}")
        return done
    finally:
        con.close()


def reembed_skills(live: bool, commit_every: int = 100) -> int:
    if not SKI.exists():
        print("[skills] no skills DB — skip")
        return 0
    con = _open_rw(SKI)
    try:
        rows = con.execute(
            "SELECT id, name, trigger FROM skills "
            "WHERE COALESCE(embedding_model,'') != ? OR length(trigger_embedding) != ?",
            (ACTIVE, EXPECT_BYTES),
        ).fetchall()
        print(f"[skills] stale={len(rows)}")
        if not live or not rows:
            return 0
        done = pending = 0
        for r in rows:
            text = f"{r['name']}\n{r['trigger']}"
            vec = embedding.encode(text)
            if vec.ndim > 1:
                vec = vec[0]
            assert vec.shape[-1] == EXPECT_DIM
            con.execute(
                "UPDATE skills SET trigger_embedding=?, embedding_model=? WHERE id=?",
                (embedding.serialize(vec), ACTIVE, r["id"]),
            )
            done += 1
            pending += 1
            if pending >= commit_every:
                con.commit()
                pending = 0
        con.commit()
        print(f"[skills] re-embedded {done}")
        return done
    finally:
        con.close()


def verify() -> None:
    print("\n=== POST-VERIFY ===")
    for label, db, tbl, col in (
        ("facts", SEM, "facts", "embedding"),
        ("skills", SKI, "skills", "trigger_embedding"),
    ):
        if not db.exists():
            continue
        c = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
        try:
            total = c.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            bad = c.execute(
                f"SELECT COUNT(*) FROM {tbl} "
                f"WHERE COALESCE(embedding_model,'') != ? OR length({col}) != ?",
                (ACTIVE, EXPECT_BYTES),
            ).fetchone()[0]
            empty_prop = 0
            if tbl == "facts":
                empty_prop = c.execute(
                    f"SELECT COUNT(*) FROM {tbl} WHERE COALESCE(embedding_model,'')!=? "
                    f"AND length(trim(COALESCE(proposition,'')))=0",
                    (ACTIVE,),
                ).fetchone()[0]
            print(f"  {label}: total={total} still_not_active={bad} (empty_prop_excused={empty_prop})")
        finally:
            c.close()


def main() -> int:
    live = "--live" in sys.argv[1:]
    print(f"ACTIVE model = {ACTIVE!r}  expect_dim={EXPECT_DIM}  expect_bytes={EXPECT_BYTES}")
    print(f"DATA = {DATA}   mode = {'LIVE (writes)' if live else 'DRY-RUN (read-only)'}")
    if live:
        _probe_or_abort()
        _backup(SEM)
        if SKI.exists():
            _backup(SKI)
    else:
        # still probe in dry-run to confirm model dim, but tolerate model-miss
        try:
            _probe_or_abort()
        except SystemExit:
            print("[dry-run] probe failed — would abort in --live")
    nf = reembed_facts(live)
    ns = reembed_skills(live)
    if live:
        verify()
        print(f"\nDONE live: facts={nf} skills={ns}. MCP server must RESTART to rebuild its recall cache.")
    else:
        print("\nDRY-RUN complete. Re-run with --live to write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
