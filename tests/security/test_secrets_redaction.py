"""Secrets-redaction tests for the dashboard /api/settings/providers endpoint.

Covers Sprint 1 hardening (CVE-004 / SEC V15):

  • The HTTP response must NEVER include raw api_keys values.
  • The response IS allowed to include the {env_name: bool} presence map.
  • UserSettings save/load round-trip preserves keys on disk.
  • The disk file (user_settings.json) keeps the values — only the HTTP
    response is redacted.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from engram import settings as user_settings


@pytest.fixture
def isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect SETTINGS_FILE to a tmp path so tests don't trash real settings."""
    settings_path = tmp_path / "user_settings.json"
    monkeypatch.setattr(user_settings, "SETTINGS_FILE", settings_path)
    yield settings_path


def test_user_settings_round_trip_preserves_keys(isolated_settings: Path) -> None:
    """save/load on disk preserves api_keys verbatim."""
    s = user_settings.UserSettings(
        provider="anthropic",
        api_keys={"ANTHROPIC_API_KEY": "sk-ant-secret-123"},
    )
    user_settings.save(s)
    loaded = user_settings.load()
    assert loaded.api_keys == {"ANTHROPIC_API_KEY": "sk-ant-secret-123"}
    assert loaded.provider == "anthropic"


def test_providers_endpoint_redacts_api_keys(
    isolated_settings: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GET /api/settings/providers must replace api_key values with bool flags.

    The raw secret must NOT appear anywhere in the JSON response body.
    """
    # Stub a key on disk so the response would include it without redaction.
    s = user_settings.UserSettings(
        provider="anthropic",
        api_keys={
            "ANTHROPIC_API_KEY": "sk-ant-secret-very-long-token-do-not-leak",
            "OPENAI_API_KEY": "sk-openai-also-secret",
            "EMPTY_KEY": "",  # presence=False
        },
    )
    user_settings.save(s)

    # Import the FastAPI app *after* SETTINGS_FILE has been monkeypatched.
    from engram.dashboard import app
    client = TestClient(app)
    resp = client.get("/api/settings/providers")
    assert resp.status_code == 200
    payload = resp.json()
    assert "current_settings" in payload
    cs = payload["current_settings"]
    assert "api_keys" in cs
    # The redacted shape: {env_name: bool}, never {env_name: "secret"}.
    assert cs["api_keys"] == {
        "ANTHROPIC_API_KEY": True,
        "OPENAI_API_KEY": True,
        "EMPTY_KEY": False,
    }
    # And the raw bytes of the response must not contain the secret.
    body = resp.content.decode("utf-8")
    assert "sk-ant-secret-very-long-token-do-not-leak" not in body
    assert "sk-openai-also-secret" not in body


def test_providers_endpoint_handles_empty_api_keys(
    isolated_settings: Path,
) -> None:
    """No keys configured → empty dict (not None / not missing key)."""
    user_settings.save(user_settings.UserSettings())
    from engram.dashboard import app
    client = TestClient(app)
    resp = client.get("/api/settings/providers")
    assert resp.status_code == 200
    cs = resp.json()["current_settings"]
    assert cs["api_keys"] == {}


def test_settings_active_endpoint_does_not_leak_keys(
    isolated_settings: Path,
) -> None:
    """/api/settings/active returns provider/model info — must not include keys."""
    user_settings.save(user_settings.UserSettings(
        api_keys={"ANTHROPIC_API_KEY": "sk-must-not-leak-here-either"},
    ))
    from engram.dashboard import app
    client = TestClient(app)
    resp = client.get("/api/settings/active")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert "sk-must-not-leak-here-either" not in body
