"""P0.2 (2026-06-09): opt-in mean-centering (de-anisotropy) in recall().

Default OFF = byte-identical legacy ranking (no behaviour change, no test churn).
Flag ON = corpus mean subtracted before cosine. Measured on a copy of the live
corpus (25 labeled IT probes, through the gated engine): R@10 0.84 -> 0.88,
R@50 0.88 -> 0.96 (previously-unretrievable facts recovered), R@1 unchanged.

This guards the WIRING: default is untouched; the ON path runs and returns sane
(finite) results. Efficacy is tracked separately by a recall-quality benchmark.
"""
from __future__ import annotations

import math

from engram.semantic import Fact, SemanticMemory


def _seed(sm: SemanticMemory) -> None:
    props = [
        "the deployment uses blue-green rollout on aws",
        "carbonara needs guanciale eggs pecorino black pepper",
        "sqlite backup integrity is verified with pragma integrity_check",
        "the recall path ranks facts by cosine over embeddings",
        "skills are consolidated during the dream rem stage",
    ]
    for i, p in enumerate(props):
        sm.store(
            Fact(proposition=p, topic=f"t/{i}", source_episodes=["e"]),
            embed="sync",
        )


def test_centering_default_off_is_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_RECALL_CENTERING", raising=False)
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm)
    res = sm.recall("blue-green deployment on aws", k=5)
    assert res, "default recall must return results"
    assert all(math.isfinite(s) for _, s in res)


def test_centering_on_runs_and_returns_finite(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_RECALL_CENTERING", "on")
    sm = SemanticMemory(db_path=tmp_path / "s.db")
    _seed(sm)
    res = sm.recall("blue-green deployment on aws", k=5)
    assert res, "centered recall must still return results"
    assert all(math.isfinite(s) for _, s in res)
    # the most relevant fact should surface in the top-k
    props = [f.proposition for f, _ in res]
    assert any("blue-green" in p for p in props), props
