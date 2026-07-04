"""TDD — CVE-008: il macro fast-path NON deve bypassare l'injection-gate
(rescan2 HIGH, 2026-06-02).

Il loop LLM gata i tool pericolosi dopo contenuto esterno
(_injection_review_blocks_call @ wake.py). Il procedural fast-path
(_try_compiled_macro -> execute_macro) li eseguiva SENZA gate. Fix: una
funzione PURA _macro_blocked_by_injection_guard usata come pre-check nel
fast-path -> se l'episodio e' contaminato (ha fetchato contenuto esterno) E il
macro contiene un tool pericoloso, il fast-path deferisce al LLM loop (gated).
Funzione pura = test senza WakeAgent (no mock fragile): usa CompiledMacro/
MacroStep/Trace e le costanti REALI.
"""
from __future__ import annotations

from engram.compilation import CompiledMacro, MacroStep
from engram.wake import (
    _DANGEROUS_TOOLS_AFTER_EXTERNAL,
    _EXTERNAL_TOOLS,
    Trace,
    _macro_blocked_by_injection_guard,
)

_EXT = next(iter(_EXTERNAL_TOOLS))      # un tool esterno reale (es. web_fetch)
_DANGER = "shell_run"                    # in _DANGEROUS_TOOLS_AFTER_EXTERNAL


def _macro(*tools) -> CompiledMacro:
    steps = [MacroStep.from_dict({"tool": t, "args": {}}) for t in tools]
    return CompiledMacro(
        skill_id="s", steps=steps, derived_from_episodes=[], confidence=0.9,
    )


def _trace(action: str) -> Trace:
    return Trace(step=1, thought="t", action=action, action_input="", observation="o")


def test_danger_constant_present():
    assert _DANGER in _DANGEROUS_TOOLS_AFTER_EXTERNAL


def test_blocks_dangerous_macro_after_external():
    macro = _macro(_EXT, _DANGER, "submit_solution")
    assert _macro_blocked_by_injection_guard(macro, [_trace(_EXT)]) is True


def test_allows_safe_macro_after_external():
    # nessun tool pericoloso nel macro -> consentito anche se contaminato
    macro = _macro("code_search", "submit_solution")
    assert _macro_blocked_by_injection_guard(macro, [_trace(_EXT)]) is False


def test_allows_dangerous_macro_when_not_contaminated():
    # nessun contenuto esterno nelle traces -> nessun gate
    macro = _macro(_DANGER, "submit_solution")
    assert _macro_blocked_by_injection_guard(macro, [_trace("code_search")]) is False


def test_env_override_disables_guard(monkeypatch):
    monkeypatch.setenv("HIPPO_ALLOW_DANGEROUS_AFTER_EXTERNAL", "1")
    macro = _macro(_EXT, _DANGER, "submit_solution")
    assert _macro_blocked_by_injection_guard(macro, [_trace(_EXT)]) is False


def test_blocks_self_contained_external_then_dangerous_fresh_episode():
    """Audit 3-round R3 #18 (RCE-adjacent): un macro che fa external -> dangerous
    DENTRO i propri step (web_fetch poi shell_run) deve essere bloccato anche su
    episodio FRESCO (traces vuote). Pre-fix il guard usciva su
    _episode_is_contaminated (che guarda solo le traces dell'episodio, non i
    macro.steps) -> la injection chain girava ungated sul fast-path."""
    macro = _macro(_EXT, _DANGER, "submit_solution")
    assert _macro_blocked_by_injection_guard(macro, []) is True


def test_self_contained_chain_with_benign_steps_between_is_blocked():
    """external -> benigni -> dangerous nello stesso macro resta una chain."""
    macro = _macro(_EXT, "code_search", "code_search", _DANGER)
    assert _macro_blocked_by_injection_guard(macro, []) is True


def test_dangerous_before_external_in_macro_is_not_a_chain():
    """dangerous PRIMA di external (ordine inverso) non e' una injection chain."""
    macro = _macro(_DANGER, _EXT)
    assert _macro_blocked_by_injection_guard(macro, []) is False


def test_self_contained_chain_respects_escape_hatch(monkeypatch):
    monkeypatch.setenv("HIPPO_ALLOW_DANGEROUS_AFTER_EXTERNAL", "1")
    macro = _macro(_EXT, _DANGER)
    assert _macro_blocked_by_injection_guard(macro, []) is False
