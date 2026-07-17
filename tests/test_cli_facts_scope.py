"""B-1 multi-tenancy on the CLI surface (2026-06-08).

The scope feature (user/agent/run isolation) shipped on the MCP surface first.
The CLI (`engram facts add/recall/search/list`) is the OTHER primary surface and
must reach parity: `--user-id/--agent-id/--run-id` scope writes and isolate
reads, with `--include-shared` opt-in for global facts. Same zero-schema topic
prefix as the MCP path (engram/scope.py), so the two surfaces interoperate.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from verimem.cli import app
from verimem.scope import scoped_topic
from verimem.semantic import Fact, SemanticMemory

runner = CliRunner()


def _db(tmp_path: Path) -> Path:
    return tmp_path / "semantic" / "semantic.db"


@pytest.fixture
def tenant_corpus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Empty isolated corpus + two tenants sharing an identical proposition
    (so only the scope filter — not embedding rank — can separate them) plus
    one unscoped/global fact."""
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
    (tmp_path / "semantic").mkdir(parents=True, exist_ok=True)
    sm = SemanticMemory(db_path=_db(tmp_path))
    prop = "the production database lives in eu-west-1"
    sm.store(Fact(id="f-alice", proposition=prop,
                  topic=scoped_topic("infra", user_id="alice"),
                  status="model_claim", source_episodes=["e"]))
    sm.store(Fact(id="f-bob", proposition=prop,
                  topic=scoped_topic("infra", user_id="bob"),
                  status="model_claim", source_episodes=["e"]))
    sm.store(Fact(id="f-global", proposition=prop, topic="infra",
                  status="model_claim", source_episodes=["e"]))
    return tmp_path


class TestFactsAddScope:
    def test_add_user_id_scopes_stored_topic(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
        (tmp_path / "semantic").mkdir(parents=True, exist_ok=True)
        r = runner.invoke(app, [
            "facts", "add", "-p", "alice keeps staging key in vault path X",
            "-t", "ops", "--user-id", "alice", "--status", "model_claim",
        ])
        assert r.exit_code == 0, r.output
        sm = SemanticMemory(db_path=_db(tmp_path))
        topics = [f.topic for f in sm.all()]
        assert topics, "fact was not stored"
        assert any(t.startswith("user:alice/") for t in topics), topics

    def test_add_rejects_bad_scope_id(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
        (tmp_path / "semantic").mkdir(parents=True, exist_ok=True)
        r = runner.invoke(app, [
            "facts", "add", "-p", "x", "-t", "ops",
            "--user-id", "a/b",  # '/' is not a legal id char
        ])
        assert r.exit_code != 0, r.output

    def test_add_rejects_topic_scope_injection(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # SECURITY (audit 2026-06-09): a topic that embeds a reserved scope
        # prefix WITHOUT the matching flag must NOT land in that tenant's scope.
        monkeypatch.setenv("ENGRAM_DATA_DIR", str(tmp_path))
        monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path))
        (tmp_path / "semantic").mkdir(parents=True, exist_ok=True)
        runner.invoke(app, [
            "facts", "add", "-p", "planted note", "-t", "user:bob/notes",
            "--status", "model_claim",  # NO --user-id
        ])
        sm = SemanticMemory(db_path=_db(tmp_path))
        topics = [f.topic for f in sm.all()]
        assert not any(t.startswith("user:bob/") for t in topics), topics


class TestFactsRecallScope:
    def test_recall_isolates_by_user(self, tenant_corpus: Path) -> None:
        r = runner.invoke(app, [
            "facts", "recall", "production database region",
            "--user-id", "alice", "--k", "10",
        ])
        assert r.exit_code == 0, r.output
        assert "f-alice" in r.output, r.output
        assert "f-bob" not in r.output, "alice query leaked bob's fact"

    def test_recall_excludes_global_without_include_shared(
        self, tenant_corpus: Path,
    ) -> None:
        r = runner.invoke(app, [
            "facts", "recall", "production database region",
            "--user-id", "alice", "--k", "10",
        ])
        assert r.exit_code == 0, r.output
        assert "f-global" not in r.output, (
            "strict isolation: unscoped fact must not appear without "
            "--include-shared"
        )

    def test_recall_include_shared_adds_global_only(
        self, tenant_corpus: Path,
    ) -> None:
        r = runner.invoke(app, [
            "facts", "recall", "production database region",
            "--user-id", "alice", "--include-shared", "--k", "10",
        ])
        assert r.exit_code == 0, r.output
        assert "f-global" in r.output, r.output
        assert "f-bob" not in r.output, (
            "include-shared must add UNSCOPED facts only, never another tenant"
        )


class TestFactsSearchScope:
    def test_search_isolates_by_user(self, tenant_corpus: Path) -> None:
        r = runner.invoke(app, [
            "facts", "search", "production", "--user-id", "alice",
            "--limit", "50",
        ])
        assert r.exit_code == 0, r.output
        assert "f-alice" in r.output, r.output
        assert "f-bob" not in r.output, "search leaked bob's fact to alice"


class TestFactsListScope:
    def test_list_isolates_by_user(self, tenant_corpus: Path) -> None:
        r = runner.invoke(app, [
            "facts", "list", "--user-id", "alice", "--limit", "100",
        ])
        assert r.exit_code == 0, r.output
        assert "f-alice" in r.output, r.output
        assert "f-bob" not in r.output, "list leaked bob's fact to alice"
        assert "f-global" not in r.output, "list strict isolation by default"

    def test_list_no_scope_sees_all(self, tenant_corpus: Path) -> None:
        # admin/backward-compat: no scope -> sees everyone.
        r = runner.invoke(app, ["facts", "list", "--limit", "100"])
        assert r.exit_code == 0, r.output
        assert "f-alice" in r.output and "f-bob" in r.output, r.output
