"""TDD — _apply_preset_to_settings deve resettare anche base_url (rescan2 MEDIUM
dashboard_routes/settings.py:268-282, 2026-06-02).

Un preset definisce provider+model e resetta gia gli override per-stage; ma
lasciava cur.base_url invariato -> un base_url stale del provider precedente
(es. moonshot) finiva proiettato sul base_url_env del nuovo provider -> endpoint
sbagliato. Fix coerente col set-OR-POP di apply_to_env (settings.py): il preset
azzera base_url, cosi apply_to_env poppa l'override stale.
"""
from __future__ import annotations

from verimem.dashboard_routes.settings import _apply_preset_to_settings
from verimem.settings import UserSettings


def test_preset_resets_base_url():
    cur = UserSettings(provider="moonshot",
                       base_url="https://old.moonshot.example/v1", model="x")
    _apply_preset_to_settings(cur, {"provider": "openai", "model": "gpt-5.4-mini"})
    assert cur.base_url == "", (
        "il preset deve resettare base_url (stale del provider precedente)"
    )
    # gli altri reset gia presenti restano corretti
    assert cur.provider == "openai"
    assert cur.model == "gpt-5.4-mini"
    assert cur.model_critic == ""
