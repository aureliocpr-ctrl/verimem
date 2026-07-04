"""WF1 spine: auto_dream_worker.run_maintenance activates LLM-free self-maintenance, safely."""
from pathlib import Path
import json
import pytest
from engram.auto_dream_worker import run_maintenance
from engram.semantic import Fact, SemanticMemory
from engram.memory import EpisodicMemory


def _fresh(tmp_path):
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    for i in range(8):
        sm.store(Fact(proposition=f"alpha project note number {i} about retrieval",
                      topic=f"project/x/sub{i % 3}", source_episodes=[f"e{i}"]))
    return sm, EpisodicMemory(db_path=tmp_path / "ep.db")


def test_runs_steps_and_writes_marker(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_AUTO_CONSOLIDATE", raising=False)
    sm, mem = _fresh(tmp_path)
    out = run_maintenance(tmp_path, now=1_000_000.0, sm=sm, mem=mem)
    assert out["ran"] is True
    assert "consolidate" in out and "scan" in out          # steps executed
    assert (tmp_path / "consolidate_last.json").exists()    # marker written


def test_cooldown_blocks_second_run(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_AUTO_CONSOLIDATE", raising=False)
    sm, mem = _fresh(tmp_path)
    run_maintenance(tmp_path, now=1_000_000.0, sm=sm, mem=mem)
    out2 = run_maintenance(tmp_path, now=1_000_050.0, sm=sm, mem=mem)  # 50s later < 4h
    assert out2 == {"ran": False, "reason": "cooldown"}


def test_disabled_by_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_AUTO_CONSOLIDATE", "0")
    out = run_maintenance(tmp_path, now=1_000_000.0)
    assert out == {"ran": False, "reason": "disabled"}
