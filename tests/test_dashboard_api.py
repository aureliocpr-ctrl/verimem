"""Dashboard FastAPI smoke + contract tests via TestClient.

Critical routes only — the whole 38-endpoint matrix is left for follow-up.
We cover:

  • GET /                          (overview, w/ onboarding redirect)
  • GET /chat                      (HTML page renders)
  • GET /skills                    (HTML, empty store)
  • GET /episodes                  (HTML, empty store)
  • GET /api/settings/active       (JSON shape)
  • GET /api/settings/providers    (JSON + secrets-redaction)
  • GET /api/permissions           (JSON shape)
  • POST /api/permissions          (round-trip)
  • POST /api/skills/{id}/promote  (mutation, with 404 branch)
  • POST /api/skills/{id}/retire   (mutation, with 404 branch)
  • POST /api/sleep                (mocked consolidation)
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from engram import settings as user_settings
from engram.dashboard_routes.auth import get_session_token


@pytest.fixture
def isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(user_settings, "SETTINGS_FILE", tmp_path / "user_settings.json")
    yield tmp_path


@pytest.fixture
def fake_dashboard_agent(monkeypatch: pytest.MonkeyPatch):
    """Replace `dashboard._ag()` with a stub agent so we don't need real LLM."""
    from engram import dashboard as dash

    fake = MagicMock()
    fake.memory.count.return_value = 0
    fake.memory.all.return_value = []
    fake.memory.get.return_value = None
    fake.skills.count.return_value = 0
    fake.skills.all.return_value = []

    promoted_skill = MagicMock()
    promoted_skill.id = "sk-1"
    promoted_skill.status = "promoted"
    fake.skills.get.side_effect = lambda sid: promoted_skill if sid == "sk-1" else None

    fake.semantic.count.return_value = 0
    fake.skills.lineage_graph.return_value = MagicMock(
        nodes={"sk-1": {"name": "x"}}, edges={},
    )

    monkeypatch.setattr(dash, "_ag", lambda: fake)
    monkeypatch.setattr(dash, "_agent", fake, raising=False)
    return fake


@pytest.fixture
def client(isolated_settings, fake_dashboard_agent) -> TestClient:
    """TestClient bound to the FastAPI app with isolated settings + agent."""
    # Mark user as onboarded so `/` doesn't redirect.
    user_settings.save(user_settings.UserSettings(onboarded=True))
    from engram.dashboard import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# HTML pages — must render
# ---------------------------------------------------------------------------


def test_overview_renders(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Overview" in resp.text


def test_chat_page_renders(client: TestClient) -> None:
    resp = client.get("/chat")
    assert resp.status_code == 200
    assert "Chat" in resp.text


def test_skills_page_renders(client: TestClient) -> None:
    resp = client.get("/skills")
    assert resp.status_code == 200


def test_skills_page_uses_design_system(client: TestClient) -> None:
    """The new skills page is served from the Jinja2 template + dashboard.css.

    We assert the marker classes that only the new template emits. If someone
    accidentally reverts to the inline-HTML version this test will fail.
    """
    resp = client.get("/skills")
    assert resp.status_code == 200
    body = resp.text
    assert '/assets/dashboard.css' in body, "design-system CSS link missing"
    # Filter pills are unique to the new template — old version had none.
    assert 'filter-pill' in body
    assert 'kpi__label' in body
    # When the store is empty the empty-state card should be visible.
    assert 'No skills yet' in body or 'skills-grid' in body


def test_assets_css_served(client: TestClient) -> None:
    resp = client.get("/assets/dashboard.css")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/css")
    # Sanity: a couple of key tokens must be present.
    body = resp.text
    assert '--c-accent' in body
    assert '.skill-card' in body


def test_assets_skills_js_served(client: TestClient) -> None:
    resp = client.get("/assets/skills.js")
    assert resp.status_code == 200
    ctype = resp.headers["content-type"]
    assert "javascript" in ctype or ctype.startswith("application/")
    assert 'filter-pill' in resp.text  # client-side filter binding


def test_episodes_page_renders(client: TestClient) -> None:
    resp = client.get("/episodes")
    assert resp.status_code == 200


def test_overview_redirects_to_welcome_when_not_onboarded(
    isolated_settings, fake_dashboard_agent,
) -> None:
    user_settings.save(user_settings.UserSettings(onboarded=False))
    from engram.dashboard import app
    c = TestClient(app, follow_redirects=False)
    resp = c.get("/")
    assert resp.status_code == 302
    assert resp.headers["location"].endswith("/welcome")


# ---------------------------------------------------------------------------
# JSON APIs — settings, permissions
# ---------------------------------------------------------------------------


def test_settings_active_returns_provider_info(client: TestClient) -> None:
    resp = client.get("/api/settings/active")
    assert resp.status_code == 200
    data = resp.json()
    for k in ("provider", "forced", "configured", "executor_model",
              "dreamer_model", "critic_model"):
        assert k in data


def test_settings_providers_redacts_keys(
    isolated_settings, fake_dashboard_agent,
) -> None:
    """Re-asserts the redaction guarantee at the dashboard level."""
    user_settings.save(user_settings.UserSettings(
        onboarded=True,
        api_keys={"ANTHROPIC_API_KEY": "sk-redact-me-now-please"},
    ))
    from engram.dashboard import app
    c = TestClient(app)
    resp = c.get("/api/settings/providers")
    assert resp.status_code == 200
    body = resp.text
    # Raw secret must not appear anywhere.
    assert "sk-redact-me-now-please" not in body
    # The presence map must be there.
    assert resp.json()["current_settings"]["api_keys"] == {"ANTHROPIC_API_KEY": True}


def test_permissions_get_returns_known_shape(client: TestClient) -> None:
    resp = client.get("/api/permissions")
    assert resp.status_code == 200
    data = resp.json()
    for k in ("sandbox_enabled", "perm_filesystem", "perm_computer_use",
              "perm_webcam", "perm_shell", "perm_web", "perm_vision"):
        assert k in data


def test_permissions_post_round_trip(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST → GET → values match what we wrote.

    Cycle #151 follow-up (2026-05-19): auth disable per cycle #124
    secure-by-default flip.
    """
    monkeypatch.setenv("HIPPO_DASHBOARD_AUTH_DISABLED", "1")
    resp = client.post("/api/permissions", json={
        "sandbox_enabled": True,
        "perm_filesystem": "home",
        "perm_computer_use": True,
        "perm_webcam": False,
        "perm_shell": True,
        "perm_web": True,
        "perm_vision": False,
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    follow = client.get("/api/permissions").json()
    assert follow["perm_shell"] is True
    assert follow["perm_filesystem"] == "home"
    assert follow["perm_vision"] is False


def test_permissions_post_rejects_invalid_payload(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pydantic validation must catch wrong types.

    Cycle #151 follow-up (2026-05-19): cycle #124 secure-by-default
    flip — senza ``monkeypatch`` il POST riceve 401 (X-Hippo-Token
    mancante) prima della validazione pydantic 422 che il test vuole
    verificare.
    """
    monkeypatch.setenv("HIPPO_DASHBOARD_AUTH_DISABLED", "1")
    resp = client.post("/api/permissions", json={
        "sandbox_enabled": "not-a-bool",
        "perm_filesystem": "home",
    })
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Skill mutation routes
# ---------------------------------------------------------------------------


def test_skill_promote_known_id(client: TestClient,
                                 fake_dashboard_agent) -> None:
    resp = client.post("/api/skills/sk-1/promote",
                       headers={"X-Hippo-Token": get_session_token()})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "promoted"
    assert body["id"] == "sk-1"
    fake_dashboard_agent.skills.store.assert_called()


def test_feedback_dedups_skills_before_update_fitness(
    client: TestClient, fake_dashboard_agent,
) -> None:
    """REAL coverage del fix anti-double-count (cycle #17): POST /api/feedback
    deve chiamare update_fitness UNA volta per skill UNICO, non per occorrenza.
    Esercita davvero la route di chat.py — sostituisce i test tautologici su
    dict.fromkeys in test_skills_used_dedup_pattern.py, che NON toccavano
    chat.py (passavano anche col dedup rotto = falsa copertura)."""
    import time

    from engram.memory import Episode
    ep = Episode(
        id="turn-dedup", task_id="t", task_text="task con skill ripetute",
        outcome="success", final_answer="a", tokens_used=0,
        skills_used=["sk1", "sk1", "sk2", "sk1"], traces=[],
        created_at=time.time(),
    )
    fake_dashboard_agent.memory.get.return_value = ep
    fake_dashboard_agent.skills.update_fitness.reset_mock()

    from engram.dashboard_routes.auth import get_session_token
    resp = client.post("/api/feedback",
                       json={"episode_id": "turn-dedup", "kind": "up"},
                       headers={"X-Hippo-Token": get_session_token()})
    assert resp.status_code == 200, resp.text
    assert resp.json()["skills_updated"] == 2, "2 skill uniche, non 4 occorrenze"

    # update_fitness UNA volta per skill UNICO (sk1, sk2) — non 4
    assert fake_dashboard_agent.skills.update_fitness.call_count == 2
    called_sids = sorted(
        (c.args[0] if c.args else c.kwargs.get("skill_id"))
        for c in fake_dashboard_agent.skills.update_fitness.call_args_list
    )
    assert called_sids == ["sk1", "sk2"], called_sids


def test_skill_promote_unknown_id_404(client: TestClient) -> None:
    resp = client.post("/api/skills/does-not-exist/promote",
                       headers={"X-Hippo-Token": get_session_token()})
    assert resp.status_code == 404
    assert "not found" in resp.text.lower()


def test_skill_retire_known_id(client: TestClient,
                                fake_dashboard_agent) -> None:
    resp = client.post("/api/skills/sk-1/retire",
                       headers={"X-Hippo-Token": get_session_token()})
    assert resp.status_code == 200
    assert resp.json()["status"] == "retired"


def test_skill_retire_unknown_id_404(client: TestClient) -> None:
    resp = client.post("/api/skills/does-not-exist/retire",
                       headers={"X-Hippo-Token": get_session_token()})
    assert resp.status_code == 404


def test_skill_promote_requires_auth(client: TestClient) -> None:
    """Enterprise posture: mutating a skill (promote) requires the session
    token — the route was state-changing but UNGATED (route-audit 2026-06-06)."""
    resp = client.post("/api/skills/sk-1/promote")  # no token
    assert resp.status_code == 401


def test_skill_retire_requires_auth(client: TestClient) -> None:
    resp = client.post("/api/skills/sk-1/retire")  # no token
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Sleep cycle endpoint
# ---------------------------------------------------------------------------


def test_sleep_api_dispatches_to_consolidate(
    client: TestClient, fake_dashboard_agent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cycle #151 follow-up (2026-05-19): auth disable per cycle #124
    secure-by-default flip — senza ``monkeypatch`` il POST riceve 401
    prima del dispatch a ``consolidate``."""
    monkeypatch.setenv("HIPPO_DASHBOARD_AUTH_DISABLED", "1")
    fake_report = MagicMock()
    fake_report.n_episodes_replayed = 5
    fake_report.n_clusters = 2
    fake_report.n_nrem_skills = 1
    fake_report.n_rem_skills = 1
    fake_report.n_facts = 3
    fake_report.promoted = ["sk-a"]
    fake_report.retired = []
    fake_report.merged = []
    fake_report.duration_s = 0.5
    fake_report.tokens_used = 1234
    fake_dashboard_agent.consolidate.return_value = fake_report

    resp = client.post("/api/sleep")
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_episodes_replayed"] == 5
    assert body["promoted"] == ["sk-a"]
    assert body["tokens_used"] == 1234


def test_sleep_api_returns_500_on_error(
    client: TestClient, fake_dashboard_agent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FORGIA #189 — error responses no longer leak exception text.

    Only the exception class name + endpoint label are returned;
    the full traceback goes to server-side logs.

    Cycle #151 (2026-05-19) follow-up: cycle #124 ha flipped
    ``HIPPO_DASHBOARD_AUTH_DISABLED`` default da ``"1"`` a ``"0"``
    (secure-by-default), e questo test non era stato aggiornato. Senza
    auth-disable il POST veniva intercettato da ``verify_session_token``
    con 401 prima di toccare l'error path che FORGIA #189 verifica.
    Soluzione minima: ``monkeypatch`` per riportare auth disabled solo
    in questo test, mantenendo intatto il default secure in produzione.
    """
    monkeypatch.setenv("HIPPO_DASHBOARD_AUTH_DISABLED", "1")
    fake_dashboard_agent.consolidate.side_effect = RuntimeError("nope")
    resp = client.post("/api/sleep")
    assert resp.status_code == 500
    # Class name returned (stable, debuggable), but message text must NOT leak.
    assert "RuntimeError" in resp.text
    assert "nope" not in resp.text


# ---------------------------------------------------------------------------
# Chat endpoint — empty body branch
# ---------------------------------------------------------------------------


def test_chat_api_rejects_empty_task(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cycle #151 (2026-05-19) follow-up — stesso motivo di
    ``test_sleep_api_returns_500_on_error``: cycle #124 secure-by-default
    flip blocca con 401 il POST a ``/api/chat`` prima della validazione
    body. ``monkeypatch`` di ``HIPPO_DASHBOARD_AUTH_DISABLED=1`` riporta
    il test al branch empty-body che intende esercitare.
    """
    monkeypatch.setenv("HIPPO_DASHBOARD_AUTH_DISABLED", "1")
    resp = client.post("/api/chat", json={"task": "   "})
    assert resp.status_code == 400
    assert "empty" in resp.text.lower()


# ---------------------------------------------------------------------------
# CVE-009 — session token auth (X-Hippo-Token)
# ---------------------------------------------------------------------------


def test_auth_info_default_is_enabled_after_cycle124(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cycle #124 (2026-05-17) secure-by-default flip: il default di
    ``HIPPO_DASHBOARD_AUTH_DISABLED`` ora è ``"0"`` → auth REQUIRED.
    Il test originale (``..._default_disabled``) era stato scritto
    quando il default era insecure-by-default. Cycle #151 (2026-05-19)
    rinomina + aggiorna l'assertion per riflettere il vero default
    corrente. La docstring del modulo auth.py riga 98-121 documenta
    questo invariante.

    Cycle 167 (2026-05-19): explicitly delenv the var so a prior test
    that leaked it into the process env (cf cleanup bug fixed in
    ``tests/test_auth_secure_default.py::clean_env``) cannot make this
    test pass-or-fail based on collection order.
    """
    monkeypatch.delenv("HIPPO_DASHBOARD_AUTH_DISABLED", raising=False)
    from engram.dashboard import app
    c = TestClient(app)
    resp = c.get("/api/auth/info")
    assert resp.status_code == 200
    body = resp.json()
    assert body["auth_required"] is True, (
        "Cycle #124 secure-by-default: auth must be REQUIRED unless the "
        "operator explicitly sets HIPPO_DASHBOARD_AUTH_DISABLED=1. "
        f"Got body={body!r}"
    )
    assert body["token_file"].endswith("session.token")


def test_state_changing_endpoint_rejects_when_auth_enabled(
    isolated_settings, fake_dashboard_agent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When HIPPO_DASHBOARD_AUTH_DISABLED=0, POST without X-Hippo-Token → 401."""
    monkeypatch.setenv("HIPPO_DASHBOARD_AUTH_DISABLED", "0")
    monkeypatch.setenv("HIPPO_DASHBOARD_TOKEN", "test-token-deadbeef")
    user_settings.save(user_settings.UserSettings(onboarded=True))
    from engram import dashboard as dash
    monkeypatch.setattr(dash, "_SESSION_TOKEN", None, raising=False)
    c = TestClient(dash.app)
    resp = c.post("/api/sleep")
    assert resp.status_code == 401
    assert "token" in resp.text.lower()


def test_state_changing_endpoint_accepts_valid_token(
    isolated_settings, fake_dashboard_agent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When auth is on, the right token unlocks the call."""
    monkeypatch.setenv("HIPPO_DASHBOARD_AUTH_DISABLED", "0")
    monkeypatch.setenv("HIPPO_DASHBOARD_TOKEN", "test-token-deadbeef")
    user_settings.save(user_settings.UserSettings(onboarded=True))
    from engram import dashboard as dash
    monkeypatch.setattr(dash, "_SESSION_TOKEN", None, raising=False)
    fake_dashboard_agent.consolidate.return_value = MagicMock(
        n_episodes_replayed=0, n_clusters=0, n_nrem_skills=0, n_rem_skills=0,
        n_facts=0, promoted=[], retired=[], merged=[],
        duration_s=0.0, tokens_used=0,
    )
    c = TestClient(dash.app)
    resp = c.post("/api/sleep", headers={"X-Hippo-Token": "test-token-deadbeef"})
    assert resp.status_code == 200


def test_read_only_endpoints_unaffected_by_auth(
    isolated_settings, fake_dashboard_agent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GETs that just read state remain unauthenticated."""
    monkeypatch.setenv("HIPPO_DASHBOARD_AUTH_DISABLED", "0")
    monkeypatch.setenv("HIPPO_DASHBOARD_TOKEN", "test-token-deadbeef")
    user_settings.save(user_settings.UserSettings(onboarded=True))
    from engram import dashboard as dash
    monkeypatch.setattr(dash, "_SESSION_TOKEN", None, raising=False)
    c = TestClient(dash.app)
    # /api/permissions is GET — passes through
    resp = c.get("/api/permissions")
    assert resp.status_code == 200
    # The /metrics page (HTML) is also GET — passes through
    resp = c.get("/metrics")
    assert resp.status_code == 200


def test_invalid_token_rejected_constant_time(
    isolated_settings, fake_dashboard_agent,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HIPPO_DASHBOARD_AUTH_DISABLED", "0")
    monkeypatch.setenv("HIPPO_DASHBOARD_TOKEN", "right-token")
    user_settings.save(user_settings.UserSettings(onboarded=True))
    from engram import dashboard as dash
    monkeypatch.setattr(dash, "_SESSION_TOKEN", None, raising=False)
    c = TestClient(dash.app)
    resp = c.post("/api/permissions",
                  headers={"X-Hippo-Token": "wrong-token"},
                  json={"sandbox_enabled": True, "perm_filesystem": "strict"})
    assert resp.status_code == 401
