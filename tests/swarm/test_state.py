"""Cycle #148.3 (2026-05-18 sera) — swarm state parser RED phase.

Parses ``~/.claude/jobs/<short_id>/state.json`` written by the Claude
supervisor process. Real sample from Fase 0 smoke (session d3ffcf29):

    {
      "state": "done",
      "detail": "printed SMOKE_TEST_OK as requested",
      "tempo": "idle",
      "inFlight": {"tasks": 0, "queued": 0, "kinds": []},
      "output": {"result": "SMOKE_TEST_OK"},
      "linkScanPath": "...d3ffcf29-c480-...jsonl",
      "intent": "Print only...",
      "sessionId": "d3ffcf29-c480-4535-8e2f-e9ee28389d38",
      "daemonShort": "d3ffcf29",
      ...
    }

API contract:
    read_state(short_id: str, *, jobs_dir: Path|None=None) -> SessionState|None
    find_state_dir(short_id: str, *, jobs_dir: Path|None=None) -> Path|None

The default jobs_dir is ``~/.claude/jobs/``. Tests use an explicit
``jobs_dir`` pointed at a tmp directory so they never touch real state.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from verimem.swarm.state import SessionState, find_state_dir, read_state

SAMPLE_STATE = {
    "state": "done",
    "detail": "printed SMOKE_TEST_OK as requested",
    "tempo": "idle",
    "inFlight": {"tasks": 0, "queued": 0, "kinds": []},
    "output": {"result": "SMOKE_TEST_OK"},
    "linkScanOffset": 42406,
    "linkScanPath": (
        "C:\\Users\\dev\\.claude\\projects\\X\\d3ffcf29-c480-4535-8e2f-e9ee28389d38.jsonl"
    ),
    "template": "bg",
    "respawnFlags": ["--max-budget-usd", "0.05"],
    "intent": "Print only SMOKE_TEST_OK",
    "sessionId": "d3ffcf29-c480-4535-8e2f-e9ee28389d38",
    "resumeSessionId": "d3ffcf29-c480-4535-8e2f-e9ee28389d38",
    "daemonShort": "d3ffcf29",
    "cliVersion": "2.1.143",
    "cwd": "C:\\some\\path",
    "createdAt": "2026-05-18T21:17:55.207Z",
    "updatedAt": "2026-05-18T21:18:09.291Z",
    "firstTerminalAt": "2026-05-18T21:18:08.282Z",
    "bridgeSessionId": "cse_xyz",
    "backend": "daemon",
    "name": "auto-name",
    "nameSource": "auto",
    "unexpected_extra_field": "must not crash",
}


@pytest.fixture
def jobs_dir(tmp_path: Path) -> Path:
    """Stand-in for ~/.claude/jobs/ — tests write a fake state.json here."""
    d = tmp_path / "jobs"
    d.mkdir()
    return d


def _seed_session(jobs_dir: Path, short_id: str, state: dict) -> Path:
    sd = jobs_dir / short_id
    sd.mkdir()
    (sd / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return sd


class TestReadState:
    """``read_state`` parses the real state.json schema."""

    def test_returns_session_state_for_real_sample(
        self, jobs_dir: Path,
    ) -> None:
        _seed_session(jobs_dir, "d3ffcf29", SAMPLE_STATE)
        st = read_state("d3ffcf29", jobs_dir=jobs_dir)
        assert st is not None
        assert isinstance(st, SessionState)
        assert st.state == "done"
        assert st.tempo == "idle"
        assert st.daemon_short == "d3ffcf29"
        assert st.session_id == "d3ffcf29-c480-4535-8e2f-e9ee28389d38"
        assert st.intent == "Print only SMOKE_TEST_OK"
        assert st.output_result == "SMOKE_TEST_OK"
        assert st.in_flight_tasks == 0
        # jsonl_path is the JSONL transcript location
        assert st.jsonl_path is not None
        assert "d3ffcf29" in st.jsonl_path

    def test_returns_none_when_short_id_missing(
        self, jobs_dir: Path,
    ) -> None:
        st = read_state("nonexist", jobs_dir=jobs_dir)
        assert st is None

    def test_handles_unknown_state_value(self, jobs_dir: Path) -> None:
        weird = dict(SAMPLE_STATE)
        weird["state"] = "future-unknown-state"
        _seed_session(jobs_dir, "abc12345", weird)
        st = read_state("abc12345", jobs_dir=jobs_dir)
        assert st is not None
        # SessionState stores state as str (no enum lock-in).
        assert st.state == "future-unknown-state"

    def test_handles_extra_unknown_fields(self, jobs_dir: Path) -> None:
        # The 'unexpected_extra_field' in SAMPLE_STATE must NOT raise.
        _seed_session(jobs_dir, "abcdef01", SAMPLE_STATE)
        st = read_state("abcdef01", jobs_dir=jobs_dir)
        assert st is not None
        assert st.state == "done"


class TestFindStateDir:
    """``find_state_dir`` locates a session's job folder."""

    def test_finds_directory(self, jobs_dir: Path) -> None:
        _seed_session(jobs_dir, "11111111", SAMPLE_STATE)
        p = find_state_dir("11111111", jobs_dir=jobs_dir)
        assert p is not None
        assert p.name == "11111111"
        assert (p / "state.json").exists()

    def test_returns_none_when_absent(self, jobs_dir: Path) -> None:
        assert find_state_dir("missing", jobs_dir=jobs_dir) is None
