"""Cycle #75 - L1-SYNTAX pollution detection tests.

Detects fact propositions polluted by malformed XML/tool-call markup
that leaked into semantic memory.

The bug surfaced repeatedly in production: when the host issues a
malformed tool-call envelope, the MCP parser silently extracts only
the proposition text and treats the embedded XML as part of the
content.

Empirical baseline (2026-05-15): 110/798 (13.8%) of live facts in
the user's corpus carry XML pollution.

This suite follows TDD strict: written RED before any implementation.
"""
from __future__ import annotations

import pytest

from engram.syntax_pollution import (
    PollutionError,
    detect_xml_markup,
    is_polluted,
    sanitize_proposition,
    scan_facts,
    validate_proposition,
)

# Build polluted samples via concatenation to avoid embedding raw XML
# in source (which would itself trigger the same bug in tooling).
_LT = "<"
_GT = ">"
_PARAM_OPEN = _LT + 'parameter name="topic"' + _GT
_PARAM_CLOSE = _LT + "/parameter" + _GT
_PROP_CLOSE = _LT + "/proposition" + _GT
_INVOKE_OPEN = _LT + 'invoke name="foo"' + _GT


# ---------------------------------------------------------------------------
# detect_xml_markup
# ---------------------------------------------------------------------------

class TestDetectXmlMarkup:
    def test_detects_parameter_tag(self):
        text = "Some fact " + _PROP_CLOSE + "\n" + _PARAM_OPEN + "topic/x" + _PARAM_CLOSE
        markers = detect_xml_markup(text)
        assert "parameter_tag" in markers
        assert "proposition_close" in markers

    def test_detects_invoke_tag(self):
        text = "Some fact " + _INVOKE_OPEN + " stuff"
        markers = detect_xml_markup(text)
        assert "invoke_tag" in markers

    def test_detects_invoke_close_tag(self):
        # Cycle #75 adversarial fix: sanitize cuts on `\n</invoke>` so
        # detect MUST recognize closing tags too, otherwise the gate
        # paths (detect-based and sanitize-based) disagree.
        text = "Real content\n" + _LT + "/invoke" + _GT + " trailing"
        markers = detect_xml_markup(text)
        assert "invoke_close" in markers

    def test_detects_parameter_close_tag(self):
        # Companion to invoke_close — same coherence rationale.
        text = "Some fact " + _LT + "/parameter" + _GT + " stuff"
        markers = detect_xml_markup(text)
        assert "parameter_close" in markers

    def test_clean_proposition_returns_empty(self):
        text = "F#10 contradiction detection riscritto 2026-05-11"
        markers = detect_xml_markup(text)
        assert markers == []

    def test_handles_none_and_empty(self):
        assert detect_xml_markup(None) == []
        assert detect_xml_markup("") == []


# ---------------------------------------------------------------------------
# is_polluted
# ---------------------------------------------------------------------------

class TestIsPolluted:
    def test_polluted_with_xml_markup(self):
        assert is_polluted("text " + _PARAM_OPEN + "y" + _PARAM_CLOSE) is True

    def test_polluted_with_empty_topic_and_proposition_close(self):
        # Real-world case: proposition contains its own close tag.
        text = "Some fact text " + _PROP_CLOSE
        assert is_polluted(text) is True

    def test_clean_text_not_polluted(self):
        assert is_polluted("Normal Italian text con accenti perchè.") is False

    def test_empty_not_polluted(self):
        assert is_polluted("") is False


# ---------------------------------------------------------------------------
# validate_proposition (gate for hippo_remember)
# ---------------------------------------------------------------------------

class TestValidateProposition:
    def test_clean_proposition_passes(self):
        # Should not raise.
        validate_proposition("Clean fact text.")

    def test_xml_pollution_raises(self):
        text = "fact " + _PARAM_OPEN + "topic/x" + _PARAM_CLOSE
        with pytest.raises(PollutionError) as exc:
            validate_proposition(text)
        assert "parameter_tag" in str(exc.value) or "xml" in str(exc.value).lower()

    def test_proposition_close_raises(self):
        with pytest.raises(PollutionError):
            validate_proposition("foo " + _PROP_CLOSE + " bar")

    def test_empty_proposition_raises(self):
        with pytest.raises(PollutionError):
            validate_proposition("")

    def test_whitespace_only_raises(self):
        with pytest.raises(PollutionError):
            validate_proposition("   \n\t  ")


# ---------------------------------------------------------------------------
# sanitize_proposition (best-effort recovery)
# ---------------------------------------------------------------------------

class TestSanitizeProposition:
    def test_strips_parameter_block(self):
        polluted = "Real content " + _PROP_CLOSE + "\n" + _PARAM_OPEN + "x" + _PARAM_CLOSE
        clean = sanitize_proposition(polluted)
        assert "parameter" not in clean.lower()
        assert "proposition" not in clean.lower()
        assert "Real content" in clean

    def test_preserves_legit_backtick_xml_without_anchor(self):
        # Real corpus case (Aurelio 2026-05-15 audit): markdown code
        # span describing XML markup as bug evidence. The detector
        # flags markers, but sanitize MUST NOT truncate — there is no
        # envelope anchor.
        legit = "Bug: sintassi XML errata `" + _INVOKE_OPEN + "` invece corretto"
        clean = sanitize_proposition(legit)
        assert clean == legit  # untouched

    def test_strips_envelope_payload(self):
        # Envelope pollution: real anchor is </proposition>.
        polluted = "Real content " + _PROP_CLOSE + "\n" + _INVOKE_OPEN
        clean = sanitize_proposition(polluted)
        assert clean == "Real content"

    def test_preserves_clean_text(self):
        assert sanitize_proposition("Already clean.") == "Already clean."

    def test_handles_none(self):
        assert sanitize_proposition(None) == ""


# ---------------------------------------------------------------------------
# scan_facts — bulk detection
# ---------------------------------------------------------------------------

class _Fact:
    """Tiny fake to mimic Fact duck-typing."""
    def __init__(self, id_, proposition, topic=""):
        self.id = id_
        self.proposition = proposition
        self.topic = topic


class TestScanFacts:
    def test_returns_only_polluted(self):
        facts = [
            _Fact("a", "Clean fact", topic="x"),
            _Fact("b", "polluted " + _PARAM_OPEN + "y" + _PARAM_CLOSE, topic=""),
            _Fact("c", "Another clean", topic="y"),
        ]
        result = scan_facts(facts)
        ids = {r["id"] for r in result["polluted"]}
        assert ids == {"b"}
        assert result["n_total"] == 3
        assert result["n_polluted"] == 1

    def test_empty_input(self):
        result = scan_facts([])
        assert result == {"n_total": 0, "n_polluted": 0, "polluted": []}

    def test_reports_markers_per_fact(self):
        facts = [_Fact("p", "x " + _PROP_CLOSE + " " + _PARAM_OPEN + "y" + _PARAM_CLOSE)]
        result = scan_facts(facts)
        assert len(result["polluted"]) == 1
        markers = result["polluted"][0]["markers"]
        assert "proposition_close" in markers
        assert "parameter_tag" in markers
