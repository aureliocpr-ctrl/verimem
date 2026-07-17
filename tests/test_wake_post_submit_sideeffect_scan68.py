"""TDD — i tool-call paralleli DOPO submit_solution nella stessa turn non
devono eseguire side-effect (rescan2 HIGH wake.py:1391-1428, 2026-06-02).

Il for sui turn.tool_calls eseguiva OGNI call: se l'LLM emette
[..., submit_solution, shell_run] nella stessa turn, shell_run girava DOPO che
l'episodio era gia risolto = side-effect post-submit indesiderato.

Fix isolato + testabile-puro: _submit_cutoff_index(tool_calls) ritorna l'indice
DOPO il primo submit_solution; i call con idx >= cutoff vengono saltati
(observation 'skipped' registrata per non disallineare tool_call/result). Test
con ToolCall REALE (no mock che nasconde).
"""
from __future__ import annotations

from verimem.wake import ToolCall, _submit_cutoff_index


def _tc(name: str) -> ToolCall:
    return ToolCall(id=name, name=name, input={})


def test_no_submit_all_execute():
    calls = [_tc("code_search"), _tc("shell_run")]
    assert _submit_cutoff_index(calls) == 2  # nessun submit -> tutti eseguiti


def test_submit_in_middle_truncates_rest():
    calls = [_tc("code_search"), _tc("submit_solution"), _tc("shell_run")]
    # submit a idx 1 -> cutoff 2 -> shell_run (idx 2) saltato
    assert _submit_cutoff_index(calls) == 2


def test_submit_first_truncates_rest():
    calls = [_tc("submit_solution"), _tc("shell_run"), _tc("desktop_click")]
    assert _submit_cutoff_index(calls) == 1


def test_submit_only():
    calls = [_tc("submit_solution")]
    assert _submit_cutoff_index(calls) == 1


def test_empty():
    assert _submit_cutoff_index([]) == 0
