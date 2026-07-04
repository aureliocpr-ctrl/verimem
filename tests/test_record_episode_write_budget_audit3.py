"""audit#3-r3 R20: hippo_record_episode persisted via a RAW a.memory.store(ep).
The embed was already non-blocking (embed='auto'), but the SQLite WRITE itself
can block up to busy_timeout (~60s) when a long background write holds the write
lock. The fact path already wraps store in store_within_budget; the episode
hot-path was the orphan. Wrap it too so the interactive MCP caller returns within
the write budget (the write finishes in the background — durable).
"""
from __future__ import annotations

import json
import time

import engram.mcp_server as ms
import engram.semantic as sem


class _SlowMem:
    """Simulates a contended SQLite write lock: store() blocks for 5s."""

    def __init__(self) -> None:
        self.calls = 0

    def store(self, ep, **kw):
        self.calls += 1
        time.sleep(5)
        return getattr(ep, "id", "x")


class _FakeAgent:
    def __init__(self) -> None:
        self.memory = _SlowMem()


async def test_record_episode_returns_within_write_budget(monkeypatch):
    fake = _FakeAgent()
    monkeypatch.setattr(ms, "_ag", lambda: fake)
    # Tighten the default write budget so the test is fast.
    monkeypatch.setattr(sem, "_SAVE_WRITE_BUDGET_S", 0.4)

    t0 = time.time()
    res = await ms.call_tool(
        "hippo_record_episode",
        {"task_text": "a budgeted episode", "final_answer": "done"},
    )
    elapsed = time.time() - t0

    assert elapsed < 3.0, (
        f"hippo_record_episode blocked {elapsed:.1f}s on a slow store — the "
        f"episode write hot-path is not budgeted (R20)"
    )
    payload = json.loads(res[0].text)
    assert payload.get("ok") is True, payload
    assert fake.memory.calls == 1, "the store must still have been attempted"


class _FastMem:
    def store(self, ep, **kw):
        return getattr(ep, "id", "x")


class _SlowSemantic:
    """The key-fact write hits the SAME semantic.db lock: store() blocks 5s."""

    def __init__(self) -> None:
        self.calls = 0

    def store(self, fact, **kw):
        self.calls += 1
        time.sleep(5)
        return None


class _FakeAgentKF:
    def __init__(self) -> None:
        self.memory = _FastMem()
        self.semantic = _SlowSemantic()


async def test_record_episode_key_fact_store_is_write_budgeted(monkeypatch):
    """R20 cont.: the key_facts store in the SAME handler hits semantic.db; an
    unbudgeted write there re-introduces the up-to-60s block the episode store
    was just fixed for. It must be budgeted too."""
    fake = _FakeAgentKF()
    monkeypatch.setattr(ms, "_ag", lambda: fake)
    monkeypatch.setattr(sem, "_SAVE_WRITE_BUDGET_S", 0.4)

    t0 = time.time()
    res = await ms.call_tool(
        "hippo_record_episode",
        {
            "task_text": "t", "final_answer": "a",
            "key_facts": [
                {"proposition": "the sky was clear all day",
                 "topic": "obs", "confidence": 0.9},
            ],
        },
    )
    elapsed = time.time() - t0

    assert elapsed < 3.0, (
        f"key_facts store blocked {elapsed:.1f}s — not write-budgeted (R20 cont.)"
    )
    payload = json.loads(res[0].text)
    assert payload.get("ok") is True, payload
    assert fake.semantic.calls == 1, "the key-fact store must have been attempted"
