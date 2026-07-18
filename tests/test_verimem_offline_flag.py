"""VERIMEM_OFFLINE works on the REAL binding path (env set BEFORE the process),
via the compat mirror in ``verimem._compat`` — NOT by adding the brand flag to
each offline-flag enumeration. Adding it to ``embedding._OFFLINE_ENV_VARS`` broke
tests that clear the legacy flag set but not the brand one (2026-07-18 CI
regression): the mirror already covered the real path, so the direct-read was
redundant AND harmful. This guards the brand promise the HONEST way — a
subprocess with the env set before import, exactly like a user's shell / .mcp.json
(the morning's lesson: an env test that sets the var AFTER import bypasses the
import-time mirror and tests an artifact).
"""
from __future__ import annotations

import os
import subprocess
import sys

_OFFLINE_VARS = ("HIPPO_OFFLINE", "ENGRAM_OFFLINE", "HF_HUB_OFFLINE",
                 "TRANSFORMERS_OFFLINE", "VERIMEM_OFFLINE")


def _run(code: str, env_over: dict) -> int:
    env = {k: v for k, v in os.environ.items() if k not in _OFFLINE_VARS}
    env.update(env_over)
    return subprocess.run([sys.executable, "-c", code], env=env).returncode


def test_verimem_offline_pins_embedding_on_the_real_path():
    code = ("import verimem; from verimem.embedding import _offline;"
            "import sys; sys.exit(0 if _offline() else 1)")
    assert _run(code, {"VERIMEM_OFFLINE": "1"}) == 0, (
        "VERIMEM_OFFLINE set before launch must pin embeddings offline via the "
        "_compat env mirror")


def test_no_offline_flag_stays_online():
    code = ("import verimem; from verimem.embedding import _offline;"
            "import sys; sys.exit(0 if not _offline() else 1)")
    assert _run(code, {}) == 0, "with no offline flag the loader must stay online"
