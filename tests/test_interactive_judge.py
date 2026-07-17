"""TDD for engram/interactive_judge.py — the ghost-CLI judge backend.

The REAL sister (spawn, ai-eye inject, console hide) is exercised live, not in unit
tests: here the transport is injected (house style). What must hold:

* batch file format: instructions + items, response parsed from the JSON file;
* the session REUSES one sister across batches (spawn once);
* scores map back to the right (source, fact) pairs in order;
* transport failure/timeout -> None (caller falls back), never raises;
* ENGRAM_GROUNDING_BACKEND=interactive routes fact_grounding_score through it
  and falls back to the injected llm when the judge is unavailable.
"""
from __future__ import annotations

import json

import pytest

from verimem import grounding_gate as G
from verimem.interactive_judge import (
    InteractiveJudge,
    reset_interactive_judge,
    set_interactive_judge,
)


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv("ENGRAM_GROUNDING_BACKEND", raising=False)
    reset_interactive_judge()
    yield
    reset_interactive_judge()


class FakeTransport:
    """Stands in for (spawn ghost sister + inject + poll response file)."""

    def __init__(self, scores_fn=lambda items: [77.0] * len(items)):
        self.scores_fn = scores_fn
        self.ensure_calls = 0
        self.batches: list[list[dict]] = []
        self.alive = True

    def ensure_session(self):
        self.ensure_calls += 1
        if not self.alive:
            raise RuntimeError("no sister")
        return "sister-1"

    def run_batch(self, batch_md: str, items: list[dict], timeout_s: float):
        self.batches.append(items)
        if not self.alive:
            return None
        return {f"item_{i + 1}": s for i, s in enumerate(self.scores_fn(items))}


def test_scores_map_back_in_order():
    t = FakeTransport(lambda items: [float(10 * (i + 1)) for i in range(len(items))])
    j = InteractiveJudge(transport=t)
    out = j.score_batch([("src A", "fact A"), ("src B", "fact B")])
    assert out == [10.0, 20.0]
    assert t.batches[0][0]["fact"] == "fact A"
    assert "SOURCE" in j.render_batch(t.batches[0]) and "item_2" in j.render_batch(t.batches[0])


def test_session_reused_across_batches():
    t = FakeTransport()
    j = InteractiveJudge(transport=t)
    j.score_batch([("s", "f1")])
    j.score_batch([("s", "f2")])
    assert t.ensure_calls == 2  # ensure is idempotent per batch...
    assert len(t.batches) == 2


def test_transport_failure_returns_none_not_raise():
    t = FakeTransport()
    t.alive = False
    j = InteractiveJudge(transport=t)
    assert j.score_batch([("s", "f")]) is None


def test_single_score_api():
    j = InteractiveJudge(transport=FakeTransport(lambda items: [88.0]))
    assert j.score("src", "fact") == 88.0


def test_gate_backend_interactive_routes_and_falls_back(monkeypatch):
    monkeypatch.setenv("ENGRAM_GROUNDING_BACKEND", "interactive")
    set_interactive_judge(InteractiveJudge(transport=FakeTransport(lambda i: [66.0])))

    class BoomLLM:
        def complete(self, *a, **k):
            raise AssertionError("llm must not be called when the judge works")

    assert G.fact_grounding_score(BoomLLM(), "src", "fact") == 66.0

    # judge dead -> fall back to the injected llm at the claude-scale cut
    dead = FakeTransport()
    dead.alive = False
    set_interactive_judge(InteractiveJudge(transport=dead))

    class StubLLM:
        def complete(self, *a, **k):
            return type("R", (), {"text": "SCORE: 78"})()

    ok, score = G.should_store_fact(StubLLM(), "src", "fact")
    assert (ok, score) == (True, 78.0)   # 78 >= claude write threshold 70


def test_response_parse_tolerates_garbage(tmp_path):
    j = InteractiveJudge(transport=FakeTransport())
    assert j.parse_response('{"item_1": 40, "item_2": "n/a"}', 2) == [40.0, None]
    assert j.parse_response("not json", 2) is None


# ---------------------------------------------------------------------------
# Sister lifecycle hardening (critic follow-up 2026-07-02): no orphan ghosts.
# ---------------------------------------------------------------------------

def test_atexit_hook_closes_singleton_transport():
    """The module registers an atexit sweep; a process dying with a live
    judge must close the sister instead of leaking a hidden claude.exe."""
    from verimem import interactive_judge as IJ

    closed = []

    class ClosableTransport(FakeTransport):
        def close(self):
            closed.append(True)

    set_interactive_judge(InteractiveJudge(transport=ClosableTransport()))
    IJ._close_singleton_at_exit()
    assert closed == [True]

    # no judge / transport without close(): the sweep must never raise
    reset_interactive_judge()
    IJ._close_singleton_at_exit()
    set_interactive_judge(InteractiveJudge(transport=FakeTransport()))
    IJ._close_singleton_at_exit()


def test_ghost_spawn_failure_kills_orphan(monkeypatch):
    """If the sister spawns but never becomes ready, the raise path must
    kill the just-spawned process — otherwise an invisible claude.exe
    survives with _claude_pid still None (close() would skip it)."""
    from verimem.interactive_judge import GhostSisterTransport

    killed = []
    t = GhostSisterTransport(boot_timeout_s=0)

    class FakeProc:
        pid = 777

    monkeypatch.setattr(t, "_popen_ghost", lambda: FakeProc())
    monkeypatch.setattr(t, "_read_tail", lambda pid, n: "")
    monkeypatch.setattr(t, "_kill_tree", lambda pid: killed.append(pid))

    with pytest.raises(RuntimeError, match="did not become ready"):
        t.ensure_session()
    assert killed == [777]
    assert t._claude_pid is None and t._proc is None


def test_ghost_close_reaches_proc_without_ready_pid(monkeypatch):
    """close() must kill a spawned-but-never-ready sister too (pid known
    only through _proc), and stay idempotent."""
    from verimem.interactive_judge import GhostSisterTransport

    killed = []
    t = GhostSisterTransport(boot_timeout_s=0)

    class FakeProc:
        pid = 888

    monkeypatch.setattr(t, "_kill_tree", lambda pid: killed.append(pid))
    t._proc = FakeProc()  # spawn happened, ready never reached
    t.close()
    t.close()
    assert killed == [888]
    assert t._proc is None
