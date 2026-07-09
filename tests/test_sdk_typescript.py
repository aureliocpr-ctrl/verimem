"""Contract test cross-language: l'SDK TypeScript contro il gateway VERO.

Un SDK che non gira contro il server reale è documentazione, non software:
questo test avvia il gateway in-process (uvicorn, porta effimera), provisiona
un tenant, poi lancia ``node --test`` sul test dell'SDK (che importa la
SORGENTE .ts — Node 23.6+ type stripping). Se Node manca: skip dichiarato.
Il contratto HTTP resta così sotto la stessa suite pytest del server: una
modifica al gateway che rompe l'SDK diventa un test rosso QUI.
"""
from __future__ import annotations

import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
uvicorn = pytest.importorskip("uvicorn")

_NODE = shutil.which("node")
_SDK_DIR = Path(__file__).resolve().parent.parent / "sdk" / "typescript"


def _node_supports_ts() -> bool:
    if not _NODE:
        return False
    try:
        out = subprocess.run([_NODE, "--version"], capture_output=True,
                             text=True, timeout=10).stdout.strip()
        major = int(out.lstrip("v").split(".")[0])
        return major >= 23  # type stripping nativo
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.skipif(not _node_supports_ts(),
                    reason="node >= 23 non disponibile (SDK TS: type stripping)")
def test_typescript_sdk_against_live_gateway(tmp_path):
    from engram.gateway import GatewayKeys, create_app

    keys = GatewayKeys(tmp_path / "gateway_keys.db")
    api_key = keys.create(tenant_id="sdk-ts", name="contract")
    app = create_app(data_dir=tmp_path, keys=keys)

    with socket.socket() as s:  # porta effimera
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    cfg = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(cfg)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    try:
        import urllib.request
        for _ in range(100):
            time.sleep(0.1)
            try:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/v1/health", timeout=1)
                break
            except Exception:  # noqa: BLE001
                continue
        else:
            pytest.fail("gateway did not come up")

        proc = subprocess.run(
            [_NODE, "--test", "test/client.test.mjs"],
            cwd=_SDK_DIR, capture_output=True, text=True, timeout=180,
            env={**__import__("os").environ,
                 "VERIMEM_URL": f"http://127.0.0.1:{port}",
                 "VERIMEM_KEY": api_key},
        )
        assert proc.returncode == 0, (
            f"SDK TS contract test FAILED\n--- stdout ---\n{proc.stdout}"
            f"\n--- stderr ---\n{proc.stderr}")
        assert "pass 2" in proc.stdout, proc.stdout
    finally:
        server.should_exit = True
        t.join(timeout=5)
