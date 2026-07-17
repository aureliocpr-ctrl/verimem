"""Live no-egress probe: PROVE zero cloud egress at runtime, not just assert it
from config. The airgap module documented this as "a separate, heavier step"
(the sovereign/datacenter segment needs proof, not a promise). This exercises a
real write+search cycle while a CPython audit hook records every socket.connect,
and reports any NON-loopback destination.

The audit hook is process-global and permanent, so each case runs in a
subprocess (isolation + a clean hook).
"""
from __future__ import annotations

import subprocess
import sys
import textwrap


def _run(body: str) -> tuple[int, str]:
    prog = textwrap.dedent(body)
    r = subprocess.run([sys.executable, "-c", prog], capture_output=True,
                       text=True, timeout=180)
    return r.returncode, r.stdout + r.stderr


def test_clean_run_proves_zero_egress():
    rc, out = _run(
        """
        import os
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        from verimem.airgap import probe_live_egress
        rep = probe_live_egress()  # default exercise: write + search, mock llm
        print("EGRESS", rep["egress"])
        print("AIR_GAPPED", rep["air_gapped"])
        assert rep["air_gapped"] is True, rep["egress"]
        assert rep["egress"] == []
        print("OK")
        """
    )
    assert rc == 0 and "OK" in out, out


def test_probe_catches_a_deliberate_egress():
    # a hostile exercise that opens a non-loopback connection MUST be reported —
    # otherwise the "proof" proves nothing.
    rc, out = _run(
        """
        import socket
        from verimem.airgap import probe_live_egress
        def leak():
            s = socket.socket()
            s.settimeout(0.001)
            try: s.connect(("93.184.216.34", 80))   # example.com, non-loopback
            except Exception: pass
        rep = probe_live_egress(exercise=leak)
        print("EGRESS", rep["egress"])
        assert rep["air_gapped"] is False, "deliberate egress not caught"
        assert any("93.184.216.34" in str(e) for e in rep["egress"])
        print("OK")
        """
    )
    assert rc == 0 and "OK" in out, out


def test_loopback_is_not_egress():
    # a local model endpoint (loopback) is NOT cloud egress and must not fail.
    rc, out = _run(
        """
        import socket
        from verimem.airgap import probe_live_egress
        def local_call():
            s = socket.socket()
            s.settimeout(0.001)
            try: s.connect(("127.0.0.1", 65000))
            except Exception: pass
        rep = probe_live_egress(exercise=local_call)
        print("EGRESS", rep["egress"])
        assert rep["air_gapped"] is True, rep["egress"]
        print("OK")
        """
    )
    assert rc == 0 and "OK" in out, out
