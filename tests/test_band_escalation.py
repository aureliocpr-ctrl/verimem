"""CE-band → LLM-judge escalation (0.7.0 — "mettilo": the llm judge is USED when available).

The local CE decides the clear cases for free; its uncertain middle band
[threshold, tau_hi) was HELD FOR REVIEW. Now, when no llm was injected but a
``claude`` CLI is on PATH (flat subscription, no API key), the band ESCALATES:
one llm adjudication decides admit/block instead of parking the write. No CLI /
opt-out / any failure → held for review exactly as before (fail-soft, never a
silent admit).
"""
from __future__ import annotations

from types import SimpleNamespace

from verimem import band_escalation as be


def test_resolver_off_switch_wins(monkeypatch):
    monkeypatch.setenv("ENGRAM_BAND_LLM", "0")
    monkeypatch.setattr(be.shutil, "which", lambda _: r"C:\bin\claude.EXE")
    be._resolve_cli.cache_clear()
    assert be.escalate_band_score("src", "fact") is None


def test_resolver_none_when_no_cli(monkeypatch):
    monkeypatch.delenv("ENGRAM_BAND_LLM", raising=False)
    monkeypatch.setattr(be.shutil, "which", lambda _: None)
    be._resolve_cli.cache_clear()
    assert be.escalate_band_score("src", "fact") is None


def test_escalation_parses_score_from_cli(monkeypatch):
    monkeypatch.delenv("ENGRAM_BAND_LLM", raising=False)
    monkeypatch.setattr(be.shutil, "which", lambda _: r"C:\bin\claude.EXE")
    be._resolve_cli.cache_clear()

    def _fake_run(*a, **k):
        return SimpleNamespace(returncode=0, stdout="Score: 87\n", stderr="")
    monkeypatch.setattr(be.subprocess, "run", _fake_run)
    assert be.escalate_band_score("the doc says X", "X") == 87.0


def test_escalation_failsoft_on_cli_error(monkeypatch):
    monkeypatch.delenv("ENGRAM_BAND_LLM", raising=False)
    monkeypatch.setattr(be.shutil, "which", lambda _: r"C:\bin\claude.EXE")
    be._resolve_cli.cache_clear()

    def _boom(*a, **k):
        raise OSError("cli exploded")
    monkeypatch.setattr(be.subprocess, "run", _boom)
    assert be.escalate_band_score("src", "fact") is None


def test_escalation_failsoft_on_unparseable_output(monkeypatch):
    monkeypatch.delenv("ENGRAM_BAND_LLM", raising=False)
    monkeypatch.setattr(be.shutil, "which", lambda _: r"C:\bin\claude.EXE")
    be._resolve_cli.cache_clear()

    def _fake_run(*a, **k):
        return SimpleNamespace(returncode=0, stdout="I cannot help with that", stderr="")
    monkeypatch.setattr(be.subprocess, "run", _fake_run)
    # unreadable verdict must NOT admit — None → held for review upstream
    assert be.escalate_band_score("src", "fact") is None


# ---- gate wiring: the band branch consumes the escalation ----------------

def _gate(monkeypatch, esc_result):
    """Run the write-gate with a CE score parked in the band (60) and a
    monkeypatched escalation verdict."""
    from verimem import anti_confab_gate as g
    from verimem import grounding_gate as gg
    monkeypatch.setenv("ENGRAM_GROUNDING_WRITE", "1")
    monkeypatch.delenv("ENGRAM_GROUNDING_WRITE_THRESHOLD", raising=False)
    monkeypatch.delenv("ENGRAM_GROUNDING_THRESHOLD", raising=False)
    monkeypatch.setenv("VERIMEM_CE_BAND_ENFORCE", "1")
    monkeypatch.setattr(
        gg, "fact_grounding_score_ex", lambda *a, **k: (60.0, "local"))
    monkeypatch.setattr(be, "escalate_band_score", lambda *a, **k: esc_result)
    return g.run_validation_gate(
        proposition="The cache TTL is 30 minutes.",
        verified_by=["source-doc:x:1"], topic="t", agent=None,
        validate="fast", source="the config sets the cache TTL to 30 minutes",
    )


def test_band_escalation_admits_on_high_llm_score(monkeypatch):
    gate = _gate(monkeypatch, 85.0)
    layers = {w.get("layer") for w in gate.warnings}
    assert "L4-review" not in layers          # not parked
    assert "L4-grounding" not in layers       # not blocked
    assert gate.action == "persist"
    assert gate.judge == "claude-band"


def test_band_escalation_blocks_on_low_llm_score(monkeypatch):
    gate = _gate(monkeypatch, 10.0)
    layers = {w.get("layer") for w in gate.warnings}
    assert "L4-grounding" in layers           # llm adjudicated: not entailed


def test_band_holds_for_review_when_no_escalation(monkeypatch):
    gate = _gate(monkeypatch, None)
    layers = {w.get("layer") for w in gate.warnings}
    assert "L4-review" in layers              # today's behavior preserved
