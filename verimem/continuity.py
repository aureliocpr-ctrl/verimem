"""Session-continuity primitives: lineage resolve, chain walks, tip, digest.

Product surface for what previously lived only in an internal legacy tool
(raw SQL writes, status outside the enum, full gate bypass): the narrative
session chain over ``facts.lineage_to``. R26 established that column as the
NARRATIVE session-successor pointer (distinct from ``derives_from``, the
logical-derivation edge) — these helpers are the read/navigate layer, and
``Memory.add`` remains the only write path (gate receipt included).

All functions are pure reads over a ``SemanticMemory`` except nothing —
writes live in the CLI layer via the SDK. Legacy interop: old rows store a
bare single id in ``lineage_to``; :func:`_parse_ids` reads both encodings
(comma-separated list, empties filtered — ``""`` must never be walked).
"""
from __future__ import annotations

import time
from collections import Counter, defaultdict
from typing import Any

MAX_DEPTH = 100  # cycle/corruption cap for chain walks

_MIN_PREFIX = 6


class LineageRefError(ValueError):
    """Malformed lineage reference (CLI exit 2): too short, empty, misused."""


class LineageNotFound(LookupError):
    """Reference did not resolve (CLI exit 1): no match, or ambiguous."""


def _parse_ids(raw: str | None) -> list[str]:
    """Comma-separated ids -> list, dropping empties (legacy '' / NULL rows)."""
    if not raw:
        return []
    return [s.strip() for s in str(raw).split(",") if s.strip()]


_NODE_COLS = ("id, topic, substr(proposition, 1, 160), created_at, "
              "lineage_to, confidence, status, meta_narrative, "
              "grounding_score")


def _node(row: tuple) -> dict[str, Any]:
    parents = _parse_ids(row[4])
    return {
        "id": row[0],
        "topic": row[1] or "",
        "preview": row[2] or "",
        "created_at": row[3],
        "lineage_to": parents,
        "extra_parents": parents[1:],
        "confidence": row[5],
        "status": row[6],
        "meta_narrative": bool(row[7]),
        # Il verdetto del moat viaggia col nodo. `status` dice CHE COSA e' il
        # fatto (l'affermazione di un modello), non se qualcuno l'ha
        # verificata: un model_claim giudicato 99.9 e uno mai guardato hanno lo
        # stesso status. Resta None quando il moat non ha girato — «mai
        # giudicato» non e' zero, ed e' la distinzione che il prodotto vende.
        "grounding_score": row[8],
    }


def resolve_prefix(sm, prefix: str) -> str:
    """Resolve a fact-id prefix (>= 6 chars) to the unique full id."""
    prefix = (prefix or "").strip()
    if len(prefix) < _MIN_PREFIX:
        raise LineageRefError(
            f"fact reference '{prefix}' is shorter than {_MIN_PREFIX} chars")
    with sm._connect() as conn:  # noqa: SLF001 — package-internal read
        rows = conn.execute(
            "SELECT id FROM facts WHERE id LIKE ? LIMIT 5",
            (prefix + "%",)).fetchall()
    if not rows:
        raise LineageNotFound(f"no fact matches prefix '{prefix}'")
    if len(rows) > 1:
        raise LineageNotFound(
            f"prefix '{prefix}' is ambiguous "
            f"({[r[0][:12] for r in rows]}...) — give more characters")
    return rows[0][0]


def resolve_lineage(sm, ref: str, topic: str = "") -> str:
    """Resolve ``--lineage-to`` ``auto`` | ``topic`` | ``latest`` | id-prefix.

    ``auto``  = newest fact sharing the FIRST topic segment of ``topic``
    (the session-chain convention — R26: session chains are 95%
    cross-topic). ``topic`` = newest fact with the EXACT same topic (the
    single-thread pin, for sibling threads sharing a segment — adversarial
    review deepseek #3). ``latest`` = newest fact regardless.
    Cold-start contract: when EXPLICITLY requested these RAISE on no match —
    a silent root would hide a broken chain; the save command's DEFAULT is
    auto-or-root instead (see :func:`save_checkpoint`).
    """
    ref = (ref or "").strip()
    if not ref:
        raise LineageRefError("empty lineage reference")
    if ref == "topic":
        t = (topic or "").strip()
        if not t:
            raise LineageRefError("lineage 'topic' needs a --topic to match")
        with sm._connect() as conn:  # noqa: SLF001
            row = conn.execute(
                "SELECT id FROM facts WHERE topic = ? "
                "ORDER BY created_at DESC LIMIT 1", (t,)).fetchone()
        if not row:
            raise LineageNotFound(
                f"lineage 'topic': no prior fact with topic '{t}'")
        return row[0]
    if ref == "latest":
        with sm._connect() as conn:  # noqa: SLF001
            row = conn.execute(
                "SELECT id FROM facts ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        if not row:
            raise LineageNotFound(
                "lineage 'latest': the store has no facts yet "
                "(omit --lineage-to for a root checkpoint)")
        return row[0]
    if ref == "auto":
        seg = (topic or "").split("/", 1)[0].strip()
        if not seg:
            raise LineageRefError("lineage 'auto' needs a --topic to match")
        with sm._connect() as conn:  # noqa: SLF001
            row = conn.execute(
                "SELECT id FROM facts WHERE topic = ? OR topic LIKE ? "
                "ORDER BY created_at DESC LIMIT 1",
                (seg, seg + "/%")).fetchone()
        if not row:
            raise LineageNotFound(
                f"lineage 'auto': no prior fact under topic segment '{seg}' "
                "(omit --lineage-to for a root checkpoint)")
        return row[0]
    return resolve_prefix(sm, ref)


def tip_fact(sm) -> dict[str, Any] | None:
    """Newest fact in the store (the 'where were we') or None when empty."""
    with sm._connect() as conn:  # noqa: SLF001
        row = conn.execute(
            f"SELECT {_NODE_COLS} FROM facts "
            "ORDER BY created_at DESC LIMIT 1").fetchone()
    return _node(row) if row else None


def walk_backward(sm, start_id: str, max_depth: int = MAX_DEPTH,
                  ) -> list[dict[str, Any]]:
    """Follow first-parent backbone from ``start_id`` to root; root->start.

    Extra parents ride along on each node (``extra_parents``). A parent id
    that no longer exists is surfaced on the last reachable node as
    ``missing_parent`` instead of silently ending the story.
    """
    chain: list[dict[str, Any]] = []
    seen: set[str] = set()
    current = start_id
    with sm._connect() as conn:  # noqa: SLF001
        for _ in range(max_depth):
            if current in seen:
                break
            seen.add(current)
            row = conn.execute(
                f"SELECT {_NODE_COLS} FROM facts WHERE id = ?",
                (current,)).fetchone()
            if not row:
                if chain:
                    chain[-1]["missing_parent"] = current
                break
            chain.append(_node(row))
            parents = chain[-1]["lineage_to"]
            if not parents:
                break
            current = parents[0]
    return list(reversed(chain))


def walk_forward(sm, start_id: str, max_depth: int = MAX_DEPTH,
                 ) -> list[dict[str, Any]]:
    """BFS over descendants: facts whose ``lineage_to`` CONTAINS an id.

    Matches all four encodings of membership in the comma-separated column
    (exact, head, tail, middle) so multi-parent children are found too.
    """
    out: list[dict[str, Any]] = []
    queue = [start_id]
    seen: set[str] = set()
    with sm._connect() as conn:  # noqa: SLF001
        while queue and len(out) < max_depth:
            node_id = queue.pop(0)
            if node_id in seen:
                continue
            seen.add(node_id)
            rows = conn.execute(
                f"SELECT {_NODE_COLS} FROM facts WHERE "
                "lineage_to = ? OR lineage_to LIKE ? "
                "OR lineage_to LIKE ? OR lineage_to LIKE ? "
                "ORDER BY created_at ASC",
                (node_id, node_id + ",%", "%," + node_id,
                 "%," + node_id + ",%")).fetchall()
            for row in rows:
                child = _node(row)
                if child["id"] not in seen:
                    out.append(child)
                    queue.append(child["id"])
    return out


def find_orphans(sm, since_epoch: float, limit: int = 50) -> dict[str, Any]:
    """Facts in the window with no lineage pointer, plus the window total."""
    with sm._connect() as conn:  # noqa: SLF001
        rows = conn.execute(
            f"SELECT {_NODE_COLS} FROM facts "
            "WHERE created_at >= ? AND (lineage_to IS NULL OR lineage_to = '') "
            "ORDER BY created_at DESC LIMIT ?",
            (since_epoch, limit)).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM facts WHERE created_at >= ?",
            (since_epoch,)).fetchone()[0]
    return {"orphans": [_node(r) for r in rows], "total": total}


def save_checkpoint(memory, text: str, *, topic: str = "session",
                    lineage_to: str | None = None,
                    verified_by: list[str] | None = None,
                    confidence: float | None = None,
                    source: str | None = None,
                    principal: str | None = None,
                    asserted_at: float | None = None) -> dict[str, Any]:
    """Write a session checkpoint THROUGH the gate, chained.

    The write is ``Memory.add(meta_narrative=True)`` — receipt included,
    injection/L3/L4 active, only the L1 self-claim family relaxed (a
    chronicle is not a claim about the agent's own code working).

    Lineage default is **auto-or-root**: try the session chain (newest fact
    under the first topic segment); none found -> honest root, no error
    (deepseek #4 / glm #12). Explicit values are strict and raise on no
    match: ``auto`` | ``topic`` | ``latest`` | id-prefix; ``none`` forces a
    root. The receipt always carries ``lineage_resolved`` so the link is
    never silent (deepseek #3).
    """
    resolved: str | None = None
    ref = (lineage_to or "").strip()
    if ref == "none":
        resolved = None
    elif ref:
        resolved = resolve_lineage(memory.semantic, ref, topic)
    else:
        try:
            resolved = resolve_lineage(memory.semantic, "auto", topic)
        except (LineageNotFound, LineageRefError):
            resolved = None  # cold start / no session yet -> root
    r = memory.add(
        text, topic=topic, meta_narrative=True,
        lineage_to=[resolved] if resolved else None,
        verified_by=verified_by, confidence=confidence,
        source=source, principal=principal,
        # Il tempo di EVENTO, quando il fatto e' vero, distinto da quello di
        # transazione. Resta None se non lo si dichiara: riempirlo d'ufficio
        # con l'ora di scrittura cancellerebbe la distinzione fra le due cose,
        # che e' cio' su cui `recall_as_of` costruisce il time-travel.
        asserted_at=asserted_at)
    r["lineage_resolved"] = resolved
    return r


HANDOFF_TOPIC_PREFIX = "continuity/handoff"


def handoff_show(sm, label: str = "default") -> dict[str, Any] | None:
    """Latest handoff fact for ``label`` (full proposition) or None."""
    topic = f"{HANDOFF_TOPIC_PREFIX}/{label}"
    with sm._connect() as conn:  # noqa: SLF001
        row = conn.execute(
            "SELECT id, topic, proposition, created_at, lineage_to "
            "FROM facts WHERE topic = ? ORDER BY created_at DESC LIMIT 1",
            (topic,)).fetchone()
    if not row:
        return None
    return {"id": row[0], "topic": row[1], "proposition": row[2],
            "created_at": row[3], "lineage_to": _parse_ids(row[4])}


def handoff_log(sm, label: str = "default", limit: int = 10,
                ) -> list[dict[str, Any]]:
    """Handoff history for ``label``, newest first."""
    topic = f"{HANDOFF_TOPIC_PREFIX}/{label}"
    with sm._connect() as conn:  # noqa: SLF001
        rows = conn.execute(
            f"SELECT {_NODE_COLS} FROM facts WHERE topic = ? "
            "ORDER BY created_at DESC LIMIT ?", (topic, limit)).fetchall()
    return [_node(r) for r in rows]


def handoff_prepare(memory, text: str, *, label: str = "default",
                    principal: str | None = None) -> dict[str, Any]:
    """Save a handoff checkpoint auto-linked into BOTH chains.

    Parents (native multi-parent ``lineage_to``): the previous handoff of
    the same label (the handoff backbone) AND the current global tip (the
    work the handoff summarizes) — so the handoff namespace never drifts
    into a disconnected island (glm #5).
    """
    sm = memory.semantic
    parents: list[str] = []
    prev = handoff_show(sm, label)
    if prev:
        parents.append(prev["id"])
    tip = tip_fact(sm)
    if tip and tip["id"] not in parents:
        parents.append(tip["id"])
    r = memory.add(
        text, topic=f"{HANDOFF_TOPIC_PREFIX}/{label}", meta_narrative=True,
        lineage_to=parents or None, principal=principal)
    r["lineage_resolved"] = parents
    return r


def relink(sm, child_ref: str, parent_ref: str, add: bool = False,
           ) -> dict[str, Any]:
    """Chain repair (glm #7): point ``child`` at ``parent``.

    ``add=False`` replaces the parent set; ``add=True`` appends (multi-
    parent). Metadata-only mutation of the narrative pointer — content and
    status untouched, so no gate re-run. Refuses self-loops.
    """
    child = resolve_prefix(sm, child_ref)
    parent = resolve_prefix(sm, parent_ref)
    if child == parent:
        raise LineageRefError("cannot link a fact to itself")
    with sm._connect() as conn:  # noqa: SLF001
        row = conn.execute(
            "SELECT lineage_to FROM facts WHERE id = ?", (child,)).fetchone()
        current = _parse_ids(row[0] if row else None)
        if add:
            new = current + ([parent] if parent not in current else [])
        else:
            new = [parent]
        conn.execute("UPDATE facts SET lineage_to = ? WHERE id = ?",
                     (",".join(new), child))
    return {"id": child, "lineage_to": new, "previous": current}


def recent_facts(sm, n: int = 10, include_hidden: bool = False,
                 ) -> list[dict[str, Any]]:
    """Newest N facts as chain nodes (default view mirrors recall's
    hidden-set: orphaned/quarantined/user_belief excluded)."""
    where = ("" if include_hidden else
             "WHERE status NOT IN ('orphaned', 'quarantined', 'user_belief') ")
    with sm._connect() as conn:  # noqa: SLF001
        rows = conn.execute(
            f"SELECT {_NODE_COLS} FROM facts {where}"
            "ORDER BY created_at DESC LIMIT ?", (int(max(1, n)),)).fetchall()
    return [_node(r) for r in rows]


def since_epoch(spec: str) -> float:
    """Parse ``today`` | ``Nh`` | ``Nd`` | ``Nm`` | ``Nw`` -> epoch cutoff."""
    import datetime as _dt
    spec = (spec or "").strip()
    if spec == "today":
        return _dt.datetime.combine(_dt.date.today(), _dt.time.min).timestamp()
    if len(spec) >= 2 and spec[-1] in ("m", "h", "d", "w"):
        try:
            num = float(spec[:-1])
        except ValueError:
            raise LineageRefError(
                f"invalid --since '{spec}' (expected NUM[m|h|d|w] or 'today')"
            ) from None
        return time.time() - num * {"m": 60, "h": 3600, "d": 86400,
                                    "w": 604800}[spec[-1]]
    raise LineageRefError(
        f"invalid --since '{spec}' (expected NUM[m|h|d|w] or 'today')")


def _namespace(topic: str, depth: int = 2) -> str:
    if not topic:
        return "(no namespace)"
    return "/".join(topic.split("/")[:depth])


def collect_digest(sm, hours: float = 24.0) -> dict[str, Any]:
    """Window narrative: counts by status, themes by namespace, chain health.

    Unlike a bare listing this is the trust-transparent recap: it shows what
    the gate DID in the window (admitted vs quarantined), how linked the
    story is (orphan ratio), and where the tip sits. Empty window -> zeros,
    never NaN (scripts consume --json).
    """
    cutoff = time.time() - hours * 3600
    with sm._connect() as conn:  # noqa: SLF001
        rows = conn.execute(
            f"SELECT {_NODE_COLS} FROM facts WHERE created_at >= ? "
            "ORDER BY created_at ASC", (cutoff,)).fetchall()
    facts = [_node(r) for r in rows]
    by_status = Counter(f["status"] for f in facts)
    themes_raw: dict[str, list[dict]] = defaultdict(list)
    for f in facts:
        themes_raw[_namespace(f["topic"])].append(f)
    themes = []
    for ns, items in themes_raw.items():
        linked = sum(1 for f in items if f["lineage_to"])
        themes.append({
            "namespace": ns,
            "n_facts": len(items),
            "linked_ratio": round(linked / len(items), 2),
            "last_seen": max(f["created_at"] for f in items),
        })
    themes.sort(key=lambda t: t["n_facts"], reverse=True)
    orphans = sum(1 for f in facts if not f["lineage_to"])
    return {
        "window_hours": hours,
        "n_facts": len(facts),
        "by_status": dict(by_status),
        "themes": themes,
        "velocity_per_hour": round(len(facts) / hours, 2) if hours else 0.0,
        "orphan_ratio": round(orphans / len(facts), 2) if facts else 0.0,
        "tip": facts[-1] if facts else None,
    }
