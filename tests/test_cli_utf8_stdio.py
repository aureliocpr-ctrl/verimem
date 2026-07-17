"""CLI must not crash on a legacy Windows console (cp1252) when printing the
status glyphs it uses everywhere (✓ ✗ → ⚠).

Repro of the production bug: on Windows the default console / a redirected pipe
encodes as cp1252, which cannot encode U+2713 ('✓') → `console.print("✓ …")`
raises `UnicodeEncodeError` mid-command (observed in CI: the warmup step's
"✓ model ready" crashed on windows-latest). The CLI entry forces UTF-8 stdio so
the encode always succeeds; modern terminals render the glyph, legacy ones show
a replacement char, but the command never aborts.
"""
from __future__ import annotations

import verimem.cli as cli


def test_force_utf8_stdio_reconfigures_both_streams(monkeypatch):
    calls = []

    class FakeStream:
        encoding = "cp1252"

        def reconfigure(self, **kw):
            calls.append(kw)

    monkeypatch.setattr(cli.sys, "stdout", FakeStream())
    monkeypatch.setattr(cli.sys, "stderr", FakeStream())
    cli._force_utf8_stdio()
    assert calls == [{"encoding": "utf-8", "errors": "replace"}] * 2


def test_force_utf8_stdio_never_raises_on_bad_or_missing_stream(monkeypatch):
    class Boom:
        def reconfigure(self, **kw):
            raise RuntimeError("legacy stream cannot reconfigure")

    # stdout raises on reconfigure; stderr has no reconfigure attr at all
    monkeypatch.setattr(cli.sys, "stdout", Boom())
    monkeypatch.setattr(cli.sys, "stderr", object())
    cli._force_utf8_stdio()  # must swallow both, never propagate


def test_main_is_the_console_entrypoint():
    # the console_scripts entry must be a callable that wires UTF-8 then runs
    assert callable(cli.main)
