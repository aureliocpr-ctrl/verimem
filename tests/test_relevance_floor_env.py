"""The single switch for read-path abstention across surfaces: ENGRAM_MIN_RELEVANCE.

explain() with no explicit floor reads the env, so a user/deployment turns "knows when
it doesn't know" ON everywhere (SDK, console) with one variable. Unset → 0.0 (the
permissive, backward-compatible default).
"""
from __future__ import annotations

from verimem.client import Memory
from verimem.relevance_floor import env_floor


def test_env_floor_parsing(monkeypatch):
    monkeypatch.delenv("ENGRAM_MIN_RELEVANCE", raising=False)
    assert env_floor() == 0.0
    for val, exp in [("auto", "auto"), ("0.7", 0.7), ("off", 0.0),
                     ("none", 0.0), ("junk", 0.0)]:
        monkeypatch.setenv("ENGRAM_MIN_RELEVANCE", val)
        assert env_floor() == exp


def _seed(tmp_path):
    mem = Memory(tmp_path / "m.db")
    mem.add("The production database is PostgreSQL.", topic="infra",
            verified_by=["source-doc:runbook:1"])
    return mem


def test_explain_default_reads_env_switch(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_MIN_RELEVANCE", "0.6")
    rep = _seed(tmp_path).explain("anything at all")
    assert rep["min_relevance"] == 0.6          # the switch reaches the SDK read-path


def test_explain_default_backward_compatible(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_MIN_RELEVANCE", raising=False)
    rep = _seed(tmp_path).explain("anything at all")
    assert rep["min_relevance"] == 0.0          # unset -> permissive, unchanged


def test_explicit_param_overrides_env(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_MIN_RELEVANCE", "0.9")
    rep = _seed(tmp_path).explain("anything at all", min_relevance=0.3)
    assert rep["min_relevance"] == 0.3          # explicit call wins over the env
