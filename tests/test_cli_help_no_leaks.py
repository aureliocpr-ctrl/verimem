"""User-facing verimem CLI help must not leak dev jargon or the legacy brand
(found via VERIMEM-MAP.md, 2026-07-18): `verimem status/sleep-now` opened with
"FORGIA #186", `verimem flow` said "Live Engine Room", `verimem trust` said
"would Engram trust". A customer running `--help` should see a clean product.
"""
from __future__ import annotations

from pathlib import Path

import verimem.cli


def test_no_dev_jargon_or_legacy_brand_in_user_facing_cli_help():
    src = Path(verimem.cli.__file__).read_text(encoding="utf-8")
    forbidden = [
        "FORGIA #186 — quick health",   # status docstring
        "FORGIA #186 — force a sleep",  # sleep-now docstring
        "Live Engine Room",                  # flow help
        "would Engram trust",                # trust docstring
        "Engram's moat",                     # trust docstring
        "wiring Engram into",                # warmup docstring
    ]
    hits = [p for p in forbidden if p in src]
    assert not hits, f"CLI help still leaks dev jargon / legacy brand: {hits}"
