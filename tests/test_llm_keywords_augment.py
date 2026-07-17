"""Cycle 168 (2026-05-22) — LLM-augmented trigger_keywords extraction.

Pure function ``extract_keywords(text, llm_callable, ...) -> list[str]``
that delegates the concept-level keyword extraction to an *injected*
LLM callable. The default rule-based populator (cycle 162) produces
shallow, wordy keywords (e.g. ``'stress,test,worker,write'``); this
cycle bumps quality with a structured LLM prompt that returns
deduplicated, lower-case, hyphen-separated concept tags
(``'regression-testing,write-concurrency,ci-pipeline'``).

Subscription-only constraint (CLAUDE.md O4): in production the
``llm_callable`` is wired to either ``mcp__engram-bridge__ask_claude``
(host subscription) or the in-process Claude Code current LLM via the
sampling pattern. NO external API key. The pure function does NOT
call any LLM directly — testability + cost-control.

RED marker: ``from verimem.llm_keywords_augment import extract_keywords``
must fail on master.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from unittest.mock import MagicMock

import pytest

# RED MARKER
from verimem.llm_keywords_augment import extract_keywords

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_llm(response_obj: object) -> Callable[[str], str]:
    """Build a MagicMock that returns ``json.dumps(response_obj)``."""
    mock = MagicMock()
    mock.return_value = json.dumps(response_obj)
    return mock


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------


class TestExtractKeywords:
    def test_returns_list_of_str(self) -> None:
        llm = _make_llm({"keywords": ["alpha", "beta", "gamma",
                                       "delta", "epsilon"]})
        out = extract_keywords("Some fact text.", llm_callable=llm)
        assert isinstance(out, list)
        assert all(isinstance(k, str) for k in out)
        assert len(out) >= 1

    def test_llm_callable_invoked_once(self) -> None:
        """The function must NOT loop or retry on success."""
        llm = _make_llm({"keywords": ["one", "two", "three", "four", "five"]})
        extract_keywords("Text.", llm_callable=llm)
        assert llm.call_count == 1, (
            f"expected exactly 1 LLM call, got {llm.call_count}"
        )

    def test_respects_n_max(self) -> None:
        """If LLM returns more than n_max, truncate."""
        llm = _make_llm({"keywords": [f"kw-{i}" for i in range(50)]})
        out = extract_keywords(
            "Text.", llm_callable=llm, n_min=5, n_max=10,
        )
        assert len(out) <= 10

    def test_respects_n_min_when_llm_returns_few(self) -> None:
        """If LLM returns < n_min keywords, still return what we got
        (no fabrication). Defensive: at least 0, never raise."""
        llm = _make_llm({"keywords": ["one", "two"]})  # only 2
        out = extract_keywords(
            "Text.", llm_callable=llm, n_min=5, n_max=10,
        )
        # We don't fabricate to reach n_min — just return what LLM gave.
        assert len(out) == 2

    def test_strips_whitespace_lowercases(self) -> None:
        """Tolerate sloppy LLM output: strip + lower."""
        llm = _make_llm({"keywords": [
            "  Alpha-Beta  ", "GAMMA", " delta ", "Epsilon-Zeta", "eta",
        ]})
        out = extract_keywords("Text.", llm_callable=llm)
        assert all(k == k.lower() for k in out), out
        assert all(k == k.strip() for k in out), out

    def test_deduplicates_keywords(self) -> None:
        """If LLM emits the same keyword twice (case-insensitive),
        keep only one."""
        llm = _make_llm({"keywords": [
            "alpha", "ALPHA", "beta", "beta", "gamma",
        ]})
        out = extract_keywords("Text.", llm_callable=llm)
        # alpha + ALPHA collapse → 1, beta x2 collapse → 1
        assert len(out) == 3, f"expected 3 unique, got {len(out)}: {out}"

    def test_handles_invalid_json_gracefully(self) -> None:
        """Malformed LLM output → empty list, no exception."""
        bad_llm = MagicMock()
        bad_llm.return_value = "not json at all { invalid"
        out = extract_keywords("Text.", llm_callable=bad_llm)
        assert out == []

    def test_handles_missing_keywords_field_gracefully(self) -> None:
        """LLM JSON missing the ``keywords`` field → []."""
        llm = _make_llm({"other_field": ["x", "y"]})
        out = extract_keywords("Text.", llm_callable=llm)
        assert out == []

    def test_handles_llm_exception_gracefully(self) -> None:
        """LLM callable raises → empty list, exception swallowed.

        This function may be batched over hundreds of facts; one bad
        LLM call must not abort the loop.
        """
        bad_llm = MagicMock()
        bad_llm.side_effect = RuntimeError("network down")
        out = extract_keywords("Text.", llm_callable=bad_llm)
        assert out == []

    def test_prompt_includes_text_verbatim(self) -> None:
        """The text we want keywords for MUST appear in the prompt
        the LLM is given. Falsifies any implementation that
        accidentally hard-codes the prompt."""
        llm = _make_llm({"keywords": ["a", "b", "c", "d", "e"]})
        text = "Cycle 175 active learning select_stuck_candidates."
        extract_keywords(text, llm_callable=llm)
        prompt_arg = llm.call_args.args[0]
        assert text in prompt_arg, (
            f"text not in prompt: prompt[:200]={prompt_arg[:200]!r}"
        )

    def test_empty_text_returns_empty(self) -> None:
        """Defensive: empty/whitespace text should NOT call LLM,
        return []. Saves cost on empty rows."""
        llm = MagicMock()
        out = extract_keywords("", llm_callable=llm)
        assert out == []
        assert llm.call_count == 0

    def test_handles_markdown_fenced_json(self) -> None:
        """Empirical observation 2026-05-22 (ask_claude haiku low-effort):
        the LLM wraps its JSON in ```json ... ``` despite the prompt
        explicitly forbidding markdown fences. The function MUST strip
        fences before parsing. Without the strip, smoke-test LIVE on
        fact a232e5c15c76 returned []."""
        fenced = (
            '```json\n'
            '{"keywords": ["git-history-rewriting", "pii-redaction", '
            '"file-removal"]}\n'
            '```'
        )
        llm = MagicMock()
        llm.return_value = fenced
        out = extract_keywords("Text.", llm_callable=llm)
        assert out == [
            "git-history-rewriting", "pii-redaction", "file-removal",
        ]

    def test_handles_markdown_fenced_no_language_specifier(self) -> None:
        """Some LLMs emit ``` without ``json``. Same strip applies."""
        fenced = '```\n{"keywords": ["alpha", "beta"]}\n```'
        llm = MagicMock()
        llm.return_value = fenced
        out = extract_keywords("Text.", llm_callable=llm)
        assert out == ["alpha", "beta"]

    def test_keywords_are_concept_level_format(self) -> None:
        """Concept-level format: lowercase, hyphen-separated, no spaces
        inside a keyword (LLM might return ``'regression testing'``
        which we normalise to ``'regression-testing'``)."""
        llm = _make_llm({"keywords": [
            "regression testing", "ci pipeline", "write concurrency",
            "tdd-strict", "single token",
        ]})
        out = extract_keywords("Text.", llm_callable=llm)
        for k in out:
            assert " " not in k, (
                f"keyword has space (not concept-level): {k!r}"
            )
