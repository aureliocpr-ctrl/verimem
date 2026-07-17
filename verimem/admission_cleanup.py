"""Reversible backlog cleanup for the admission gate (verimem.admission_cleanup).

The admission gate (verimem.admission_gate, opt-in) governs only NEW writes. This
routes the EXISTING telemetry-topic facts OUT of the curated ``facts`` table into
the ``telemetry`` table — reclaiming the corpus that the gate would have kept
clean from the start (measured 2026-06-04: ~55% of the live store was telemetry).

Safety contract:
  - ``dry_run=True`` by DEFAULT: only reports, mutates nothing.
  - Decision reuses ``admission_gate.classify_admission`` (single source of truth)
    and acts ONLY on ROUTE_TELEMETRY. Duplicates / low-provenance are left alone
    (more judgment needed; out of scope for this safe first pass).
  - The authoritative UNDO is the pre-cleanup full DB backup (VACUUM INTO). Moved
    rows keep their essentials in ``telemetry`` (id/topic/proposition/created_at/
    writer_role); embeddings are dropped (telemetry is never semantically recalled).
  - Run with the MCP server STOPPED (coordinate with restart) to avoid racing live
    writes.
"""
from __future__ import annotations

import json
import sqlite3

from ._call_telemetry import is_call_telemetry
from .admission_gate import ROUTE_TELEMETRY, classify_admission

#: Embedding BLOB columns dropped from the archived payload — telemetry is never
#: recalled semantically, so re-embeddable vectors are pure bloat (same choice as
#: the fact gate, which drops embeddings too).
_EPISODE_EMBED_COLS = ("summary_embedding", "dg_embedding", "context_embedding")


def cleanup_telemetry(db_path, *, dry_run: bool = True) -> dict:
    """Route existing telemetry facts out of ``facts`` into ``telemetry``.

    Returns ``{scanned, telemetry_found, moved, dry_run}``. With ``dry_run=True``
    (default) ``moved`` is 0 and nothing is mutated.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, topic, proposition, status, writer_role, source_episodes, "
            "created_at FROM facts WHERE superseded_by IS NULL"
        ).fetchall()
        to_move = [
            r for r in rows
            if classify_admission(
                topic=r["topic"], proposition=r["proposition"], status=r["status"],
                writer_role=r["writer_role"], source_episodes=r["source_episodes"],
            ).decision == ROUTE_TELEMETRY
        ]
        result = {
            "scanned": len(rows),
            "telemetry_found": len(to_move),
            "moved": 0,
            "dry_run": dry_run,
        }
        if dry_run or not to_move:
            return result

        conn.execute(
            "CREATE TABLE IF NOT EXISTS telemetry (id TEXT PRIMARY KEY, topic TEXT, "
            "proposition TEXT, created_at REAL, writer_role TEXT)"
        )
        # created_at is read defensively (always present in the live schema, but
        # the unit-test fixture may omit it).
        for r in to_move:
            keys = r.keys()
            created = r["created_at"] if "created_at" in keys else None
            conn.execute(
                "INSERT OR REPLACE INTO telemetry(id, topic, proposition, "
                "created_at, writer_role) VALUES(?,?,?,?,?)",
                (r["id"], r["topic"], r["proposition"], created, r["writer_role"]),
            )
            conn.execute("DELETE FROM facts WHERE id = ?", (r["id"],))
        conn.commit()
        result["moved"] = len(to_move)
        return result
    finally:
        conn.close()


def cleanup_episode_telemetry(db_path, *, dry_run: bool = True) -> dict:
    """Route existing call-telemetry episodes out of ``episodes`` into
    ``episode_telemetry`` — the gemello of :func:`cleanup_telemetry` for the
    EPISODE backlog (the live ``episodes`` carry ~22% auto-saved cross-LLM call
    records: ``[agy-call …]``, ``[gemini-call …]``).

    Decision reuses :func:`verimem._call_telemetry.is_call_telemetry` — the SAME
    predicate the live write-gate (``memory._store_episode_telemetry``) uses, so
    cleanup and gate can never disagree on what counts as telemetry.

    Non-lossy on the meaningful fields: the full row (task_text, outcome,
    final_answer, notes, critique, …) plus any linked ``traces`` rows are preserved
    as a JSON ``payload`` (the live gate serializes ``Episode.traces`` too, so this
    keeps cleanup and gate byte-compatible); only the re-embeddable embedding BLOBs
    are dropped (telemetry is never recalled semantically). The linked ``traces``
    are then deleted EXPLICITLY — not relying on ``PRAGMA foreign_keys`` — so no
    orphan trace can survive the episode delete (critic counterexample 2026-06-14).
    The schema matches the table the live gate writes. ``dry_run`` defaults True;
    the authoritative undo is the pre-run DB backup. Idempotent.

    Returns ``{scanned, telemetry_found, moved, dry_run}``.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(episodes)").fetchall()]
        rows = conn.execute("SELECT * FROM episodes").fetchall()
        to_move = [r for r in rows if is_call_telemetry(r["task_text"] or "")]
        result = {
            "scanned": len(rows),
            "telemetry_found": len(to_move),
            "moved": 0,
            "dry_run": dry_run,
        }
        if dry_run or not to_move:
            return result

        has_traces = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='traces'"
        ).fetchone() is not None
        conn.execute(
            "CREATE TABLE IF NOT EXISTS episode_telemetry (id TEXT PRIMARY KEY, "
            "task_text TEXT, outcome TEXT, created_at REAL, payload TEXT)"
        )
        keep = [c for c in cols if c not in _EPISODE_EMBED_COLS]
        for r in to_move:
            payload = {c: r[c] for c in keep}
            if has_traces:
                # archive the linked traces in the payload (non-lossy, mirrors the
                # gate's Episode.traces), then delete them so none is left orphaned.
                trs = conn.execute(
                    "SELECT * FROM traces WHERE episode_id = ? ORDER BY step",
                    (r["id"],),
                ).fetchall()
                if trs:
                    payload["_traces"] = [dict(t) for t in trs]
            conn.execute(
                "INSERT OR REPLACE INTO episode_telemetry"
                "(id, task_text, outcome, created_at, payload) VALUES(?,?,?,?,?)",
                (
                    r["id"],
                    r["task_text"],
                    r["outcome"] if "outcome" in cols else None,
                    r["created_at"] if "created_at" in cols else None,
                    json.dumps(payload, default=str),
                ),
            )
            if has_traces:
                conn.execute("DELETE FROM traces WHERE episode_id = ?", (r["id"],))
            conn.execute("DELETE FROM episodes WHERE id = ?", (r["id"],))
        conn.commit()
        result["moved"] = len(to_move)
        return result
    finally:
        conn.close()


def requalify_quarantined(db_path, *, dry_run: bool = True) -> dict:
    """Re-evaluate quarantined facts with the CURRENT gate and promote to
    ``model_claim`` the ones no detector trips anymore — recovering real
    knowledge that a SINCE-FIXED false positive (e.g. the 2026-06-14 L1.18/L1.9
    fixes) had hidden from recall (the recall path hard-excludes quarantined rows).

    SAFE: a fact is recovered ONLY if ALL three quarantine sources now pass —
      (1) no L1.x anti-confab warning (``_l1_warnings`` empty),
      (2) not flagged by ``prompt_injection.detect_injection`` (security TP),
      (3) the admission gate admits it to the curated corpus (not telemetry,
          not REJECT_POLLUTED / FLAG_INJECTION).
    So genuine positives (injection, polluted, telemetry) stay quarantined.
    ``dry_run`` default; the authoritative undo is the pre-run DB backup.

    Returns ``{scanned, recoverable, promoted, dry_run}``.
    """
    from .anti_confab_gate import (
        _has_dev_context,
        _has_personal_context,
        _l1_warnings,
    )
    from .prompt_injection import detect_injection

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, topic, proposition, verified_by, writer_role, "
            "source_episodes FROM facts "
            "WHERE status='quarantined' AND superseded_by IS NULL"
        ).fetchall()
        recoverable: list[str] = []
        for r in rows:
            prop = r["proposition"] or ""
            try:
                vb = json.loads(r["verified_by"]) if r["verified_by"] else []
            except (ValueError, TypeError):
                vb = []
            if not isinstance(vb, list):
                vb = []
            # Consistent with run_validation_gate (2026-06-19): an L1 hit on a PERSONAL fact
            # with no dev signal is a false positive that no longer escalates, so it must NOT
            # block recovery — else historical personal-fact FPs ('dentist appointment
            # scheduled', quarantined before the gate fix) could never be un-quarantined.
            if _l1_warnings(prop, vb) and not (
                _has_personal_context(prop) and not _has_dev_context(prop)
            ):
                continue  # still trips an ESCALATING L1.x detector (dev-claim, not personal FP)
            if (detect_injection(prop).is_injection
                    or detect_injection(r["topic"] or "").is_injection):
                # genuine prompt-injection in the proposition OR the topic — keep
                # quarantined. The live write path quarantines on prop-OR-topic
                # (semantic.py: `_iv.is_injection or _iv_topic.is_injection`); requalify
                # checked only the proposition, so a benign-prop / injection-TOPIC fact
                # was re-promoted and its poison topic re-entered recall (review 2026-06-20).
                continue
            verdict = classify_admission(
                topic=r["topic"], proposition=prop, status="model_claim",
                writer_role=(r["writer_role"] or "agent_inference"),
                source_episodes=r["source_episodes"],
            )
            if verdict.decision == ROUTE_TELEMETRY or not verdict.admit_to_curated:
                continue  # telemetry / polluted / flagged — keep quarantined
            recoverable.append(r["id"])
        result = {
            "scanned": len(rows),
            "recoverable": len(recoverable),
            "promoted": 0,
            "dry_run": dry_run,
        }
        if dry_run or not recoverable:
            return result
        for fid in recoverable:
            conn.execute(
                "UPDATE facts SET status='model_claim' WHERE id=?", (fid,)
            )
        conn.commit()
        result["promoted"] = len(recoverable)
        return result
    finally:
        conn.close()


__all__ = [
    "cleanup_telemetry",
    "cleanup_episode_telemetry",
    "requalify_quarantined",
]
