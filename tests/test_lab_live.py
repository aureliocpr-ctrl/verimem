"""Cycle #146 (2026-05-18 sera) — Lab Live dashboard for multi-agent chat.

Aurelio richiede: durante il cycle 145 experiment (3 agent paralleli che
chattano via memoria HippoAgent), vorrebbe vedere LIVE in CLI le loro
interazioni — tipo tail -f con Rich formatting + color per ruolo. Cycle
146 = `engram lab live` dashboard che polla SQLite ogni N sec e mostra
i nuovi fact su topic chat in cronologico, color-coded per [ROLE @T].

API contract:
    fetch_chat_since(sm, topic, since_ts=0.0) -> list[dict]
        Returns chat fact ordered ASC by created_at, since_ts excluded.

    parse_role(proposition) -> str
        Extracts "ORCHESTRATOR" / "Python-Eng" / "Code-Reviewer" /
        "QA-Eng" / "Unknown" from "[ROLE @HH:MM:SS] msg" prefix.

TDD RED→GREEN: this file must fail import on verimem.lab_live.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from verimem.lab_live import fetch_chat_since, parse_role
from verimem.semantic import Fact, SemanticMemory

_TOPIC = "lab/test-chat-cycle146"


@pytest.fixture
def sm(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sem.db")


class TestFetchChatSince:
    """fetch_chat_since pulls chat fact ASC by created_at."""

    def test_fetches_all_when_since_zero(self, sm: SemanticMemory) -> None:
        for i, role in enumerate(["ORCHESTRATOR", "Python-Eng", "QA-Eng"]):
            f = Fact(
                proposition=f"[{role} @20:30:0{i}] msg {i}",
                topic=_TOPIC, confidence=1.0,
            )
            sm.store(f)
        out = fetch_chat_since(sm, _TOPIC, since_ts=0.0)
        assert len(out) == 3, (
            f"cycle 146: must return all 3 facts on since_ts=0, got {len(out)}"
        )
        # ASC by created_at — first is ORCHESTRATOR
        assert "ORCHESTRATOR" in out[0]["proposition"], (
            f"cycle 146: first must be ORCHESTRATOR, got {out[0]!r}"
        )

    def test_excludes_facts_at_or_before_since_ts(
        self, sm: SemanticMemory,
    ) -> None:
        f1 = Fact(proposition="[ORCHESTRATOR @T] old", topic=_TOPIC, confidence=1.0)
        sm.store(f1)
        boundary = time.time()
        time.sleep(0.05)
        f2 = Fact(proposition="[Python-Eng @T] new", topic=_TOPIC, confidence=1.0)
        sm.store(f2)
        out = fetch_chat_since(sm, _TOPIC, since_ts=boundary)
        # Only f2 must come back — f1 created_at <= boundary
        assert len(out) == 1, (
            f"cycle 146: only post-boundary fact must surface, got {len(out)}"
        )
        assert "Python-Eng" in out[0]["proposition"]

    def test_empty_topic_returns_empty_list(self, sm: SemanticMemory) -> None:
        out = fetch_chat_since(sm, "lab/never-used-topic", since_ts=0.0)
        assert out == [], (
            f"cycle 146: empty topic must return [], got {out!r}"
        )


class TestParseRole:
    """parse_role extracts role tag from chat proposition."""

    def test_orchestrator_tag(self) -> None:
        assert parse_role("[ORCHESTRATOR @20:30:00] cycle start") == "ORCHESTRATOR"

    def test_python_eng_tag(self) -> None:
        assert parse_role("[Python-Eng @20:38:15] memoria-read done") == "Python-Eng"

    def test_code_reviewer_tag(self) -> None:
        assert parse_role("[Code-Reviewer @20:40:00] 2 issue found") == "Code-Reviewer"

    def test_qa_eng_tag(self) -> None:
        assert parse_role("[QA-Eng @20:42:00] 3/3 PASS") == "QA-Eng"

    def test_no_role_returns_unknown(self) -> None:
        assert parse_role("plain text no tag") == "Unknown"
        assert parse_role("") == "Unknown"
