"""``_EXPECTED_EMBEDDING_BYTES`` (byte-filter del recall facts/episodi/skill) deve
SEGUIRE ``CONFIG.embedding_dim`` (env ``HIPPO_EMBEDDING_DIM``), NON essere un
letterale ``384*4``. Altrimenti un cambio di dimensione embedding (es. upgrade a
``multilingual-e5-base`` 768d) farebbe escludere TUTTI i vettori a 768d dal
length-guard SQL -> recall vuoto. Landmine mappato 2026-06-04 (config.py:110-111
lo segnalava come letterale DECOUPLED).

Test ermetico via SUBPROCESS con ``HIPPO_EMBEDDING_DIM=768`` impostato PRIMA
dell'import: un letterale 384*4 ignora l'env (-> 1536 -> RED); il fix dim-dinamico
segue (-> 3072 -> GREEN). Non tocca lo stato live.
"""
from __future__ import annotations

import subprocess
import sys


def test_expected_bytes_follows_embedding_dim_env():
    code = (
        "import os; os.environ['HIPPO_EMBEDDING_DIM']='768'; "
        "from engram import semantic; "
        "v=semantic._EXPECTED_EMBEDDING_BYTES; "
        "assert v==768*4, f'atteso 3072 (768*4), ottenuto {v} -> letterale 384*4 hardcoded'; "
        "print('OK', v)"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, f"RED: stdout={r.stdout!r} stderr={r.stderr[-600:]!r}"
    assert "OK 3072" in r.stdout


def test_expected_bytes_default_dim_is_1536():
    """Backward-compat: senza env (dim default 384) il filtro resta 1536 (=384*4)."""
    code = (
        "from engram import semantic; "
        "v=semantic._EXPECTED_EMBEDDING_BYTES; "
        "assert v==384*4, f'atteso 1536 a dim default, ottenuto {v}'; "
        "print('OK', v)"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, f"stdout={r.stdout!r} stderr={r.stderr[-600:]!r}"
    assert "OK 1536" in r.stdout
