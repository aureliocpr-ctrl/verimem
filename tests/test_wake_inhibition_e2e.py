"""FORGIA pezzo #173 — E2E proof: lateral inhibition changes retrieval.

Construct a realistic case in which `_retrieve_skills` would
naturally return BOTH antagonist skills (similar embeddings, both
promoted, similar fitness), then verify that flipping
`CONFIG.retrieval_inhibition_enabled = True` causes one of them to
drop out — which is exactly the guadagno reale of #171.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from engram import config as config_mod
from engram.config import CONFIG
from engram.memory import EpisodicMemory
from engram.skill import Skill, SkillLibrary
from engram.wake import WakeAgent


def _patch_config(monkeypatch, **fields) -> None:
    new = dataclasses.replace(CONFIG, **fields)
    monkeypatch.setattr(config_mod, "CONFIG", new)
    from engram import memory as memory_mod
    from engram import sleep as sleep_mod
    from engram import wake as wake_mod
    monkeypatch.setattr(sleep_mod, "CONFIG", new)
    monkeypatch.setattr(memory_mod, "CONFIG", new)
    monkeypatch.setattr(wake_mod, "CONFIG", new)


def _build(tmp_path: Path) -> WakeAgent:
    mem = EpisodicMemory(db_path=tmp_path / "ep.db")
    skills = SkillLibrary(
        dir_path=tmp_path / "sk", db_path=tmp_path / "sk" / "idx.db",
    )
    return WakeAgent(memory=mem, skills=skills)


def _seed_pair(wake: WakeAgent, *, antagonist: bool) -> None:
    """Two skills with overlapping triggers, both promoted, ~equal fitness."""
    a = Skill(
        id="A", name="parse_strict", trigger="parse json",
        body="strict parser",
        status="promoted", trials=20, successes=18,
        antagonists=["B"] if antagonist else [],
    )
    b = Skill(
        id="B", name="parse_lenient", trigger="parse json",
        body="lenient parser",
        status="promoted", trials=20, successes=18,
        antagonists=["A"] if antagonist else [],
    )
    wake.skills.store(a)
    wake.skills.store(b)


def test_inhibition_off_returns_both_antagonists(tmp_path: Path, monkeypatch):
    """Without the flag, the retrieval pipeline can return both."""
    _patch_config(monkeypatch, retrieval_inhibition_enabled=False)
    wake = _build(tmp_path)
    _seed_pair(wake, antagonist=True)
    out = wake._retrieve_skills("parse json input")
    ids = {s.id for s in out}
    # When the flag is off, antagonist links are ignored — so the
    # retrieval can keep both relevant skills.
    assert ids == {"A", "B"}, (
        f"expected both A and B (no inhibition), got {ids}"
    )


def test_inhibition_on_drops_antagonist(tmp_path: Path, monkeypatch):
    """With the flag, only ONE of the antagonist pair survives."""
    _patch_config(monkeypatch, retrieval_inhibition_enabled=True)
    wake = _build(tmp_path)
    _seed_pair(wake, antagonist=True)
    out = wake._retrieve_skills("parse json input")
    ids = {s.id for s in out}
    # Exactly one of the two antagonists, never both.
    assert len(ids & {"A", "B"}) == 1, (
        f"inhibition should drop one antagonist, got {ids}"
    )


def test_inhibition_on_no_antagonists_keeps_both(
    tmp_path: Path, monkeypatch,
):
    """Sanity: flag on but no antagonist links → behaviour unchanged."""
    _patch_config(monkeypatch, retrieval_inhibition_enabled=True)
    wake = _build(tmp_path)
    _seed_pair(wake, antagonist=False)
    out = wake._retrieve_skills("parse json input")
    ids = {s.id for s in out}
    assert ids == {"A", "B"}
