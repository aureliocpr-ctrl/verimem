"""`verimem` — the PUBLIC package name (iter 58, naming Phase 1).

Aurelio 2026-07-06: three names for one product (verimem / engram / hippo_*)
confuse a user. Phase 1 makes the user-facing story 100% Verimem with zero
breakage: `verimem` is an alias package over `engram` (same objects, same
mechanism as the hippoagent legacy shim, but canonical — NO deprecation
warning), plus a `verimem` console script. Internal deep rename = v0.4 gated.
"""
from __future__ import annotations


def test_import_verimem_exposes_memory():
    import verimem

    from engram.client import Memory as EngramMemory
    assert verimem.Memory is EngramMemory, "same class object, not a copy"


def test_submodule_identity():
    import verimem.semantic as vs

    import engram.semantic as es
    assert vs is es, "verimem.X and engram.X are the SAME module object"
    assert vs.SemanticMemory is es.SemanticMemory


def test_no_deprecation_warning_on_import():
    import subprocess
    import sys
    r = subprocess.run(
        [sys.executable, "-W", "error::DeprecationWarning", "-c",
         "import verimem; print(verimem.__version__)"],
        capture_output=True, text=True, timeout=120,
        cwd=r"C:\Users\aurel\Code\hippoagent")
    assert r.returncode == 0, (r.stderr or "")[-400:]
    assert r.stdout.strip(), "version exposed"
