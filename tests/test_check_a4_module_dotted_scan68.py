"""TDD — check_a4_violations._module_to_dotted suffix-safe (scan 68-Opus P2).
Bug: `rstrip('.py')` rimuove il SET di char {'.','p','y'} dalla coda, non il
suffisso '.py'. Quindi 'engram/policy.py' -> 'engram/polic', 'copy.py' -> 'co',
'registry.py' -> 'registr' -> dotted name sbagliato -> git grep trova 0
importatori -> falso segnale nel detector A4-marketing. Fix: removesuffix('.py').
Test HERMETIC (funzione pura, no git, no DB)."""
from __future__ import annotations

from scripts.check_a4_violations import _module_to_dotted


def test_module_ending_in_p_or_y_not_corrupted():
    # questi venivano corrotti da rstrip('.py')
    assert _module_to_dotted("engram/policy.py") == "verimem.policy"
    assert _module_to_dotted("engram/registry.py") == "verimem.registry"
    assert _module_to_dotted("engram/copy.py") == "verimem.copy"
    assert _module_to_dotted("engram/entropy.py") == "verimem.entropy"


def test_normal_module_unaffected():
    assert _module_to_dotted("engram/semantic.py") == "verimem.semantic"
    assert _module_to_dotted("clp/agentos/win_ocr.py") == "clp.agentos.win_ocr"


def test_init_collapses_to_package():
    assert _module_to_dotted("engram/__init__.py") == "engram"
    assert _module_to_dotted("engram/sub/__init__.py") == "verimem.sub"


def test_windows_backslash_normalized():
    assert _module_to_dotted("engram\\policy.py") == "verimem.policy"
