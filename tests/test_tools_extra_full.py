"""Coverage push for verimem.tools_extra — desktop, vision, webcam, sensitive paths.

Strategy:
- pyautogui mocked via sys.modules injection (cross-platform — pyautogui import
  is platform-bound; we replace it with a Mock).
- vision_describe paths exercised with monkeypatched provider helpers.
- _is_sensitive enumerated against deny-list patterns.
- _init_pyautogui_safety verifies FAILSAFE/PAUSE pinning.
- Hotkey deny-list checked with both deny and unsafe=True override.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from verimem import tools_extra
from verimem.tools import ToolResult

# ---------------------------------------------------------------------------
# _is_sensitive — every deny-list pattern
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", [
    ".ssh", ".aws", ".gnupg", ".docker", ".kube", ".azure",
    "credentials", ".env", ".netrc",
    "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa",
    "user_settings.json", "secrets.json",
])
def test_is_sensitive_matches_deny_list_directories(tmp_path, name):
    """Sensitive path components anywhere in the resolved path."""
    target = tmp_path / name / "subfile.txt"
    assert tools_extra._is_sensitive(target) is True


def test_is_sensitive_matches_pem_extension(tmp_path):
    target = tmp_path / "private_key.pem"
    assert tools_extra._is_sensitive(target) is True


def test_is_sensitive_matches_key_extension(tmp_path):
    target = tmp_path / "tls_cert.key"
    assert tools_extra._is_sensitive(target) is True


def test_is_sensitive_matches_env_with_editor_backup(tmp_path):
    """`.env~` (Vim backup) should still be flagged as sensitive."""
    target = tmp_path / ".env~"
    assert tools_extra._is_sensitive(target) is True


def test_is_sensitive_matches_env_with_bak_suffix(tmp_path):
    target = tmp_path / ".env.bak"
    assert tools_extra._is_sensitive(target) is True


def test_is_sensitive_matches_emacs_autosave(tmp_path):
    """Emacs autosave: #.env# → .env stripped."""
    target = tmp_path / "#.env#"
    assert tools_extra._is_sensitive(target) is True


def test_is_sensitive_matches_emacs_lockfile(tmp_path):
    """Emacs lockfile: .#.env → .env stripped."""
    target = tmp_path / ".#.env"
    assert tools_extra._is_sensitive(target) is True


def test_is_sensitive_does_not_match_innocent(tmp_path):
    target = tmp_path / "regular_file.txt"
    assert tools_extra._is_sensitive(target) is False


def test_is_sensitive_does_not_match_subset(tmp_path):
    """`environment.txt` should NOT match `.env`."""
    target = tmp_path / "environment.txt"
    assert tools_extra._is_sensitive(target) is False


def test_strip_editor_backup_suffixes_repeats():
    """Combos like `.env.bak~` collapse to `.env`."""
    assert tools_extra._strip_editor_backup_suffixes(".env.bak~") == ".env"
    assert tools_extra._strip_editor_backup_suffixes(".env~") == ".env"
    assert tools_extra._strip_editor_backup_suffixes("file.tmp") == "file"
    assert tools_extra._strip_editor_backup_suffixes(".env.save") == ".env"
    assert tools_extra._strip_editor_backup_suffixes("") == ""


def test_strip_editor_backup_suffixes_no_change():
    """Names without backup suffixes pass through."""
    assert tools_extra._strip_editor_backup_suffixes("normal.txt") == "normal.txt"


# ---------------------------------------------------------------------------
# _init_pyautogui_safety
# ---------------------------------------------------------------------------


def test_init_pyautogui_safety_pins_failsafe_and_pause():
    """FAILSAFE = True, PAUSE bumped to ≥ 0.05."""
    pg = MagicMock()
    pg.PAUSE = 0.0
    tools_extra._init_pyautogui_safety(pg)
    assert pg.FAILSAFE is True
    assert pg.PAUSE >= 0.05


def test_init_pyautogui_safety_keeps_higher_pause():
    """If PAUSE is already >= 0.05, leave it alone."""
    pg = MagicMock()
    pg.PAUSE = 1.0
    tools_extra._init_pyautogui_safety(pg)
    assert pg.PAUSE == 1.0


def test_init_pyautogui_safety_swallows_attribute_errors():
    """If pyautogui throws on PAUSE/FAILSAFE assignment, stay silent."""
    class BrokenPyautogui:
        @property
        def FAILSAFE(self):
            raise AttributeError("boom")

        @FAILSAFE.setter
        def FAILSAFE(self, value):
            raise AttributeError("boom-set")
    pg = BrokenPyautogui()
    # Should not raise
    tools_extra._init_pyautogui_safety(pg)


# ---------------------------------------------------------------------------
# Hotkey deny-list — desktop_key
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_pyautogui(monkeypatch):
    """Inject a mock pyautogui into sys.modules so desktop_* tools find it."""
    mock_pg = MagicMock()
    mock_pg.FAILSAFE = False
    mock_pg.PAUSE = 0.0
    monkeypatch.setitem(sys.modules, "pyautogui", mock_pg)
    yield mock_pg


@pytest.fixture
def enable_computer_use(monkeypatch):
    monkeypatch.setenv("HIPPO_ENABLE_COMPUTER_USE", "1")


@pytest.mark.parametrize("denied_combo", [
    "win+l", "WIN+L", "  win+l ", "win + l",  # case + whitespace tolerant
    "ctrl+alt+del", "ctrl+alt+delete",
    "alt+f4", "cmd+q", "command+q",
    "ctrl+alt+end", "ctrl+shift+esc",
])
def test_desktop_key_rejects_deny_list(enable_computer_use, fake_pyautogui, denied_combo):
    r = tools_extra.desktop_key(denied_combo)
    assert r.ok is False
    assert "deny-list" in r.error or "safety" in r.error
    # pyautogui should NEVER be called for a denied hotkey
    assert fake_pyautogui.hotkey.call_count == 0
    assert fake_pyautogui.press.call_count == 0


def test_desktop_key_unsafe_override_bypasses_deny_list(enable_computer_use, fake_pyautogui):
    """unsafe=True allows the hotkey to fire."""
    r = tools_extra.desktop_key("win+l", unsafe=True)
    assert r.ok is True
    assert fake_pyautogui.hotkey.called


def test_desktop_key_normal_combo_fires(enable_computer_use, fake_pyautogui):
    r = tools_extra.desktop_key("ctrl+s")
    assert r.ok is True
    fake_pyautogui.hotkey.assert_called_once_with("ctrl", "s")


def test_desktop_key_single_key_uses_press(enable_computer_use, fake_pyautogui):
    r = tools_extra.desktop_key("enter")
    assert r.ok is True
    fake_pyautogui.press.assert_called_once_with("enter")


def test_desktop_key_disabled_when_perm_off(monkeypatch, fake_pyautogui):
    """Without HIPPO_ENABLE_COMPUTER_USE=1, desktop_key refuses."""
    monkeypatch.delenv("HIPPO_ENABLE_COMPUTER_USE", raising=False)
    r = tools_extra.desktop_key("enter")
    assert r.ok is False
    assert "disabled" in r.error.lower()


# ---------------------------------------------------------------------------
# desktop_click
# ---------------------------------------------------------------------------


def test_desktop_click_disabled_when_perm_off(monkeypatch, fake_pyautogui):
    monkeypatch.delenv("HIPPO_ENABLE_COMPUTER_USE", raising=False)
    r = tools_extra.desktop_click(100, 200)
    assert r.ok is False
    assert "disabled" in r.error.lower()


def test_desktop_click_fires_pyautogui(enable_computer_use, fake_pyautogui):
    r = tools_extra.desktop_click(100, 200, button="right", clicks=2)
    assert r.ok is True
    fake_pyautogui.click.assert_called_once_with(x=100, y=200, button="right", clicks=2)


def test_desktop_click_pyautogui_unavailable(monkeypatch, enable_computer_use):
    """If pyautogui import fails, return a ToolResult error (no crash)."""
    monkeypatch.setitem(sys.modules, "pyautogui",
                         type("X", (), {"__getattr__":
                              lambda self, k: (_ for _ in ()).throw(
                                  ImportError("nope"))})())
    # Simulate: import succeeds but accessing attributes raises (rare but possible).
    # The real branch we want is `import pyautogui` raising ImportError, which
    # happens by removing it from sys.modules and intercepting __import__.
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **kw):
        if name == "pyautogui":
            raise ImportError("not installed")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    if "pyautogui" in sys.modules:
        del sys.modules["pyautogui"]
    r = tools_extra.desktop_click(1, 2)
    assert r.ok is False
    assert "pyautogui" in r.error.lower()


# ---------------------------------------------------------------------------
# desktop_type
# ---------------------------------------------------------------------------


def test_desktop_type_disabled_when_perm_off(monkeypatch, fake_pyautogui):
    monkeypatch.delenv("HIPPO_ENABLE_COMPUTER_USE", raising=False)
    r = tools_extra.desktop_type("hello")
    assert r.ok is False
    assert "disabled" in r.error.lower()


def test_desktop_type_fires_pyautogui(enable_computer_use, fake_pyautogui):
    r = tools_extra.desktop_type("hello", interval=0.05)
    assert r.ok is True
    fake_pyautogui.typewrite.assert_called_once_with("hello", interval=0.05)


# ---------------------------------------------------------------------------
# desktop_screenshot
# ---------------------------------------------------------------------------


def test_desktop_screenshot_pyautogui_unavailable(monkeypatch):
    monkeypatch.setenv("HIPPO_ENABLE_COMPUTER_USE", "1")  # SCAN-68: screenshot ora gated (commit 2efced6)
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **kw):
        if name == "pyautogui":
            raise ImportError("no pyautogui in CI")
        return real_import(name, *a, **kw)

    if "pyautogui" in sys.modules:
        del sys.modules["pyautogui"]
    monkeypatch.setattr(builtins, "__import__", fake_import)
    r = tools_extra.desktop_screenshot()
    assert r.ok is False
    assert "pyautogui" in r.error.lower()


def test_desktop_screenshot_with_mocked_pyautogui(tmp_path, fake_pyautogui, monkeypatch):
    """Mock pyautogui.screenshot returns a fake image; verify save + ok."""
    monkeypatch.setenv("HIPPO_ENABLE_COMPUTER_USE", "1")  # SCAN-68: screenshot ora gated (commit 2efced6)
    fake_img = MagicMock()
    fake_img.size = (1920, 1080)
    fake_img.save = MagicMock()
    fake_pyautogui.screenshot.return_value = fake_img

    out_path = tmp_path / "shot.png"
    r = tools_extra.desktop_screenshot(save_path=str(out_path))
    assert r.ok is True
    assert r.extra["width"] == 1920
    assert r.extra["height"] == 1080
    fake_img.save.assert_called_once_with(out_path)


def test_desktop_screenshot_with_describe(tmp_path, fake_pyautogui, monkeypatch):
    """describe=True triggers vision_describe — verify the wiring."""
    monkeypatch.setenv("HIPPO_ENABLE_COMPUTER_USE", "1")  # SCAN-68: screenshot ora gated (commit 2efced6)
    fake_img = MagicMock()
    fake_img.size = (800, 600)
    fake_img.save = MagicMock()
    fake_pyautogui.screenshot.return_value = fake_img

    captured = {}

    def fake_vision_describe(image, prompt):
        captured["image"] = image
        captured["prompt"] = prompt
        return ToolResult(ok=True, output="a Windows desktop", extra={})

    monkeypatch.setattr(tools_extra, "vision_describe", fake_vision_describe)
    out_path = tmp_path / "shot2.png"
    r = tools_extra.desktop_screenshot(save_path=str(out_path),
                                         describe=True, prompt="What is here?")
    assert r.ok is True
    assert r.output == "a Windows desktop"
    assert captured["prompt"] == "What is here?"


# ---------------------------------------------------------------------------
# Vision describe — provider dispatch
# ---------------------------------------------------------------------------


def test_vision_describe_disabled(monkeypatch, tmp_path):
    """When vision is explicitly disabled, return early before image load."""
    # Ensure tools_extra._enabled('vision') returns False:
    monkeypatch.setenv("HIPPO_DISABLE_VISION", "1")
    monkeypatch.delenv("HIPPO_ENABLE_VISION", raising=False)
    img = tmp_path / "real.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 10)
    # Verify _enabled really sees vision as off
    assert tools_extra._enabled("vision", default=True) is False
    r = tools_extra.vision_describe(str(img))
    assert r.ok is False
    assert ("disabled" in r.error.lower() or "permission" in r.error.lower()
            or "vision" in r.error.lower())


def test_vision_describe_image_load_failure(monkeypatch, tmp_path):
    """A non-existent path → load failure → ok=False."""
    monkeypatch.delenv("HIPPO_DISABLE_VISION", raising=False)
    r = tools_extra.vision_describe(str(tmp_path / "no_such_image.png"))
    assert r.ok is False
    assert "cannot load" in r.error.lower()


def test_resolve_vision_model_env_override(monkeypatch):
    monkeypatch.setenv("HIPPO_VISION_MODEL", "custom-vision-7b")
    assert tools_extra._resolve_vision_model("anthropic") == "custom-vision-7b"


def test_resolve_vision_model_ollama_env_override(monkeypatch):
    monkeypatch.delenv("HIPPO_VISION_MODEL", raising=False)
    monkeypatch.setenv("OLLAMA_VISION_MODEL", "qwen2-vl:7b")
    assert tools_extra._resolve_vision_model("ollama") == "qwen2-vl:7b"


def test_resolve_vision_model_falls_back_to_table(monkeypatch):
    monkeypatch.delenv("HIPPO_VISION_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_VISION_MODEL", raising=False)
    out = tools_extra._resolve_vision_model("groq")
    assert out  # must be a non-empty string from VISION_MODELS


def test_resolve_vision_model_unknown_provider(monkeypatch):
    monkeypatch.delenv("HIPPO_VISION_MODEL", raising=False)
    out = tools_extra._resolve_vision_model("not-a-real-provider")
    assert out == ""


def test_vision_describe_provider_routing_anthropic(monkeypatch, tmp_path):
    """Forced anthropic → routes through _vision_anthropic."""
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 10)  # PNG header
    monkeypatch.setenv("HIPPO_LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("HIPPO_DISABLE_VISION", raising=False)

    captured = {}

    def fake_anthropic(b64, mt, prompt):
        captured["mt"] = mt
        captured["prompt"] = prompt
        return ToolResult(ok=True, output="describe-a", extra={"model": "test"})

    monkeypatch.setattr(tools_extra, "_vision_anthropic", fake_anthropic)
    r = tools_extra.vision_describe(str(img), prompt="summarise")
    assert r.ok is True
    assert r.output == "describe-a"
    assert captured["prompt"] == "summarise"
    assert captured["mt"] == "image/png"


def test_vision_describe_provider_routing_ollama(monkeypatch, tmp_path):
    img = tmp_path / "x.jpg"
    img.write_bytes(b"\xff\xd8\xff\xe0" + b"x" * 10)
    monkeypatch.setenv("HIPPO_LLM_PROVIDER", "ollama")

    def fake_ollama(b64, prompt):
        return ToolResult(ok=True, output="describe-ollama", extra={})

    monkeypatch.setattr(tools_extra, "_vision_ollama", fake_ollama)
    r = tools_extra.vision_describe(str(img), prompt="hi")
    assert r.ok is True
    assert r.output == "describe-ollama"


def test_vision_describe_provider_routing_openai_compat(monkeypatch, tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 10)
    monkeypatch.setenv("HIPPO_LLM_PROVIDER", "openai")

    def fake_openai_compat(provider, b64, mt, prompt):
        return ToolResult(ok=True, output=f"describe-{provider}", extra={})

    monkeypatch.setattr(tools_extra, "_vision_openai_compat", fake_openai_compat)
    r = tools_extra.vision_describe(str(img))
    assert r.ok is True
    assert r.output == "describe-openai"


def test_vision_describe_provider_raises_returns_error(monkeypatch, tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 10)
    monkeypatch.setenv("HIPPO_LLM_PROVIDER", "anthropic")

    def boom(*a, **kw):
        raise RuntimeError("anthropic offline")

    monkeypatch.setattr(tools_extra, "_vision_anthropic", boom)
    r = tools_extra.vision_describe(str(img))
    assert r.ok is False
    assert "vision call failed" in r.error


# ---------------------------------------------------------------------------
# webcam_snapshot — opt-in gating + cv2 import handling
# ---------------------------------------------------------------------------


def test_webcam_snapshot_disabled_by_default(monkeypatch):
    monkeypatch.delenv("HIPPO_ENABLE_WEBCAM", raising=False)
    r = tools_extra.webcam_snapshot()
    assert r.ok is False
    assert "disabled" in r.error.lower()


def test_webcam_snapshot_cv2_unavailable(monkeypatch):
    monkeypatch.setenv("HIPPO_ENABLE_WEBCAM", "1")
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *a, **kw):
        if name == "cv2":
            raise ImportError("no cv2 in CI")
        return real_import(name, *a, **kw)

    if "cv2" in sys.modules:
        del sys.modules["cv2"]
    monkeypatch.setattr(builtins, "__import__", fake_import)
    r = tools_extra.webcam_snapshot()
    assert r.ok is False
    assert "opencv" in r.error.lower()


def test_webcam_describe_propagates_snap_failure(monkeypatch):
    """If snapshot fails, webcam_describe returns the snap error directly."""
    monkeypatch.delenv("HIPPO_ENABLE_WEBCAM", raising=False)
    r = tools_extra.webcam_describe()
    assert r.ok is False  # webcam disabled


# ---------------------------------------------------------------------------
# extra_tools / all_tools registry
# ---------------------------------------------------------------------------


def test_extra_tools_registry_includes_all_specs():
    out = tools_extra.extra_tools()
    expected = {
        "fs_read_file", "fs_write_file", "fs_list_dir", "fs_search_files",
        "web_fetch", "web_search",
        "vision_describe",
        "webcam_snapshot", "webcam_describe",
        "desktop_screenshot", "desktop_click", "desktop_type", "desktop_key",
        "shell_run",
    }
    assert expected.issubset(set(out.keys()))


def test_all_tools_includes_default_plus_extras():
    out = tools_extra.all_tools()
    # Default tools are the python sandbox + submit_solution
    assert "run_python" in out
    assert "submit_solution" in out
    # Plus extras
    assert "fs_read_file" in out
    assert "web_fetch" in out


# ---------------------------------------------------------------------------
# shell_run — perm gate
# ---------------------------------------------------------------------------


def test_shell_run_disabled_by_default(monkeypatch):
    monkeypatch.delenv("HIPPO_ENABLE_SHELL", raising=False)
    r = tools_extra.shell_run("echo hi")
    assert r.ok is False
    assert "shell" in r.error.lower() and "disabled" in r.error.lower()


def test_shell_run_executes_when_enabled(monkeypatch):
    """When opt-in, shell_run runs the command and captures output."""
    monkeypatch.setenv("HIPPO_ENABLE_SHELL", "1")
    # Use a portable command — `python --version` works on all OSes.
    r = tools_extra.shell_run("python --version")
    assert r.ok is True
    # Output may be on stdout or stderr depending on Python version
    combined = (r.output or "") + (r.error or "")
    assert "Python" in combined


def test_shell_run_timeout_handling(monkeypatch):
    """A timeout exit returns a clear error message."""
    monkeypatch.setenv("HIPPO_ENABLE_SHELL", "1")
    import os as _os
    # Cross-platform sleep. Windows ``timeout /t`` requires an interactive
    # console (it errors out with "Input redirection is not supported"
    # under subprocess.run), so we use PowerShell's Start-Sleep instead,
    # which works headless. (Fixes CI #43 Windows job 2026-05-16.)
    if _os.name == "nt":
        cmd = "powershell -NoProfile -Command Start-Sleep -s 5"
    else:
        cmd = "sleep 5"
    r = tools_extra.shell_run(cmd, timeout_s=1)
    assert r.ok is False
    assert "timeout" in r.error.lower()


def test_enabled_helper(monkeypatch):
    """Verify _enabled accepts each truthy alias."""
    monkeypatch.setenv("HIPPO_ENABLE_FOO", "1")
    assert tools_extra._enabled("foo") is True
    monkeypatch.setenv("HIPPO_ENABLE_FOO", "true")
    assert tools_extra._enabled("foo") is True
    monkeypatch.setenv("HIPPO_ENABLE_FOO", "yes")
    assert tools_extra._enabled("foo") is True
    monkeypatch.setenv("HIPPO_ENABLE_FOO", "on")
    assert tools_extra._enabled("foo") is True
    monkeypatch.setenv("HIPPO_ENABLE_FOO", "0")
    assert tools_extra._enabled("foo") is False
    monkeypatch.delenv("HIPPO_ENABLE_FOO", raising=False)
    assert tools_extra._enabled("foo") is False
    # Default=True with no DISABLE override
    assert tools_extra._enabled("nonexistent_thing", default=True) is True
    # Default=True can be turned off explicitly
    monkeypatch.setenv("HIPPO_DISABLE_NONEXISTENT_THING", "1")
    assert tools_extra._enabled("nonexistent_thing", default=True) is False
