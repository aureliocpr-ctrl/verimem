"""The structural per-test isolation guards in conftest.py.

2026-07-20: the final full suite showed 19 order-dependent failures (seed
4060964388). Minimal reproduced pair: running test_mcp_thin.py first left
``verimem.mcp_server``'s thin-mode probe globals (``_remote_mem`` /
``_remote_checked`` / ``_remote_auth_error``) pointing at a gateway that no
longer exists, and 5 test_mcp_server cases then delegated their reads into
the void. Same CLASS as the VERIMEM_MULTI_WRITER env leak fixed the day
before: per-test state (env var or module global) escaping one test and
poisoning another. Instead of patching each leaking test, conftest now owns
two guards that make the whole class impossible; these are their unit tests.
"""
from __future__ import annotations

import os

import pytest


def test_env_guard_removes_new_and_restores_overwritten(monkeypatch):
    from tests.conftest import _verimem_env_guard

    monkeypatch.setenv("VERIMEM_GUARD_BASE", "orig")

    guard = _verimem_env_guard()
    next(guard)
    # simulate a test that writes os.environ directly and forgets to clean up
    os.environ["VERIMEM_GUARD_NEW"] = "leak"
    os.environ["VERIMEM_GUARD_BASE"] = "clobbered"
    os.environ["ENGRAM_GUARD_NEW"] = "leak"
    os.environ["HIPPO_GUARD_NEW"] = "leak"
    with pytest.raises(StopIteration):
        next(guard)

    assert "VERIMEM_GUARD_NEW" not in os.environ
    assert "ENGRAM_GUARD_NEW" not in os.environ
    assert "HIPPO_GUARD_NEW" not in os.environ
    assert os.environ["VERIMEM_GUARD_BASE"] == "orig"


def test_env_guard_leaves_foreign_env_alone(monkeypatch):
    """The guard owns only the product's prefixes — PATH etc. stay untouched."""
    from tests.conftest import _verimem_env_guard

    monkeypatch.setenv("UNRELATED_GUARD_PROBE", "before")
    guard = _verimem_env_guard()
    next(guard)
    os.environ["UNRELATED_GUARD_PROBE"] = "after"
    with pytest.raises(StopIteration):
        next(guard)
    assert os.environ["UNRELATED_GUARD_PROBE"] == "after"


def test_remote_probe_reset_clears_thin_singletons():
    import verimem.mcp_server as m
    from tests.conftest import _reset_mcp_remote_probe_state

    m._remote_mem = object()
    m._remote_checked = True
    m._remote_auth_error = "server rejected our key"
    _reset_mcp_remote_probe_state()
    assert m._remote_mem is None
    assert m._remote_checked is False
    assert m._remote_auth_error is None
