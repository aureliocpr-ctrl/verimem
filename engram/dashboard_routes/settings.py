"""/settings page + provider/model/permissions/presets/fallback APIs.

This file is one slice of the legacy `dashboard.py` monolith. Every route
here mutates user-level settings (provider keys, sandbox toggles, presets) —
keeping them grouped lets a security reviewer audit the whole settings
surface in one place.
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .. import settings as user_settings
from ..observability import get_log
from .auth import verify_session_token
from .layout import page

log = get_log()


def _safe_error(exc: Exception, where: str) -> str:
    """FORGIA #189 — sanitize exception messages for HTTP responses."""
    log.exception("settings_api_error", where=where,
                   exc_type=type(exc).__name__)
    return f"{where}: {type(exc).__name__}"

# Curated model presets — quick switch buttons in /settings.
# Updated 2026-05: includes Claude 4.7, Gemini 2/3, Grok 4, GPT-5 (when key works),
# DeepSeek V4, Kimi K2, Llama 4 (via OpenRouter or providers).
PRESETS: list[dict[str, Any]] = [
    # Free / local
    {"id": "ollama-qwen-1.5b", "label": "Qwen 2.5 1.5B (local)",
     "provider": "ollama", "model": "qwen2.5:1.5b", "tier": "free / tiny"},
    {"id": "ollama-qwen-7b", "label": "Qwen 2.5 7B (local)",
     "provider": "ollama", "model": "qwen2.5:7b-instruct", "tier": "free / small"},
    {"id": "groq-llama-70b", "label": "Llama 3.3 70B",
     "provider": "groq", "model": "llama-3.3-70b-versatile", "tier": "free tier"},
    {"id": "groq-qwen-32b", "label": "Qwen 3 32B (Groq)",
     "provider": "groq", "model": "qwen/qwen3-32b", "tier": "free tier"},
    {"id": "gemini-flash", "label": "Gemini 1.5 Flash",
     "provider": "gemini", "model": "gemini-1.5-flash", "tier": "free tier"},
    # Paid — entry
    {"id": "claude-haiku", "label": "Claude Haiku 4.5",
     "provider": "anthropic", "model": "claude-haiku-4-5-20251001", "tier": "paid · cheap"},
    {"id": "deepseek-chat", "label": "DeepSeek V4 Flash",
     "provider": "deepseek", "model": "deepseek-v4-flash", "tier": "paid · cheap"},
    {"id": "kimi", "label": "Kimi K2",
     "provider": "moonshot", "model": "kimi-k2-0915-preview", "tier": "paid"},
    {"id": "openai-gpt-mini", "label": "GPT-4o mini",
     "provider": "openai", "model": "gpt-4o-mini", "tier": "paid · cheap"},
    # Paid — premium (Opus 4.7 = default sistema; gli altri sono scelta esplicita user)
    {"id": "claude-opus", "label": "Claude Opus 4.7 (default)",
     "provider": "anthropic", "model": "claude-opus-4-7", "tier": "paid · top"},
    {"id": "claude-sonnet", "label": "Claude Sonnet 4.6",
     "provider": "anthropic", "model": "claude-sonnet-4-6", "tier": "paid · pro"},
    {"id": "deepseek-reasoner", "label": "DeepSeek V4 Pro",
     "provider": "deepseek", "model": "deepseek-v4-pro", "tier": "paid · pro"},
    {"id": "openrouter-grok", "label": "Grok 4 (via OpenRouter)",
     "provider": "openrouter", "model": "x-ai/grok-4", "tier": "paid · pro"},
    {"id": "openai-gpt", "label": "GPT-4o",
     "provider": "openai", "model": "gpt-4o", "tier": "paid · pro"},
]


_SETTINGS_HTML = """
<h1>⚙ Settings</h1>

<div class="card">
  <h2 style="border:0;margin-top:0;">Active LLM</h2>
  <div id="active-summary" style="color:var(--dim);font-size:13px;">loading…</div>
</div>

<div class="card">
  <h2 style="border:0;margin-top:0;">⚡ Quick model switcher</h2>
  <p style="color:var(--dim);font-size:13px;margin-top:0;">
    One-click switch between curated presets. Free options first, scale up
    when needed. Requires the matching API key set in the Provider section below.
  </p>
  <div id="presets" style="display:flex;flex-wrap:wrap;gap:8px;"></div>
</div>

<div class="card">
  <h2 style="border:0;margin-top:0;">🔁 Fallback chain</h2>
  <p style="color:var(--dim);font-size:13px;margin-top:0;">
    When the active provider hits rate-limit / quota / 5xx, Engram transparently
    tries the next configured provider in this list. Order matters — first
    matching wins.
  </p>
  <div id="fallback-chain" style="display:flex;flex-wrap:wrap;gap:8px;
       min-height:36px;border:1px dashed #30363d;border-radius:4px;padding:6px;">
  </div>
  <div style="margin-top:8px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
    <select id="fallback-add" style="background:#0a0d12;color:var(--text);
      border:1px solid #30363d;border-radius:4px;padding:6px 10px;"></select>
    <button id="fallback-add-btn" style="background:#21262d;color:var(--text);
      border:1px solid #30363d;padding:6px 12px;border-radius:4px;cursor:pointer;">
      + Add to chain</button>
    <button id="fallback-save" style="background:var(--accent);color:#0e1116;
      border:0;padding:6px 14px;border-radius:4px;cursor:pointer;font-weight:700;">
      💾 Save chain</button>
    <span id="fallback-status" style="color:var(--dim);"></span>
  </div>
</div>

<div class="card" id="permissions-card">
  <h2 style="border:0;margin-top:0;">🔐 Permissions / Sandbox</h2>
  <p style="color:var(--dim);font-size:13px;margin-top:0;">
    Master toggle off = the agent has full unrestricted access to your
    computer (filesystem, shell, computer use, webcam, web, vision).
    Use granular toggles below for fine-grained control.
  </p>
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;">
    <label style="font-size:18px;font-weight:700;">Sandbox</label>
    <label class="switch">
      <input type="checkbox" id="sandbox_enabled">
      <span class="slider"></span>
    </label>
    <span id="sandbox-status" style="color:var(--dim);"></span>
  </div>
  <div id="perm-grid" style="display:grid;grid-template-columns:200px 1fr;gap:8px;align-items:center;"></div>
  <div style="margin-top:14px;display:flex;gap:8px;">
    <button id="perm-save" style="background:var(--accent);color:#0e1116;border:0;
      padding:8px 18px;border-radius:4px;cursor:pointer;font-weight:700;">
      💾 Save permissions</button>
    <button id="perm-unleash" style="background:#dc2626;color:white;border:0;
      padding:8px 18px;border-radius:4px;cursor:pointer;">
      🔓 Unleash (all permissions ON)</button>
    <button id="perm-lockdown" style="background:#16a34a;color:white;border:0;
      padding:8px 18px;border-radius:4px;cursor:pointer;">
      🔒 Lockdown (sandbox strict)</button>
    <span id="perm-status" style="color:var(--dim);align-self:center;margin-left:auto;"></span>
  </div>
</div>

<style>
  .switch { position: relative; display: inline-block; width: 50px; height: 26px; }
  .switch input { opacity: 0; width: 0; height: 0; }
  .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
    background-color: #444; transition: .2s; border-radius: 26px; }
  .slider:before { position: absolute; content: ""; height: 20px; width: 20px; left: 3px;
    bottom: 3px; background-color: white; transition: .2s; border-radius: 50%; }
  input:checked + .slider { background-color: var(--accent); }
  input:checked + .slider:before { transform: translateX(24px); }
</style>

<div class="card">
  <h2 style="border:0;margin-top:0;">Provider</h2>
  <p style="color:var(--dim); font-size:13px; margin-top:0;">
    Pick a provider, enter its API key (or run Ollama locally — no key needed),
    and HippoAgent will use it for new tasks. Switch live, no restart needed.
  </p>

  <div style="display:grid;grid-template-columns:160px 1fr;gap:10px;align-items:center;">
    <label>Provider</label>
    <select id="provider" style="background:#0a0d12;color:var(--text);border:1px solid #30363d;
      border-radius:4px;padding:8px;font-family:inherit;"></select>

    <label>API key</label>
    <input id="api_key" type="password" placeholder="leave empty to keep current"
      style="background:#0a0d12;color:var(--text);border:1px solid #30363d;
      border-radius:4px;padding:8px;font-family:inherit;">

    <label id="base_url_label">Base URL <span style="color:var(--dim);">(optional)</span></label>
    <input id="base_url" placeholder="custom endpoint, e.g. https://your-azure-host/v1"
      style="background:#0a0d12;color:var(--text);border:1px solid #30363d;
      border-radius:4px;padding:8px;font-family:inherit;">

    <label>Model (all stages)</label>
    <select id="model_select" style="background:#0a0d12;color:var(--text);border:1px solid #30363d;
      border-radius:4px;padding:8px;font-family:inherit;">
      <option value="">(provider default)</option>
    </select>

    <label>Custom model id <span style="color:var(--dim);">(overrides dropdown)</span></label>
    <input id="model_text" placeholder="e.g. gpt-4o, qwen2.5:7b, claude-haiku-4-5-20251001"
      style="background:#0a0d12;color:var(--text);border:1px solid #30363d;
      border-radius:4px;padding:8px;font-family:inherit;">

    <label>Executor model <span style="color:var(--dim);">(opt.)</span></label>
    <input id="model_executor"
      style="background:#0a0d12;color:var(--text);border:1px solid #30363d;
      border-radius:4px;padding:8px;font-family:inherit;">

    <label>Dreamer model <span style="color:var(--dim);">(opt., smarter)</span></label>
    <input id="model_dreamer"
      style="background:#0a0d12;color:var(--text);border:1px solid #30363d;
      border-radius:4px;padding:8px;font-family:inherit;">

    <label>Critic model <span style="color:var(--dim);">(opt., cheap)</span></label>
    <input id="model_critic"
      style="background:#0a0d12;color:var(--text);border:1px solid #30363d;
      border-radius:4px;padding:8px;font-family:inherit;">
  </div>

  <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap;">
    <button id="discover" style="background:#21262d;color:var(--text);border:1px solid #30363d;
      padding:8px 14px;border-radius:4px;cursor:pointer;">🔍 Discover models</button>
    <button id="test" style="background:#21262d;color:var(--text);border:1px solid #30363d;
      padding:8px 14px;border-radius:4px;cursor:pointer;">🧪 Test connection</button>
    <button id="save" style="background:var(--accent);color:#0e1116;border:0;
      padding:8px 18px;border-radius:4px;cursor:pointer;font-weight:700;">💾 Save</button>
    <span id="status" style="color:var(--dim);align-self:center;margin-left:auto;"></span>
  </div>
</div>

<div class="card">
  <h2 style="border:0;margin-top:0;">All providers</h2>
  <p style="color:var(--dim);font-size:13px;margin-top:0;">
    Status of every known provider. Click any row to set it as active.
  </p>
  <div id="providers-table">loading…</div>
</div>

<script src="/static/settings.js" defer></script>
"""


# ----- Pydantic bodies ----------------------------------------------------


class SettingsBody(BaseModel):
    provider: str = ""
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    model_executor: str = ""
    model_dreamer: str = ""
    model_critic: str = ""


class PermissionsBody(BaseModel):
    sandbox_enabled: bool = True
    perm_filesystem: str = "home"
    perm_computer_use: bool = False
    perm_webcam: bool = False
    perm_shell: bool = False
    perm_web: bool = True
    perm_vision: bool = True


class FallbackChainBody(BaseModel):
    fallback_providers: list[str] = []


class PresetApply(BaseModel):
    preset_id: str


# ----- Helpers ------------------------------------------------------------


def _env_for_provider(provider: str) -> str | None:
    from ..llm import PROVIDERS, _canonical
    p = _canonical(provider)
    if p == "anthropic":
        return "ANTHROPIC_API_KEY"
    if p == "ollama":
        return None  # no api key
    spec = PROVIDERS.get(p)
    return spec["env"] if spec else None


def _apply_preset_to_settings(cur: Any, preset: dict[str, Any]) -> None:
    """Apply a preset (provider+model) to a UserSettings in-place.

    SCAN-68 FIX 2026-06-02 (NONNA): un preset definisce il modello per TUTTI
    gli stage -> resetta le override per-stage (executor/dreamer/critic),
    altrimenti restano puntate ai modelli di un altro provider (es. switch a
    ollama lascia model_critic=claude-* -> HIPPO_MODEL_CRITIC incoerente).
    """
    cur.provider = preset["provider"]
    cur.model = preset["model"]
    cur.model_executor = ""
    cur.model_dreamer = ""
    cur.model_critic = ""
    # SCAN-68 round 2: resetta anche base_url (stale del provider precedente);
    # con apply_to_env set-OR-POP, base_url="" poppa l'override stale.
    cur.base_url = ""
    if preset["provider"] == "ollama":
        cur.ollama_model = preset["model"]


# ----- Routes -------------------------------------------------------------


def register(app: FastAPI, templates: Jinja2Templates) -> None:  # noqa: ARG001
    @app.get("/settings", response_class=HTMLResponse)
    def settings_page() -> HTMLResponse:
        return page("Settings", _SETTINGS_HTML)

    @app.get("/api/settings/active")
    def settings_active() -> JSONResponse:
        from ..llm import _autodetect_provider, _canonical, is_configured, resolve_model
        forced = os.environ.get("HIPPO_LLM_PROVIDER", "").strip()
        provider = _canonical(forced) if forced else _autodetect_provider()
        return JSONResponse({
            "provider": provider,
            "forced": bool(forced),
            "configured": is_configured(provider),
            "executor_model": resolve_model("executor"),
            "dreamer_model": resolve_model("dreamer"),
            "critic_model": resolve_model("critic"),
        })

    @app.get("/api/settings/providers")
    def settings_providers() -> JSONResponse:
        from ..llm import ALIASES, PROVIDERS, is_configured, list_providers
        aliases_by: dict[str, list[str]] = {}
        for alias, canon in ALIASES.items():
            aliases_by.setdefault(canon, []).append(alias)
        out = []
        for name in list_providers():
            if name == "mock":
                continue
            if name == "anthropic":
                env, default = "ANTHROPIC_API_KEY", "claude-haiku-4-5-..."
            elif name == "ollama":
                env, default = "OLLAMA_HOST", "(local)"
            else:
                spec = PROVIDERS.get(name, {})
                env = spec.get("env", "")
                default = spec.get("default_model", "")
            out.append({
                "name": name,
                "env": env,
                "default_model": default,
                "configured": is_configured(name),
                "aliases": aliases_by.get(name, []),
            })
        cur = user_settings.load()
        # CVE-004 / SEC V15 fix: never expose API keys in HTTP responses.
        # Replace with a {env_name: bool} map indicating presence, not value.
        safe = cur.to_dict()
        safe["api_keys"] = {env: bool(val) for env, val in (cur.api_keys or {}).items()}
        return JSONResponse({"providers": out, "current_settings": safe})

    @app.get("/api/settings/models")
    def settings_models(provider: str) -> JSONResponse:
        from ..llm import list_models_for_provider
        try:
            models = list_models_for_provider(provider, timeout=20.0)
        except Exception as exc:
            return JSONResponse({"error": _safe_error(exc, "list_models")},
                                 status_code=400)
        return JSONResponse({"models": models})

    @app.get("/api/settings/recommended_models")
    def settings_recommended_models(provider: str | None = None) -> JSONResponse:
        """Curated model list from `providers.yaml` — no provider round-trip.

        When `provider` is given, returns only that provider's curated models.
        Otherwise returns the full map {provider_name: [model dicts]}.

        Use this in the UI to populate model selectors without paying the
        latency of a real `/v1/models` call to every configured provider.
        """
        from ..provider_registry import PROVIDERS_BY_NAME

        def _serialise(spec) -> list[dict]:
            return [m.model_dump() for m in spec.recommended_models]

        if provider:
            spec = PROVIDERS_BY_NAME.get(provider.lower().strip())
            if spec is None:
                return JSONResponse(
                    {"error": f"unknown provider: {provider}"},
                    status_code=404,
                )
            return JSONResponse({
                "provider": spec.name,
                "default_model": spec.default_model,
                "recommended_models": _serialise(spec),
            })

        out: dict[str, dict] = {}
        for name, spec in PROVIDERS_BY_NAME.items():
            if name == "mock":
                continue
            out[name] = {
                "default_model": spec.default_model,
                "recommended_models": _serialise(spec),
            }
        return JSONResponse({"providers": out})

    @app.post("/api/settings", dependencies=[Depends(verify_session_token)])
    def settings_save(body: SettingsBody) -> JSONResponse:
        from ..llm import _canonical
        cur = user_settings.load()
        if body.provider:
            cur.provider = _canonical(body.provider)
        elif body.provider == "":
            cur.provider = ""
        cur.base_url = body.base_url
        cur.model = body.model
        cur.model_executor = body.model_executor
        cur.model_dreamer = body.model_dreamer
        cur.model_critic = body.model_critic
        if body.api_key:
            env_name = _env_for_provider(body.provider) if body.provider else None
            if env_name:
                cur.api_keys[env_name] = body.api_key
        cur.onboarded = True
        user_settings.save(cur)
        return JSONResponse({"ok": True, "provider": cur.provider})

    @app.post("/api/settings/test",
              dependencies=[Depends(verify_session_token)])
    def settings_test(body: SettingsBody) -> JSONResponse:
        """Apply candidate settings to env temporarily and ping the LLM."""
        import time
        snapshot_keys = ["HIPPO_LLM_PROVIDER", "HIPPO_MODEL", "HIPPO_MODEL_EXECUTOR",
                         "HIPPO_MODEL_DREAMER", "HIPPO_MODEL_CRITIC", "OLLAMA_HOST", "OLLAMA_MODEL"]
        env_name = _env_for_provider(body.provider) if body.provider else None
        if env_name:
            snapshot_keys.append(env_name)
        snapshot = {k: os.environ.get(k) for k in snapshot_keys}
        try:
            if body.provider:
                os.environ["HIPPO_LLM_PROVIDER"] = body.provider
            if body.model:
                os.environ["HIPPO_MODEL"] = body.model
            if body.model_executor:
                os.environ["HIPPO_MODEL_EXECUTOR"] = body.model_executor
            if env_name and body.api_key:
                os.environ[env_name] = body.api_key
            from ..llm import get_llm
            llm = get_llm(use_mock=False)
            t0 = time.time()
            resp = llm.complete(
                system="Reply only with the single word: pong",
                messages=[{"role": "user", "content": "ping"}],
                temperature=0.0,
                max_tokens=8,
            )
            latency_ms = int((time.time() - t0) * 1000)
            text = (resp.text or "").strip().lower()[:40]
            return JSONResponse({
                "ok": True,
                "message": f"replied: {text!r}",
                "model": resp.model,
                "input_tokens": resp.input_tokens,
                "output_tokens": resp.output_tokens,
                "latency_ms": latency_ms,
            })
        except Exception as exc:
            return JSONResponse(
                {"ok": False, "error": _safe_error(exc, "test_provider")},
                status_code=400,
            )
        finally:
            for k, v in snapshot.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            user_settings.apply_to_env()

    # ----- Permissions / fallback ---------------------------------------

    @app.get("/api/fallback")
    def fallback_get() -> JSONResponse:
        s = user_settings.load()
        return JSONResponse({"fallback_providers": s.fallback_providers})

    @app.post("/api/fallback", dependencies=[Depends(verify_session_token)])
    def fallback_save(body: FallbackChainBody) -> JSONResponse:
        cur = user_settings.load()
        cur.fallback_providers = list(body.fallback_providers)
        user_settings.save(cur)
        return JSONResponse({"ok": True, "fallback_providers": cur.fallback_providers})

    @app.get("/api/permissions")
    def permissions_get() -> JSONResponse:
        s = user_settings.load()
        return JSONResponse({
            "sandbox_enabled": s.sandbox_enabled,
            "perm_filesystem": s.perm_filesystem,
            "perm_computer_use": s.perm_computer_use,
            "perm_webcam": s.perm_webcam,
            "perm_shell": s.perm_shell,
            "perm_web": s.perm_web,
            "perm_vision": s.perm_vision,
        })

    @app.post("/api/permissions",
              dependencies=[Depends(verify_session_token)])
    def permissions_save(body: PermissionsBody) -> JSONResponse:
        cur = user_settings.load()
        cur.sandbox_enabled = body.sandbox_enabled
        cur.perm_filesystem = body.perm_filesystem
        cur.perm_computer_use = body.perm_computer_use
        cur.perm_webcam = body.perm_webcam
        cur.perm_shell = body.perm_shell
        cur.perm_web = body.perm_web
        cur.perm_vision = body.perm_vision
        user_settings.save(cur)
        return JSONResponse({
            "ok": True,
            "sandbox_enabled": cur.sandbox_enabled,
        })

    # ----- Presets ------------------------------------------------------

    @app.get("/api/presets")
    def presets_get() -> JSONResponse:
        cur = user_settings.load()
        active_provider = cur.provider
        active_model = cur.model
        out = []
        for p in PRESETS:
            active = (p["provider"] == active_provider and p["model"] == active_model)
            out.append({**p, "active": active})
        return JSONResponse({"presets": out})

    @app.post("/api/presets/apply",
              dependencies=[Depends(verify_session_token)])
    def presets_apply(body: PresetApply) -> JSONResponse:
        preset = next((p for p in PRESETS if p["id"] == body.preset_id), None)
        if not preset:
            return JSONResponse({"error": "unknown preset"}, status_code=400)
        cur = user_settings.load()
        _apply_preset_to_settings(cur, preset)
        user_settings.save(cur)
        return JSONResponse({"ok": True, "provider": cur.provider, "model": cur.model})
