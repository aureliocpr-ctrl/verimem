"""Wiring of the (previously dormant) topic_priors off-topic penalty into recall.

apply_topic_penalty was a pure, tested function with NO live caller. It is now wired
into SemanticMemory.recall (both warm paths) via _apply_topic_penalty_to_sims, gated
by ENGRAM_TOPIC_PENALTY (default 0.0 = no-op, so default ranking is unchanged until
A/B'd on the live corpus). These tests cover the wiring helper without loading e5.
"""
from __future__ import annotations

import types

import numpy as np

from verimem.semantic import _apply_topic_penalty_to_sims, _topic_penalty_strength


def _facts(*topics):
    return [types.SimpleNamespace(topic=t) for t in topics]


def test_default_is_noop(monkeypatch):
    monkeypatch.delenv("ENGRAM_TOPIC_PENALTY", raising=False)
    assert _topic_penalty_strength() == 0.0
    sims = np.array([0.9, 0.8, 0.7])
    out = _apply_topic_penalty_to_sims(sims, _facts("lessons/x", "pentest/y", "proj/z"), "tls audit")
    assert np.allclose(out, sims)  # unchanged when off


def test_penalty_downranks_lessons_for_task_query(monkeypatch):
    monkeypatch.setenv("ENGRAM_TOPIC_PENALTY", "0.10")
    sims = np.array([0.90, 0.80])
    out = _apply_topic_penalty_to_sims(sims, _facts("lessons/agent", "pentest/testfire"), "tls cert chain audit")
    assert abs(out[0] - 0.90 * 0.90) < 1e-9   # lessons/* penalised -10%
    assert abs(out[1] - 0.80) < 1e-9          # on-topic untouched


def test_meta_query_exempts_lessons(monkeypatch):
    monkeypatch.setenv("ENGRAM_TOPIC_PENALTY", "0.10")
    sims = np.array([0.90, 0.80])
    out = _apply_topic_penalty_to_sims(sims, _facts("lessons/agent", "pentest/x"), "what is the lesson here")
    assert np.allclose(out, sims)  # meta query → no penalty


def test_works_on_dict_rows(monkeypatch):
    monkeypatch.setenv("ENGRAM_TOPIC_PENALTY", "0.10")
    sims = np.array([0.90, 0.80])
    rows = [{"topic": "lessons/agent"}, {"topic": "pentest/x"}]
    out = _apply_topic_penalty_to_sims(sims, rows, "tls audit")
    assert abs(out[0] - 0.81) < 1e-9 and abs(out[1] - 0.80) < 1e-9


def test_bad_env_is_safe(monkeypatch):
    monkeypatch.setenv("ENGRAM_TOPIC_PENALTY", "not-a-number")
    assert _topic_penalty_strength() == 0.0
