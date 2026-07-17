"""TDD — presets_apply resetta le override model per-stage (scan 68-Opus P2).
Bug: applicando un preset (provider+model globali) le override per-stage
(model_executor/dreamer/critic) restavano invariate -> dopo uno switch a
ollama, model_critic poteva restare un modello claude -> apply_to_env esporta
HIPPO_MODEL_CRITIC=claude-* con provider=ollama -> config incoerente.
Un preset definisce il modello per TUTTI gli stage -> reset delle override.
Test HERMETIC (funzione pura su UserSettings, no HTTP, no file, no DB)."""
from __future__ import annotations

from verimem import settings as user_settings
from verimem.dashboard_routes.settings import _apply_preset_to_settings


def test_apply_preset_resets_per_stage_models():
    cur = user_settings.UserSettings(
        provider="claude", model="claude-3-opus",
        model_executor="claude-3-opus", model_dreamer="claude-3-haiku",
        model_critic="claude-3-sonnet",
    )
    _apply_preset_to_settings(
        cur, {"id": "ollama-llama3", "provider": "ollama", "model": "llama3"})
    assert cur.provider == "ollama"
    assert cur.model == "llama3"
    assert cur.ollama_model == "llama3"
    # le override per-stage NON devono restare puntate ai modelli claude
    assert cur.model_executor == "", "override executor deve essere resettata"
    assert cur.model_dreamer == "", "override dreamer deve essere resettata"
    assert cur.model_critic == "", "override critic deve essere resettata"


def test_apply_preset_non_ollama_sets_provider_and_clears_stage():
    cur = user_settings.UserSettings(
        provider="ollama", model="llama3", ollama_model="llama3",
        model_critic="llama3",
    )
    _apply_preset_to_settings(
        cur, {"id": "claude-opus", "provider": "claude", "model": "claude-3-opus"})
    assert cur.provider == "claude"
    assert cur.model == "claude-3-opus"
    assert cur.model_critic == ""


def test_apply_to_env_clears_stale_per_stage_model(monkeypatch):
    # AUDIT (gap agente -> bug piu' profondo): il reset dell'oggetto settings NON
    # basta se apply_to_env non PULISCE la env-var stale. Con model_critic="",
    # un HIPPO_MODEL_CRITIC=claude-* precedente deve essere RIMOSSO da os.environ.
    import os

    from verimem import settings as us
    monkeypatch.setenv("HIPPO_MODEL_CRITIC", "claude-3-opus")  # stale da preset prima
    monkeypatch.setenv("HIPPO_MODEL_EXECUTOR", "claude-3-opus")
    us.apply_to_env(us.UserSettings(provider="ollama", model="llama3"))  # per-stage ""
    assert os.environ.get("HIPPO_MODEL_CRITIC") is None, "HIPPO_MODEL_CRITIC stale non pulita"
    assert os.environ.get("HIPPO_MODEL_EXECUTOR") is None, "HIPPO_MODEL_EXECUTOR stale non pulita"


def test_preset_to_env_chain_no_claude_under_ollama(monkeypatch):
    # Catena end-to-end (quella che l'agente segnalava non coperta): preset ollama
    # -> reset per-stage -> apply_to_env -> nessun modello claude resta nelle env per-stage.
    import os

    from verimem import settings as us
    from verimem.dashboard_routes.settings import _apply_preset_to_settings
    monkeypatch.setenv("HIPPO_MODEL_CRITIC", "claude-3-opus")
    cur = us.UserSettings(provider="claude", model="claude-3-opus",
                          model_critic="claude-3-opus", model_executor="claude-3-haiku")
    _apply_preset_to_settings(cur, {"id": "ollama-llama3", "provider": "ollama", "model": "llama3"})
    us.apply_to_env(cur)
    for var in ("HIPPO_MODEL_CRITIC", "HIPPO_MODEL_EXECUTOR", "HIPPO_MODEL_DREAMER"):
        v = os.environ.get(var)
        assert not (v and "claude" in v), f"{var}={v!r}: modello claude sotto provider ollama"


def test_apply_to_env_full_projection_clears_global_and_ollama(monkeypatch):
    # AUDIT round 2 (agente empirico): la proiezione deve essere COMPLETA — un
    # model="" / ollama_model="" deve RIMUOVERE HIPPO_MODEL / OLLAMA_MODEL stale,
    # non solo i per-stage (prima erano set-only -> restavano valori vecchi).
    import os

    from verimem import settings as us
    monkeypatch.setenv("HIPPO_MODEL", "claude-opus-4")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3")
    monkeypatch.setenv("OLLAMA_HOST", "http://stale:11434")
    us.apply_to_env(us.UserSettings(provider="claude"))  # tutto vuoto tranne provider
    assert os.environ.get("HIPPO_MODEL") is None, "HIPPO_MODEL stale non pulito"
    assert os.environ.get("OLLAMA_MODEL") is None, "OLLAMA_MODEL stale non pulito"
    assert os.environ.get("OLLAMA_HOST") is None, "OLLAMA_HOST stale non pulito"
