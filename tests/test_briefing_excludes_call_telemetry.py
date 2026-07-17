"""Briefing must hide cross-LLM call telemetry from recent episodes AND from the
emerging/correction/risk quartet scan.

EMPIRICAL trigger (2026-06-13): a LIVE hippo_briefing showed 4/5 recent_episodes
were `[agy-call …]` / `[gemini-call …]` records — the bridge auto-saves every
cross-LLM ask as an episode (123/554 = 22% of the corpus). They are machine
telemetry, not user tasks: they crowd the human-readable recent list and dilute
the quartet (which looks for repeated TASK signatures), so the proactive signals
almost never fire on the real corpus.
"""
from __future__ import annotations

import time
import types

from verimem.briefing import _is_call_telemetry_episode, get_briefing

_DAY = 86400.0


def _ep(task_text, *, outcome="success", age_days=1.0, now=None, id="e"):
    now = now or time.time()
    return types.SimpleNamespace(
        task_text=task_text, outcome=outcome,
        created_at=now - age_days * _DAY, id=id,
    )


class _FakeMem:
    def __init__(self, eps):
        self._eps = eps

    def all(self, limit=None):
        return self._eps if limit is None else self._eps[:limit]

    def count(self):
        return len(self._eps)


class _FakeAgent:
    def __init__(self, eps):
        self.memory = _FakeMem(eps)
        self.skills = None
        self.semantic = None


def test_is_call_telemetry_episode_matches_bridge_records():
    for p in ["[agy-call 2026-06-13] prompt=...", "[gemini-call x]", "[CLAUDE-CALL y]",
              "  [deepseek-call z]", "[kimi-call w]"]:
        assert _is_call_telemetry_episode(_ep(p)) is True, p
    for p in ["fix the embedding recall bug", "[DECISION-TRAJECTORY] cycle #53",
              "Apply ROT3 to 'quick'", "call the API to fetch data"]:
        assert _is_call_telemetry_episode(_ep(p)) is False, p


def test_recent_episodes_excludes_call_telemetry():
    now = time.time()
    eps = [  # most-recent first: telemetry on top (what the live briefing showed)
        _ep("[agy-call A] prompt=critic", age_days=0.1, now=now, id="t1"),
        _ep("[gemini-call B] prompt=critic", age_days=0.2, now=now, id="t2"),
        _ep("[claude-call C]", age_days=0.3, now=now, id="t3"),
        _ep("fix the embedding recall bug", age_days=0.4, now=now, id="r1"),
        _ep("write the quarterly report", age_days=0.5, now=now, id="r2"),
    ]
    out = get_briefing(agent=_FakeAgent(eps), n_recent_episodes=3)
    ids = [e["id"] for e in out["recent_episodes"]]
    assert ids == ["r1", "r2"], f"only real episodes survive, got {ids}"
    assert all("-call" not in e["task_text"] for e in out["recent_episodes"])


def test_recent_episodes_still_caps_at_n_with_real_tasks():
    now = time.time()
    eps = [_ep(f"real task number {i}", age_days=i * 0.1, now=now, id=f"r{i}")
           for i in range(10)]
    out = get_briefing(agent=_FakeAgent(eps), n_recent_episodes=3)
    assert len(out["recent_episodes"]) == 3


def test_quartet_ignores_a_call_telemetry_only_corpus():
    # A corpus of ONLY call telemetry must yield no proactive signal and no
    # recent episodes — the noise is fully excluded.
    now = time.time()
    eps = [_ep(f"[agy-call {i}] prompt=critic adversarial", age_days=i * 0.1, now=now,
               id=f"t{i}") for i in range(12)]
    out = get_briefing(agent=_FakeAgent(eps),
                       task_text="critic adversarial prompt review")
    assert out["recent_episodes"] == []
    assert out["emerging"]["is_emerging"] is False
    assert out["correction"]["has_correction"] is False
    assert out["risk_guard"]["is_risky"] is False


def test_quartet_sees_real_signal_behind_telemetry_noise():
    # A real failure->success correction must still fire even when buried under a
    # pile of call-telemetry episodes (proving the quartet scans the REAL ones).
    now = time.time()
    noise = [_ep(f"[gemini-call {i}] prompt=x", age_days=i * 0.05, now=now, id=f"n{i}")
             for i in range(20)]
    real = [
        _ep("fix embedding recall bug model", outcome="failure", age_days=5, now=now, id="f1"),
        _ep("fix embedding recall bug model", outcome="failure", age_days=4, now=now, id="f2"),
        _ep("fix embedding recall bug model", outcome="success", age_days=3, now=now, id="s1"),
    ]
    out = get_briefing(agent=_FakeAgent(noise + real),
                       task_text="fix the embedding recall bug in the model")
    assert out["correction"]["has_correction"] is True, (
        "the real correction pair must be seen through the telemetry noise"
    )
    assert out["correction"]["failures_before_success"] == 2
