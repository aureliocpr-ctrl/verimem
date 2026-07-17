"""Deferred UPDATE durability via per-deferral nonce (data-loss hunt #1, 2026-06-14).

The boot replay used to skip any journal entry whose fact id already existed in the
db (`if memory.get(fid) is not None: continue`). For a content-hash id, hippo_remember
re-stores the SAME id to UPDATE confidence/status/verified_by — so "id exists" is the
normal precondition, NOT proof the deferred write landed. A kill before the background
store therefore silently dropped the update (caller was told deferred:true=success).

Fix: idempotency is keyed by a per-deferral NONCE echoed in the done-marker, so a
genuinely-newer deferred UPDATE replays even though its id is present, while a stale
done-marker of an earlier deferral of the same id no longer masks it.
"""
from __future__ import annotations

import json
from dataclasses import asdict

from verimem.semantic import Fact, SemanticMemory, _journal_path_for


def _seed(tmp_path, conf=0.5):
    db = tmp_path / "semantic" / "semantic.db"
    db.parent.mkdir(parents=True)
    sm = SemanticMemory(db_path=db)
    fact = Fact(proposition="deferred update target", topic="t/upd", confidence=conf)
    sm.store(fact, embed="sync")
    return db, fact


def _write_journal(db, *lines):
    _journal_path_for(db).write_text(
        "".join(json.dumps(o) + "\n" for o in lines), encoding="utf-8"
    )


def test_deferred_update_without_done_is_replayed(tmp_path):
    """THE BUG: an UPDATE deferral whose id already exists, with NO done-marker
    (background store never landed), must be replayed — not masked by id-presence."""
    db, fact = _seed(tmp_path, conf=0.5)
    upd = asdict(fact)
    upd["confidence"] = 0.95
    _write_journal(db, {"kind": "fact", "nonce": "n-new", "fact": upd,
                        "store_kwargs": {"embed": "sync"}})

    sm2 = SemanticMemory(db_path=db)  # boot → replay
    got = sm2.get(fact.id)
    assert got is not None
    assert abs(got.confidence - 0.95) < 1e-9, (
        "deferred UPDATE (no done-marker) must replay, not be dropped on id-presence"
    )
    assert not _journal_path_for(db).exists(), "journal consumed after replay"


def test_deferral_with_matching_done_nonce_is_skipped(tmp_path):
    """Idempotent: when THIS deferral's nonce is marked done (the background store
    landed), the entry is skipped — no double apply."""
    db, fact = _seed(tmp_path, conf=0.5)
    upd = asdict(fact)
    upd["confidence"] = 0.95
    _write_journal(
        db,
        {"kind": "fact", "nonce": "n1", "fact": upd, "store_kwargs": {"embed": "sync"}},
        {"kind": "done", "id": fact.id, "nonce": "n1"},
    )
    sm2 = SemanticMemory(db_path=db)
    got = sm2.get(fact.id)
    assert abs(got.confidence - 0.5) < 1e-9, "done-marked deferral must be skipped"


def test_stale_done_nonce_does_not_mask_new_deferral(tmp_path):
    """A done-marker from an EARLIER completed deferral of the same id must NOT mask
    a newer, un-completed deferral of that id (the masking mechanism)."""
    db, fact = _seed(tmp_path, conf=0.5)
    upd = asdict(fact)
    upd["confidence"] = 0.95
    _write_journal(
        db,
        {"kind": "done", "id": fact.id, "nonce": "n-old"},  # earlier deferral, landed
        {"kind": "fact", "nonce": "n-new", "fact": upd,  # newer deferral, NOT landed
         "store_kwargs": {"embed": "sync"}},
    )
    sm2 = SemanticMemory(db_path=db)
    got = sm2.get(fact.id)
    assert abs(got.confidence - 0.95) < 1e-9, (
        "new deferral must replay; a stale same-id done-marker must not mask it"
    )


def test_failed_entry_keeps_journal_for_retry_not_dropped(tmp_path):
    """Data-loss fix (review 2026-06-20): if a journal entry's store() RAISES (e.g.
    SQLite 'database is locked' past busy_timeout, or an invalid status), the claim
    file must NOT be unlinked — else that deferred write is lost forever. It must
    survive for the stale-recovery path to retry on a later boot."""
    db, fact = _seed(tmp_path, conf=0.5)
    upd = asdict(fact)
    upd["confidence"] = 0.95
    bad = asdict(fact)
    bad["id"] = "bad-status-fact"
    bad["status"] = "not_a_real_status"   # store() raises ValueError on this
    _write_journal(
        db,
        {"kind": "fact", "nonce": "n-ok", "fact": upd, "store_kwargs": {"embed": "sync"}},
        {"kind": "fact", "nonce": "n-bad", "fact": bad, "store_kwargs": {"embed": "sync"}},
    )
    sm2 = SemanticMemory(db_path=db)  # boot → replay (one ok, one raises)
    assert abs(sm2.get(fact.id).confidence - 0.95) < 1e-9, "the good entry must replay"
    # the claim file (renamed journal) must SURVIVE because an entry failed
    survivors = list(db.parent.glob("pending_facts.replay-*.jsonl"))
    assert survivors, "claim with a failed entry must be kept for retry, not unlinked"


def test_legacy_entry_without_nonce_keeps_old_id_presence_guard(tmp_path):
    """Back-compat: a pre-nonce journal entry (no nonce) keeps the old behaviour —
    skipped when the id already exists — so an upgrade never double-applies it."""
    db, fact = _seed(tmp_path, conf=0.5)
    stale = asdict(fact)
    stale["confidence"] = 0.95  # would change the row IF (wrongly) replayed
    _write_journal(db, {"kind": "fact", "fact": stale,
                        "store_kwargs": {"embed": "sync"}})  # NO nonce
    sm2 = SemanticMemory(db_path=db)
    got = sm2.get(fact.id)
    assert abs(got.confidence - 0.5) < 1e-9, (
        "legacy (no-nonce) entry must keep the id-presence skip for back-compat"
    )
