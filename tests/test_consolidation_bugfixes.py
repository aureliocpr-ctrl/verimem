"""Cycle #151 (2026-05-19) — Agent B review bug fixes RED tests.

Cycle 145 ha generato 5 bug review da Agent B su engram/consolidation.py
(cycle 144 orchestrator auto-consolidation). Cycle 149 ha tentato di
applicarli via swarm sonnet ma è stato abortito (sonnet rischio
hallucination su task architetturale). Cycle 151 li applica TDD strict
con verifica empirica diretta, NO swarm.

Bug coperti in questo file (4 dei 5):

  HIGH#1  LIKE wildcard collision in _cluster_already_consolidated
          (riga 179-180): pattern LIKE non escapa ``_`` e ``%`` nel
          prefix → false positive collision.

  MED#3   _select_key_facts dedup-then-truncate collision
          (riga 122-127): dedup su ``head = p[:120]`` invece che su
          ``p`` originale → 2 atomi distinct collassano se prefix
          identico ≥ 120 char.

  MED#4   N+1 connection in _cluster_already_consolidated loop
          (riga 243): chiamata N volte (una per cluster) → N open/close
          conn per ogni run.

  LOW#5   _source_episodes_for_facts ignora dict/scalar JSON
          (riga 207-211): skip ``isinstance(parsed, str)`` → fact legacy
          con ``source_episodes='"ep-id"'`` (JSON scalar string)
          vengono ignorati.

HIGH#2 TOCTOU race (auto_consolidate parallel) NON è coperto qui — è
out of scope per cycle 151 (richiede ``BEGIN IMMEDIATE`` su sm.store
cross-connection oppure UNIQUE migration, design analysis separato).
TODO esplicito.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from verimem import consolidation as cmod
from verimem.consolidation import (
    _cluster_already_consolidated,
    _select_key_facts,
    _source_episodes_for_facts,
    auto_consolidate,
)
from verimem.memory import EpisodicMemory
from verimem.semantic import Fact, SemanticMemory


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sem.db")


@pytest.fixture
def mem(tmp_path: Path) -> EpisodicMemory:
    return EpisodicMemory(db_path=tmp_path / "ep.db")


def _seed_facts(sm: SemanticMemory, topic: str, n: int) -> list[str]:
    ids: list[str] = []
    for i in range(n):
        f = Fact(
            proposition=f"Atom #{i} in {topic}",
            topic=topic,
            confidence=0.7,
            verified_by=[f"test:{topic}:{i}"],
            status="model_claim",
        )
        sm.store(f)
        ids.append(f.id)
    return ids


# ======================================================================
# HIGH#1 — LIKE wildcard collision
# ======================================================================
def test_high1_like_wildcard_no_false_positive_on_underscore(
    sm: SemanticMemory, mem: EpisodicMemory,
) -> None:
    """Pre-fix bug: _cluster_already_consolidated uses ``proposition LIKE
    ?`` with ``{tag} {prefix} %``. SQL LIKE meta-char ``_`` matches any
    single char → ``project/foo_bar`` (pattern) falsely matches a
    pre-existing master for ``project/fooXbar`` (proposition).

    Setup: seed a master fact whose proposition embeds the prefix
    ``project/fooXbar``. Then probe a *different* prefix
    ``project/foo_bar`` that only collides via SQL LIKE underscore.
    Post-fix: the probe must NOT report the cluster as already
    consolidated.
    """
    # First populate a real cluster + run auto_consolidate to produce
    # the master record for "project/fooXbar".
    _seed_facts(sm, "project/fooXbar/area", 6)
    auto_consolidate(sm, mem, min_size=5, dry_run=False)

    # Now probe the LIKE-colliding sibling prefix.
    probed = _cluster_already_consolidated(sm, "project/foo_bar")
    assert probed is False, (
        "HIGH#1: 'project/foo_bar' must NOT be considered already "
        "consolidated when only a 'project/fooXbar' master exists. "
        "LIKE underscore is matching any single char — fix expected to "
        "use topic equality on the master suffix instead of proposition "
        "LIKE."
    )


def test_high1_like_wildcard_no_false_positive_on_percent(
    sm: SemanticMemory, mem: EpisodicMemory,
) -> None:
    """Similar to underscore but for ``%`` LIKE meta-char. Pattern
    ``project/foo%`` would falsely match many masters.
    """
    _seed_facts(sm, "project/foobar/area", 6)
    auto_consolidate(sm, mem, min_size=5, dry_run=False)
    # ``%`` in the probed prefix should not match the foobar master
    # via LIKE wildcard expansion.
    probed = _cluster_already_consolidated(sm, "project/foo%")
    assert probed is False, (
        "HIGH#1: '%' in probed prefix must NOT match an existing master "
        "via SQL LIKE wildcard. Fix expected to drop LIKE on proposition "
        "in favour of topic equality on the master suffix."
    )


# ======================================================================
# MED#3 — _select_key_facts dedup-then-truncate collision
# ======================================================================
def test_med3_select_key_facts_dedup_on_full_not_truncate() -> None:
    """Pre-fix bug: dedup happens on ``head = p[:120]`` instead of on
    the full proposition. Two distinct atomi with identical 120-char
    prefix collapse into one.
    """
    prefix = "X" * 119  # exactly under truncate boundary so suffix counts
    prop_a = prefix + " — verdetto A finale 1"
    prop_b = prefix + " — verdetto B finale 2"
    result = _select_key_facts([prop_a, prop_b], k=3)
    assert len(result) == 2, (
        f"MED#3: two distinct propositions with identical 120-char "
        f"prefix must NOT collapse. Got {len(result)} item(s) instead "
        f"of 2: {result!r}. Fix expected to dedup on the full "
        f"proposition, truncate only on output."
    )


def test_med3_select_key_facts_still_dedups_true_duplicates() -> None:
    """Post-fix must still dedup *real* duplicates (same full prop)."""
    p = "Atom duplicato esatto."
    result = _select_key_facts([p, p, p], k=3)
    assert len(result) == 1, (
        f"MED#3: true duplicates must still dedup, got {result!r}"
    )


# ======================================================================
# MED#4 — N+1 connection in _cluster_already_consolidated loop
# ======================================================================
def test_med4_idempotent_rerun_uses_preload_set_zero_calls(
    sm: SemanticMemory, mem: EpisodicMemory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MED#4 N+1 connection invariant on the **idempotent re-run path**.

    Cycle 155 HIGH#2 TOCTOU lock (2026-05-19) ha aggiunto un re-check
    sotto al lock per chiudere la race tra thread paralleli: per ogni
    cluster NON ancora nel pre-loaded set, ``_cluster_already_consolidated``
    viene chiamato 1 volta nello slow-path. Questo è il prezzo della
    concurrency safety.

    L'invariante MED#4 originale (zero chiamate per common case)
    sopravvive intatto sul **re-run idempotente**: dopo il primo
    ``auto_consolidate`` che popola le master rows, una seconda chiamata
    vede ogni cluster già nel pre-loaded set sul fast-path e skippa.
    Zero slow-path entries, zero ``_cluster_already_consolidated`` calls.

    Questo è il path produzione-hot (cron / SessionStart re-run su
    corpus dove molti cluster sono già consolidati), quindi l'invariante
    resta esattamente dove conta di più.

    Cycle 155 trade-off documentation:
      • Fresh corpus, no concurrency: N calls (slow path) but each is
        one O(1) SELECT — way cheaper than pre-MED#4 bug.
      • Idempotent re-run, no concurrency: 0 calls (THIS test).
      • Concurrent runs: N calls slow-path under
        ``_CONSOLIDATE_LOCK`` — correctness > raw perf.
    """
    # Seed + first run: populate master rows so the second is idempotent.
    for i in range(8):
        _seed_facts(sm, f"project/c{i}/area", 6)
    auto_consolidate(sm, mem, min_size=5, dry_run=False)

    # Second run: every cluster ora è nel pre-loaded set sul fast path.
    # ``_cluster_already_consolidated`` NON deve essere chiamato.
    call_count = [0]
    original = cmod._cluster_already_consolidated

    def counted(*args, **kwargs):  # type: ignore[no-untyped-def]
        call_count[0] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(cmod, "_cluster_already_consolidated", counted)
    auto_consolidate(sm, mem, min_size=5, dry_run=False)

    assert call_count[0] == 0, (
        f"MED#4 idempotent re-run invariant: con tutti 8 cluster già "
        f"consolidati e visibili nel pre-loaded set, "
        f"_cluster_already_consolidated NON deve essere chiamato. Got "
        f"{call_count[0]} calls (slow-path entries despite pre-load "
        f"hit). Cycle 151 MED#4 + cycle 155 HIGH#2 combo broken on "
        f"the common production path."
    )


# ======================================================================
# LOW#5 — _source_episodes_for_facts ignores scalar JSON
# ======================================================================
def test_low5_source_episodes_handles_scalar_string(
    sm: SemanticMemory,
) -> None:
    """Pre-fix bug: only ``isinstance(parsed, list)`` branch is handled.
    Legacy facts with ``source_episodes`` stored as a JSON scalar string
    (e.g. ``'"ep-legacy-123"'``) are silently dropped from the output.

    Fix: add ``elif isinstance(parsed, str) and parsed.strip()`` branch.
    """
    # Build a Fact and then directly mutate its source_episodes column
    # in the DB to the legacy scalar-string shape. Fact dataclass stores
    # list-encoded JSON normally; we bypass to simulate legacy data.
    f = Fact(
        proposition="Legacy fact with scalar source_episodes",
        topic="legacy/cycle151",
        confidence=0.5,
        status="model_claim",
    )
    sm.store(f)
    with sm._connect() as conn:  # noqa: SLF001
        conn.execute(
            "UPDATE facts SET source_episodes = ? WHERE id = ?",
            (json.dumps("ep-legacy-123"), f.id),
        )
        conn.commit()

    out = _source_episodes_for_facts(sm, [f.id])
    assert "ep-legacy-123" in out, (
        f"LOW#5: scalar JSON source_episodes='\"ep-legacy-123\"' must be "
        f"surfaced post-fix, got {out!r}. Fix expected: handle "
        f"isinstance(parsed, str) branch in _source_episodes_for_facts."
    )


def test_low5_source_episodes_still_handles_list(
    sm: SemanticMemory,
) -> None:
    """Post-fix must NOT regress the list branch."""
    f = Fact(
        proposition="Fact with list source_episodes",
        topic="legacy/cycle151",
        confidence=0.5,
        status="model_claim",
    )
    sm.store(f)
    with sm._connect() as conn:  # noqa: SLF001
        conn.execute(
            "UPDATE facts SET source_episodes = ? WHERE id = ?",
            (json.dumps(["ep-a", "ep-b"]), f.id),
        )
        conn.commit()
    out = _source_episodes_for_facts(sm, [f.id])
    assert "ep-a" in out and "ep-b" in out, (
        f"LOW#5 regression: list branch must still work post-fix, "
        f"got {out!r}"
    )


def test_low5_source_episodes_skips_empty_scalar(
    sm: SemanticMemory,
) -> None:
    """Edge case: empty / whitespace-only scalar must NOT pollute the
    output set."""
    f = Fact(
        proposition="Fact with empty scalar",
        topic="legacy/cycle151",
        confidence=0.5,
        status="model_claim",
    )
    sm.store(f)
    with sm._connect() as conn:  # noqa: SLF001
        conn.execute(
            "UPDATE facts SET source_episodes = ? WHERE id = ?",
            (json.dumps("   "), f.id),
        )
        conn.commit()
    out = _source_episodes_for_facts(sm, [f.id])
    # Empty/whitespace scalar must be skipped (no junk in output set).
    assert "   " not in out and "" not in out, (
        f"LOW#5: empty/whitespace scalar must be skipped, got {out!r}"
    )
