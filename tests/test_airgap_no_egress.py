"""Air-gap NO-EGRESS proof (empirical): in offline mode, a REAL embedding encode
opens ZERO connections to a non-local host.

The only external-network risk in local/air-gap mode is the embedding model load
(sentence-transformers -> HF Hub). With the offline flags set and the model
cached, ``embedding.encode`` must hit the network zero times. The LLM side is
already local (Ollama = localhost). This is the empirical proof an air-gapped /
sovereign buyer demands, beyond the static ``airgap.airgap_status`` check.

Run in a FRESH subprocess: the conftest autouse fixture stubs ``embedding._model``
in-process, so the genuine cache-only model load + a real socket interception can
only be exercised out-of-process (also the realistic setting). Requires the
embedding model to be cached locally (it is, after any prior encode).
"""
from __future__ import annotations

import subprocess
import sys
import textwrap

from tests._real_model import requires_real_model

# Spawns a FRESH subprocess that loads the REAL model offline; skip when it
# isn't cached (CI without a warmed HF cache) — see helper.
pytestmark = requires_real_model


def test_offline_embedding_makes_no_external_connection():
    script = textwrap.dedent(
        """
        import os, socket
        for f in ("HIPPO_OFFLINE", "ENGRAM_OFFLINE", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
            os.environ[f] = "1"
        # Force in-process encode so we exercise the real cache-only model load
        # (not a localhost handoff to the shared encode daemon).
        os.environ["ENGRAM_ENCODE_SERVICE"] = "0"

        _LOCAL = {"127.0.0.1", "::1", "localhost", "0.0.0.0", ""}
        nonlocal_hosts = []

        def _host(addr):
            return str(addr[0]) if isinstance(addr, tuple) and addr else str(addr)

        _real_connect = socket.socket.connect
        _real_create = socket.create_connection

        def _rec_connect(self, address, *a, **k):
            h = _host(address)
            if h.strip().lower() not in _LOCAL:
                nonlocal_hosts.append(h)
            return _real_connect(self, address, *a, **k)

        def _rec_create(address, *a, **k):
            h = _host(address)
            if h.strip().lower() not in _LOCAL:
                nonlocal_hosts.append(h)
            return _real_create(address, *a, **k)

        socket.socket.connect = _rec_connect
        socket.create_connection = _rec_create

        from verimem import embedding
        vec = embedding.encode("air-gap no-egress probe")
        ok = vec is not None and len(vec) > 0
        print("ENCODE_OK" if ok else "ENCODE_FAIL")
        print("NONLOCAL=" + repr(nonlocal_hosts))
        print("VERDICT=" + ("NO_EGRESS" if not nonlocal_hosts else "EGRESS_DETECTED"))
        """
    )
    out = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, timeout=240,
    )
    assert "ENCODE_OK" in out.stdout, (
        "offline embedding encode failed (model not cached locally?):\n"
        f"stdout={out.stdout}\nstderr={out.stderr[-800:]}"
    )
    assert "VERDICT=NO_EGRESS" in out.stdout, (
        "AIR-GAP VIOLATED — offline embedding opened a non-local connection:\n"
        f"stdout={out.stdout}\nstderr={out.stderr[-800:]}"
    )
