"""Cycle 399 — ResonatorMemory CLI falsifiable contracts."""
from __future__ import annotations


def test_cli_remember_recall_roundtrip(tmp_path) -> None:
    """Contract (a): remember + recall recovers same text."""
    from engram.resonator_cli import cmd_recall, cmd_remember
    state = tmp_path / "memory.npz"
    index = tmp_path / "index.jsonl"
    r = cmd_remember("test fact alpha", state, index)
    assert r["ok"] and r["n_facts"] == 1
    out = cmd_recall(state, index)
    texts = [x["text"] for x in out["recovered"]]
    assert "test fact alpha" in texts, out


def test_cli_stats_initial_empty(tmp_path) -> None:
    """Contract: stats on empty state."""
    from engram.resonator_cli import cmd_stats
    state = tmp_path / "memory.npz"
    index = tmp_path / "index.jsonl"
    s = cmd_stats(state, index)
    assert s["n_facts"] == 0
    assert s["n_indexed_texts"] == 0
    assert s["state_exists"] is False


def test_cli_stats_after_remember(tmp_path) -> None:
    """Contract: stats reflects added facts."""
    from engram.resonator_cli import cmd_remember, cmd_stats
    state = tmp_path / "memory.npz"
    index = tmp_path / "index.jsonl"
    cmd_remember("fact 1", state, index)
    cmd_remember("fact 2", state, index)
    s = cmd_stats(state, index)
    assert s["n_facts"] == 2
    assert s["n_indexed_texts"] == 2


def test_cli_persist_roundtrip(tmp_path) -> None:
    """Contract (b): save → reload preserves state."""
    from engram.resonator_cli import cmd_recall, cmd_remember
    state = tmp_path / "memory.npz"
    index = tmp_path / "index.jsonl"
    cmd_remember("persistent fact", state, index)
    # cmd_recall reloads from state_path → must find the fact
    out = cmd_recall(state, index)
    texts = [x["text"] for x in out["recovered"]]
    assert "persistent fact" in texts


def test_cli_reset_wipes_state(tmp_path) -> None:
    """Contract (c): reset removes files."""
    from engram.resonator_cli import cmd_remember, cmd_reset, cmd_stats
    state = tmp_path / "memory.npz"
    index = tmp_path / "index.jsonl"
    cmd_remember("doomed", state, index)
    cmd_reset(state, index)
    s = cmd_stats(state, index)
    assert s["n_facts"] == 0
    assert s["state_exists"] is False
    assert s["index_exists"] is False


def test_cli_recall_distinguishes_known_unknown(tmp_path) -> None:
    """Contract: matching_pursuit may find spurious atoms not in index."""
    from engram.resonator_cli import cmd_recall, cmd_remember
    state = tmp_path / "memory.npz"
    index = tmp_path / "index.jsonl"
    cmd_remember("hello world", state, index)
    out = cmd_recall(state, index)
    # We've added 1 fact; matching_pursuit may find at least 1 recognized
    assert out["n_recovered"] >= 1
    # Sum recovered+unknown == n_passes
    assert out["n_recovered"] + out["n_unknown"] == out["n_passes"]
