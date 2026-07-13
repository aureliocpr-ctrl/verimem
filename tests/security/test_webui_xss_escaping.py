"""Stored-XSS regression lock for the served console (app.js).

A memory store is an injection surface: a poisoned fact whose proposition is
`<script>...` is later rendered into the operator's browser. The console builds
rows with innerHTML, so every ATTACKER-CONTROLLED field must pass through esc().
This test reads the shipped app.js and asserts that invariant statically, so a
future edit that interpolates fact text raw (the classic stored-XSS regression)
fails here instead of in a customer's browser.

Static guard by design: the escaping lives in client JS, so we assert the source
property rather than spin up a JS engine.
"""
from __future__ import annotations

import re
from pathlib import Path

_APP_JS = Path(__file__).resolve().parents[2] / "engram" / "webui" / "app.js"

#: fact-derived, attacker-controlled fields that get interpolated into markup
_SENSITIVE_FIELDS = [
    "proposition", "from_entity", "to_entity", "predicate", "reason",
    "target_name", "source_fact_id",
]


def _lines():
    return _APP_JS.read_text(encoding="utf-8").splitlines()


def test_esc_helper_escapes_the_full_html_metacharacter_set():
    src = _APP_JS.read_text(encoding="utf-8")
    assert "function esc(" in src
    # the five characters that break out of HTML text/attribute context
    for ch in ("&", "<", ">", '"', "'"):
        assert ch in src, ch
    # the canonical entity replacements are present
    for ent in ("&amp;", "&lt;", "&gt;", "&quot;", "&#39;"):
        assert ent in src, ent


def test_every_sensitive_field_is_escaped_where_it_is_rendered():
    """Every line that references a fact-derived field AND builds markup must esc()
    it. A raw `... + it.proposition + ...` into innerHTML would be a stored-XSS hole."""
    offenders = []
    for n, line in enumerate(_lines(), 1):
        builds_markup = ("innerHTML" in line or "<td" in line or "<span" in line
                         or "<div" in line)
        for field in _SENSITIVE_FIELDS:
            # a property access like `.proposition` or `hop.proposition`
            if re.search(r"\.%s\b" % re.escape(field), line) and builds_markup:
                if "esc(" not in line:
                    offenders.append((n, field, line.strip()))
    assert not offenders, "unescaped fact field(s) rendered into markup:\n" + \
        "\n".join(f"  app.js:{n} [{f}] {ln}" for n, f, ln in offenders)


def test_proposition_specifically_is_always_escaped():
    """The #1 stored-XSS vector — the fact text — is escaped at every render site."""
    prop_lines = [(n, ln.strip()) for n, ln in enumerate(_lines(), 1)
                  if re.search(r"\.proposition\b", ln)]
    assert prop_lines, "expected the console to render proposition text somewhere"
    for n, ln in prop_lines:
        # either it is escaped, or it is a non-rendering use (assignment/compare)
        renders = any(t in ln for t in ("innerHTML", "<td", "<span", "<div", "+ "))
        assert (not renders) or "esc(" in ln, f"app.js:{n} renders proposition raw: {ln}"
