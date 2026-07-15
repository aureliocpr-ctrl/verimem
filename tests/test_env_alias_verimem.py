"""REBRAND env bridge — ``VERIMEM_*`` come prefisso di prodotto (task 2026-07-15).

Il prodotto si chiama Verimem (PyPI ``verimem``, ``from verimem import Memory``)
ma le 91 env di configurazione sono nate ``ENGRAM_*``. Questo bridge estende il
mirror esistente HIPPO_↔ENGRAM_ (cycle #41) col prefisso brand: chi configura
``VERIMEM_X`` viene visto da OGNI lettore di ``ENGRAM_X`` (e ``HIPPO_X``)
senza toccare i 91 call-site. setdefault-only: un valore esplicito non è MAI
sovrascritto → zero breaking per costruzione.
"""
from __future__ import annotations

import os

import pytest

from engram import _compat


@pytest.fixture()
def clean_env(monkeypatch):
    """Rimuove le tre varianti del suffisso di test dall'ambiente."""
    for k in ("VERIMEM_ALIAS_PROBE", "ENGRAM_ALIAS_PROBE", "HIPPO_ALIAS_PROBE",
              "VERIMEM_SOURCE_TRUST", "ENGRAM_SOURCE_TRUST",
              "HIPPO_SOURCE_TRUST"):
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


def test_verimem_env_is_mirrored_to_engram_and_hippo(clean_env):
    clean_env.setenv("VERIMEM_ALIAS_PROBE", "42")
    _compat.init_env_aliases()
    assert os.environ["ENGRAM_ALIAS_PROBE"] == "42"
    assert os.environ["HIPPO_ALIAS_PROBE"] == "42"     # transitivo, path legacy


def test_engram_env_is_mirrored_to_verimem(clean_env):
    clean_env.setenv("ENGRAM_ALIAS_PROBE", "7")
    _compat.init_env_aliases()
    assert os.environ["VERIMEM_ALIAS_PROBE"] == "7"    # simmetria (introspezione)


def test_explicit_values_are_never_clobbered(clean_env):
    clean_env.setenv("VERIMEM_ALIAS_PROBE", "brand")
    clean_env.setenv("ENGRAM_ALIAS_PROBE", "legacy")
    _compat.init_env_aliases()
    # entrambi espliciti → entrambi intatti (i lettori ENGRAM_ vedono "legacy")
    assert os.environ["VERIMEM_ALIAS_PROBE"] == "brand"
    assert os.environ["ENGRAM_ALIAS_PROBE"] == "legacy"


def test_idempotent(clean_env):
    clean_env.setenv("VERIMEM_ALIAS_PROBE", "1")
    _compat.init_env_aliases()
    added_again = _compat.init_env_aliases()
    assert added_again == 0
    assert os.environ["ENGRAM_ALIAS_PROBE"] == "1"


def test_real_consumer_sees_verimem_flag(clean_env):
    """End-to-end su un lettore REALE: source_trust.enabled() legge
    ENGRAM_SOURCE_TRUST — configurato via VERIMEM_SOURCE_TRUST deve accendersi."""
    from engram import source_trust
    clean_env.setenv("VERIMEM_SOURCE_TRUST", "1")
    assert source_trust.enabled() is False        # prima del bridge: spento
    _compat.init_env_aliases()
    assert source_trust.enabled() is True         # dopo: il flag brand è visto
