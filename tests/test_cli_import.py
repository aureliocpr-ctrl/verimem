"""`verimem import` — consent-first onboarding from chat exports.

Default = LIST ONLY (nothing imported without an explicit --ids/--all).
Hermetic: stub LLM injected via monkeypatch of the CLI's LLM factory.
"""
from __future__ import annotations

import json

from typer.testing import CliRunner

from verimem.cli import app

runner = CliRunner()


def _claude_export(tmp_path):
    data = [{"uuid": "cl-1", "name": "Recipe ideas",
             "created_at": "2026-01-02T10:00:00Z", "updated_at": "2026-01-02T11:00:00Z",
             "chat_messages": [
                 {"uuid": "m1", "sender": "human", "text": "I dislike snakes and cats."},
                 {"uuid": "m2", "sender": "assistant", "text": "Noted!"},
             ]}]
    p = tmp_path / "conversations.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_import_default_lists_only(tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "data"))
    p = _claude_export(tmp_path)
    r = runner.invoke(app, ["import", str(p)])
    assert r.exit_code == 0, r.output
    assert "cl-1" in r.output and "Recipe ideas" in r.output
    assert "--ids" in r.output or "--all" in r.output, "must explain how to consent"


def test_import_with_ids_ingests(tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_DATA_DIR", str(tmp_path / "data"))

    class _StubLLM:
        def complete(self, system, messages, **kw):
            class R:
                text = "The user dislikes snakes and cats"
            return R()

    import verimem.cli as cli_mod
    monkeypatch.setattr(cli_mod, "_import_llm", lambda model=None: _StubLLM())

    p = _claude_export(tmp_path)
    r = runner.invoke(app, ["import", str(p), "--ids", "cl-1"])
    assert r.exit_code == 0, r.output
    assert "imported" in r.output.lower()
    assert "1" in r.output


def test_import_missing_file_exits_1(tmp_path):
    r = runner.invoke(app, ["import", str(tmp_path / "manca.json")])
    assert r.exit_code == 1
    assert "not found" in r.output.lower()
