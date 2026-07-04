"""CYCLE #41 counterexample test (critic-found bug, job 614b682c67d39a7f).

Bug found by critic-orchestrator counterexample worker (confidence 0.93):

  The hippoagent backward-compat shim's _EngramShimFinder.find_spec returned
  `real.__spec__` (name='engram.X'). CPython's _bootstrap._load_unlocked
  ignores `sys.modules[fullname]` set by the finder and re-executes the
  module body of engram.X, creating a SECOND copy of the module under
  the hippoagent.X alias.

Effects:
  - hippoagent.skill.Skill is NOT engram.skill.Skill (two distinct classes)
  - isinstance(engram_instance, hippoagent.skill.Skill) → False
  - Module-level state (MCP registry, singletons, schema cache) duplicated

The fix uses a custom Loader whose exec_module is a no-op, so CPython's
_load_unlocked does not re-execute engram.X — the cached module is reused.
"""
from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

PYEXE = sys.executable
REPO = Path(__file__).resolve().parent.parent


def _run_isolated(script: str) -> tuple[int, str, str]:
    """Run `script` in a fresh Python subprocess (no state leak from test).

    Each invocation gets a clean sys.modules + clean import order so we can
    test BOTH "engram first" and "hippoagent first" import orderings.
    """
    proc = subprocess.run(
        [PYEXE, "-W", "ignore::DeprecationWarning", "-c", script],
        capture_output=True, text=True, timeout=30, cwd=str(REPO),
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def test_identity_when_engram_imported_first():
    """Critic counterexample: engram.skill loaded BEFORE hippoagent.skill must
    still expose the SAME class via both import paths."""
    rc, out, err = _run_isolated("""
import engram.skill           # loads engram.skill first
from hippoagent.skill import Skill as ShimSkill
import engram.skill as engram_skill_mod
print('engram.skill is hippoagent.skill?', engram_skill_mod.Skill is ShimSkill)
""")
    assert rc == 0, f"subprocess failed: {err}"
    assert out.endswith("True"), (
        f"Identity failed when engram imported first:\n{out}\nstderr: {err}"
    )


def test_identity_when_hippoagent_imported_first():
    """Mirror direction: hippoagent.skill loaded first must also keep identity."""
    rc, out, err = _run_isolated("""
from hippoagent.skill import Skill as ShimSkill
import engram.skill as engram_skill_mod
print('engram.skill is hippoagent.skill?', engram_skill_mod.Skill is ShimSkill)
""")
    assert rc == 0, f"subprocess failed: {err}"
    assert out.endswith("True")


def test_isinstance_cross_import_path():
    """Instance built via engram.skill must satisfy isinstance(x, hippoagent.skill.Skill)."""
    rc, out, err = _run_isolated("""
from engram.skill import Skill as EngramSkill
inst = EngramSkill(name='t', body='b', trigger='go')
from hippoagent.skill import Skill as ShimSkill
print('isinstance cross-path?', isinstance(inst, ShimSkill))
""")
    assert rc == 0, f"subprocess failed: {err}"
    assert out.endswith("True"), (
        f"isinstance failed across import paths:\n{out}\nstderr: {err}"
    )


def test_module_singleton_state_not_duplicated():
    """Module-level state set in engram.X must be visible via hippoagent.X."""
    rc, out, err = _run_isolated("""
import engram.skill as eng
eng._test_sentinel_value = 'set_via_engram'
import hippoagent.skill as ship
print('sentinel via hippoagent?', getattr(ship, '_test_sentinel_value', '<missing>'))
""")
    assert rc == 0, f"subprocess failed: {err}"
    assert out.endswith("set_via_engram"), (
        f"Module state not shared between engram.skill and hippoagent.skill:\n{out}\nstderr: {err}"
    )


def test_sys_modules_keys_share_object_identity():
    """sys.modules['engram.X'] and sys.modules['hippoagent.X'] must be the same object."""
    rc, out, err = _run_isolated("""
import engram.skill
from hippoagent.skill import Skill
import sys
same = sys.modules.get('engram.skill') is sys.modules.get('hippoagent.skill')
print('sys.modules identity?', same)
""")
    assert rc == 0, f"subprocess failed: {err}"
    assert out.endswith("True")
