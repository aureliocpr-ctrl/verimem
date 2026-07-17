"""Cycle 229 (2026-05-23) — emerging skill → persistent fact registration.

Closes the discovery → persistence loop:

  detect (213) → normalize (214/215) → draft (217) → persist disk (222)
    → auto-dream wire (223) → MCP expose (218, 227)
                              ↓
                      REGISTER AS FACT (229) ← here
                              ↓
                  Next-session SessionStart hook sees it via
                  hippo_facts_recall on topic "emerging_skill/*"

A4 honest framing: this is a *registration* step, NOT an *adoption*
step. The registered facts have ``status='model_claim'`` (i.e. NOT
verified) so the cycle-184 anti-confab L1.8 gate does NOT pick them
up as verified claims. They surface in topic searches as "the system
believes these skills are emerging" — a soft claim awaiting human
or LLM-driven adoption (the future ``hippo_emerging_skills_promote``
tool of cycle 230+).

Idempotent: each draft's fact id is derived deterministically from
its ``skill_name`` so repeated registration UPDATEs instead of
duplicating. Confidence is calibrated as ``purity × cohesion``
clamped to [0.05, 0.95].

Defensive: missing DB → no-op; empty list → no-op; failed insert →
counted as ``n_skipped`` not raised.
"""
from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from .prompt_injection import detect_injection
from .redaction import redact_secrets

_LOG = logging.getLogger(__name__)

_TOPIC_PREFIX = "emerging_skill/auto-discovered"


def _fact_id_for(skill_name: str) -> str:
    """Deterministic content-hash id so repeated registration is idempotent."""
    src = f"emerging_skill::{skill_name}".encode()
    return hashlib.sha256(src).hexdigest()[:16]


def _confidence_from_evidence(evidence: dict[str, Any]) -> float:
    purity = float(evidence.get("topic_purity", 0.0) or 0.0)
    cohesion = float(evidence.get("cohesion", 0.0) or 0.0)
    raw = purity * cohesion
    return max(0.05, min(0.95, raw))


def _proposition_for(draft: dict[str, Any]) -> str:
    name = str(draft.get("skill_name", "") or "")
    evidence = draft.get("evidence", {}) or {}
    keywords = draft.get("trigger_keywords", []) or []
    body_preview = str(draft.get("draft_text", "") or "")[:400]
    parts = [
        f"Auto-discovered skill: {name}",
        (
            "Evidence: size={size}, purity={purity:.2f}, "
            "cohesion={cohesion:.2f}, score={score:.2f}, topic={topic}".format(
                size=int(evidence.get("size", 0) or 0),
                purity=float(evidence.get("topic_purity", 0.0) or 0.0),
                cohesion=float(evidence.get("cohesion", 0.0) or 0.0),
                score=float(evidence.get("emergence_score", 0.0) or 0.0),
                topic=str(evidence.get("dominant_topic", "") or ""),
            )
        ),
        "Trigger keywords: " + ", ".join(str(k) for k in keywords[:8]),
        "Draft preview:",
        body_preview,
    ]
    return "\n".join(parts)


def register_emerging_drafts_as_facts(
    semantic_db: Path | str,
    drafts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Persist each draft as an ``emerging_skill/*`` fact.

    Args:
        semantic_db: path to live ``semantic.db``.
        drafts: list of dicts as produced by
            ``verimem.skill_drafter.draft_skill_from_community``.

    Returns:
        ``{"n_inserted": int, "n_updated": int, "n_skipped": int,
            "registered_ids": list[str]}``.
        All zeros on missing DB or empty input.
    """
    db_path = Path(semantic_db)
    if not db_path.exists() or not drafts:
        return {
            "n_inserted": 0, "n_updated": 0,
            "n_skipped": len(drafts) if drafts else 0,
            "registered_ids": [],
        }

    n_inserted = 0
    n_updated = 0
    n_skipped = 0
    registered: list[str] = []

    try:
        # A-5 (audit#2 2026-06-08): busy_timeout=60s (matches semantic.db / the
        # other stores) — the real deployment is multi-process (CLI + MCP +
        # auto-dream worker all write semantic.db), so a contended write must
        # WAIT, not raise 'database is locked' on first contact.
        conn = sqlite3.connect(str(db_path), timeout=60.0)
        try:
            now = time.time()
            for d in drafts:
                name = str(d.get("skill_name", "") or "").strip()
                if not name:
                    n_skipped += 1
                    continue
                fid = _fact_id_for(name)
                topic = f"{_TOPIC_PREFIX}/{name}"
                proposition = _proposition_for(d)
                # Screen this raw-INSERT path too (audit P1 2026-06-07): emerging
                # drafts are synthesized from episodes and were persisted via raw
                # INSERT, bypassing SemanticMemory.store()'s redaction + injection
                # screen. Redact secrets in-place; SKIP a draft that trips the
                # injection detector (auto-synthesized drafts are non-critical — a
                # poisoned one is safe to drop and re-derivable on the next mine).
                if os.environ.get("ENGRAM_REDACT_SECRETS", "on").strip().lower() not in (
                    "0", "off", "false", "no",
                ):
                    proposition = redact_secrets(proposition)[0]
                if os.environ.get(
                    "ENGRAM_INJECTION_SCREEN", "on"
                ).strip().lower() not in ("0", "off", "false", "no") and detect_injection(
                    proposition
                ).is_injection:
                    n_skipped += 1
                    continue
                confidence = _confidence_from_evidence(
                    d.get("evidence", {}) or {},
                )
                # Detect existing row (idempotent UPDATE vs INSERT).
                exists = conn.execute(
                    "SELECT 1 FROM facts WHERE id = ?", (fid,),
                ).fetchone() is not None
                # Cycle 237: anchor the emerging-skill fact to its
                # source cluster by setting lineage_to to the FIRST
                # member fact_id (deterministic + navigable via
                # `clp chain show`). When fact_ids is empty (defensive
                # guard) the field stays NULL and the fact is an
                # orphan — same behaviour as cycle 229.
                source_fact_ids = d.get("fact_ids", []) or []
                lineage_to = (
                    str(source_fact_ids[0]) if source_fact_ids else None
                )
                if exists:
                    # Only UPDATE lineage_to when we have a value to
                    # set; otherwise keep whatever was there before.
                    if lineage_to is not None:
                        conn.execute(
                            "UPDATE facts SET proposition = ?, topic = ?, "
                            "status = 'model_claim', confidence = ?, "
                            "lineage_to = ? "
                            "WHERE id = ?",
                            (proposition, topic, confidence,
                             lineage_to, fid),
                        )
                    else:
                        conn.execute(
                            "UPDATE facts SET proposition = ?, topic = ?, "
                            "status = 'model_claim', confidence = ? "
                            "WHERE id = ?",
                            (proposition, topic, confidence, fid),
                        )
                    n_updated += 1
                else:
                    # Real semantic.db schema (cycle 113+) has several
                    # NOT NULL columns: source_episodes, embedding,
                    # verified_by. Provide neutral defaults so the
                    # INSERT succeeds on both the live DB and the
                    # test fixtures (which use a stripped schema).
                    try:
                        conn.execute(
                            "INSERT INTO facts "
                            "(id, proposition, topic, status, "
                            " confidence, created_at, embedding, "
                            " source_episodes, verified_by, "
                            " lineage_to) "
                            "VALUES (?, ?, ?, 'model_claim', ?, ?, "
                            "        ?, ?, ?, ?)",
                            (
                                fid, proposition, topic, confidence,
                                now,
                                b"",  # filtered out by cycle 172/113 guard
                                "[]",
                                "[]",
                                lineage_to,
                            ),
                        )
                    except sqlite3.OperationalError:
                        # Test fixtures use minimal schema; retry with
                        # a lean column list. If lineage_to column is
                        # present in the fixture, preserve it; else
                        # drop it (smallest schema path).
                        cols = {
                            r[1] for r in conn.execute(
                                "PRAGMA table_info(facts)",
                            ).fetchall()
                        }
                        if "lineage_to" in cols:
                            conn.execute(
                                "INSERT INTO facts "
                                "(id, proposition, topic, status, "
                                " confidence, created_at, "
                                " lineage_to) "
                                "VALUES (?, ?, ?, 'model_claim', ?, ?, ?)",
                                (
                                    fid, proposition, topic, confidence,
                                    now, lineage_to,
                                ),
                            )
                        else:
                            conn.execute(
                                "INSERT INTO facts "
                                "(id, proposition, topic, status, "
                                " confidence, created_at) "
                                "VALUES (?, ?, ?, 'model_claim', ?, ?)",
                                (
                                    fid, proposition, topic, confidence,
                                    now,
                                ),
                            )
                    n_inserted += 1
                registered.append(fid)
            conn.commit()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        # Defensive: any SQL error → return whatever we got + count skipped.
        # A-5 (audit#2 2026-06-08): LOG it — a persistent write failure used to
        # vanish silently (operators saw only a rising n_skipped with no cause).
        n_skipped += max(0, len(drafts) - n_inserted - n_updated)
        _LOG.warning(
            "register_emerging_drafts_as_facts: SQL error, %d draft(s) skipped: %s",
            max(0, len(drafts) - n_inserted - n_updated), exc,
        )

    return {
        "n_inserted": n_inserted,
        "n_updated": n_updated,
        "n_skipped": n_skipped,
        "registered_ids": registered,
    }


__all__ = ["register_emerging_drafts_as_facts"]
