"""`engram airgap` CLI self-check (typer CliRunner). Exit 0 if air-gapped, 1 if not."""
from __future__ import annotations

from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()

_AIRGAP_ENV = (
    "HIPPO_LLM_PROVIDER", "HIPPO_HOSTED", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE",
    "ENGRAM_OFFLINE", "HIPPO_OFFLINE", "OPENAI_BASE_URL",
)


def _clear(monkeypatch):
    for v in _AIRGAP_ENV:
        monkeypatch.delenv(v, raising=False)


def test_airgap_not_gapped_exits_1(monkeypatch):
    _clear(monkeypatch)
    r = runner.invoke(app, ["airgap"])
    assert r.exit_code == 1, r.output
    assert "not air-gapped" in r.output.lower()


def test_airgap_local_config_exits_0(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("HIPPO_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    r = runner.invoke(app, ["airgap"])
    assert r.exit_code == 0, r.output
    assert "air-gapped" in r.output.lower()


def test_airgap_json_emits_verdict(monkeypatch):
    _clear(monkeypatch)
    monkeypatch.setenv("HIPPO_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    r = runner.invoke(app, ["airgap", "--json"])
    assert r.exit_code == 0, r.output
    assert "air_gapped" in r.output
    assert "true" in r.output.lower()
