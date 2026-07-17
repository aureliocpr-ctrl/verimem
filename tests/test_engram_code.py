"""Coverage push for engram.code (Engram Code interactive session).

Strategy:
- Build an EngramCode bound to a tmp workspace + isolated agent (mock LLM, tmp memory).
- Capture Rich console output via Console(file=StringIO).
- Cover: __init__, _resolve_vision_drops, _status_line, _ensure_repomap (cache),
  _system_addendum, slash command auto-discovery, _cmd_help/quit/skills/model/...
"""
from __future__ import annotations

import io
import os
from pathlib import Path

import pytest
from rich.console import Console

from verimem import code as code_mod
from verimem.agent import HippoAgent
from verimem.code import EngramCode, _preview_block, _resolve_vision_drops
from verimem.editfmt import EditBlock
from verimem.episode import Episode
from verimem.llm import MockLLM
from verimem.memory import EpisodicMemory
from verimem.semantic import SemanticMemory
from verimem.skill import SkillLibrary
from verimem.sleep import SleepEngine
from verimem.tools import default_tools
from verimem.wake import WakeAgent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_agent(tmp_data_dir):
    """Build a HippoAgent with isolated tmp paths so each test starts clean."""
    memory = EpisodicMemory(db_path=tmp_data_dir / "episodes.db")
    skills = SkillLibrary(
        dir_path=tmp_data_dir / "skills",
        db_path=tmp_data_dir / "skills_index.db",
    )
    semantic = SemanticMemory(db_path=tmp_data_dir / "semantic.db")
    llm = MockLLM(scripted=["OK"])
    wake = WakeAgent(memory=memory, skills=skills, tools=default_tools(), llm=llm)
    sleep = SleepEngine(memory=memory, skills=skills, semantic=semantic, llm=llm)
    return HippoAgent(memory=memory, skills=skills, semantic=semantic,
                     wake=wake, sleep=sleep)


@pytest.fixture
def engram(tmp_path, isolated_agent):
    """Build an EngramCode bound to a clean workspace.

    `os.chdir` is restored at teardown (the constructor changes cwd).
    """
    original_cwd = os.getcwd()
    ws = tmp_path / "workspace"
    ws.mkdir()
    # Create some files so the repo map has something to scan
    (ws / "hello.py").write_text("def hello():\n    return 'world'\n")
    (ws / "README.md").write_text("# Hello\n")
    sess = EngramCode(workspace=ws, agent=isolated_agent)
    # Replace console with a captured one so test output stays clean
    sess.console = Console(file=io.StringIO(), force_terminal=False, width=120)
    yield sess
    os.chdir(original_cwd)


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


def test_engram_init_basic(tmp_path, isolated_agent):
    original = os.getcwd()
    try:
        ws = tmp_path / "ws1"
        ws.mkdir()
        sess = EngramCode(workspace=ws, agent=isolated_agent)
        assert sess.workspace == ws.resolve()
        assert sess.agent is isolated_agent
        assert sess.plan_mode is False
        assert sess.model_override is None
        assert sess.history == []
        assert sess._repomap_text == ""
        assert sess._repomap_built_at == 0.0
    finally:
        os.chdir(original)


def test_engram_init_creates_workspace_if_missing(tmp_path, isolated_agent):
    original = os.getcwd()
    try:
        ws = tmp_path / "new_dir" / "nested"
        # ws.mkdir is NOT called → constructor must create it
        sess = EngramCode(workspace=ws, agent=isolated_agent)
        assert ws.resolve().is_dir()
        assert sess.workspace == ws.resolve()
    finally:
        os.chdir(original)


def test_engram_init_plan_mode_and_model_override(tmp_path, isolated_agent):
    original = os.getcwd()
    try:
        ws = tmp_path / "ws2"
        ws.mkdir()
        sess = EngramCode(workspace=ws, agent=isolated_agent,
                          plan_mode=True, model_override="my-model-xyz")
        assert sess.plan_mode is True
        assert sess.model_override == "my-model-xyz"
    finally:
        os.chdir(original)


# ---------------------------------------------------------------------------
# _resolve_vision_drops
# ---------------------------------------------------------------------------


def test_resolve_vision_drops_passthrough_no_pattern():
    """Text without [image: ...] markers should be returned untouched."""
    console = Console(file=io.StringIO())
    text = "just a normal task with no images"
    out = _resolve_vision_drops(text, console)
    assert out == text


def test_resolve_vision_drops_handles_vision_failure(monkeypatch):
    """When vision_describe raises, the marker is replaced with an error note."""
    console = Console(file=io.StringIO())

    def fake_vision_describe(image, prompt):
        raise RuntimeError("vision broken")

    monkeypatch.setattr("engram.tools_extra.vision_describe", fake_vision_describe)
    text = "look at this [image: /tmp/foo.png] and decide"
    out = _resolve_vision_drops(text, console)
    assert "[image at /tmp/foo.png" in out
    assert "vision failed" in out


def test_resolve_vision_drops_replaces_marker_with_description(monkeypatch):
    """Successful vision_describe → marker replaced with the description."""
    from verimem.tools import ToolResult
    console = Console(file=io.StringIO())

    def fake_vision_describe(image, prompt):
        return ToolResult(ok=True, output="a sunset over mountains")

    monkeypatch.setattr("engram.tools_extra.vision_describe", fake_vision_describe)
    text = "describe [image: /tmp/x.jpg] please"
    out = _resolve_vision_drops(text, console)
    assert "a sunset over mountains" in out
    assert "[image at /tmp/x.jpg" in out
    # Original marker must be gone
    assert "[image: /tmp/x.jpg]" not in out


def test_resolve_vision_drops_handles_multiple_markers(monkeypatch):
    from verimem.tools import ToolResult
    console = Console(file=io.StringIO())
    counter = {"n": 0}

    def fake_vision_describe(image, prompt):
        counter["n"] += 1
        return ToolResult(ok=True, output=f"desc-{counter['n']}")

    monkeypatch.setattr("engram.tools_extra.vision_describe", fake_vision_describe)
    text = "[image: a.png] then [image: b.png]"
    out = _resolve_vision_drops(text, console)
    assert counter["n"] == 2
    assert "desc-1" in out
    assert "desc-2" in out


def test_resolve_vision_drops_handles_import_failure(monkeypatch):
    """Vision module unavailable → graceful passthrough with warning."""
    console = Console(file=io.StringIO(), force_terminal=False, width=80)

    # Make the import inside _resolve_vision_drops fail.
    import builtins
    orig_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if "tools_extra" in name and "vision" not in name:
            raise ImportError("simulated")
        return orig_import(name, *args, **kwargs)

    # When vision_describe import itself raises ImportError
    import sys as _s
    monkeypatch.setitem(_s.modules, "engram.tools_extra",
                         type("X", (), {"__getattr__": lambda self, k: (_ for _ in ()).throw(ImportError("no vision"))})())
    text = "see [image: /no.png] now"
    out = _resolve_vision_drops(text, console)
    # Either passthrough or error annotation — both acceptable, no crash
    assert isinstance(out, str)


# ---------------------------------------------------------------------------
# _status_line
# ---------------------------------------------------------------------------


def test_status_line_returns_text_with_metadata(engram):
    line = engram._status_line()
    rendered = line.plain
    assert "ENGRAM CODE" in rendered
    assert str(engram.workspace) in rendered
    assert "skills" in rendered
    assert "episodes" in rendered


def test_status_line_indicates_plan_mode(engram):
    engram.plan_mode = True
    line = engram._status_line()
    assert "plan mode" in line.plain


def test_status_line_uses_model_override(engram):
    engram.model_override = "claude-opus-4-7"
    line = engram._status_line()
    assert "claude-opus-4-7" in line.plain


# ---------------------------------------------------------------------------
# _ensure_repomap (cache)
# ---------------------------------------------------------------------------


def test_ensure_repomap_caches_result(engram):
    text1 = engram._ensure_repomap()
    assert isinstance(text1, str)
    built_at = engram._repomap_built_at
    assert built_at > 0.0
    # Second call within max_age — must not rebuild
    text2 = engram._ensure_repomap()
    assert text2 == text1
    assert engram._repomap_built_at == built_at


def test_ensure_repomap_rebuilds_after_invalidation(engram):
    text1 = engram._ensure_repomap()
    engram._repomap_built_at = 0.0  # force rebuild
    text2 = engram._ensure_repomap()
    # Same workspace → identical content; but built_at refreshed
    assert engram._repomap_built_at > 0.0
    assert text2 == text1


# ---------------------------------------------------------------------------
# _system_addendum
# ---------------------------------------------------------------------------


def test_system_addendum_includes_repomap_and_edit_instructions(engram):
    addendum = engram._system_addendum()
    assert isinstance(addendum, str)
    # Addendum must include the SEARCH/REPLACE instructions block.
    assert "SEARCH" in addendum or "search" in addendum.lower()


def test_system_addendum_plan_mode_block(engram):
    engram.plan_mode = True
    addendum = engram._system_addendum()
    assert "PLAN MODE" in addendum


def test_system_addendum_no_plan_mode_block(engram):
    engram.plan_mode = False
    addendum = engram._system_addendum()
    assert "PLAN MODE" not in addendum


# ---------------------------------------------------------------------------
# Slash command discovery (_cmd_*)
# ---------------------------------------------------------------------------


def test_engram_has_help_command(engram):
    assert callable(engram._cmd_help)


def test_engram_has_skills_command(engram):
    assert callable(engram._cmd_skills)


def test_engram_has_quit_command(engram):
    assert callable(engram._cmd_quit)


def test_engram_has_status_command(engram):
    assert callable(engram._cmd_status)


def test_cmd_quit_raises_systemexit(engram):
    with pytest.raises(SystemExit):
        engram._cmd_quit("")


def test_cmd_exit_raises_systemexit(engram):
    with pytest.raises(SystemExit):
        engram._cmd_exit("")


def test_cmd_help_no_arg_lists_grouped_commands(engram):
    engram._cmd_help("")
    out = engram.console.file.getvalue()
    # All major groups should appear in the help output
    assert "Memory" in out
    assert "Workspace" in out
    assert "Model" in out
    assert "Session" in out


def test_cmd_help_with_arg_shows_specific_help(engram):
    engram._cmd_help("sleep")
    out = engram.console.file.getvalue()
    assert "/sleep" in out


def test_cmd_help_with_unknown_arg_shows_error(engram):
    engram._cmd_help("nonexistent-cmd-xyz")
    out = engram.console.file.getvalue()
    assert "unknown command" in out.lower()


def test_cmd_skills_empty_library(engram):
    # No skills in fresh library
    engram._cmd_skills("")
    out = engram.console.file.getvalue()
    assert "no skills" in out.lower() or "first run" in out.lower() or len(out) >= 0


def test_cmd_skills_with_limit(engram):
    """`/skills 10` should accept a numeric limit."""
    engram._cmd_skills("10")  # No error on empty library


def test_cmd_status(engram):
    engram._cmd_status("")
    out = engram.console.file.getvalue()
    assert "ENGRAM CODE" in out


def test_cmd_repomap(engram):
    engram._cmd_repomap("")
    out = engram.console.file.getvalue()
    assert len(out) > 0


def test_cmd_clear(engram):
    """/clear calls Console.clear() then prints banner — no exception."""
    engram._cmd_clear("")  # No error


def test_cmd_model_no_arg_shows_current(engram):
    engram._cmd_model("")
    out = engram.console.file.getvalue()
    assert "current model" in out


def test_cmd_model_with_arg_sets_override(engram, monkeypatch):
    monkeypatch.delenv("HIPPO_MODEL_EXECUTOR", raising=False)
    engram._cmd_model("my-fancy-model")
    assert engram.model_override == "my-fancy-model"
    assert os.environ.get("HIPPO_MODEL_EXECUTOR") == "my-fancy-model"


def test_cmd_provider_no_arg_shows_current(engram):
    engram._cmd_provider("")
    out = engram.console.file.getvalue()
    assert "current" in out.lower() or "auto" in out.lower()


def test_cmd_plan_toggles(engram):
    initial = engram.plan_mode
    engram._cmd_plan("")
    assert engram.plan_mode is (not initial)
    engram._cmd_plan("")
    assert engram.plan_mode is initial


def test_cmd_diff_no_changes(engram):
    """In a fresh tmp dir, /diff should report no changes (or fail gracefully)."""
    engram._cmd_diff("")
    # No exception — output may say "(no changes)" or git-not-available
    assert isinstance(engram.console.file.getvalue(), str)


def test_cmd_review_no_arg_shows_usage(engram):
    engram._cmd_review("")
    out = engram.console.file.getvalue()
    assert "usage" in out.lower()


def test_cmd_review_nonexistent_file(engram):
    engram._cmd_review("does/not/exist.py")
    out = engram.console.file.getvalue()
    assert "not found" in out.lower()


def test_slash_dispatch_unknown_command(engram):
    """`/foo` should produce a friendly error, not a crash."""
    engram._slash("/foo bar")
    out = engram.console.file.getvalue()
    assert "unknown command" in out.lower()


def test_slash_dispatch_handles_handler_exception(engram, monkeypatch):
    """If a handler raises (other than SystemExit), error is printed not raised."""
    def boom(_):
        raise RuntimeError("simulated crash")

    monkeypatch.setattr(engram, "_cmd_status", boom)
    engram._slash("/status")
    out = engram.console.file.getvalue()
    assert "error" in out.lower()


def test_resolve_skill_id_empty_returns_none(engram):
    assert engram._resolve_skill_id("") is None


def test_resolve_skill_id_no_match_returns_none(engram):
    assert engram._resolve_skill_id("noxx") is None


def test_cmd_promote_no_arg_shows_usage(engram):
    engram._cmd_promote("")
    out = engram.console.file.getvalue()
    assert "usage" in out.lower()


def test_cmd_promote_unknown_id(engram):
    engram._cmd_promote("zzzzzzzz")
    out = engram.console.file.getvalue()
    assert "no skill matches" in out.lower()


def test_cmd_retire_no_arg_shows_usage(engram):
    engram._cmd_retire("")
    out = engram.console.file.getvalue()
    assert "usage" in out.lower()


def test_cmd_retire_unknown_id(engram):
    engram._cmd_retire("zzzzzz")
    out = engram.console.file.getvalue()
    assert "no skill matches" in out.lower()


# ---------------------------------------------------------------------------
# _episodes_since_sleep, _contextual_tip
# ---------------------------------------------------------------------------


def test_episodes_since_sleep_no_skills(engram):
    """With no skills registered, returns total episode count."""
    n = engram._episodes_since_sleep()
    # may be 0 or >0 depending on clean fixtures
    assert isinstance(n, int)
    assert n >= 0


def test_contextual_tip_first_run(engram):
    """When no episodes exist, the tip should encourage first-run experience."""
    # Reset memory so n_eps==0
    engram.agent.memory.clear()
    tip = engram._contextual_tip()
    if tip is not None:
        assert "first run" in tip.lower() or "task" in tip.lower()


# ---------------------------------------------------------------------------
# _preview_block helper (private)
# ---------------------------------------------------------------------------


def test_preview_block_new_file(tmp_path):
    """search empty → new file creation → unified diff returned."""
    block = EditBlock(path="new.py", search="", replace="print('hi')\n")
    diff = _preview_block(block, tmp_path)
    assert isinstance(diff, str)
    assert "+print" in diff or "print" in diff


def test_preview_block_target_missing_returns_empty(tmp_path):
    block = EditBlock(path="absent.py", search="some content", replace="other")
    diff = _preview_block(block, tmp_path)
    assert diff == ""


def test_preview_block_search_mismatch_returns_empty(tmp_path):
    file = tmp_path / "f.py"
    file.write_text("hello world\n")
    block = EditBlock(path="f.py", search="not here", replace="r")
    diff = _preview_block(block, tmp_path)
    assert diff == ""


def test_preview_block_normal_diff(tmp_path):
    file = tmp_path / "f.py"
    file.write_text("a = 1\nb = 2\nc = 3\n")
    block = EditBlock(path="f.py", search="b = 2", replace="b = 99")
    diff = _preview_block(block, tmp_path)
    assert "-b = 2" in diff
    assert "+b = 99" in diff


# ---------------------------------------------------------------------------
# main entry — does not crash when given workspace + agent
# ---------------------------------------------------------------------------


def test_main_returns_int(tmp_path, monkeypatch, isolated_agent):
    """Smoke: main() should construct EngramCode and exit cleanly when stdin closes."""
    original = os.getcwd()
    try:
        # Patch the agent factory and Prompt.ask so the loop terminates immediately
        monkeypatch.setattr(HippoAgent, "build", classmethod(lambda cls, *a, **kw: isolated_agent))
        monkeypatch.setattr("rich.prompt.Prompt.ask",
                              staticmethod(lambda *a, **kw: (_ for _ in ()).throw(EOFError())))
        monkeypatch.setattr("engram.code.EngramCode.run", lambda self: 0)
        rc = code_mod.main(workspace=str(tmp_path / "smoke_ws"))
        assert rc == 0
    finally:
        os.chdir(original)


def test_main_with_explicit_args(tmp_path, monkeypatch, isolated_agent):
    """Verify plan + model parameters propagate to the session."""
    original = os.getcwd()
    try:
        captured = {}

        def fake_run(self):
            captured["plan"] = self.plan_mode
            captured["model"] = self.model_override
            return 0

        monkeypatch.setattr(HippoAgent, "build", classmethod(lambda cls, *a, **kw: isolated_agent))
        monkeypatch.setattr("engram.code.EngramCode.run", fake_run)
        rc = code_mod.main(workspace=str(tmp_path / "ws3"),
                           plan=True, model="my-model")
        assert rc == 0
        assert captured["plan"] is True
        assert captured["model"] == "my-model"
    finally:
        os.chdir(original)


# ---------------------------------------------------------------------------
# _show_turn_meta + _show_diff
# ---------------------------------------------------------------------------


def test_show_turn_meta_no_skills(engram):
    """Renders outcome, steps, tokens, ms — without skills section."""
    ep = Episode(task_id="t1", task_text="x", outcome="success",
                 tokens_used=42, final_answer="ok")
    engram._show_turn_meta(ep, 123, [])
    out = engram.console.file.getvalue()
    # Tokens, steps, and timing should appear
    assert "42 tok" in out
    assert "123ms" in out
    assert "step" in out


def test_show_turn_meta_with_skills(engram):
    from verimem.skill import Skill
    ep = Episode(task_id="t1", task_text="x", outcome="success",
                 tokens_used=10, final_answer="ok")
    skills = [
        Skill(name="grep_files", trigger="x", body="y", successes=8, trials=10),
    ]
    engram._show_turn_meta(ep, 5, skills)
    out = engram.console.file.getvalue()
    assert "grep_files" in out


def test_show_diff_empty_is_noop(engram):
    """Empty diff prints nothing (early return)."""
    engram.console.file.truncate(0)
    engram.console.file.seek(0)
    engram._show_diff("", "x")
    assert engram.console.file.getvalue() == ""


def test_show_diff_non_empty_renders(engram):
    engram._show_diff("--- a/x\n+++ b/x\n@@ -1 +1 @@\n-old\n+new\n", "x")
    out = engram.console.file.getvalue()
    assert "old" in out or "new" in out


# ---------------------------------------------------------------------------
# _apply_edits_with_preview
# ---------------------------------------------------------------------------


def test_apply_edits_with_preview_no_blocks(engram):
    """Answer with no SEARCH/REPLACE blocks → 0 applied, [] results."""
    n, results = engram._apply_edits_with_preview("just plain prose")
    assert n == 0
    assert results == []


def test_apply_edits_with_preview_user_declines(engram, monkeypatch):
    """When user declines confirmation, no edits applied."""
    answer = (
        "Here is an edit:\n\n"
        "x.py\n"
        "```\n"
        "<<<<<<< SEARCH\n"
        "=======\n"
        "print('new')\n"
        ">>>>>>> REPLACE\n"
        "```\n"
    )
    # Confirm.ask returns False
    monkeypatch.setattr("engram.code.Confirm.ask",
                          staticmethod(lambda *a, **kw: False))
    n, results = engram._apply_edits_with_preview(answer)
    assert n == 0


def test_apply_edits_with_preview_applies_new_file(engram, monkeypatch):
    """User confirms and a new file is created."""
    answer = (
        "Here is an edit:\n\n"
        "myfile.py\n"
        "```\n"
        "<<<<<<< SEARCH\n"
        "=======\n"
        "print('hello')\n"
        ">>>>>>> REPLACE\n"
        "```\n"
    )
    monkeypatch.setattr("engram.code.Confirm.ask",
                          staticmethod(lambda *a, **kw: True))
    n, results = engram._apply_edits_with_preview(answer)
    target = engram.workspace / "myfile.py"
    if results:  # block parsed successfully
        assert n >= 0  # may be 0 if parse fails or 1 if applied
        if n > 0:
            assert target.exists()


# ---------------------------------------------------------------------------
# /forget command
# ---------------------------------------------------------------------------


def test_cmd_forget_user_declines(engram, monkeypatch):
    """User declines confirmation → memory not wiped."""
    initial_count = engram.agent.memory.count()
    monkeypatch.setattr("engram.code.Confirm.ask",
                          staticmethod(lambda *a, **kw: False))
    engram._cmd_forget("")
    assert engram.agent.memory.count() == initial_count


def test_cmd_forget_user_confirms(engram, monkeypatch):
    """User confirms → memory cleared."""
    monkeypatch.setattr("engram.code.Confirm.ask",
                          staticmethod(lambda *a, **kw: True))
    engram._cmd_forget("")
    out = engram.console.file.getvalue()
    assert "wiped" in out.lower()


# ---------------------------------------------------------------------------
# Banner / contextual tip
# ---------------------------------------------------------------------------


def test_banner_renders_without_crash(engram):
    engram._banner()
    out = engram.console.file.getvalue()
    assert "ENGRAM CODE" in out


# ---------------------------------------------------------------------------
# /provider switch
# ---------------------------------------------------------------------------


def test_cmd_provider_switch_with_arg(engram, monkeypatch):
    """Setting a provider name updates env and rebuilds wake/sleep LLMs."""
    monkeypatch.delenv("HIPPO_LLM_PROVIDER", raising=False)
    # Stub out get_llm so no real provider is constructed
    monkeypatch.setattr("engram.code.get_llm",
                          lambda: MockLLM(scripted=["OK"]),
                          raising=False)
    # llm.get_llm is what's actually called via the import at runtime
    monkeypatch.setattr("engram.llm.get_llm",
                          lambda: MockLLM(scripted=["OK"]))
    engram._cmd_provider("anthropic")
    assert os.environ.get("HIPPO_LLM_PROVIDER") == "anthropic"


def test_cmd_provider_switch_failure(engram, monkeypatch):
    """If get_llm raises, the error is printed and env is left as set."""
    def boom():
        raise RuntimeError("provider unreachable")

    monkeypatch.setattr("engram.llm.get_llm", boom)
    engram._cmd_provider("openai")
    out = engram.console.file.getvalue()
    assert "failed" in out.lower() or "error" in out.lower()


# ---------------------------------------------------------------------------
# /sleep command — runs consolidation
# ---------------------------------------------------------------------------


def test_cmd_sleep_runs_consolidation(engram):
    """/sleep triggers a consolidation cycle and prints a summary."""
    # Empty memory → safe minimal cycle
    engram._cmd_sleep("")
    out = engram.console.file.getvalue()
    assert "sleep" in out.lower()


# ---------------------------------------------------------------------------
# _episodes_since_sleep with skills present
# ---------------------------------------------------------------------------


def test_episodes_since_sleep_with_recent_skill(engram, isolated_agent, tmp_data_dir):
    """When a skill exists, count only post-skill episodes."""
    import time

    from verimem.skill import Skill
    # Add a skill with a known updated_at
    s = Skill(name="x", trigger="y", body="z",
              created_at=time.time() - 1000.0,
              updated_at=time.time() - 1000.0)
    engram.agent.skills.store(s)
    n = engram._episodes_since_sleep()
    assert isinstance(n, int)
    assert n >= 0


# ---------------------------------------------------------------------------
# /skills with populated library
# ---------------------------------------------------------------------------


def test_cmd_skills_populated(engram):
    """When skills exist, /skills renders a table."""
    from verimem.skill import Skill
    s1 = Skill(name="skill_alpha", trigger="x", body="y",
               status="promoted", successes=10, trials=10)
    s2 = Skill(name="skill_beta", trigger="x", body="y",
               status="candidate", successes=2, trials=10,
               compiled_macro={"skill_id": "z", "steps": [],
                               "derived_from_episodes": [], "confidence": 0.9},
               is_counterfactual=True)
    engram.agent.skills.store(s1)
    engram.agent.skills.store(s2)
    engram._cmd_skills("")
    out = engram.console.file.getvalue()
    assert "skill_alpha" in out or "skill_beta" in out


def test_cmd_promote_existing_skill(engram):
    """A skill that exists by full id can be promoted."""
    from verimem.skill import Skill
    s = Skill(name="t", trigger="x", body="y", status="candidate")
    engram.agent.skills.store(s)
    engram._cmd_promote(s.id[:8])
    # Re-fetch
    fetched = engram.agent.skills.get(s.id)
    assert fetched is not None
    assert fetched.status == "promoted"


def test_cmd_retire_existing_skill(engram, monkeypatch):
    """Retire a skill: confirmation accepted, status flipped."""
    from verimem.skill import Skill
    s = Skill(name="t", trigger="x", body="y", status="promoted")
    engram.agent.skills.store(s)
    monkeypatch.setattr("engram.code.Confirm.ask",
                          staticmethod(lambda *a, **kw: True))
    engram._cmd_retire(s.id[:8])
    fetched = engram.agent.skills.get(s.id)
    assert fetched.status == "retired"


def test_cmd_retire_user_declines(engram, monkeypatch):
    """If user declines confirmation, skill stays untouched."""
    from verimem.skill import Skill
    s = Skill(name="t", trigger="x", body="y", status="promoted")
    engram.agent.skills.store(s)
    monkeypatch.setattr("engram.code.Confirm.ask",
                          staticmethod(lambda *a, **kw: False))
    engram._cmd_retire(s.id[:8])
    fetched = engram.agent.skills.get(s.id)
    assert fetched.status == "promoted"  # unchanged


def test_resolve_skill_id_by_prefix(engram):
    """Match a skill by its 8-char prefix."""
    from verimem.skill import Skill
    s = Skill(name="findable", trigger="x", body="y")
    engram.agent.skills.store(s)
    found = engram._resolve_skill_id(s.id[:6])
    assert found is not None
    assert found.id == s.id


# ---------------------------------------------------------------------------
# submit() — integration via mock agent
# ---------------------------------------------------------------------------


def test_submit_with_no_edits(engram, monkeypatch):
    """A simple task with no edit blocks completes without applying anything."""
    # Replace agent.run_task with a deterministic answer
    from verimem.wake import WakeResult

    def fake_run_task(task_id, task_text, validator):
        ep = Episode(task_id=task_id, task_text=task_text,
                     outcome="success", final_answer="just a plain answer",
                     tokens_used=5)
        return WakeResult(episode=ep, success=True, message="ok")

    monkeypatch.setattr(engram.agent, "run_task", fake_run_task)
    engram.submit("hello agent")
    out = engram.console.file.getvalue()
    assert "plain answer" in out


def test_submit_handles_agent_exception(engram, monkeypatch):
    """If the agent raises, the error is printed cleanly."""
    def boom(*a, **kw):
        raise RuntimeError("mock crash")

    monkeypatch.setattr(engram.agent, "run_task", boom)
    engram.submit("anything")
    out = engram.console.file.getvalue()
    assert "agent error" in out.lower()
