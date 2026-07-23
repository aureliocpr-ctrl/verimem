"""Universal mutation audit — hash-chained, action-only, fail-closed (0.8 step 1).

Every destructive operation on the facts store (delete / purge / forget /
supersede / reset) appends one row to ``audit_mutations`` INSIDE THE SAME
TRANSACTION as the mutation itself. The row records the ACTION — who
(``principal``), what (``action``), on which record (``resource_id``, an
opaque id), when (``ts``), with what outcome — chained via the
``verimem.tamper_evidence`` primitives so any edit, interior deletion or
reorder of past rows is detectable by ``verify()``.

Three deliberate design decisions, each forged against two independent
adversarial reviews (GLM-5.2 + deepseek, convergent findings):

* ACTION-ONLY, never content (F1/F8): storing WHAT was deleted — even as a
  hash, brute-forceable on short text — inside an immutable chain makes GDPR
  Art.17 erasure a logical contradiction. The chain proves THAT/WHO/WHEN/
  WHICH-RECORD, not what the record said. Free text (supersede reasons,
  propositions) must never reach this table.
* FAIL-CLOSED (F2/F5): ``record_mutation`` never swallows. It runs after the
  mutation's SQL on the SAME connection; any failure propagates, the caller's
  transaction rolls back, and the mutation does not happen. An attacker who
  can break audit writes (full disk, dropped table) gets a refused delete,
  not an untracked one.
* MANDATORY PRINCIPAL (F3/F6): enforced by the core callers' signatures and
  re-validated here — never None, never blank, bounded length. Background
  jobs declare ``system:<job>``; surfaces stamp their own identity
  (``sdk:local`` / ``gw:<tenant>`` / ``mcp:*`` / ``cli:local``).

Anti-fork note (F4): the previous-head SELECT runs inside the caller's
transaction AFTER the mutation's write statements, so SQLite's single-writer
lock is already held exclusively — two concurrent mutators serialize and can
never chain off the same head. Callers must therefore invoke
``record_mutation`` after at least one write on ``conn``. The stale-snapshot
interleaving (T2 opens its read snapshot before T1 commits, then writes) was
raised by an adversarial review and empirically REFUTED: WAL refuses the
reader→writer upgrade from an out-of-date snapshot (SQLITE_BUSY_SNAPSHOT
surfacing as "database is locked"), so the contended transaction errors out
fail-closed — no mutation, no audit row, no fork. Verified live with two raw
connections reproducing that exact schedule, and by a 4-thread concurrent
delete stress (48/48 rows, linear chain, verify() clean).

GDPR note on identifiers: ``resource_id`` and the ids inside ``detail``
(new_id, op_id) are opaque UUIDs, deliberately NOT salted-hashed — "which
record" is the audit's whole point. They carry no personal data themselves,
and once the referenced row is erased the identifier becomes unlinkable (no
lookup path back to a person), which is exactly the erasure the chain must
survive.

Declared limits of this cycle: no total order with the ``adjudications``
chain (separate DB, separate chain); tamper-EVIDENT not tamper-PROOF until
the head is anchored off-box (signed anchor = a later, Opus-side cycle —
``tamper_evidence.sign_head`` already exists for it).
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from typing import Any

from .tamper_evidence import GENESIS_HASH
from .tamper_evidence import entry_hash as _entry_hash

__all__ = [
    "MUTATION_ACTIONS",
    "TABLE_SQL",
    "head_conn",
    "record_mutation",
    "require_principal",
    "verify_conn",
]

#: The closed set of auditable destructive actions. ``delete`` is the core
#: default; ``purge``/``forget`` are surface-chosen labels for the same core
#: removal (GDPR chain purge, MCP forget); ``supersede`` retires a fact;
#: ``reset`` is the whole-table clear; ``restore`` is the manual rollback of
#: already-committed supersede hops (supersede_chain failure path) — without
#: it the chain would describe supersessions the DB no longer shows, which an
#: auditor cannot tell apart from state tampering.
MUTATION_ACTIONS = ("delete", "purge", "forget", "supersede", "reset",
                    "restore")

_PRINCIPAL_MAX = 256

TABLE_SQL = """CREATE TABLE IF NOT EXISTS audit_mutations (
    id TEXT PRIMARY KEY,
    ts REAL NOT NULL,
    principal TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '{}',
    outcome TEXT NOT NULL DEFAULT 'ok',
    entry_hash TEXT NOT NULL
)"""


def require_principal(principal: Any) -> str:
    """Validate and return the principal, or raise ``ValueError``.

    MANDATORY at every destructive core entry point: never None, never blank,
    bounded (an unbounded attacker-supplied string would bloat the immutable
    chain — refuse, don't truncate: a truncated identity is an ambiguous one).
    """
    if not isinstance(principal, str) or not principal.strip():
        raise ValueError(
            "principal is mandatory for destructive operations — pass the "
            "acting identity (e.g. 'sdk:local', 'gw:<tenant>', "
            "'system:reconcile'); None/blank is never acceptable")
    if len(principal) > _PRINCIPAL_MAX:
        raise ValueError(
            f"principal exceeds {_PRINCIPAL_MAX} chars — refusing to write "
            "an unbounded identity into the audit chain")
    return principal


def _chain_payload(*, id: str, ts: float, principal: str, action: str,
                   resource_id: str, detail: str, outcome: str) -> dict:
    """The EXACT field set hashed into the chain. ``record_mutation`` (write)
    and ``verify_conn`` (recompute) MUST build this identically — verify reads
    the stored column values verbatim, so record hashes values in their
    to-be-stored form (``detail`` is the already-serialized JSON string, never
    a re-serialized dict — re-serialization drift would false-flag intact
    rows)."""
    return {"id": id, "ts": ts, "principal": principal, "action": action,
            "resource_id": resource_id, "detail": detail, "outcome": outcome}


def record_mutation(conn: sqlite3.Connection, *, principal: str, action: str,
                    resource_id: str, detail: dict[str, Any] | None = None,
                    outcome: str = "ok", ts: float | None = None) -> str:
    """Append one mutation row on the CALLER's connection/transaction.

    Never commits, never swallows: the caller's transaction boundary is the
    atomicity contract (mutation + audit land together or roll back
    together). Call AFTER the mutation's own write statements — see the
    anti-fork note in the module docstring.

    ``detail`` must be small, structured, and PII-free (opaque ids, counts,
    flags). It is serialized canonically here and hashed as the stored
    string.
    """
    require_principal(principal)
    if action not in MUTATION_ACTIONS:
        raise ValueError(
            f"unknown mutation action {action!r} — auditable actions are "
            f"{MUTATION_ACTIONS}")
    rid = uuid.uuid4().hex[:16]
    # float() before hashing: SQLite REAL affinity stores an int ts as a
    # float, so verify() would recompute a float and false-flag intact data.
    ts_val = float(ts) if ts is not None else time.time()
    detail_json = json.dumps(dict(detail or {}), sort_keys=True,
                             separators=(",", ":"), ensure_ascii=True,
                             default=str)
    prev_row = conn.execute(
        "SELECT entry_hash FROM audit_mutations ORDER BY rowid DESC LIMIT 1"
    ).fetchone()
    prev = prev_row[0] if prev_row and prev_row[0] else GENESIS_HASH
    eh = _entry_hash(_chain_payload(
        id=rid, ts=ts_val, principal=principal, action=action,
        resource_id=resource_id, detail=detail_json, outcome=outcome), prev)
    conn.execute(
        "INSERT INTO audit_mutations (id, ts, principal, action, resource_id, "
        "detail, outcome, entry_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (rid, ts_val, principal, action, resource_id, detail_json, outcome,
         eh))
    return rid


def verify_conn(conn: sqlite3.Connection) -> str | None:
    """Recompute the chain in append (rowid) order; return the id of the FIRST
    row whose stored hash does not match — an edit, a broken prev-link from an
    interior deletion, a reorder, or a NULLed hash (demotion tamper). ``None``
    when intact.

    Limits (same honest contract as ``adjudication_log.verify``): TAIL
    truncation and a full re-hash rewrite are invisible to an in-DB check —
    they need the archived/signed head compared off-box.
    """
    prev = GENESIS_HASH
    rows = conn.execute(
        "SELECT id, ts, principal, action, resource_id, detail, outcome, "
        "entry_hash FROM audit_mutations ORDER BY rowid ASC").fetchall()
    for r in rows:
        (rid, ts_val, principal, action, resource_id, detail_json, outcome,
         eh) = r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]
        if eh is None:
            return rid  # this table is born chained: NULL is always tamper
        payload = _chain_payload(
            id=rid, ts=ts_val, principal=principal, action=action,
            resource_id=resource_id, detail=detail_json, outcome=outcome)
        if _entry_hash(payload, prev) != eh:
            return rid
        prev = eh
    return None


def head_conn(conn: sqlite3.Connection) -> str | None:
    """The current chain head (newest row's ``entry_hash``), or ``None`` when
    the chain is empty. Archive it off-box: comparing a later recompute
    against an archived head catches the full-rewrite ``verify_conn`` alone
    cannot see."""
    r = conn.execute(
        "SELECT entry_hash FROM audit_mutations ORDER BY rowid DESC LIMIT 1"
    ).fetchone()
    return r[0] if r else None
