"""`verimem` — the PUBLIC package name (iter 58, naming Phase 1).

Aurelio 2026-07-06: three names for one product (verimem / engram / hippo_*)
confuse a user. Phase 1 makes the user-facing story 100% Verimem with zero
breakage: `verimem` is an alias package over `engram` (same objects, same
mechanism as the hippoagent legacy shim, but canonical — NO deprecation
warning), plus a `verimem` console script. Internal deep rename = v0.4 gated.
"""
from __future__ import annotations

import pathlib

#: repo root derived from this file — NEVER a hardcoded absolute path
#: (the first CI run in repo history failed on every non-Windows runner here)
_REPO_ROOT = str(pathlib.Path(__file__).resolve().parents[1])

from tests._real_model import requires_real_model  # noqa: E402


def test_import_verimem_exposes_memory():
    import verimem
    from verimem.client import Memory as EngramMemory
    assert verimem.Memory is EngramMemory, "same class object, not a copy"


def test_submodule_identity():
    import verimem.semantic as es
    import verimem.semantic as vs
    assert vs is es, "verimem.X and verimem.X are the SAME module object"
    assert vs.SemanticMemory is es.SemanticMemory


def test_no_deprecation_warning_on_import():
    import subprocess
    import sys
    r = subprocess.run(
        [sys.executable, "-W", "error::DeprecationWarning", "-c",
         "import verimem; print(verimem.__version__)"],
        capture_output=True, text=True, timeout=120,
        cwd=_REPO_ROOT)
    assert r.returncode == 0, (r.stderr or "")[-400:]
    assert r.stdout.strip(), "version exposed"


@requires_real_model  # subprocess embeds for real: fresh python, no stub
def test_sdk_import_safe_without_server_and_byok_deps():
    """Packaging contract (iter 59): `import verimem/verimem` + the 5-verb SDK
    must work WITHOUT fastapi/uvicorn/jinja2/openai installed (they moved to
    [server]/[byok] extras). Simulated by blocking the modules in a child
    interpreter — an import of any blocked dep on the SDK path would raise."""
    import subprocess
    import sys
    code = (
        "import sys\n"
        "for m in ('fastapi','uvicorn','jinja2','openai'):\n"
        "    sys.modules[m] = None\n"   # import -> ImportError('None in sys.modules')
        "import tempfile, pathlib\n"
        "from verimem import Memory\n"
        "mem = Memory(pathlib.Path(tempfile.mkdtemp())/'m.db')\n"
        "r = mem.add('packaging probe fact')\n"
        "assert r['stored'], r\n"
        "assert mem.search('packaging probe')\n"
        "assert mem.explain('packaging probe')['n_facts'] >= 1\n"
        "print('SDK OK without server/byok deps')\n"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                       text=True, timeout=300,
                       cwd=_REPO_ROOT)
    assert r.returncode == 0, (r.stderr or "")[-500:]
    assert "SDK OK" in r.stdout


def test_find_spec_is_honest_about_missing_modules():
    """Review 5-lenti C7: the finder used to return a synthetic spec for ANY
    verimem.* name — feature-detection via find_spec got false positives."""
    import importlib.util
    assert importlib.util.find_spec("verimem.no_such_module_xyz123") is None


def test_missing_submodule_error_names_verimem():
    """C7: the ModuleNotFoundError must name what the USER typed, not the
    internal package."""
    import importlib

    import pytest as _pytest
    with _pytest.raises(ModuleNotFoundError) as ei:
        importlib.import_module("verimem.no_such_module_xyz123b")
    assert ei.value.name == "verimem.no_such_module_xyz123b"


def test_python_dash_m_runs_flat_modules():
    """C7: `python -m verimem.X` on a flat module used to die with 'is a
    package and cannot be directly executed' (is_package=True on everything)."""
    import subprocess
    import sys
    r = subprocess.run(
        [sys.executable, "-m", "verimem.temporal_context"],
        capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-500:]


def test_nested_subpackage_module_identity():
    """C7 (double-execution hazard): with the finder APPENDED to meta_path,
    PathFinder won nested names (verimem.swarm.X) via the swapped parent's
    real __path__ and re-executed the file under the alias name — two distinct
    module objects, the exact cycle-#41 trap the docstring promises to avoid."""
    import verimem.swarm.lifecycle as e
    import verimem.swarm.lifecycle as v
    assert v is e, "nested alias must be the SAME module object"
