"""Self-model — single-row, replace-only, versioned continuity record.

Cycle #67 (2026-05-14). Stores the *current* state of the
Aurelio+Claude collaboration as a structured JSON document. Read by
the SessionStart hook to give every fresh Claude instance a coherent
view of "who we are right now" — bridging the gap between persistent
memory (facts/episodes) and an interpreted self.

Unlike a normal fact:
  - Single row (no duplication).
  - Replace-only updates with full audit history.
  - Always-injected at SessionStart (never retrieved by cosine).
  - Bounded size (4 KB default) to avoid context saturation.

Storage: SQLite at ~/.engram/self_model.db (or a configurable path).
Schema (two tables):

    CREATE TABLE self_model_current (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        version INTEGER NOT NULL,
        updated_at REAL NOT NULL,
        content_json TEXT NOT NULL,
        actor TEXT
    );
    CREATE TABLE self_model_audit (
        version INTEGER PRIMARY KEY,
        updated_at REAL NOT NULL,
        content_json TEXT NOT NULL,
        actor TEXT
    );

The single-row constraint on `self_model_current` is enforced by the
`id = 1` CHECK plus an UPSERT (`ON CONFLICT(id) DO UPDATE`). The audit
table grows monotonically with every update.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

DEFAULT_MAX_BYTES = 4096


class SelfModelTooLarge(ValueError):
    """Raised when a proposed update exceeds the max byte budget."""


class SelfModelStore:
    """SQLite-backed self-model store.

    Thread-safe per-instance via SQLite's connection lock; concurrent
    instances against the same file serialise via SQLite's database
    lock (cycle #67 tests cover this case).
    """

    def __init__(
        self,
        db_path: Path,
        *,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ) -> None:
        self.db_path = Path(db_path)
        self.max_bytes = int(max_bytes)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS self_model_current (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    version INTEGER NOT NULL,
                    updated_at REAL NOT NULL,
                    content_json TEXT NOT NULL,
                    actor TEXT
                );
                CREATE TABLE IF NOT EXISTS self_model_audit (
                    version INTEGER PRIMARY KEY,
                    updated_at REAL NOT NULL,
                    content_json TEXT NOT NULL,
                    actor TEXT
                );
                """
            )

    def get(self) -> dict[str, Any] | None:
        """Return the current model as {version, updated_at, content, actor},
        or None if no model has ever been written."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT version, updated_at, content_json, actor "
                "FROM self_model_current WHERE id = 1"
            ).fetchone()
        if row is None:
            return None
        version, updated_at, content_json, actor = row
        return {
            "version": int(version),
            "updated_at": float(updated_at),
            "content": json.loads(content_json),
            "actor": actor,
        }

    def update(
        self,
        content: dict[str, Any],
        *,
        actor: str | None = None,
    ) -> dict[str, Any]:
        """Replace the current model with a new content dict and append
        the old record to the audit table. Returns the new record dict."""
        payload = json.dumps(
            content, ensure_ascii=False, separators=(",", ":"),
        )
        if len(payload.encode("utf-8")) > self.max_bytes:
            raise SelfModelTooLarge(
                f"content {len(payload)} bytes exceeds limit "
                f"{self.max_bytes}"
            )

        now = time.time()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                current = conn.execute(
                    "SELECT version FROM self_model_current WHERE id = 1"
                ).fetchone()
                next_version = (
                    int(current[0]) + 1 if current else 1
                )
                conn.execute(
                    """
                    INSERT INTO self_model_current
                        (id, version, updated_at, content_json, actor)
                    VALUES (1, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        version = excluded.version,
                        updated_at = excluded.updated_at,
                        content_json = excluded.content_json,
                        actor = excluded.actor
                    """,
                    (next_version, now, payload, actor),
                )
                conn.execute(
                    """
                    INSERT INTO self_model_audit
                        (version, updated_at, content_json, actor)
                    VALUES (?, ?, ?, ?)
                    """,
                    (next_version, now, payload, actor),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

        return {
            "version": next_version,
            "updated_at": now,
            "content": content,
            "actor": actor,
        }

    def history(self) -> list[dict[str, Any]]:
        """Return all versions (oldest first) from the audit table."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT version, updated_at, content_json, actor "
                "FROM self_model_audit ORDER BY version ASC"
            ).fetchall()
        return [
            {
                "version": int(v),
                "updated_at": float(ts),
                "content": json.loads(cj),
                "actor": actor,
            }
            for v, ts, cj, actor in rows
        ]


def render_for_injection(record: dict[str, Any] | None) -> str:
    """Render the self-model as a compact human-readable block suitable
    for SessionStart context injection. Returns "" if record is None."""
    if record is None:
        return ""
    c = record.get("content", {})
    lines: list[str] = ["=== SELF MODEL (continuity layer, cycle #67) ==="]
    lines.append(f"version: {record['version']} (updated_at epoch "
                 f"{record['updated_at']:.0f})")
    if c.get("recent_focus"):
        lines.append(f"focus ora: {c['recent_focus']}")
    goals = c.get("current_goals") or []
    if goals:
        lines.append("goal correnti:")
        for g in goals[:8]:
            lines.append(f"  - {g}")
    decisions = c.get("open_decisions") or []
    if decisions:
        lines.append("decisioni aperte:")
        for d in decisions[:6]:
            lines.append(f"  - {d}")
    projects = c.get("active_projects") or []
    if projects:
        lines.append(f"progetti attivi: {', '.join(projects[:8])}")
    if c.get("collab_style"):
        lines.append(f"stile collab: {c['collab_style']}")
    if c.get("notes"):
        notes = str(c["notes"])[:300]
        lines.append(f"note: {notes}")
    lines.append("=" * 46)
    return "\n".join(lines)


def render_anchor_block(
    store: Any,
    *,
    sem: Any = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
    top_k_facts: int = 3,
    weight_threshold: float = 0.01,
) -> dict[str, Any]:
    """P3-bis (cycle #70) — render anchor recall as Markdown block ≤ max_bytes.

    Builds a SessionStart-ready block from `EntityStore.list_anchors()`
    decay-pesato. For each anchor: name, weight, half_life, and top-K
    linked fact propositions (from optional SemanticMemory).

    Args:
        store: `EntityStore` instance (or None for empty output).
        sem: optional `SemanticMemory` to resolve fact_ids → propositions.
            If None, only fact_ids are listed.
        max_bytes: UTF-8 byte budget. Output truncated cleanly with a
            "..." marker if exceeded.
        top_k_facts: max facts shown per anchor.
        weight_threshold: minimum decay weight to include anchor.

    Returns:
        {"markdown": str, "n_anchors": int, "truncated": bool}

    Behavior:
        - store=None → {"markdown": "", "n_anchors": 0, "truncated": False}
        - No anchors → markdown="" (no header), n_anchors=0
        - Tie-break order: weight desc, then entity_id asc (deterministic)
        - Decay formula: 2^(-age_days/half_life_days), half_life<=0 → weight=1
        - UTF-8-correct byte counting (len(s.encode('utf-8'))) — Unicode safe
    """
    empty = {"markdown": "", "n_anchors": 0, "truncated": False}
    if store is None:
        return empty
    try:
        anchors_raw = store.list_anchors()
    except Exception:
        return empty
    if not anchors_raw:
        return empty

    now = time.time()
    weighted: list[dict[str, Any]] = []
    for row in anchors_raw:
        eid = row["entity_id"]
        attrs = row.get("attrs") or {}
        half_life = float(attrs.get("half_life_days", 7.0))
        created_at = float(attrs.get("created_anchor_at", now))
        age_days = max(0.0, (now - created_at) / 86400.0)
        if half_life <= 0:
            weight = 1.0
        else:
            weight = 2.0 ** (-age_days / half_life)
        if weight < weight_threshold:
            continue
        weighted.append({
            "entity_id": eid,
            "name": row["name"],
            "weight": weight,
            "age_days": age_days,
            "half_life_days": half_life,
        })
    if not weighted:
        return empty

    # Deterministic tie-break: weight desc, then entity_id asc
    weighted.sort(key=lambda a: (-a["weight"], a["entity_id"]))

    # Build markdown lines greedily until max_bytes
    header = "## Anchor recall (cycle #70 / live decay)"
    lines: list[str] = [header, ""]
    truncated = False

    def _line_bytes(ls: list[str]) -> int:
        return len("\n".join(ls).encode("utf-8"))

    truncation_marker = "\n_(truncated)_"
    marker_bytes = len(truncation_marker.encode("utf-8"))
    budget = max_bytes - marker_bytes  # reserve room for marker

    for a in weighted:
        anchor_line = (
            f"- **{a['name']}** "
            f"(weight {a['weight']:.2f}, "
            f"hl {a['half_life_days']:.1f}d, "
            f"age {a['age_days']:.1f}d)"
        )
        candidate_lines = [anchor_line]
        # Top-K linked facts (preserve insertion order — caller can
        # pre-rank if needed)
        try:
            fact_ids = store.facts_for_entity(a["entity_id"])
        except Exception:
            fact_ids = []
        n_shown = 0
        for fid in fact_ids[: top_k_facts * 3]:
            if n_shown >= top_k_facts:
                break
            prop = fid  # fallback to id if sem unavailable
            if sem is not None:
                try:
                    # live_only (correctness-hunt #3 HIGH-2): entity_facts links
                    # aren't pruned on supersede/orphan, so resolve only LIVE
                    # facts — never inject a retracted/superseded proposition
                    # into the SessionStart self-model block.
                    f = sem.get(fid, live_only=True)
                except TypeError:
                    f = sem.get(fid)  # older sem without the kwarg
                except Exception:
                    f = None
                if f is None:
                    continue  # dead/missing fact: skip, don't render its id
                prop = (getattr(f, "proposition", None)
                        or getattr(f, "id", fid))
            # Cap fact line length for readability
            prop_short = (prop or "")[:140]
            candidate_lines.append(f"  - {prop_short}")
            n_shown += 1

        # Probe: would adding these lines exceed budget?
        probe = lines + candidate_lines
        if _line_bytes(probe) > budget:
            # Try adding just the anchor line without facts
            probe2 = lines + [anchor_line]
            if _line_bytes(probe2) <= budget:
                lines.append(anchor_line)
            truncated = True
            break
        lines.extend(candidate_lines)

    if truncated:
        lines.append("_(truncated)_")
    md = "\n".join(lines)
    # Final defensive trim (in case header alone overflowed — pathological)
    encoded = md.encode("utf-8")
    if len(encoded) > max_bytes:
        # Hard cut at byte boundary, restore valid UTF-8
        cut = encoded[:max_bytes]
        # Decode safely, ignoring partial codepoints at the end
        md = cut.decode("utf-8", errors="ignore")
        truncated = True

    return {
        "markdown": md,
        "n_anchors": len(weighted),
        "truncated": truncated,
    }


__all__ = [
    "SelfModelStore",
    "SelfModelTooLarge",
    "DEFAULT_MAX_BYTES",
    "render_for_injection",
    "render_anchor_block",
]
