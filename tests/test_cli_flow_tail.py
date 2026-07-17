"""``verimem flow tail`` — la Live Engine Room nel TERMINALE.

La stessa pista del /ui/engine ma come feed testuale: tail di events.jsonl
(il bus cross-process), una riga colorata per evento, con surface e actor —
così vedi Claude Code (mcp), il gateway e gli agenti di altri fornitori
(VERIMEM_ACTOR) nello stesso pannello, da un pane di terminale.
"""
from __future__ import annotations

import json
import time

import pytest
from typer.testing import CliRunner

from verimem import event_jsonl_log
from verimem.flow_tail import render_flow_line


def _rec(name, **payload):
    return {"name": name, "payload": payload, "ts": time.time()}


# ---- renderer (puro, testabile senza terminale) -------------------------------

def test_render_admitted_line_carries_actor_and_surface():
    line = render_flow_line(_rec(
        "flow.write", stored=True, status="model_claim", fact_id="abc12345",
        topic="hq", surface="mcp", actor="claude-code"))
    assert "ADMITTED" in line
    assert "mcp" in line and "claude-code" in line
    assert "abc12345"[:8] in line


def test_render_quarantined_line():
    line = render_flow_line(_rec(
        "flow.write", stored=True, status="quarantined", fact_id="x",
        topic="deploy", surface="gateway", tenant="acme"))
    assert "QUARANTINED" in line
    assert "acme" in line


def test_render_recall_answer_and_abstain():
    ans = render_flow_line(_rec(
        "flow.recall", kind="search", n=3, best=0.81, surface="sdk"))
    abst = render_flow_line(_rec(
        "flow.recall", kind="explain", n=0, abstained=True, surface="mcp"))
    assert "ANSWER" in ans and "0.81" in ans
    assert "ABSTAIN" in abst


def test_render_ignores_non_flow_events():
    assert render_flow_line({"name": "episode_stored", "payload": {}}) is None


# ---- CLI ----------------------------------------------------------------------

def test_cli_flow_tail_once_prints_replay(tmp_path, monkeypatch):
    monkeypatch.setattr(
        event_jsonl_log, "EVENT_LOG_PATH", tmp_path / "events.jsonl")
    lines = [
        _rec("flow.write", stored=True, status="model_claim",
             fact_id="abc12345", topic="hq", surface="mcp", actor="codex"),
        _rec("flow.write", stored=True, status="quarantined",
             fact_id="d4e5f6a7", topic="deploy", surface="sdk"),
        _rec("flow.recall", kind="explain", n=0, abstained=True,
             surface="gateway", tenant="acme"),
        _rec("episode_stored", episode_id="zz"),          # rumore: ignorato
    ]
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(r) for r in lines) + "\n", encoding="utf-8")

    from verimem.cli import app
    res = CliRunner().invoke(app, ["flow", "tail", "--once", "--replay", "10"])
    assert res.exit_code == 0, res.output
    assert "ADMITTED" in res.output
    assert "QUARANTINED" in res.output
    assert "ABSTAIN" in res.output
    assert "codex" in res.output
    assert "episode_stored" not in res.output
