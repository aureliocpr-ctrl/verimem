"""Glue smoke tests for the live QA runner — real retrieval, hermetic LLM.

Exercises build_records_* with a REAL SemanticMemory (so we prove the gold
context is actually retrieved) but scores with MockLLM, so no claude -p / network
is touched. The live claude -p path is verified separately by an actual sample run.
"""
from __future__ import annotations

import json
import subprocess

from benchmark.qa_eval import score_qa
from benchmark.qa_runner import (
    LeanClaudeCLILLM,
    build_records_locomo,
    build_records_longmemeval,
    extract_memories,
    hyde_query,
)
from engram.llm import MockLLM


def test_extract_memories_parses_and_strips_enumerators() -> None:
    llm = MockLLM(scripted=[
        "- Caroline studied Business Administration.\n"
        "2. Caroline likes hiking.\nMel paints sunrises."])
    mems = extract_memories(llm, "some chunk")
    assert "Caroline studied Business Administration." in mems
    assert any("hiking" in m for m in mems)
    assert any("Mel paints" in m for m in mems)
    assert all(not m.startswith(("-", "2.")) for m in mems)  # bullets/numbers gone


def test_extract_memories_fallback_on_error() -> None:
    class _Boom:
        def complete(self, *a, **k):  # noqa: ANN002, ANN003
            raise RuntimeError("x")

    assert extract_memories(_Boom(), "chunk") == []


def test_hyde_query_appends_hypothetical() -> None:
    q = hyde_query(MockLLM(scripted=["He studied Business Administration."]),
                   "What degree?")
    assert "What degree?" in q and "Business Administration" in q


def test_hyde_query_falls_back_on_error() -> None:
    class _Boom:
        def complete(self, *a, **k):  # noqa: ANN002, ANN003
            raise RuntimeError("x")

    assert hyde_query(_Boom(), "What degree?") == "What degree?"


def test_build_records_longmemeval_retrieves_gold(tmp_path) -> None:
    data = [{
        "question_id": "q1",
        "question_type": "single-session-user",
        "question": "What degree did I graduate with?",
        "answer": "Business Administration",
        "haystack_session_ids": ["s1", "s2"],
        "haystack_sessions": [
            [{"role": "user", "content": "I graduated with a Business Administration degree."}],
            [{"role": "user", "content": "I love hiking on weekends."}],
        ],
    }]
    recs = build_records_longmemeval(data, k=2, workdir=tmp_path)
    assert len(recs) == 1
    r = recs[0]
    assert {"id", "question", "gold", "context", "category"} <= set(r)
    assert r["gold"] == "Business Administration"
    assert r["category"] == "single-session-user"
    # the gold session must be among the retrieved context (retrieval works)
    assert any("Business Administration" in c for c in r["context"])


def test_build_records_locomo_shape_and_gold(tmp_path) -> None:
    data = [{
        "sample_id": "conv0",
        "conversation": {
            "session_1": [
                {"dia_id": "D1:1", "speaker": "Caroline",
                 "text": "I went to the LGBTQ support group on 7 May 2023."},
                {"dia_id": "D1:2", "speaker": "Mel", "text": "That's great to hear."},
            ],
        },
        "qa": [
            {"question": "When did Caroline go to the LGBTQ support group?",
             "answer": "7 May 2023", "evidence": ["D1:1"], "category": 2},
        ],
    }]
    recs = build_records_locomo(data, k=2, workdir=tmp_path, per_conv=5)
    assert len(recs) == 1
    r = recs[0]
    assert r["gold"] == "7 May 2023"
    assert r["category"] == "2"
    assert any("LGBTQ" in c for c in r["context"])


def test_build_records_locomo_window_bundles_neighbours(tmp_path) -> None:
    # window=1 stores each turn with its neighbours, so the retrieved context
    # for a middle turn carries an adjacent turn too (the QA-accuracy lever).
    data = [{
        "conversation": {"session_1": [
            {"dia_id": "D1:1", "speaker": "A", "text": "alpha unique zebra"},
            {"dia_id": "D1:2", "speaker": "B", "text": "beta unique zebra"},
            {"dia_id": "D1:3", "speaker": "A", "text": "gamma unique zebra"},
        ]},
        "qa": [{"question": "what about beta?", "answer": "beta",
                "evidence": ["D1:2"], "category": 1}],
    }]
    recs = build_records_locomo(data, k=3, workdir=tmp_path, per_conv=5, window=1)
    joined = " ".join(recs[0]["context"])
    assert "beta unique zebra" in joined
    # a neighbour is bundled in (proves the window, not a lone turn)
    assert ("alpha unique zebra" in joined) or ("gamma unique zebra" in joined)


def test_build_records_locomo_carries_session_date(tmp_path) -> None:
    # temporal-reasoning QA needs the session timestamp to resolve "yesterday";
    # the ingest must prepend session_X_date_time to each turn.
    data = [{
        "conversation": {
            "session_1_date_time": "1:56 pm on 8 May, 2023",
            "session_1": [
                {"dia_id": "D1:1", "speaker": "Caroline",
                 "text": "I went to the group yesterday unique zebra"},
            ],
        },
        "qa": [{"question": "when did Caroline go unique zebra",
                "answer": "7 May 2023", "evidence": ["D1:1"], "category": 2}],
    }]
    recs = build_records_locomo(data, k=2, workdir=tmp_path, per_conv=5, window=0)
    joined = " ".join(recs[0]["context"])
    assert "8 May, 2023" in joined  # the session timestamp reached the context


def test_lean_client_strips_context_and_parses(monkeypatch) -> None:
    captured: dict = {}

    class _FakeProc:
        returncode = 0
        stdout = json.dumps({"result": "Business Administration",
                             "usage": {"input_tokens": 10, "output_tokens": 3}})
        stderr = ""

    def _fake_run(cmd, **kw):  # noqa: ANN001, ANN003
        captured["cmd"] = cmd
        captured["input"] = kw.get("input")
        return _FakeProc()

    monkeypatch.setattr(subprocess, "run", _fake_run)
    llm = LeanClaudeCLILLM(model="claude-sonnet-4-6")
    r = llm.complete("MY_SYSTEM", [{"role": "user", "content": "MY_USER"}])
    assert r.text == "Business Administration"
    # system goes to --system-prompt (NOT stdin); only user content is piped
    assert "--system-prompt" in captured["cmd"] and "MY_SYSTEM" in captured["cmd"]
    assert captured["input"] == "MY_USER"
    # the lean flags that strip the global CLAUDE.md / hooks are present
    assert "--setting-sources" in captured["cmd"] and "project" in captured["cmd"]
    assert "--exclude-dynamic-system-prompt-sections" in captured["cmd"]
    assert "--model" in captured["cmd"] and "claude-sonnet-4-6" in captured["cmd"]


def test_build_records_locomo_qa_sample_seeded(tmp_path) -> None:
    data = [{
        "conversation": {
            "session_1_date_time": "1 Jan 2023",
            "session_1": [{"dia_id": f"D1:{i}", "speaker": "A",
                           "text": f"fact {i} zebra"} for i in range(1, 7)],
        },
        "qa": [{"question": f"q{i}", "answer": f"a{i}",
                "evidence": [f"D1:{i}"], "category": 1} for i in range(1, 7)],
    }]
    r1 = build_records_locomo(data, k=2, workdir=tmp_path, qa_sample=3, seed=7)
    r2 = build_records_locomo(data, k=2, workdir=tmp_path, qa_sample=3, seed=7)
    assert len(r1) == 3
    assert [x["id"] for x in r1] == [x["id"] for x in r2]  # seeded determinism


def test_qa_runner_endtoend_with_mock(tmp_path) -> None:
    data = [{
        "question_id": "q1",
        "question_type": "single-session-user",
        "question": "What degree did I graduate with?",
        "answer": "Business Administration",
        "haystack_session_ids": ["s1"],
        "haystack_sessions": [
            [{"role": "user", "content": "I graduated with a Business Administration degree."}],
        ],
    }]
    recs = build_records_longmemeval(data, k=1, workdir=tmp_path)
    res = score_qa(
        recs,
        answer_llm=MockLLM(scripted=["Business Administration"]),
        judge_llm=MockLLM(scripted=["CORRECT"]),
    )
    assert res["n"] == 1 and res["accuracy"] == 1.0


def test_lean_claude_survives_non_utf8_stdout(monkeypatch) -> None:
    """Real crash 2026-07-06 (exp4, an Italian/accented answer): claude -p
    stdout decoded utf-8 STRICT raised UnicodeDecodeError on byte 0xe8 ('è'),
    killing the whole run mid-benchmark. The subprocess read must use
    errors='replace' so one odd byte degrades to U+FFFD, never aborts —
    critical for the Italian QA axis. Contract test: the fake reproduces the
    strict-decode crash unless errors='replace' is passed."""
    import subprocess

    from benchmark.qa_runner import LeanClaudeCLILLM

    class _Proc:
        returncode = 0
        # a well-formed JSON where the model text had a replaced byte
        stdout = '{"result": "caff� latte", "usage": {}}'
        stderr = ""

    def _fake_run(cmd, **kw):
        if kw.get("errors") != "replace":
            raise UnicodeDecodeError("utf-8", b"\xe8", 0, 1,
                                     "invalid continuation byte")
        return _Proc()

    monkeypatch.setattr(subprocess, "run", _fake_run)
    llm = LeanClaudeCLILLM(model="claude-sonnet-4-6")
    r = llm.complete("SYS", [{"role": "user", "content": "Come stai?"}])
    assert "caff" in r.text and "latte" in r.text  # survived, text usable
