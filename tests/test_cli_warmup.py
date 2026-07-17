"""`engram warmup` — pre-load (and download on first run) the embedding model
with clear feedback.

Mainstream first-run gap: the embedding model (~440 MB e5-base) downloads
SILENTLY on the first recall, so a new user thinks recall is broken while it is
actually fetching weights in the background. `engram warmup` makes that step
explicit + observable (and is the natural pre-bake step in CI / Docker build).
"""
from __future__ import annotations

import numpy as np
from typer.testing import CliRunner

import verimem.cli as cli
import verimem.embedding as emb

runner = CliRunner()


def test_warmup_loads_model_and_reports_ready(monkeypatch):
    loaded = {"v": False}

    def fake_model():
        loaded["v"] = True
        return object()

    monkeypatch.setattr(emb, "_model", fake_model)
    monkeypatch.setattr(emb, "encode", lambda *_a, **_k: np.ones(8, dtype=np.float32))

    res = runner.invoke(cli.app, ["warmup", "--no-daemon"])

    assert res.exit_code == 0, res.output
    assert loaded["v"] is True, "warmup must trigger the in-process model load (the download)"
    assert "ready" in res.output.lower()


def test_warmup_reports_failure_clearly_and_exits_nonzero(monkeypatch):
    def boom():
        raise RuntimeError("model not cached and HF_HUB_OFFLINE=1")

    monkeypatch.setattr(emb, "_model", boom)

    res = runner.invoke(cli.app, ["warmup", "--no-daemon"])

    assert res.exit_code == 1
    out = res.output.lower()
    assert "fail" in out or "✗" in res.output
    # actionable hint for the most common cause (offline + not cached)
    assert "offline" in out
