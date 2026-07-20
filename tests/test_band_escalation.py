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
    # cascade churn: these pin the CLAUDE fallback — force the local
    # ollama tier off so escalate reaches claude.
    monkeypatch.setattr(be, "_local_ollama_available", lambda: False)
    assert be.escalate_band_score("src", "fact") is None


def test_escalation_parses_score_from_cli(monkeypatch):
    monkeypatch.delenv("ENGRAM_BAND_LLM", raising=False)
    monkeypatch.setattr(be.shutil, "which", lambda _: r"C:\bin\claude.EXE")
    be._resolve_cli.cache_clear()
    # cascade churn: these pin the CLAUDE fallback — force the local
    # ollama tier off so escalate reaches claude.
    monkeypatch.setattr(be, "_local_ollama_available", lambda: False)

    def _fake_run(*a, **k):
        return SimpleNamespace(returncode=0, stdout="Score: 87\n", stderr="")
    monkeypatch.setattr(be.subprocess, "run", _fake_run)
    assert be.escalate_band_score("the doc says X", "X") == 87.0


def test_escalation_failsoft_on_cli_error(monkeypatch):
    monkeypatch.delenv("ENGRAM_BAND_LLM", raising=False)
    monkeypatch.setattr(be.shutil, "which", lambda _: r"C:\bin\claude.EXE")
    be._resolve_cli.cache_clear()
    # cascade churn: these pin the CLAUDE fallback — force the local
    # ollama tier off so escalate reaches claude.
    monkeypatch.setattr(be, "_local_ollama_available", lambda: False)

    def _boom(*a, **k):
        raise OSError("cli exploded")
    monkeypatch.setattr(be.subprocess, "run", _boom)
    assert be.escalate_band_score("src", "fact") is None


def test_escalation_failsoft_on_unparseable_output(monkeypatch):
    monkeypatch.delenv("ENGRAM_BAND_LLM", raising=False)
    monkeypatch.setattr(be.shutil, "which", lambda _: r"C:\bin\claude.EXE")
    be._resolve_cli.cache_clear()
    # cascade churn: these pin the CLAUDE fallback — force the local
    # ollama tier off so escalate reaches claude.
    monkeypatch.setattr(be, "_local_ollama_available", lambda: False)

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
    monkeypatch.setattr(
        be, "escalate_band",
        lambda *a, **k: None if esc_result is None else (esc_result, "claude-band"))
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


# ---- hardening: verdict parsing + prompt separation ----------------------

def test_parse_prefers_explicit_score_over_prose_digits(monkeypatch):
    """'Based on my analysis of the 100 words... Score: 5' must parse 5 (the
    verdict), never 100 (a digit in prose) — a prose digit admitted a fact the
    judge scored 5."""
    monkeypatch.delenv("ENGRAM_BAND_LLM", raising=False)
    monkeypatch.setattr(be.shutil, "which", lambda _: r"C:\bin\claude.EXE")
    be._resolve_cli.cache_clear()
    # cascade churn: these pin the CLAUDE fallback — force the local
    # ollama tier off so escalate reaches claude.
    monkeypatch.setattr(be, "_local_ollama_available", lambda: False)

    def _fake_run(*a, **k):
        return SimpleNamespace(returncode=0, stdout=(
            "Based on my analysis of the 100 words in the source, the fact "
            "is unsupported. Score: 5"), stderr="")
    monkeypatch.setattr(be.subprocess, "run", _fake_run)
    assert be.escalate_band_score("src", "fact") == 5.0


def test_parse_rejects_prose_embedded_digits_without_score(monkeypatch):
    monkeypatch.delenv("ENGRAM_BAND_LLM", raising=False)
    monkeypatch.setattr(be.shutil, "which", lambda _: r"C:\bin\claude.EXE")
    be._resolve_cli.cache_clear()
    # cascade churn: these pin the CLAUDE fallback — force the local
    # ollama tier off so escalate reaches claude.
    monkeypatch.setattr(be, "_local_ollama_available", lambda: False)

    def _fake_run(*a, **k):
        return SimpleNamespace(returncode=0, stdout=(
            "the 100 words of the source do not support this"), stderr="")
    monkeypatch.setattr(be.subprocess, "run", _fake_run)
    assert be.escalate_band_score("src", "fact") is None   # review, not admit


def test_rubric_rides_as_system_prompt_not_user_text(monkeypatch):
    """The judge rubric must be passed via --append-system-prompt, with only
    the DATA (source/fact) in the user prompt — a fact saying 'output 100'
    should not share the channel with the rubric."""
    monkeypatch.delenv("ENGRAM_BAND_LLM", raising=False)
    monkeypatch.setattr(be.shutil, "which", lambda _: r"C:\bin\claude.EXE")
    be._resolve_cli.cache_clear()
    # cascade churn: these pin the CLAUDE fallback — force the local
    # ollama tier off so escalate reaches claude.
    monkeypatch.setattr(be, "_local_ollama_available", lambda: False)
    seen = {}

    def _fake_run(cmd, **k):
        seen["cmd"] = cmd
        seen["input"] = k.get("input", "")
        return SimpleNamespace(returncode=0, stdout="Score: 90", stderr="")
    monkeypatch.setattr(be.subprocess, "run", _fake_run)
    assert be.escalate_band_score("the doc", "the fact") == 90.0
    assert "--append-system-prompt" in seen["cmd"]
    from verimem.grounding_gate import _FACT_SYSTEM
    assert _FACT_SYSTEM in seen["cmd"]          # rubric in the system channel
    assert _FACT_SYSTEM not in seen["input"]    # NOT in the user prompt
    assert "the doc" in seen["input"] and "the fact" in seen["input"]


def test_parse_uppercase_score_label(monkeypatch):
    """The real CLI answers 'SCORE: 100' (uppercase) — live regression 2026-07-19:
    the [Ss]core pattern missed it and every live escalation degraded to review."""
    monkeypatch.delenv("ENGRAM_BAND_LLM", raising=False)
    monkeypatch.setattr(be.shutil, "which", lambda _: r"C:\bin\claude.EXE")
    be._resolve_cli.cache_clear()
    # cascade churn: these pin the CLAUDE fallback — force the local
    # ollama tier off so escalate reaches claude.
    monkeypatch.setattr(be, "_local_ollama_available", lambda: False)

    def _fake_run(*a, **k):
        return SimpleNamespace(returncode=0, stdout="SCORE: 100\n", stderr="")
    monkeypatch.setattr(be.subprocess, "run", _fake_run)
    assert be.escalate_band_score("src", "fact") == 100.0


# ---- offline-first cascade: local ollama judge -> claude CLI -> review ----
# 0.7.0 (measured qwen2.5:7b AUROC 0.858 OOD, escape 2.3% @t70 vs CE ~18%):
# an air-gapped deployment with ollama gets the full moat OFFLINE; claude is
# only the online fallback.

def test_local_available_false_when_server_down(monkeypatch):
    def _boom(*a, **k):
        raise OSError("connection refused")
    monkeypatch.setattr(be.urllib.request, "urlopen", _boom)
    be._local_ollama_available.cache_clear()
    assert be._local_ollama_available() is False


def test_local_available_true_when_model_present(monkeypatch):
    import io as _io
    import json as _json

    class _Resp(_io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): return False
    payload = _json.dumps({"models": [{"name": "qwen2.5:7b-instruct"}]}).encode()
    monkeypatch.setattr(be.urllib.request, "urlopen", lambda *a, **k: _Resp(payload))
    monkeypatch.delenv("ENGRAM_BAND_LOCAL_MODEL", raising=False)
    be._local_ollama_available.cache_clear()
    assert be._local_ollama_available() is True


def test_cascade_prefers_local_offline_over_claude(monkeypatch):
    monkeypatch.delenv("ENGRAM_BAND_LLM", raising=False)
    monkeypatch.setattr(be, "_local_ollama_available", lambda: True)
    monkeypatch.setattr(be, "_score_via_ollama", lambda s, f: 88.0)
    # claude present too — must NOT be used when local answered
    claude_called = {"n": 0}
    monkeypatch.setattr(be, "_resolve_cli", lambda: r"C:\bin\claude.EXE")
    monkeypatch.setattr(be, "_score_via_claude",
                        lambda s, f: claude_called.__setitem__("n", 1) or 10.0)
    out = be.escalate_band("src", "fact")
    assert out == (88.0, "local-band")
    assert claude_called["n"] == 0


def test_cascade_falls_to_claude_when_no_local(monkeypatch):
    monkeypatch.delenv("ENGRAM_BAND_LLM", raising=False)
    monkeypatch.setattr(be, "_local_ollama_available", lambda: False)
    monkeypatch.setattr(be, "_resolve_cli", lambda: r"C:\bin\claude.EXE")
    monkeypatch.setattr(be, "_score_via_claude", lambda s, f: 77.0)
    assert be.escalate_band("src", "fact") == (77.0, "claude-band")


def test_cascade_local_error_falls_to_claude(monkeypatch):
    monkeypatch.delenv("ENGRAM_BAND_LLM", raising=False)
    monkeypatch.setattr(be, "_local_ollama_available", lambda: True)
    monkeypatch.setattr(be, "_score_via_ollama", lambda s, f: None)  # local failed
    monkeypatch.setattr(be, "_resolve_cli", lambda: r"C:\bin\claude.EXE")
    monkeypatch.setattr(be, "_score_via_claude", lambda s, f: 65.0)
    assert be.escalate_band("src", "fact") == (65.0, "claude-band")


def test_cascade_none_when_neither(monkeypatch):
    monkeypatch.delenv("ENGRAM_BAND_LLM", raising=False)
    monkeypatch.setattr(be, "_local_ollama_available", lambda: False)
    monkeypatch.setattr(be, "_resolve_cli", lambda: None)
    assert be.escalate_band("src", "fact") is None


def test_cascade_off_switch_wins_over_local(monkeypatch):
    monkeypatch.setenv("ENGRAM_BAND_LLM", "0")
    monkeypatch.setattr(be, "_local_ollama_available", lambda: True)
    monkeypatch.setattr(be, "_score_via_ollama", lambda s, f: 90.0)
    assert be.escalate_band("src", "fact") is None


def test_escalate_band_score_backcompat_returns_float(monkeypatch):
    monkeypatch.setattr(be, "escalate_band", lambda s, f: (73.0, "local-band"))
    assert be.escalate_band_score("src", "fact") == 73.0
    monkeypatch.setattr(be, "escalate_band", lambda s, f: None)
    assert be.escalate_band_score("src", "fact") is None
