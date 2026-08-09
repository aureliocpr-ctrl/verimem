"""Asking for the moat and not getting it must not be silent.

The gate already refuses to skip L4 quietly in one direction: a write that
CARRIES a source but finds no reachable judge emits the `L4-skipped` advisory,
whose comment in anti_confab_gate.py reads "Say so out loud, NEVER a silent
skip". The mirror case — a judge is available but the write carries NO source —
had no advisory at all: L4 simply did not run and the receipt said nothing.

For an unsourced write that is ordinary and expected (the SDK docstring
documents it, and most writes have no source). But a caller who passed
`ground=True` EXPLICITLY asked for entailment verification. Getting none, and
being told nothing, is the difference between "not checked" and "checked and
fine" — and the receipt is where that distinction has to live.

Scope on purpose: the advisory fires only on the EXPLICIT request, never on the
preset default, or it would annotate the ~92% of writes that carry no source
and become wallpaper. It is advisory: the fact is admitted exactly as before.
"""
from __future__ import annotations

import pytest

CONFAB = ("The Anthropic Q3 2027 revenue was exactly 4.7 billion dollars "
          "according to the audited filing.")


@pytest.fixture()
def mem(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_TRUST", "0")
    monkeypatch.setenv("ENGRAM_RECONCILE_ON_WRITE", "0")
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    from verimem.client import Memory
    return Memory(tmp_path / "l4.db")


def _layers(res):
    return [w.get("layer") for w in (res.get("warnings") or [])]


def test_explicit_ground_without_a_source_is_reported(mem):
    res = mem.add(CONFAB, topic="w", ground=True)
    assert "L4-no-source" in _layers(res), (
        "ground=True asked for entailment verification and got none — the "
        f"receipt must say so, got layers={_layers(res)}")


def test_the_advisory_does_not_change_the_disposition(mem):
    """Advisory means advisory: the write lands exactly as it did before."""
    res = mem.add(CONFAB, topic="w", ground=True)
    assert res["stored"] is True
    assert res["status"] != "quarantined"
    assert res["grounding_score"] is None


def test_the_default_preset_stays_quiet(mem):
    """Not specifying ground must not annotate every unsourced write."""
    res = mem.add("Rex is a labrador.", topic="w")
    assert "L4-no-source" not in _layers(res)


def test_a_sourced_write_never_gets_it(mem):
    """With a source the moat runs; there is nothing to warn about."""
    res = mem.add("Rex is a labrador.", topic="w", ground=True,
                  source="The kennel registry lists Rex as a labrador.")
    assert "L4-no-source" not in _layers(res)
    assert res["grounding_score"] is not None


def test_the_advisory_never_owns_the_block_reason(mem):
    """An advisory that steals the receipt's reason is worse than no advisory:
    the caller would be told the write was held for a missing source when a
    real detector is what actually blocked it."""
    res = mem.add("The migration is complete and everything works perfectly.",
                  topic="w", ground=True)          # trips the L1 self-claim screen
    layers = _layers(res)
    assert "L4-no-source" in layers, layers
    blocking = [x for x in layers if x != "L4-no-source"]
    if blocking:                                    # a real detector fired too
        reason = (res.get("advice") or "")
        assert "no source" not in reason.lower(), (
            f"the advisory owns the reason over a real block by {blocking}")
