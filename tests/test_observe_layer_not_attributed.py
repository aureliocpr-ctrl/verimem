"""Observe advisories (`L3-semantic-observe`, `SOURCE_TRUST-observe`) must NOT own a
block's receipt reason nor be credited in the trust ledger — they did not cause the
block.

Regression for the opus critic finding on Phase 1.1 (2026-07-19): the layer string
`"L3-semantic-observe"` satisfies `.startswith("L3")`, and `"L3"` is rank 0 (top) of
`_BLOCK_LAYER_PRIORITY`, so an observe advisory HIJACKED the receipt reason of a real
L1/L4 block and polluted `by_layer` — defeating observe mode's entire purpose
(measuring a layer's would-be block rate BEFORE it enforces). Same latent bug on the
pre-existing `SOURCE_TRUST-observe` (rank 3 via `startswith("SOURCE_TRUST")`).
"""
from __future__ import annotations

from verimem import client as _c


def test_reason_prefers_real_l1_block_over_l3_semantic_observe():
    warnings = [
        {"layer": "L1.13", "advice": "agent self-claim of completed work"},
        {"layer": "L3-semantic-observe",
         "advice": "a stored memory semantically contradicts this claim; set ..."},
    ]
    assert _c._reason_from_warnings(warnings) == "agent self-claim of completed work"


def test_reason_prefers_grounding_over_source_trust_observe():
    warnings = [
        {"layer": "L4-grounding", "advice": "source does not entail the proposition"},
        {"layer": "SOURCE_TRUST-observe",
         "advice": "source trust below threshold (observe)"},
    ]
    assert _c._reason_from_warnings(warnings) == "source does not entail the proposition"


def test_reason_empty_when_only_observe_advisory():
    # an ADMITTED write whose only note is an observe advisory has no block reason
    warnings = [{"layer": "L3-semantic-observe", "advice": "…contradicts…"}]
    assert _c._reason_from_warnings(warnings) == ""


def test_blocking_layers_excludes_observe_advisories():
    warnings = [
        {"layer": "L1"}, {"layer": "L3-semantic-observe"},
        {"layer": "SOURCE_TRUST-observe"}, {"layer": "L4-grounding"},
    ]
    assert _c._blocking_layers(warnings) == ["L1", "L4-grounding"]


def test_blocking_layers_keeps_l4_skipped_advisory():
    # L4-skipped is a genuine "no judge available" advisory that MAY be the reason
    # when it is the only note — it is NOT an `*-observe` layer, so it is kept.
    warnings = [{"layer": "L4-skipped"}, {"layer": "L3-semantic-observe"}]
    assert _c._blocking_layers(warnings) == ["L4-skipped"]
