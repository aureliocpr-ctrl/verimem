"""Mini-world generator sanity (task #17 step 3) — deterministic, honest eval.

The mini-world is the pre-registered JUDGE of the source-trust graft: same
seeded write stream through the REAL gate, flag OFF vs ON; if ON does not
halve the wrong-rate, the graft does not proceed. These tests pin the
generator's determinism and the wrong-evaluation logic — not the verdict.
"""
from __future__ import annotations

from benchmark.source_trust_miniworld import (
    WorldConfig,
    extract_value,
    generate_stream,
)


def test_stream_deterministic_and_shaped():
    cfg = WorldConfig(n_keys=5, n_honest=3, n_liars=2, ticks=4, seed=9)
    s1 = generate_stream(cfg)
    s2 = generate_stream(cfg)
    assert s1 == s2, "same seed → identical stream"
    assert all(ev["tick"] < 4 and ev["source"] and ev["value"] for ev in s1)
    sources = {ev["source"] for ev in s1}
    assert len(sources) == 5  # 3 honest + 2 liars all write eventually


def test_honest_report_current_or_stale_liars_never_true():
    cfg = WorldConfig(n_keys=4, n_honest=2, n_liars=2, ticks=6, seed=3,
                      churn_every=2, p_stale=0.5)
    stream = generate_stream(cfg)
    for ev in stream:
        if ev["kind"] == "liar":
            assert ev["value"] != ev["true_value"], (
                "a liar must never report the current true value")
        else:
            assert ev["value"] in (ev["true_value"], ev["prev_value"]), (
                "honest sources report the current value or a stale one")


def test_extract_value_roundtrip():
    prop = "The access code of project_3 is qz81vk."
    assert extract_value(prop) == "qz81vk"
    assert extract_value("no template here") is None
