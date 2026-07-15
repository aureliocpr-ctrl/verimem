"""Test fixtures: isolated temp dirs for memory/skills, deterministic embedding stub, mock LLM."""
from __future__ import annotations

# E5 GO-LIVE (2026-06-04): il default ATTIVO del server passa a e5-base 768d.
# I test usano lo STUB embedding 384d (sotto, _EMBED_DIM=384) + asserzioni a 384,
# quindi PINNANO qui modello/dim ai valori storici (multilingue-L12, 384) PRIMA di
# qualunque import di engram.config -> suite invariata, veloce, indipendente dal
# default e5 del server (separazione: server=e5/768 via config-default, test=L12/384).
import os as _os

_os.environ.setdefault("HIPPO_EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
_os.environ.setdefault("HIPPO_EMBEDDING_DIM", "384")

import hashlib
import re
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Provide a temp data directory; tests pass explicit paths to constructors."""
    new = Path(tmp_path) / "hippo_data"
    (new / "episodes").mkdir(parents=True, exist_ok=True)
    (new / "skills").mkdir(parents=True, exist_ok=True)
    (new / "semantic").mkdir(parents=True, exist_ok=True)
    return new


# ---------------------------------------------------------------------------
# Deterministic embedding stub — see QA_AUDIT I-1.
#
# `sentence-transformers` is a heavy dependency (HuggingFace model download
# at first call, ~80MB on disk, several seconds startup). The unit-test suite
# should not depend on it. We replace `embedding._model()` with a stub that
# returns a deterministic 384-dim L2-normalized vector. Same text → same
# vector; texts that share tokens have cosine similarity proportional to the
# token overlap (so clustering / recall tests still produce meaningful
# groups, just like real sentence-transformers do).
#
# Implementation: hashing-trick bag-of-tokens — each lowercased token hashes
# to a stable bucket in [0, 384), with a per-token sign drawn from a second
# hash. The resulting vector is L2-normalized. Two texts that share many
# tokens land near each other; two unrelated texts are roughly orthogonal.
# ---------------------------------------------------------------------------


_EMBED_DIM = 384
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _stub_vector(text: str) -> np.ndarray:
    """Hashing-trick bag-of-tokens → deterministic 384-d L2-normalized vector."""
    v = np.zeros(_EMBED_DIM, dtype=np.float32)
    tokens = _TOKEN_RE.findall((text or "").lower())
    if not tokens:
        # Empty / pure-symbol input — derive a constant non-zero vector from
        # the raw bytes so cosine of two empty strings is still defined (=1).
        digest = hashlib.sha256((text or "").encode("utf-8", errors="replace")).digest()
        seed = int.from_bytes(digest[:8], "big") % (2**32 - 1)
        rng = np.random.default_rng(seed)
        v = rng.standard_normal(_EMBED_DIM).astype(np.float32)
    else:
        for tok in tokens:
            d = hashlib.sha256(tok.encode("utf-8")).digest()
            bucket = int.from_bytes(d[:4], "big") % _EMBED_DIM
            sign = 1.0 if d[4] & 1 else -1.0
            v[bucket] += sign
    norm = np.linalg.norm(v)
    if norm > 0:
        v = v / norm
    return v.astype(np.float32, copy=False)


class _StubModel:
    """Drop-in replacement for sentence-transformers `SentenceTransformer`.

    Implements the subset of the API that `embedding.encode` uses:
      - encode(text, normalize_embeddings=..., show_progress_bar=...)
      - encode([t1, t2, ...], normalize_embeddings=..., show_progress_bar=..., convert_to_numpy=...)
    """

    def encode(self, text, normalize_embeddings=True, show_progress_bar=False,
               convert_to_numpy=True):
        if isinstance(text, str):
            return _stub_vector(text)
        return np.stack([_stub_vector(t) for t in text]).astype(np.float32)


@pytest.fixture(autouse=True)
def _stub_embedding_model(monkeypatch):
    """Replace the lazy `embedding._model()` with a deterministic stub.

    Auto-applied to every test. Real sentence-transformers is never loaded
    in unit tests — keeps the suite offline-safe and fast.
    """
    try:
        from engram import embedding
    except ImportError:
        return  # nothing to stub
    stub = _StubModel()
    # Bypass the lru_cache: override the function itself.
    monkeypatch.setattr(embedding, "_model", lambda: stub)
    # The stub IS a loaded model: set the _MODEL global too so is_loaded()==True.
    # Without this, DELEGATE-ONLY mode (HIPPO_ENCODE_DELEGATE_ONLY — which an
    # in-process mcp_server.main() leaks permanently via os.environ.setdefault)
    # makes _encode_one RAISE EncodeDelegateUnavailable instead of using the stub,
    # silently breaking every test that encodes once the flag has leaked
    # (root of the 2026-06-06 CI pytest failures, concentrated in test_wake_*).
    monkeypatch.setattr(embedding, "_MODEL", stub)
    # Belt-and-suspenders: unit tests use the in-process stub, never delegate-only.
    monkeypatch.delenv("HIPPO_ENCODE_DELEGATE_ONLY", raising=False)
    # Tests must use the stub, never a live shared encode daemon — disable the
    # encode service so encode() always falls through to the stubbed in-process
    # model. (Tests that exercise the service path re-enable it explicitly.)
    monkeypatch.setenv("ENGRAM_ENCODE_SERVICE", "0")
    # Drop any single-text embedding cache populated before the stub took
    # over (otherwise tests would see real-model vectors leak across runs).
    embedding.encode_cache_clear()
    yield
    embedding.encode_cache_clear()


@pytest.fixture(autouse=True)
def _reset_settings_v2_cache():
    """Invalidate the pydantic-settings singleton cache between tests.

    `settings_v2._build_settings` is `@lru_cache`-wrapped so that production
    code reads a single Settings instance per process. In tests, env vars
    flip per case, so the cache must be cleared at every boundary or a test
    that runs second sees the first test's snapshot.
    """
    try:
        from engram import settings_v2
    except ImportError:
        return
    settings_v2._build_settings.cache_clear()
    yield
    settings_v2._build_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_session_token():
    """Clear the cached dashboard session token between tests.

    The token is module-global in `dashboard_routes.auth._SESSION_TOKEN`;
    once set by one test it persists across the run, so a test that flips
    `HIPPO_DASHBOARD_TOKEN` to a fresh value would still match the old one.
    """
    try:
        from engram.dashboard_routes import auth as _dash_auth
    except ImportError:
        return
    _dash_auth.reset_session_token()
    yield
    _dash_auth.reset_session_token()


@pytest.fixture(autouse=True)
def _restore_module_config():
    """Restore the CONFIG binding inside modules that allow override.

    Several modules (`skill`, `wake`, `sleep`, `tools`, `dashboard_routes.*`)
    read `CONFIG` as a module-level import. Tests sometimes swap that
    binding (e.g. via `monkeypatch.setattr(engram.skill, "CONFIG", new)`)
    to flip a feature flag. monkeypatch undoes the change at fixture
    teardown, but tests that DON'T use monkeypatch and write directly to
    the binding leave the override in place. This safety net snapshots
    the bindings before the test and restores them after, so a forgotten
    `module.CONFIG = …` cannot poison the rest of the run.
    """
    bindings: list[tuple[object, object]] = []
    for modname in ("engram.skill", "engram.wake", "engram.sleep",
                    "engram.tools", "engram.tools_extra"):
        try:
            mod = __import__(modname, fromlist=["CONFIG"])
        except ImportError:
            continue
        if hasattr(mod, "CONFIG"):
            bindings.append((mod, mod.CONFIG))
    yield
    for mod, original in bindings:
        mod.CONFIG = original


@pytest.fixture(autouse=True)
def _reset_mcp_rate_buckets():
    """Wipe MCP token buckets between tests.

    `mcp_server._RATE_BUCKETS` is a process-global dict. A test that exhausts
    `hippo_run_task`'s bucket would leave the next test starting with 0 tokens.
    """
    try:
        from engram import mcp_server as _mcp
    except ImportError:
        return
    with _mcp._BUCKETS_LOCK:
        _mcp._RATE_BUCKETS.clear()
    yield
    with _mcp._BUCKETS_LOCK:
        _mcp._RATE_BUCKETS.clear()


@pytest.fixture(autouse=True)
def _isolate_test_env(monkeypatch, tmp_path_factory):
    """Isolate tests from the user's ``user_settings.json`` and shell env.

    Audit 2026-05-13 found 22 tests failed with seed=42 because
    ``engram.settings.apply_to_env()`` ran on import and read the
    operator's saved ``user_settings.json`` (with ``provider="anthropic"``).
    Tests that instantiate ``WakeAgent`` without an explicit ``llm`` then
    tried to construct an Anthropic client and raised
    ``LLMError("ANTHROPIC_API_KEY not set")`` — even on tests that have
    nothing to do with the LLM provider.

    Force MockLLM by pinning ``HIPPO_OFFLINE=1`` for every test. Specific
    tests that need to exercise real provider selection can override
    this with their own monkeypatch.delenv inside the test.

    CYCLE #25 fix (root cause data leak): pinna anche HIPPO_DATA_DIR a una
    tmp_path per-test. Pre-fix: i test che istanziavano EpisodicMemory()
    senza db_path andavano al CONFIG.episodes_db = DB LIVE. Audit live ha
    rivelato 14 episodi "task one"/"task two" (test fixture failure)
    accumulati in 2.7h dalle mie sessioni di test cycle #18-24. Cycle #9
    aveva pulito 562→140 ma il leak ricorreva ogni volta che giravo i
    test localmente. Fix definitivo: ogni test ha la sua data_dir
    isolata, impossibile inquinare DB operatore.
    """
    monkeypatch.setenv("HIPPO_OFFLINE", "1")
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    monkeypatch.delenv("HIPPO_HOSTED", raising=False)
    # SCAN-68 / 2026-06-04 (NONNA): l'admission gate e' OPT-IN (default OFF =
    # comportamento legacy byte-identico). L'operatore lo attiva LIVE via env
    # ENGRAM_ADMISSION_GATE (setx persistente) o flag-file. Senza neutralizzarlo
    # qui, ogni test eredita l'env persistente e quelli scritti per il default
    # (es. test_explicit_telemetry_topic_is_still_served) falliscono perche' il
    # gate instrada la telemetria fuori dai facts. delenv rende la suite
    # indipendente dall'ambiente live; i test del gate fanno opt-in esplicito
    # con monkeypatch.setenv (gira DOPO questa fixture autouse). Il flag-file e'
    # gia' neutro: CONFIG.data_dir e' pinnato sotto a una tmp senza ADMISSION_GATE_ON.
    monkeypatch.delenv("ENGRAM_ADMISSION_GATE", raising=False)
    # RERANK default-ON flip 2026-06-10: recall() ora applica il cross-encoder
    # di default. Nei test va pinnato OFF ("0", NON delenv: unset = ON) o ogni
    # recall senza flag tenterebbe il load del CE reale (lento; con HF offline
    # fallisce -> fallback silenzioso) e gli assert sull'ordine bi-encoder si
    # romperebbero. I test del rerank (test_recall_rerank_optin_audit) fanno
    # opt-in/opt-out esplicito con monkeypatch DENTRO il test (gira DOPO questa
    # fixture autouse); il test del default vero fa delenv esplicito.
    monkeypatch.setenv("ENGRAM_RECALL_RERANK", "0")
    # CYCLE #25: isola HIPPO_DATA_DIR a una tmp_path per-test.
    # CONFIG è frozen dataclass costruito a import-time → monkeypatch
    # diretto fallisce con FrozenInstanceError. Use object.__setattr__
    # per bypass + restore esplicito su teardown via try/finally.
    test_data_dir = tmp_path_factory.mktemp("hippo_test_data")
    monkeypatch.setenv("HIPPO_DATA_DIR", str(test_data_dir))
    # A6 FIX 2026-06-08: config._data_root() now honors ENGRAM_DATA_DIR (the
    # README/.mcp.json name) BEFORE HIPPO_DATA_DIR. A shell that exports
    # ENGRAM_DATA_DIR (the maintainer's does -> ~/.engram) would otherwise leak
    # the REAL corpus into tests. Pin it to the per-test tmp too so isolation
    # holds regardless of which name takes precedence.
    monkeypatch.setenv("ENGRAM_DATA_DIR", str(test_data_dir))
    # SCAN-68 FIX 2026-06-02 (NONNA): pinna ANCHE ENGRAM_DIR. Root-cause della
    # pollution del DB reale: i test che spawnano `clp save` come SUBPROCESS
    # (es. test_pre_compact_hook_end_to_end) risolvono da ENGRAM_DIR (package
    # clp, NON HIPPO_DATA_DIR) -> scrivevano in ~/.engram reale. Il subprocess
    # eredita os.environ, quindi pinnando ENGRAM_DIR usa la tmp isolata.
    monkeypatch.setenv("ENGRAM_DIR", str(test_data_dir))
    original = {}
    try:
        from engram.config import CONFIG
        (test_data_dir / "episodes").mkdir(exist_ok=True)
        (test_data_dir / "skills").mkdir(exist_ok=True)
        (test_data_dir / "semantic").mkdir(exist_ok=True)
        overrides = {
            "data_dir": test_data_dir,
            "episodes_db": test_data_dir / "episodes" / "episodes.db",
            "skills_dir": test_data_dir / "skills",
            "skills_db": test_data_dir / "skills" / "skills_index.db",
            "semantic_db": test_data_dir / "semantic" / "semantic.db",
            "runs_dir": test_data_dir / "runs",
            "reports_dir": test_data_dir / "reports",
        }
        for k, v in overrides.items():
            original[k] = getattr(CONFIG, k)
            object.__setattr__(CONFIG, k, v)
    except ImportError:
        pass
    # CYCLE #28 (critic counterexample on #25): engram.settings:20
    # has `SETTINGS_FILE = CONFIG.data_dir / "user_settings.json"`
    # materialized at MODULE-IMPORT time. Overriding CONFIG.data_dir
    # post-import does NOT update SETTINGS_FILE → tests that trigger
    # apply_to_env() read from the live operator's user_settings.json.
    # Fix: override SETTINGS_FILE explicitly if settings module is loaded.
    settings_original_path = None
    try:
        from engram import settings as _settings
        if hasattr(_settings, "SETTINGS_FILE"):
            settings_original_path = _settings.SETTINGS_FILE
            _settings.SETTINGS_FILE = test_data_dir / "user_settings.json"
    except ImportError:
        pass
    try:
        yield
    finally:
        if original:
            from engram.config import CONFIG
            for k, v in original.items():
                object.__setattr__(CONFIG, k, v)
        # Restore settings.SETTINGS_FILE
        if settings_original_path is not None:
            try:
                from engram import settings as _settings
                _settings.SETTINGS_FILE = settings_original_path
            except ImportError:
                pass
