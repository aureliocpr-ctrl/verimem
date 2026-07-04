"""Smoke tests for engram.tui — module import + minimal app construction.

Note: tui.py is OMITTED from coverage in pyproject.toml (pure UI surface,
exercised manually). These tests guard against import-time regressions and
basic widget composition correctness.
"""
from __future__ import annotations

import pytest

# Skip the whole file if textual isn't installed
textual = pytest.importorskip("textual")


def test_tui_imports_cleanly():
    """The tui module must import without error."""
    from engram import tui
    assert hasattr(tui, "main")
    assert hasattr(tui, "HippoTUI")
    assert hasattr(tui, "ChatPane")
    assert hasattr(tui, "SkillsPane")
    assert hasattr(tui, "EpisodesPane")
    assert hasattr(tui, "SettingsPane")


def test_tui_main_callable():
    """main is a callable entry point."""
    from engram.tui import main
    assert callable(main)


def test_chat_pane_default_css_present():
    from engram.tui import ChatPane
    assert "ChatPane" in ChatPane.DEFAULT_CSS
    assert "chat-log" in ChatPane.DEFAULT_CSS


def test_skills_pane_default_css_present():
    from engram.tui import SkillsPane
    assert "SkillsPane" in SkillsPane.DEFAULT_CSS


def test_episodes_pane_default_css_present():
    from engram.tui import EpisodesPane
    assert "EpisodesPane" in EpisodesPane.DEFAULT_CSS


def test_settings_pane_default_css_present():
    from engram.tui import SettingsPane
    assert "SettingsPane" in SettingsPane.DEFAULT_CSS


def test_hippo_tui_has_bindings():
    """HippoTUI must define keyboard bindings."""
    from engram.tui import HippoTUI
    assert HippoTUI.BINDINGS
    keys = [b.key for b in HippoTUI.BINDINGS]
    assert "ctrl+enter" in keys
    assert "ctrl+r" in keys
    assert "ctrl+s" in keys
    assert "ctrl+q" in keys


def test_hippo_tui_title():
    from engram.tui import HippoTUI
    assert HippoTUI.TITLE


@pytest.mark.asyncio
async def test_hippo_tui_minimal_pilot(monkeypatch, tmp_data_dir):
    """Smoke: build the app in offscreen mode, verify primary widgets present.

    Uses Textual's pilot.run_test() to mount the app headlessly.
    """
    # Replace HippoAgent.build so the TUI doesn't pull in real LLM/state
    from engram.agent import HippoAgent
    from engram.llm import MockLLM
    from engram.memory import EpisodicMemory
    from engram.semantic import SemanticMemory
    from engram.skill import SkillLibrary
    from engram.sleep import SleepEngine
    from engram.tools import default_tools
    from engram.tui import HippoTUI
    from engram.wake import WakeAgent

    def fake_build(cls=None, **kwargs):
        memory = EpisodicMemory(db_path=tmp_data_dir / "ep.db")
        skills = SkillLibrary(
            dir_path=tmp_data_dir / "skills",
            db_path=tmp_data_dir / "skills_idx.db",
        )
        semantic = SemanticMemory(db_path=tmp_data_dir / "sem.db")
        llm = MockLLM(["OK"])
        wake = WakeAgent(memory=memory, skills=skills,
                         tools=default_tools(), llm=llm)
        sleep = SleepEngine(memory=memory, skills=skills,
                              semantic=semantic, llm=llm)
        return HippoAgent(memory=memory, skills=skills, semantic=semantic,
                         wake=wake, sleep=sleep)

    monkeypatch.setattr(HippoAgent, "build", classmethod(
        lambda cls, *a, **kw: fake_build(),
    ))

    app = HippoTUI()
    async with app.run_test() as pilot:
        # Verify the app has mounted with the four tabs
        from textual.widgets import TabbedContent
        tabs = app.query(TabbedContent)
        assert tabs
        await pilot.pause()
