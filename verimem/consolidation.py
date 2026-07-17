"""Cycle #144 (2026-05-18 sera) — auto-consolidation orchestrator.

Cycle 151 (2026-05-19) ha applicato 4 dei 5 bug fix dal review Agent B:
  - HIGH#1 LIKE wildcard collision in _cluster_already_consolidated
  - MED#3  dedup-truncate collision in _select_key_facts
  - MED#4  N+1 connection in auto_consolidate loop
          (nuovo helper _preload_consolidated_prefixes)
  - LOW#5  scalar JSON ignored in _source_episodes_for_facts

OUT-OF-SCOPE cycle 151 (TODO design analysis follow-up):
  - HIGH#2 TOCTOU race in auto_consolidate parallel: 2 process
    concorrenti possono entrambi superare il check pre-load e
    persistere 2 master duplicati per lo stesso cluster. Fix
    richiede o ``BEGIN IMMEDIATE`` su sm.store cross-connection
    (non-banale perché sm.store apre la sua connessione interna)
    oppure UNIQUE INDEX condizionale via migration schema.
    Workaround locale: avvolgere auto_consolidate in
    ``threading.Lock`` lato caller per processi singoli.

Aurelio direttiva post-vista frammentazione: 'non dobbiamo frammentare,
dobbiamo concatenare'. Cycle 142+143 ha aperto coding-failure+learning
sides ma il sistema NON sa auto-concatenare i propri fact: ogni cycle
N aggiunge un fact ``project/hippoagent/cycleN-*`` che resta singleton
fra i 25+ sotto-topic dello stesso namespace. Frammentazione monotona
finché un operator/altra sessione fa 1-shot consolidation a mano.

Cycle 144 attacca il root cause con orchestrator AUTO che:
    1. Detecta cluster fact con topic-prefix comune (depth 2) ≥ N
    2. Propone master node draft (proposition + ≤3 key_facts atomi)
    3. Persist master Episode + Fact + ``narrative_link`` causal_edges
       verso i source_episodes dei sub-fact del cluster
    4. Idempotency: re-run salta cluster già consolidati (check fact
       con stesso proposition prefix)

NOT a replacement for the existing hippo_dream_* pipeline — that runs
LLM-driven REM-style consolidation across a shadow DB. This is the
cheap deterministic auto-link that closes the frammentazione gap
WITHOUT calling the LLM, runnable in a cron / SessionStart hook.

API (cycle 144 MVP):
    detect_cluster_candidates(sm, *, min_size=5, prefix_depth=2)
        → list[{topic_prefix, fact_ids, fact_count}]

    propose_master_node(sm, cluster) → {proposition, topic, key_facts}

    auto_consolidate(sm, mem, *, min_size=5, prefix_depth=2,
                     dry_run=False)
        → {clusters_detected, masters_proposed, masters_persisted,
           edges_created, duration_ms}
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import TYPE_CHECKING

from .episode import Episode
from .semantic import Fact

if TYPE_CHECKING:
    from .memory import EpisodicMemory
    from .semantic import SemanticMemory


# Tag baked into the master fact proposition + topic so re-runs can
# identify already-consolidated clusters and skip them (idempotency).
_AUTO_MASTER_TAG = "AUTO-CLUSTER-MASTER"
_AUTO_MASTER_TOPIC_SUFFIX = "auto-MASTER"

# Cycle 155 HIGH#2 TOCTOU race fix: module-level lock that serializes
# the per-cluster ``_persist_master`` block inside ``auto_consolidate``.
# Two threads in the same process can no longer both pass the
# ``consolidated_prefixes`` membership check and both store a duplicate
# master. Cross-process protection still requires either a SQLite
# UNIQUE INDEX migration (schema-level) or BEGIN IMMEDIATE on the
# write transaction (not landed in cycle 155 — design follow-up).
#
# Cycle 153 honeycomb deliverable, action #3, sequence B post cycle 154
# refactor (``_persist_master`` is the natural seam for atomic block).
_CONSOLIDATE_LOCK = threading.Lock()


# ======================================================================
# Cluster detection
# ======================================================================
def _topic_prefix(topic: str, depth: int) -> str:
    """Return the first ``depth`` slash-separated segments of ``topic``.

    ``project/foo/sub-a`` at depth=2 → ``project/foo``.
    Empty / shallower topics return as-is.
    """
    if not topic:
        return ""
    parts = topic.split("/")
    return "/".join(parts[:depth])


def detect_cluster_candidates(
    sm: SemanticMemory, *, min_size: int = 5, prefix_depth: int = 2,
) -> list[dict]:
    """Group live facts by ``prefix_depth`` of their topic, return clusters
    that contain at least ``min_size`` facts.

    Skips:
      • facts whose topic is empty/None (can't cluster without a prefix)
      • facts that are themselves auto-master markers (idempotency)

    Returns a list of dicts, one per cluster, sorted by descending
    fact_count so the largest clusters get consolidated first.
    """
    with sm._connect() as conn:  # noqa: SLF001 — internal probe
        rows = conn.execute(
            "SELECT id, topic, proposition FROM facts "
            "WHERE superseded_by IS NULL AND topic <> '' AND topic IS NOT NULL "
            "AND proposition NOT LIKE ?",
            (f"{_AUTO_MASTER_TAG}%",),
        ).fetchall()
    bucket: dict[str, list[str]] = {}
    for r in rows:
        prefix = _topic_prefix(r["topic"], prefix_depth)
        if not prefix:
            continue
        bucket.setdefault(prefix, []).append(r["id"])
    clusters: list[dict] = [
        {
            "topic_prefix": prefix,
            "fact_ids": fact_ids,
            "fact_count": len(fact_ids),
        }
        for prefix, fact_ids in bucket.items()
        if len(fact_ids) >= min_size
    ]
    clusters.sort(key=lambda c: c["fact_count"], reverse=True)
    return clusters


# ======================================================================
# Master node proposal
# ======================================================================
def _select_key_facts(propositions: list[str], k: int = 3) -> list[str]:
    """Pick up to ``k`` representative propositions from the cluster.

    Heuristic (no LLM): sort by length descending so the longest, most
    information-dense atomi rise to the top, then truncate to k. A
    proposition that mentions a date/version/SHA is empirically longer
    than a one-liner stub. Cheap and stable across runs.

    Cycle 151 MED#3 fix: dedup su ``p`` originale (full proposition),
    NON su ``p[:120]``. Pre-fix due atomi distinti con primi 120 char
    identici collassavano nello stesso ``head`` e venivano fusi nel
    set. Truncate avviene SOLO all'output, dopo il check di dedup.
    """
    if not propositions:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for p in sorted(propositions, key=len, reverse=True):
        if p in seen:
            continue
        seen.add(p)
        out.append(p[:120])  # truncate only kept, dedup on full p
        if len(out) >= k:
            break
    return out


def propose_master_node(
    sm: SemanticMemory, cluster: dict,
) -> dict:
    """Draft a master Fact for one cluster.

    Returns ``{proposition, topic, key_facts}``. The caller (or
    ``auto_consolidate``) decides whether to persist.
    """
    prefix = cluster["topic_prefix"]
    fact_ids = cluster["fact_ids"]
    with sm._connect() as conn:  # noqa: SLF001
        rows = conn.execute(
            "SELECT proposition FROM facts WHERE id IN ("
            + ",".join(["?"] * len(fact_ids)) + ")",
            tuple(fact_ids),
        ).fetchall()
    props = [r["proposition"] or "" for r in rows]
    key_facts = _select_key_facts(props, k=3)

    proposition = (
        f"{_AUTO_MASTER_TAG} {prefix} — auto-consolidated entry point "
        f"organizing {len(fact_ids)} sub-facts under this prefix. "
        f"Top representative atomi: "
        f"{' | '.join(p[:60] for p in key_facts)}"
    )
    topic = f"{prefix}/{_AUTO_MASTER_TOPIC_SUFFIX}"
    return {
        "proposition": proposition,
        "topic": topic,
        "key_facts": key_facts,
    }


# ======================================================================
# Orchestrator
# ======================================================================
def _cluster_already_consolidated(
    sm: SemanticMemory, prefix: str,
) -> bool:
    """Idempotency probe: an AUTO-CLUSTER-MASTER fact already exists for
    this prefix.

    Cycle 151 HIGH#1 fix: switched from ``proposition LIKE ?`` (unsafe
    because SQL LIKE meta-chars ``_`` and ``%`` in the prefix would
    cause false positives) to topic equality on the canonical master
    suffix ``<prefix>/{_AUTO_MASTER_TOPIC_SUFFIX}``. Same semantics,
    no meta-char collision, also benefits from the topic index.

    NOTE: this single-call probe is preserved for callers and tests.
    ``auto_consolidate`` itself uses a pre-loaded set to avoid the
    N+1 connection pattern (cycle 151 MED#4 fix).
    """
    expected_topic = f"{prefix}/{_AUTO_MASTER_TOPIC_SUFFIX}"
    with sm._connect() as conn:  # noqa: SLF001
        row = conn.execute(
            "SELECT 1 FROM facts "
            "WHERE topic = ? AND superseded_by IS NULL LIMIT 1",
            (expected_topic,),
        ).fetchone()
    return row is not None


def _preload_consolidated_prefixes(sm: SemanticMemory) -> set[str]:
    """Cycle 151 MED#4 fix: ONE SQL select to pull every already-
    consolidated topic, derive the originating prefix, return as a set
    for O(1) lookup. Replaces the N×_cluster_already_consolidated calls
    inside auto_consolidate (each opening a fresh connection with a
    10s busy timeout).

    A topic ``X/Y/auto-MASTER`` was created by the orchestrator for
    cluster prefix ``X/Y``, so we strip the suffix to recover the
    prefix.
    """
    suffix = f"/{_AUTO_MASTER_TOPIC_SUFFIX}"
    with sm._connect() as conn:  # noqa: SLF001
        rows = conn.execute(
            "SELECT topic FROM facts "
            "WHERE topic LIKE ? AND superseded_by IS NULL",
            (f"%{suffix}",),
        ).fetchall()
    out: set[str] = set()
    for r in rows:
        t = r["topic"] or ""
        if t.endswith(suffix):
            out.add(t[: -len(suffix)])
    return out


def _source_episodes_for_facts(
    sm: SemanticMemory, fact_ids: list[str],
) -> list[str]:
    """Collect all ``source_episodes`` from the given facts.

    Cycle 159.8 fix (opus single bug hunt, 2026-05-19): the previous
    implementation called ``json.loads(raw)`` on the column value, but
    ``SemanticMemory.store`` writes ``source_episodes`` as a *comma-
    separated string* (see ``semantic.py:466`` — ``",".join(fact.
    source_episodes)``), and the read path mirrors that at
    ``semantic.py:1345`` via ``.split(",")``. ``json.loads`` on
    ``"ep_a,ep_b"`` raises ``JSONDecodeError``, the bare ``except`` ate
    it, and ``out`` was always empty — silently breaking the very
    feature this orchestrator advertises in its module docstring
    (``narrative_link`` causal edges from the master to every source
    episode of the cluster's sub-facts). The result was that
    ``auto_consolidate`` always fell into the ``if not source_eps:``
    fallback at line 278 and wrote a single self-edge per master,
    instead of the documented one-edge-per-source.

    Empty ``fact_ids`` is also handled defensively here so a direct
    caller doesn't trigger an ``IN ()`` SQL error — the orchestrator
    filters by ``min_size`` upstream, but this function is part of the
    module's public surface.
    """
    if not fact_ids:
        return []
    with sm._connect() as conn:  # noqa: SLF001
        rows = conn.execute(
            "SELECT source_episodes FROM facts WHERE id IN ("
            + ",".join(["?"] * len(fact_ids)) + ")",
            tuple(fact_ids),
        ).fetchall()
    out: set[str] = set()
    for r in rows:
        # Cycle 167 fix (2026-05-19): reconcile cycle 151 LOW#5 (JSON-
        # encoded list / scalar legacy data) with cycle 159.8 (comma-
        # separated current storage). Try JSON first to recover legacy
        # rows; fall back to comma-split for the current ``store`` path.
        #
        #   raw stored as ``'["ep_a", "ep_b"]'``  (legacy JSON list)   → parse
        #   raw stored as ``'"ep-legacy-123"'``   (legacy JSON scalar) → parse
        #   raw stored as ``'ep_a,ep_b'``         (cycle 159.8 default)→ split
        raw = r["source_episodes"] or ""
        if not raw:
            continue
        parsed: object | None = None
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            parsed = None
        if isinstance(parsed, list):
            for x in parsed:
                if isinstance(x, str) and x.strip():
                    out.add(x.strip())
        elif isinstance(parsed, str) and parsed.strip():
            out.add(parsed.strip())
        else:
            # Fallback: comma-separated string (cycle 159.8 storage path).
            for x in raw.split(","):
                x = x.strip()
                if x:
                    out.add(x)
    return list(out)


def auto_consolidate(
    sm: SemanticMemory,
    mem: EpisodicMemory,
    *,
    min_size: int = 5,
    prefix_depth: int = 2,
    dry_run: bool = False,
) -> dict:
    """End-to-end auto-consolidation pass.

    For each detected cluster not yet consolidated, persist:
      • one master Episode (task_id=topic, outcome='success')
      • one master Fact (proposition + verified_by=cluster fact_ids)
      • one ``narrative_link`` causal_edge from the master Episode to
        every source-episode of the cluster's sub-facts (so
        ``hippo_lineage_trace forward`` from the master walks the
        cluster in one hop)

    Returns aggregate stats.
    """
    t0 = time.perf_counter()
    clusters = detect_cluster_candidates(
        sm, min_size=min_size, prefix_depth=prefix_depth,
    )
    masters_proposed = 0
    masters_persisted = 0
    edges_created = 0

    # Cycle 151 MED#4 fix: pre-load the set of already-consolidated
    # cluster prefixes with ONE SELECT, then O(1) lookup per cluster.
    consolidated_prefixes = _preload_consolidated_prefixes(sm)

    for cluster in clusters:
        # Cycle 155 HIGH#2 TOCTOU double-checked locking pattern:
        #
        # Fast path (no lock): if the pre-loaded set already contains
        # the prefix, skip — cheap MED#4 idempotency probe, no SQL.
        #
        # Slow path (under lock): re-verify via fresh SQL query because
        # the local pre-loaded set is thread-local and stale w.r.t. a
        # parallel thread that may have just persisted a duplicate
        # master. The lock + fresh re-check is what closes the TOCTOU
        # window.
        if cluster["topic_prefix"] in consolidated_prefixes:
            continue
        with _CONSOLIDATE_LOCK:
            # Re-check fresh from DB (covers parallel-thread races
            # the local set cannot see).
            if _cluster_already_consolidated(sm, cluster["topic_prefix"]):
                consolidated_prefixes.add(cluster["topic_prefix"])
                continue

            master = propose_master_node(sm, cluster)
            masters_proposed += 1
            if dry_run:
                continue

            # Cycle 154 refactor: extract _persist_master + _wire_edges so
            # auto_consolidate stays at the orchestration level. The
            # per-cluster atomic block (Episode store + Fact store + edge
            # wiring) is now a single function call.
            # Cycle 156 §5.2 race-losing semantics: the _CONSOLIDATE_LOCK +
            # re-check above closes the INTRA-process TOCTOU, but two separate
            # PROCESSES share no lock. Both can pass the membership check and
            # reach _persist_master; the partial UNIQUE INDEX
            # idx_facts_auto_master_unique then rejects the second writer with
            # sqlite3.IntegrityError. That is the designed graceful outcome —
            # we lost the race, the invariant (<=1 live master/topic) holds.
            # Skip without counting a persist (no stats confabulation).
            try:
                _ep_id, _fact_id, edges_n = _persist_master(
                    sm, mem, cluster, master,
                )
            except sqlite3.IntegrityError:
                consolidated_prefixes.add(cluster["topic_prefix"])
                continue
            masters_persisted += 1
            edges_created += edges_n
            # Update the in-process pre-loaded set so the *next* cluster
            # iteration sees this prefix as consolidated without re-
            # querying SQLite (other threads will see it via the SQL
            # re-check above on their next slow-path entry).
            consolidated_prefixes.add(cluster["topic_prefix"])

    return {
        "clusters_detected": len(clusters),
        "masters_proposed": masters_proposed,
        "masters_persisted": masters_persisted,
        "edges_created": edges_created,
        "duration_ms": (time.perf_counter() - t0) * 1000.0,
    }


# ======================================================================
# Cycle 154 (2026-05-19) — auto_consolidate God Function refactor.
#
# Cycle 153 honeycomb mesh review (6 sonnet teammates) ha identificato
# auto_consolidate come God Function con cyclomatic complexity ~9,
# consenso 5/6 angoli (architect / maintainability / performance / ux /
# security). Le 3 responsabilità inline (persistence Episode, persistence
# Fact, wire edges) erano impossibili da unit-testare in isolamento.
#
# Estratti due helper private dedicati. ``_persist_master`` è il
# candidato naturale per il futuro lock atomico HIGH#2 TOCTOU (cycle 155).
# ======================================================================
def _persist_master(
    sm: SemanticMemory,
    mem: EpisodicMemory,
    cluster: dict,
    master: dict,
) -> tuple[str, str, int]:
    """Persist one cluster's master node (guarded Fact first, then Episode).

    Steps:
      1. Build a master Episode (task_id=topic, outcome='success'). Its id
         is generated at construction, so it can be referenced before store.
      2. Build + store a master Fact whose ``source_episodes`` points at the
         (not-yet-stored) Episode id and whose ``verified_by`` points at the
         cluster sub-fact ids. This store is FIRST and is the abort point.
      3. Store the Episode, then wire ``narrative_link`` causal edges from it
         to every source-episode of the cluster sub-facts (via
         :func:`_wire_edges`).

    Returns ``(ep_id, fact_id, edges_created)``. The triplet is what
    callers need to log progress, build linkage graphs, or attribute
    the operation to a transaction id in higher-level orchestration.

    Audit#2 (2026-06-08, A-6): the master Fact carries a UNIQUE index
    (``idx_facts_auto_master_unique``) — under concurrent auto-consolidate
    exactly one writer wins; the losers' ``sm.store(f)`` raises
    ``IntegrityError`` (caught upstream). Storing the Episode BEFORE that
    guarded Fact left an ORPHAN Episode behind on every lost race (no master
    fact references it), accumulating under parallel consolidation. Fact-first
    means a lost race aborts before any Episode is written. ``source_episodes``
    is a soft cross-DB id list (not an FK) so a fact pointing at an Episode
    that a later rare I/O error failed to store degrades gracefully on recall
    — strictly better than the high-frequency orphan-episode leak.

    NOT a hard cross-DB transaction: the two stores hit two SQLite files, so
    true atomicity would still need a ``threading.Lock()`` / ``BEGIN
    IMMEDIATE`` seam (HIGH#2 TOCTOU, cycle 155). The reorder removes the
    orphan-episode failure mode; it does not make the pair atomic.
    """
    ep = Episode(
        task_id=master["topic"],
        task_text=(
            f"Auto-consolidation pass cycle 144 for cluster "
            f"{cluster['topic_prefix']} ({cluster['fact_count']} facts)"
        ),
        final_answer=master["proposition"],
        outcome="success",
        created_at=time.time(),
    )
    # ep.id is assigned at construction (a fresh uuid), so the Fact can
    # reference it before the Episode is stored — letting the unique-index
    # guard on the Fact abort a lost race with no Episode side effect.
    f = Fact(
        proposition=master["proposition"],
        topic=master["topic"],
        confidence=0.85,  # high-trust: deterministic auto from real facts
        source_episodes=[ep.id],
        verified_by=[f"fact:{fid}" for fid in cluster["fact_ids"]],
        status="model_claim",
    )
    sm.store(f)  # FIRST: lost unique-index race raises here -> no orphan episode
    mem.store(ep)

    edges_n = _wire_edges(sm, mem, ep.id, cluster["fact_ids"])
    return ep.id, f.id, edges_n


def _wire_edges(
    sm: SemanticMemory,
    mem: EpisodicMemory,
    ep_id: str,
    fact_ids: list[str],
) -> int:
    """Insert ``narrative_link`` causal_edges from ``ep_id`` to every
    source-episode of ``fact_ids``. Returns the count of edges inserted.

    Cycle 170 fix (2026-05-19, ROADMAP §5b bug #1 from team Arm-D in
    cycle 159.8): the previous implementation fell back to
    ``source_eps = [ep_id]`` when ``_source_episodes_for_facts``
    returned empty, producing a self-edge ``(ep_id, ep_id,
    narrative_link, 1.0)`` per cluster. A self-edge in a causal graph
    is semantically degenerate ("this episode caused itself") and
    pollutes ``hippo_lineage_trace``. The master Episode is *already*
    reachable from the lineage walker via ``facts.source_episodes``
    on the master Fact (see ``_persist_master`` line 456, which writes
    ``source_episodes=[ep.id]`` on the master), so the fallback edge
    added zero retrieval value while adding graph noise.

    Post-fix: if there are no source episodes to link to, we simply
    write nothing. The master remains reachable via the fact↔episode
    relation that the cycle #52 unified-graph walker already crosses.
    """
    source_eps = _source_episodes_for_facts(sm, fact_ids)
    if not source_eps:
        return 0
    edges_n = 0
    with mem._connect() as conn:  # noqa: SLF001
        for dst in source_eps:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO causal_edges "
                    "(src_episode_id, dst_episode_id, via_skill_id, weight) "
                    "VALUES (?, ?, ?, ?)",
                    (ep_id, dst, "narrative_link", 1.0),
                )
                edges_n += 1
            except Exception:  # noqa: BLE001 — never crash on edge insert
                continue
    return edges_n
