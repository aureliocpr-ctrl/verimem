"""CYCLE #24 — regression test eager preload sentence-transformers.

Bug regressato: main() non chiamava più embedding.encode('warmup')
prima di asyncio.run(_serve()). Conseguenza: primo recall/remember
post-restart paga 5-20s cold load → cliente MCP timeout.

Test che verifica:
  1. HIPPO_EAGER_PRELOAD=1 (default) → embedding.encode chiamato
  2. HIPPO_EAGER_PRELOAD=0 → embedding.encode NON chiamato
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


def test_main_eager_preload_default_on(monkeypatch):
    """Default boot: the server self-configures DELEGATE-ONLY mode and MUST NOT
    cold-load the embedding model in-process.

    Updated 2026-06-06 for the recurring-hang fix (9da43c4): main() now sets
    HIPPO_ENCODE_DELEGATE_ONLY=1 (setdefault), and preload SKIPS the in-process
    warm — the ~33s `import sentence_transformers` under _MODEL_LOCK was the
    recall/save hang. The shared encode daemon (a separate process) warms the
    model instead; this process delegates. So `embedding.encode('warmup')` must
    NOT be called in-process at boot.
    """
    import os
    monkeypatch.delenv("HIPPO_EAGER_PRELOAD", raising=False)
    monkeypatch.delenv("HIPPO_DISABLED", raising=False)
    monkeypatch.delenv("HIPPO_ENCODE_DELEGATE_ONLY", raising=False)  # let main() set the default

    from engram import mcp_server

    calls = []
    def fake_encode(text):
        calls.append(text)
        return None

    def fake_asyncio_run(coro):
        # Chiudi la coroutine senza eseguirla per non aprire stdio_server
        coro.close()

    with patch("engram.embedding.encode", side_effect=fake_encode):
        with patch("engram.mcp_server.asyncio.run", side_effect=fake_asyncio_run):
            mcp_server.main()

    # delegate-only is the default the server self-configures
    assert os.environ.get("HIPPO_ENCODE_DELEGATE_ONLY") == "1", (
        "main() must default to delegate-only (HIPPO_ENCODE_DELEGATE_ONLY=1)"
    )
    # …and it must NOT cold-load the model in-process (delegates to the daemon)
    assert "warmup" not in calls, (
        f"delegate-only server must not warm the model in-process at boot: {calls}"
    )


def test_main_eager_preload_disabled_via_env(monkeypatch):
    """HIPPO_EAGER_PRELOAD=0 → skip warmup."""
    monkeypatch.setenv("HIPPO_EAGER_PRELOAD", "0")
    monkeypatch.delenv("HIPPO_DISABLED", raising=False)

    from engram import mcp_server

    calls = []
    def fake_encode(text):
        calls.append(text)
        return None

    def fake_asyncio_run(coro):
        coro.close()

    with patch("engram.embedding.encode", side_effect=fake_encode):
        with patch("engram.mcp_server.asyncio.run", side_effect=fake_asyncio_run):
            mcp_server.main()

    assert calls == [], (
        f"Eager preload non rispettato con HIPPO_EAGER_PRELOAD=0: {calls}"
    )


def test_main_eager_preload_does_not_block_on_exception(monkeypatch):
    """Se embedding.encode crasha, main() prosegue verso _serve."""
    monkeypatch.delenv("HIPPO_EAGER_PRELOAD", raising=False)
    monkeypatch.delenv("HIPPO_DISABLED", raising=False)

    from engram import mcp_server

    def crashing_encode(text):
        raise RuntimeError("simulated model load failure")

    served = {"called": False}
    def fake_asyncio_run(coro):
        served["called"] = True
        coro.close()

    with patch("engram.embedding.encode", side_effect=crashing_encode):
        with patch("engram.mcp_server.asyncio.run", side_effect=fake_asyncio_run):
            # Non deve lanciare
            mcp_server.main()

    assert served["called"], (
        "main() non è arrivato a asyncio.run dopo eager preload exception"
    )


def test_main_hippo_disabled_skips_everything(monkeypatch):
    """HIPPO_DISABLED=1 → exit prima di tutto (no preload, no serve)."""
    monkeypatch.setenv("HIPPO_DISABLED", "1")

    from engram import mcp_server

    calls = []
    def fake_encode(text):
        calls.append(text)
        return None

    served = {"called": False}
    def fake_asyncio_run(coro):
        served["called"] = True
        coro.close()

    with patch("engram.embedding.encode", side_effect=fake_encode):
        with patch("engram.mcp_server.asyncio.run", side_effect=fake_asyncio_run):
            with pytest.raises(SystemExit) as exc_info:
                mcp_server.main()
            assert exc_info.value.code == 0

    assert calls == []
    assert not served["called"]
