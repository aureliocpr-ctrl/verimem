"""HippoAgent.build() wires the semantic NLI reconcile judge when ENGRAM_RECONCILE_NLI is
on (the live MCP path runs build()), so the validated fix is reachable in production. Off
by default. Hermetic — ENGRAM_DATA_DIR points at a tmp dir so no real corpus is touched;
LazyLLM defers any real backend, so no API key is needed."""
from __future__ import annotations

import pytest


@pytest.fixture
def _isolated(tmp_path, monkeypatch):
    # Patch the EXISTING (frozen) CONFIG instance in-place + restore — NOT importlib.reload,
    # which swaps the module object and pollutes every other test's CONFIG reference.
    from engram.config import CONFIG
    d = tmp_path / "engram"
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(d))
    orig = {a: getattr(CONFIG, a) for a in ("data_dir", "project_root") if hasattr(CONFIG, a)}
    for a in orig:
        object.__setattr__(CONFIG, a, d)
    try:
        yield
    finally:
        for a, v in orig.items():
            object.__setattr__(CONFIG, a, v)


def test_build_wires_judge_when_enabled(_isolated, monkeypatch):
    monkeypatch.setenv("ENGRAM_RECONCILE_NLI", "1")
    from engram.agent import HippoAgent
    from engram.semantic_conflict import LLMRelationJudge

    agent = HippoAgent.build()
    assert isinstance(getattr(agent.semantic, "_reconcile_judge", None), LLMRelationJudge)


def test_build_no_judge_by_default(_isolated, monkeypatch):
    monkeypatch.delenv("ENGRAM_RECONCILE_NLI", raising=False)
    from engram.agent import HippoAgent

    agent = HippoAgent.build()
    assert getattr(agent.semantic, "_reconcile_judge", None) is None
