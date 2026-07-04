"""TDD — desktop_screenshot deve essere gateato da HIPPO_ENABLE_COMPUTER_USE (scan 68-Opus 2026-06-02).

desktop_click/desktop_type/desktop_key sono gateati con _enabled("computer_use") (default OFF),
ma desktop_screenshot NO => catturava lo schermo (info-disclosure) senza opt-in dell'utente.
HERMETIC: pyautogui e' stubato (nessuna cattura schermo reale), env controllato.
"""
from __future__ import annotations

import sys


class _FakeImg:
    size = (2, 2)

    def save(self, p):
        import pathlib
        pathlib.Path(p).write_bytes(b"x")


class _FakePyAutoGui:
    FAILSAFE = False
    PAUSE = 0.0

    def screenshot(self):
        return _FakeImg()


def test_desktop_screenshot_gated_by_computer_use(tmp_path, monkeypatch):
    monkeypatch.delenv("HIPPO_ENABLE_COMPUTER_USE", raising=False)
    monkeypatch.setitem(sys.modules, "pyautogui", _FakePyAutoGui())
    from engram.tools_extra import desktop_screenshot
    res = desktop_screenshot(save_path=str(tmp_path / "s.png"))
    assert res.ok is False, f"screenshot NON gateato (schermo catturato senza opt-in): {res.output!r}"
    assert "computer use" in (res.error or "").lower() or "computer_use" in (res.error or "").lower(), \
        f"errore gate inatteso: {res.error!r}"


def test_desktop_screenshot_works_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setenv("HIPPO_ENABLE_COMPUTER_USE", "1")
    monkeypatch.setitem(sys.modules, "pyautogui", _FakePyAutoGui())
    from engram.tools_extra import desktop_screenshot
    res = desktop_screenshot(save_path=str(tmp_path / "s.png"))
    assert res.ok is True, f"con gate abilitato deve funzionare: {res.error!r}"
