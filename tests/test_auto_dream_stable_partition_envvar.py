"""Cycle 285 (2026-05-23) — TDD contract for ENGRAM_USE_STABLE_PARTITION
env var routing in auto_dream_worker.

Cycle 284 wired stable_partition into _persist_emergence_drafts +
_propose_via_engram via an opt-in env var. This contract verifies:

1. With env unset/0: enable_stable_partition reaches the helper as False.
2. With env=1: enable_stable_partition reaches the helper as True.
3. With env=invalid (e.g. 'banana'): treated as False (defensive).

The test patches `_persist_emergence_drafts` to capture its kwargs and
drives `_propose_via_engram` with a minimal engram_dir.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from verimem import auto_dream_worker as adw

_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    proposition TEXT NOT NULL DEFAULT '',
    topic TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 0.5,
    source_episodes TEXT NOT NULL DEFAULT '[]',
    created_at REAL NOT NULL DEFAULT 0.0,
    embedding BLOB NOT NULL DEFAULT '',
    verified_by TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'model_claim',
    lineage_to TEXT,
    superseded_by TEXT
);
CREATE TABLE IF NOT EXISTS causal_edges (src TEXT, dst TEXT, weight REAL);
"""


def _bootstrap_engram_dir(tmp_path: Path) -> Path:
    engram_dir = tmp_path / "engram"
    (engram_dir / "semantic").mkdir(parents=True)
    (engram_dir / "skills").mkdir()
    (engram_dir / "episodes").mkdir()
    db = engram_dir / "semantic" / "semantic.db"
    conn = sqlite3.connect(str(db))
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()
    # skills_index.db schema (minimal stub for build_thompson_seed +
    # build_stuck_retry_seed graceful fallback to "" suffix).
    skills_db = engram_dir / "skills" / "skills_index.db"
    conn = sqlite3.connect(str(skills_db))
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS skills (id TEXT PRIMARY KEY, "
            "name TEXT, fitness REAL, trials INTEGER, "
            "successes INTEGER, status TEXT)"
        )
        conn.commit()
    finally:
        conn.close()
    return engram_dir


def _seed_non_empty_facts(engram_dir: Path) -> None:
    """Cycle 290: seed semantic.db with synthetic facts + causal_edges so
    the 2nd call site detect_emerging_skills(...) at auto_dream_worker
    line ~246 is forced to execute (not short-circuited by empty corpus).

    Forces detect_communities to find at least one community, which in
    turn triggers the inner register_emerging_drafts_as_facts branch
    that invokes detect_emerging_skills.
    """
    import numpy as np

    db = engram_dir / "semantic" / "semantic.db"
    conn = sqlite3.connect(str(db))
    try:
        rng = np.random.default_rng(7)
        # Seed 8 facts in a single tight cluster (high embedding cohesion)
        # plus dense lineage chain to ensure Louvain finds the community.
        for i in range(8):
            base = np.zeros(384, dtype=np.float32)
            base[0] = 1.0
            emb = base + 0.05 * rng.standard_normal(384).astype(np.float32)
            parent = f"f_{i-1}" if i > 0 else None
            conn.execute(
                "INSERT INTO facts (id, proposition, topic, embedding, "
                "lineage_to) VALUES (?, ?, ?, ?, ?)",
                (
                    f"f_{i}",
                    f"fact {i} tight cluster",
                    "project/test/cluster",
                    emb.tobytes(),
                    parent,
                ),
            )
            # Dense causal edges for connectivity
            for j in range(i):
                conn.execute(
                    "INSERT INTO causal_edges (src, dst, weight) "
                    "VALUES (?, ?, ?)",
                    (f"f_{i}", f"f_{j}", 1.0),
                )
        conn.commit()
    finally:
        conn.close()


@pytest.mark.parametrize(
    "env_value,expected_flag",
    [
        (None, False),  # unset
        ("", False),  # empty
        ("0", False),
        ("false", False),
        ("banana", False),  # invalid string treated as False
        ("1", True),
        ("true", True),
        ("True", True),
        ("YES", True),
        ("on", True),
    ],
)
def test_env_var_routes_correctly(
    tmp_path: Path, env_value: str | None, expected_flag: bool,
) -> None:
    engram_dir = _bootstrap_engram_dir(tmp_path)
    captured: dict[str, object] = {}

    def fake_persist(**kwargs):
        captured.update(kwargs)
        return {"n_written": 0, "batch_dir": "", "skipped": 0}

    # Patch the helper to capture invocation kwargs without touching disk.
    with patch.object(
        adw, "_persist_emergence_drafts", side_effect=fake_persist,
    ):
        env = dict(os.environ)
        if env_value is None:
            env.pop("ENGRAM_USE_STABLE_PARTITION", None)
        else:
            env["ENGRAM_USE_STABLE_PARTITION"] = env_value
        with patch.dict(os.environ, env, clear=True):
            try:
                adw._propose_via_engram(engram_dir=engram_dir)
            except Exception:  # noqa: BLE001
                pass  # downstream propose_dream_tasks may fail; we
                # only assert on captured kwargs.

    assert captured, "_persist_emergence_drafts was not invoked"
    assert captured.get("enable_stable_partition") == expected_flag, (
        f"env={env_value!r} -> got "
        f"enable_stable_partition={captured.get('enable_stable_partition')}, "
        f"expected {expected_flag}"
    )


@pytest.mark.parametrize(
    "env_value,expected_flag",
    [
        (None, False),
        ("0", False),
        ("1", True),
        ("on", True),
    ],
)
def test_env_var_routes_to_detect_emerging_skills_call_site(
    tmp_path: Path, env_value: str | None, expected_flag: bool,
) -> None:
    """M13 SECOND-CALL-SITE COVERAGE (cycle 289 from cycle 287 counterexample).

    cycle 287 critic counterexample worker flagged that the cycle 285 test
    only patches _persist_emergence_drafts. The second call site
    detect_emerging_skills(...,enable_stable_partition=_use_stable) at
    line 246 of auto_dream_worker.py is not pinned by the original test.

    This contract patches the lazy-imported detect_emerging_skills to
    capture kwargs at the second call site and asserts identical routing.
    """
    engram_dir = _bootstrap_engram_dir(tmp_path)
    captured_second: dict[str, object] = {}

    def fake_detect(*args, **kwargs):
        # Capture ONLY the second-call-site invocation (the first
        # happens inside _persist_emergence_drafts, but we stub that
        # to a no-op first so detect_emerging_skills is only invoked
        # from the second call site).
        captured_second.update(kwargs)
        return []

    def fake_persist(**kwargs):
        return {"n_written": 0, "batch_dir": "", "skipped": 0}

    with patch.object(
        adw, "_persist_emergence_drafts", side_effect=fake_persist,
    ), patch(
        "verimem.skill_emergence_detector.detect_emerging_skills",
        side_effect=fake_detect,
    ):
        env = dict(os.environ)
        if env_value is None:
            env.pop("ENGRAM_USE_STABLE_PARTITION", None)
        else:
            env["ENGRAM_USE_STABLE_PARTITION"] = env_value
        with patch.dict(os.environ, env, clear=True):
            try:
                adw._propose_via_engram(engram_dir=engram_dir)
            except Exception:  # noqa: BLE001
                pass

    # AUDIT 2026-06-02 (NONNA): assert UNCONDIZIONATO. Prima 'if captured_second'
    # rendeva il test vacuo quando il 2o call-site non veniva raggiunto (passava
    # senza verificare nulla). Ora: se NON e' raggiunto il test FALLISCE
    # (rivelando il limite), se e' raggiunto verifica il routing del flag.
    assert captured_second, (
        f"env={env_value!r}: il 2o call-site detect_emerging_skills NON e' stato "
        "raggiunto -> niente da verificare (prima era un pass vacuo)")
    assert captured_second.get("enable_stable_partition") == expected_flag, (
        f"env={env_value!r} 2nd call site -> got enable_stable_partition="
        f"{captured_second.get('enable_stable_partition')}, expected {expected_flag}"
    )


@pytest.mark.parametrize(
    "env_value,expected_flag",
    [
        ("0", False),
        ("1", True),
    ],
)
def test_env_var_routes_to_2nd_call_site_non_empty_corpus(
    tmp_path: Path, env_value: str, expected_flag: bool,
) -> None:
    """Cycle 290: closes the cycle 289 vacuous-satisfaction caveat.

    Uses a non-empty engram_dir (8 facts + dense causal edges, single
    cluster) so detect_communities finds at least one community and
    the inner register_emerging_drafts_as_facts branch is forced to
    invoke detect_emerging_skills at the 2nd call site.

    Asserts captured_second is NON-EMPTY (i.e. the 2nd call site WAS
    reached) AND routes the correct enable_stable_partition value.
    """
    engram_dir = _bootstrap_engram_dir(tmp_path)
    _seed_non_empty_facts(engram_dir)
    captured_second: dict[str, object] = {}

    def fake_detect(*args, **kwargs):
        captured_second.update(kwargs)
        return []

    def fake_persist(**kwargs):
        return {"n_written": 0, "batch_dir": "", "skipped": 0}

    with patch.object(
        adw, "_persist_emergence_drafts", side_effect=fake_persist,
    ), patch(
        "verimem.skill_emergence_detector.detect_emerging_skills",
        side_effect=fake_detect,
    ):
        env = dict(os.environ)
        env["ENGRAM_USE_STABLE_PARTITION"] = env_value
        with patch.dict(os.environ, env, clear=True):
            try:
                adw._propose_via_engram(engram_dir=engram_dir)
            except Exception:  # noqa: BLE001
                pass

    # NON-VACUOUS assertion: 2nd call site MUST have been invoked.
    assert captured_second, (
        f"env={env_value!r}: 2nd call site (detect_emerging_skills) "
        f"was NOT invoked. The non-empty corpus fixture failed to "
        f"force full path execution — fixture seed needs revision."
    )
    assert (
        captured_second.get("enable_stable_partition") == expected_flag
    ), (
        f"env={env_value!r} 2nd call site -> "
        f"got enable_stable_partition="
        f"{captured_second.get('enable_stable_partition')}, "
        f"expected {expected_flag}"
    )
