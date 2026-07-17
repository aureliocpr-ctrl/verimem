"""TDD — apply_to_env deve fare set-OR-POP anche sul base_url (rescan2 MEDIUM
settings.py:108-113, 2026-06-02).

Il fix SCAN-68 round-2 ha reso set-OR-POP i model/host (un valore vuoto RIMUOVE
la env-var stale), ma il base_url provider-specifico era ancora solo-SET: un
base_url svuotato lasciava l'override (es. MOONSHOT_BASE_URL) stale in os.environ
-> config incoerente dopo un cambio.

Fix aggiusta-non-rovina: base_url segue lo stesso set-OR-POP, risolvendo
base_url_env dal provider corrente. HERMETIC (monkeypatch os.environ).
"""
from __future__ import annotations

import os

from verimem.settings import UserSettings, apply_to_env


def test_base_url_set_when_present(monkeypatch):
    monkeypatch.delenv("MOONSHOT_BASE_URL", raising=False)
    apply_to_env(UserSettings(provider="moonshot",
                              base_url="https://api.moonshot.ai/v1"))
    assert os.environ.get("MOONSHOT_BASE_URL") == "https://api.moonshot.ai/v1"


def test_base_url_popped_when_emptied(monkeypatch):
    # override stale gia presente -> base_url svuotato deve RIMUOVERLO
    monkeypatch.setenv("MOONSHOT_BASE_URL", "https://stale.example/v1")
    apply_to_env(UserSettings(provider="moonshot", base_url=""))
    assert "MOONSHOT_BASE_URL" not in os.environ, (
        "base_url svuotato deve poppare l'override stale (set-OR-POP)"
    )
