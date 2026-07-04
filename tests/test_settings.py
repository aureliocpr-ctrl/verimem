"""UserSettings save/load round-trip + permission gates.

Covers `engram.settings`:

  • UserSettings.to_dict / from_dict round-trip
  • save → load preserves all fields (provider, models, api_keys, perms)
  • apply_to_env projects perm_* fields onto the right env vars
  • perm_shell=False makes shell_run refuse with a clear error
  • perm_filesystem="strict" / "home" / "full" map to the right env flags
  • sandbox_enabled=False is a master kill-switch (all caps on)
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from engram import settings as user_settings
from engram import tools_extra


@pytest.fixture
def isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect SETTINGS_FILE to a tmp path so tests don't touch real settings."""
    settings_path = tmp_path / "user_settings.json"
    monkeypatch.setattr(user_settings, "SETTINGS_FILE", settings_path)
    yield settings_path


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------


def test_default_user_settings_round_trip(isolated_settings: Path) -> None:
    """A fresh UserSettings written then read back must compare equal."""
    s = user_settings.UserSettings()
    user_settings.save(s)
    loaded = user_settings.load()
    assert loaded.to_dict() == s.to_dict()


def test_full_round_trip_preserves_all_fields(isolated_settings: Path) -> None:
    s = user_settings.UserSettings(
        provider="anthropic",
        base_url="https://my.proxy.example/v1",
        api_keys={"ANTHROPIC_API_KEY": "sk-ant-x", "OPENAI_API_KEY": "sk-oai-y"},
        model="claude-haiku-4-5-20251001",
        model_executor="claude-haiku-4-5-20251001",
        model_dreamer="claude-opus-4-7",
        model_critic="claude-haiku-4-5-20251001",
        ollama_host="http://127.0.0.1:11434",
        ollama_model="qwen2.5:7b-instruct",
        onboarded=True,
        sandbox_enabled=True,
        perm_filesystem="home",
        perm_computer_use=True,
        perm_webcam=False,
        perm_shell=True,
        perm_web=True,
        perm_vision=False,
        fallback_providers=["anthropic", "groq", "ollama"],
    )
    user_settings.save(s)
    loaded = user_settings.load()
    for field in s.__dataclass_fields__:
        assert getattr(loaded, field) == getattr(s, field), f"field mismatch: {field}"


def test_load_returns_defaults_when_file_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(user_settings, "SETTINGS_FILE", tmp_path / "absent.json")
    s = user_settings.load()
    # Default object — equal to a freshly constructed UserSettings()
    assert s.to_dict() == user_settings.UserSettings().to_dict()


def test_load_returns_defaults_on_corrupt_file(
    isolated_settings: Path,
) -> None:
    isolated_settings.parent.mkdir(parents=True, exist_ok=True)
    isolated_settings.write_text("{ this is not json", encoding="utf-8")
    s = user_settings.load()
    # Should fall back to defaults instead of crashing.
    assert s.to_dict() == user_settings.UserSettings().to_dict()


def test_from_dict_ignores_unknown_fields() -> None:
    """Forward-compat: a serialized dict with new fields must not crash."""
    data = {"provider": "anthropic", "totally_unknown_future_field": 42}
    s = user_settings.UserSettings.from_dict(data)
    assert s.provider == "anthropic"


def test_upsert_api_key_adds_and_removes(isolated_settings: Path) -> None:
    user_settings.save(user_settings.UserSettings())
    s = user_settings.upsert_api_key("ANTHROPIC_API_KEY", "sk-x")
    assert s.api_keys["ANTHROPIC_API_KEY"] == "sk-x"
    # Empty value → removed.
    s = user_settings.upsert_api_key("ANTHROPIC_API_KEY", "")
    assert "ANTHROPIC_API_KEY" not in s.api_keys


def test_update_patches_known_fields_only(isolated_settings: Path) -> None:
    user_settings.save(user_settings.UserSettings())
    s = user_settings.update(provider="groq", totally_bogus=999)
    assert s.provider == "groq"
    assert not hasattr(s, "totally_bogus")


# ---------------------------------------------------------------------------
# apply_to_env — perm gates → env vars
# ---------------------------------------------------------------------------


def test_apply_to_env_projects_capability_flags(
    isolated_settings: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """perm_shell=True → HIPPO_ENABLE_SHELL=1; False → 0. Same for the rest."""
    s = user_settings.UserSettings(
        sandbox_enabled=True,
        perm_computer_use=False, perm_webcam=False, perm_shell=False,
        perm_web=True, perm_vision=True,
    )
    user_settings.apply_to_env(s)
    assert os.environ["HIPPO_ENABLE_SHELL"] == "0"
    assert os.environ["HIPPO_ENABLE_COMPUTER_USE"] == "0"
    assert os.environ["HIPPO_ENABLE_WEBCAM"] == "0"
    assert os.environ["HIPPO_ENABLE_WEB"] == "1"
    assert os.environ["HIPPO_ENABLE_VISION"] == "1"


def test_apply_to_env_strict_filesystem_sets_strict_flag(
    isolated_settings: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = user_settings.UserSettings(perm_filesystem="strict")
    user_settings.apply_to_env(s)
    assert os.environ.get("HIPPO_FS_STRICT") == "1"
    assert "HIPPO_FS_HOME" not in os.environ
    assert "HIPPO_FS_ROOT" not in os.environ


def test_apply_to_env_home_filesystem_sets_home_flag(
    isolated_settings: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = user_settings.UserSettings(perm_filesystem="home")
    user_settings.apply_to_env(s)
    assert os.environ.get("HIPPO_FS_HOME") == "1"
    assert "HIPPO_FS_STRICT" not in os.environ
    assert "HIPPO_FS_ROOT" not in os.environ


def test_apply_to_env_full_filesystem_sets_root_flag(
    isolated_settings: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = user_settings.UserSettings(perm_filesystem="full")
    user_settings.apply_to_env(s)
    assert "HIPPO_FS_ROOT" in os.environ
    assert "HIPPO_FS_STRICT" not in os.environ
    assert "HIPPO_FS_HOME" not in os.environ


def test_apply_to_env_sandbox_off_unleashes_everything(
    isolated_settings: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sandbox_enabled=False is the 'unleash' preset: all caps go ON."""
    s = user_settings.UserSettings(
        sandbox_enabled=False,
        perm_computer_use=False, perm_webcam=False, perm_shell=False,
        perm_web=False, perm_vision=False,
        perm_filesystem="strict",
    )
    user_settings.apply_to_env(s)
    assert os.environ["HIPPO_ENABLE_SHELL"] == "1"
    assert os.environ["HIPPO_ENABLE_COMPUTER_USE"] == "1"
    assert os.environ["HIPPO_ENABLE_WEBCAM"] == "1"
    assert os.environ["HIPPO_ENABLE_WEB"] == "1"
    assert os.environ["HIPPO_ENABLE_VISION"] == "1"
    # Sandbox-off retains "full" filesystem (data/home dirs all in scope).
    assert "HIPPO_FS_ROOT" in os.environ


# ---------------------------------------------------------------------------
# Permission gates → tool refusal
# ---------------------------------------------------------------------------


def test_perm_shell_off_makes_shell_run_refuse(
    isolated_settings: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When perm_shell=False, shell_run must refuse with a clear error.

    This is the user-visible end of the permission system: even if the LLM
    decides to call shell_run, the kernel-level gate stops it.
    """
    s = user_settings.UserSettings(perm_shell=False)
    user_settings.apply_to_env(s)
    # Sanity: HIPPO_ENABLE_SHELL is now off.
    assert os.environ["HIPPO_ENABLE_SHELL"] == "0"
    # Some env vars left over from prior fixtures may still flag enable;
    # explicitly force-disable to confirm shell_run honours it.
    monkeypatch.setenv("HIPPO_ENABLE_SHELL", "0")
    monkeypatch.delenv("HIPPO_DISABLE_SHELL", raising=False)
    result = tools_extra.shell_run("echo hello")
    assert result.ok is False
    assert "shell" in (result.error or "").lower()


def test_perm_shell_on_makes_shell_run_work(
    isolated_settings: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sanity counterpart: with perm_shell=True, shell_run actually runs."""
    s = user_settings.UserSettings(perm_shell=True)
    user_settings.apply_to_env(s)
    assert os.environ["HIPPO_ENABLE_SHELL"] == "1"
    # On Windows: `cmd /c echo hello`. On POSIX: /bin/sh -c.
    cmd = "echo hello"
    result = tools_extra.shell_run(cmd, timeout_s=5)
    assert result.ok is True, f"shell_run failed: {result.error}"
    assert "hello" in result.output.lower()


def test_perm_computer_use_off_blocks_desktop_click(
    isolated_settings: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """desktop_click is gated by HIPPO_ENABLE_COMPUTER_USE."""
    s = user_settings.UserSettings(perm_computer_use=False)
    user_settings.apply_to_env(s)
    monkeypatch.setenv("HIPPO_ENABLE_COMPUTER_USE", "0")
    monkeypatch.setenv("HIPPO_DISABLE_COMPUTER_USE", "1")
    result = tools_extra.desktop_click(0, 0)
    assert result.ok is False
    assert "computer use" in (result.error or "").lower()


def test_perm_webcam_off_blocks_webcam_snapshot(
    isolated_settings: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = user_settings.UserSettings(perm_webcam=False)
    user_settings.apply_to_env(s)
    monkeypatch.setenv("HIPPO_ENABLE_WEBCAM", "0")
    monkeypatch.setenv("HIPPO_DISABLE_WEBCAM", "1")
    result = tools_extra.webcam_snapshot()
    assert result.ok is False
    assert "webcam" in (result.error or "").lower()
