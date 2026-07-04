"""User settings — persisted JSON, applied as env overrides at runtime.

The dashboard /settings page (and CLI) write here. On every read of an LLM
client, env vars are derived from this file so changes take effect *without*
restarting the dashboard.

API keys are stored in plaintext on disk under ~/.hippoagent or the project
data dir. Treat the file as a secret. (For production, swap in OS keychain.)
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import CONFIG

SETTINGS_FILE = CONFIG.data_dir / "user_settings.json"
_LOCK = threading.RLock()


@dataclass
class UserSettings:
    """Persisted user-level configuration."""
    # ---- LLM provider ----
    provider: str = ""                  # one of llm.PROVIDERS keys, "" = autodetect
    base_url: str = ""                  # override provider base_url (for self-hosted/Azure)
    api_keys: dict[str, str] = field(default_factory=dict)  # env name -> value
    model: str = ""                     # HIPPO_MODEL (all stages)
    model_executor: str = ""            # HIPPO_MODEL_EXECUTOR
    model_dreamer: str = ""             # HIPPO_MODEL_DREAMER
    model_critic: str = ""              # HIPPO_MODEL_CRITIC
    ollama_host: str = ""               # OLLAMA_HOST override
    ollama_model: str = ""              # OLLAMA_MODEL override
    onboarded: bool = False             # has the user completed first-run setup?

    # ---- Capability permissions (sandbox) ----
    # Master kill-switch: when True, all "dangerous" capabilities are gated.
    sandbox_enabled: bool = True
    # Granular toggles. When sandbox_enabled=False, all are effectively True.
    # CVE-003 / SEC V4 fix: default is "strict" (data dir only).
    # Users can opt into "home" via the dashboard with explicit confirmation.
    perm_filesystem: str = "strict"     # "strict" | "home" | "full"
    perm_computer_use: bool = False     # pyautogui screen/click/type/key
    perm_webcam: bool = False
    perm_shell: bool = False            # arbitrary shell commands
    perm_web: bool = True               # web_fetch + web_search
    perm_vision: bool = True            # vision_describe

    # ---- Auto-fallback provider chain ----
    # When the primary provider returns a rate-limit / quota / 5xx error, the
    # client transparently tries the next one. Empty list = no fallback.
    # Format: list of provider names, e.g. ["anthropic", "groq", "ollama"].
    fallback_providers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> UserSettings:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def load() -> UserSettings:
    with _LOCK:
        if not SETTINGS_FILE.exists():
            return UserSettings()
        try:
            return UserSettings.from_dict(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
        except Exception:
            return UserSettings()


def save(s: UserSettings) -> None:
    with _LOCK:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(s.to_dict(), indent=2), encoding="utf-8")
        apply_to_env(s)


def apply_to_env(s: UserSettings | None = None) -> None:
    """Project the persisted settings onto os.environ for this process."""
    s = s or load()
    # 12-factor precedence: an EXPLICIT env override wins over the persisted
    # provider. CRITICAL for local/air-gap mode — before this, the module-level
    # apply_to_env() on import (+ get_llm's lazy `from . import settings`)
    # clobbered an explicit HIPPO_LLM_PROVIDER=ollama with the saved provider,
    # so a multi-LLM run (wake OK, then sleep/critic) silently fell back to the
    # saved cloud provider = air-gap leak / crash "ANTHROPIC_API_KEY not set"
    # (verified live 2026-06-06). An operator who forces a provider keeps it.
    _env_prov = os.environ.get("HIPPO_LLM_PROVIDER", "").strip()
    if _env_prov:
        pass  # explicit operator override present — never clobber it
    elif s.provider:
        os.environ["HIPPO_LLM_PROVIDER"] = s.provider
    elif "HIPPO_LLM_PROVIDER" in os.environ:
        del os.environ["HIPPO_LLM_PROVIDER"]
    # SCAN-68 (audit 2026-06-02, NONNA, round 2): set-OR-POP per TUTTE le var di
    # modello/host. Un valore vuoto deve RIMUOVERE la env-var stale, non solo
    # "non settarla": altrimenti dopo un cambio preset (es. -> ollama, che
    # resetta i per-stage a "") un HIPPO_MODEL_CRITIC=claude-* (o un HIPPO_MODEL/
    # OLLAMA_MODEL) precedente persisteva in os.environ -> config incoerente.
    # "Project the persisted settings" = proiezione COMPLETA, stale incluse.
    for _env, _val in (
        ("HIPPO_MODEL", s.model),
        ("HIPPO_MODEL_EXECUTOR", s.model_executor),
        ("HIPPO_MODEL_DREAMER", s.model_dreamer),
        ("HIPPO_MODEL_CRITIC", s.model_critic),
        ("OLLAMA_HOST", s.ollama_host),
        ("OLLAMA_MODEL", s.ollama_model),
    ):
        if _val:
            os.environ[_env] = _val
        else:
            os.environ.pop(_env, None)
    # Provider-specific base_url override — set-OR-POP (SCAN-68 round 2, come i
    # model/host sopra): un base_url svuotato deve RIMUOVERE l'override stale,
    # non lasciarlo proiettato in os.environ. Serve solo il provider per
    # risolvere il base_url_env.
    if s.provider:
        from .llm import PROVIDERS
        spec = PROVIDERS.get(s.provider)
        if spec and spec.get("base_url_env"):
            if s.base_url:
                os.environ[spec["base_url_env"]] = s.base_url
            else:
                os.environ.pop(spec["base_url_env"], None)
    # API keys
    for env_name, value in (s.api_keys or {}).items():
        if value:
            os.environ[env_name] = value

    # Capability permissions → env flags read by tools_extra._enabled() etc.
    # When sandbox is disabled, all permissions become True regardless of granular toggles.
    sandbox_off = not s.sandbox_enabled

    def _set(name: str, on: bool) -> None:
        os.environ[name] = "1" if on else "0"

    _set("HIPPO_ENABLE_COMPUTER_USE", sandbox_off or s.perm_computer_use)
    _set("HIPPO_ENABLE_WEBCAM", sandbox_off or s.perm_webcam)
    _set("HIPPO_ENABLE_SHELL", sandbox_off or s.perm_shell)
    _set("HIPPO_ENABLE_WEB", sandbox_off or s.perm_web)
    _set("HIPPO_ENABLE_VISION", sandbox_off or s.perm_vision)

    # Filesystem scope. "strict" is the default (data dir only). The user
    # must explicitly opt into "home" or "full" via the dashboard.
    # CVE-003 / SEC V4 fix.
    if sandbox_off or s.perm_filesystem == "full":
        # NOTE: sandbox_off intentionally retains "full" to honour the
        # explicit "Unleash" preset, but the dashboard now warns the user.
        os.environ.pop("HIPPO_FS_STRICT", None)
        os.environ.pop("HIPPO_FS_HOME", None)
        os.environ["HIPPO_FS_ROOT"] = str(Path("/").resolve()) \
            if os.name != "nt" else "C:\\"
    elif s.perm_filesystem == "home":
        os.environ.pop("HIPPO_FS_STRICT", None)
        os.environ.pop("HIPPO_FS_ROOT", None)
        os.environ["HIPPO_FS_HOME"] = "1"
    else:  # "strict" — default
        os.environ["HIPPO_FS_STRICT"] = "1"
        os.environ.pop("HIPPO_FS_ROOT", None)
        os.environ.pop("HIPPO_FS_HOME", None)

    # Settings v2: invalidate the cached Settings singleton so subsequent
    # `get_settings()` calls reflect the env we just wrote. Best-effort —
    # circular-import-safe via local import.
    try:
        from .settings_v2 import refresh_settings
        refresh_settings()
    except Exception:
        pass


def update(**patch) -> UserSettings:
    """Update one or more fields and persist."""
    cur = load()
    for k, v in patch.items():
        if hasattr(cur, k):
            setattr(cur, k, v)
    save(cur)
    return cur


def upsert_api_key(env_name: str, value: str) -> UserSettings:
    cur = load()
    if not value:
        cur.api_keys.pop(env_name, None)
    else:
        cur.api_keys[env_name] = value
    save(cur)
    return cur


# Apply on import so any subsequent `from .config import CONFIG` and llm calls
# see the persisted settings.
try:
    apply_to_env()
except Exception:
    pass
