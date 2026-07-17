"""Cycle #67 — Self-model layer (continuity, not retrieval).

The self_model is a single-row, replace-only, versioned record that
captures the *current* state of the Aurelio+Claude collaboration:
goals, open decisions, active projects, collab style, recent focus.

Unlike a fact:
  - Single row (no duplication, no ranking).
  - Replace-only (each update creates a new version, old kept in audit).
  - Always-injected (read at SessionStart, not retrieved by cosine).
  - Bounded size (default 4 KB) to never saturate the host LLM context.

These tests cover pure logic + storage round-trip. Pure SQLite, no
MCP, no encoder. Idempotent across runs (uses a tmp DB).
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import pytest

from verimem.self_model import (
    DEFAULT_MAX_BYTES,
    SelfModelStore,
    SelfModelTooLarge,
    render_for_injection,
)


@pytest.fixture()
def store(tmp_path: Path) -> SelfModelStore:
    db = tmp_path / "self_model.db"
    return SelfModelStore(db_path=db)


def test_get_returns_none_when_empty(store: SelfModelStore):
    """Fresh store has no model; get must return None, not raise."""
    assert store.get() is None


def test_update_then_get_round_trip(store: SelfModelStore):
    content = {
        "current_goals": ["close cycle #67"],
        "active_projects": ["HippoAgent"],
        "collab_style": "italian, brevity, CEO mode",
        "recent_focus": "self_model layer",
        "notes": "",
    }
    record = store.update(content)
    assert record["version"] == 1
    assert record["content"] == content
    assert record["updated_at"] > 0

    got = store.get()
    assert got is not None
    assert got["version"] == 1
    assert got["content"] == content


def test_update_increments_version(store: SelfModelStore):
    store.update({"recent_focus": "v1"})
    store.update({"recent_focus": "v2"})
    got = store.get()
    assert got["version"] == 2
    assert got["content"]["recent_focus"] == "v2"


def test_audit_log_keeps_previous_versions(store: SelfModelStore):
    """update() must move the previous record into the audit table."""
    store.update({"recent_focus": "v1"})
    store.update({"recent_focus": "v2"})
    store.update({"recent_focus": "v3"})
    history = store.history()
    assert len(history) == 3
    assert [h["version"] for h in history] == [1, 2, 3]
    assert history[-1]["content"]["recent_focus"] == "v3"


def test_size_limit_rejects_oversized_content(store: SelfModelStore):
    """Updates that exceed max_bytes after JSON serialisation must raise.
    This protects the host LLM context from accidental saturation."""
    huge = {"notes": "x" * (DEFAULT_MAX_BYTES + 100)}
    with pytest.raises(SelfModelTooLarge):
        store.update(huge)


def test_size_limit_accepts_at_boundary(store: SelfModelStore):
    """A record exactly at the byte limit must succeed."""
    # Pad to ~3500 bytes (well within 4096 budget) to test happy path.
    content = {"notes": "y" * 3500}
    record = store.update(content)
    assert record["version"] == 1


def test_get_uses_latest_only(store: SelfModelStore):
    """get() always returns the latest version, never an intermediate."""
    store.update({"recent_focus": "old"})
    store.update({"recent_focus": "new"})
    got = store.get()
    assert got["content"]["recent_focus"] == "new"


def test_render_for_injection_produces_compact_text(store: SelfModelStore):
    """The render helper must produce a human-readable summary suitable
    for SessionStart context injection. Compact, ≤500 chars typical."""
    store.update({
        "current_goals": ["close cycle #67", "validate self_model"],
        "open_decisions": ["auto-trigger in cycle #68?"],
        "active_projects": ["HippoAgent", "Nexus"],
        "collab_style": "italian, brevity, CEO mode",
        "recent_focus": "self_model layer",
    })
    record = store.get()
    text = render_for_injection(record)
    assert "self_model" in text or "Self model" in text or "SELF" in text.upper()
    assert "cycle #67" in text
    assert "HippoAgent" in text
    # Compact enough not to dominate the SessionStart payload
    assert len(text) < 1200


def test_render_when_none_returns_empty_string():
    """If no self_model exists yet, render returns "" (no injection)."""
    assert render_for_injection(None) == ""


def test_concurrent_updates_serialise_safely(tmp_path: Path):
    """Two stores against the same DB file must not corrupt the table."""
    db = tmp_path / "shared.db"
    s1 = SelfModelStore(db_path=db)
    s2 = SelfModelStore(db_path=db)
    s1.update({"recent_focus": "from-s1"})
    s2.update({"recent_focus": "from-s2"})
    # Both writes succeed; final version is 2 (audit keeps both)
    history = s1.history()
    assert len(history) == 2
    assert history[-1]["content"]["recent_focus"] == "from-s2"


def test_update_records_audit_actor(store: SelfModelStore):
    """update() accepts an optional `actor` field for audit purposes."""
    store.update({"recent_focus": "v1"}, actor="claude")
    store.update({"recent_focus": "v2"}, actor="aurelio")
    history = store.history()
    assert history[0]["actor"] == "claude"
    assert history[1]["actor"] == "aurelio"
