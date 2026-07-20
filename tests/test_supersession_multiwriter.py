"""Same-source supersession under a SHARED server (Kimi red-team audit F2).

Default-ON supersession is justified by a written safety argument whose load
-bearing leg is a single-agent-per-tenant assumption: "the sole agent
superseding its OWN values is the intended feature". The architecture-A thin
tier makes that FALSE BY CONSTRUCTION — N agent sessions behind one shared
server authenticate with ONE tenant key, so they are many writers in one
tenant. With `verified_by` spoofable and `asserted_at` caller-controlled, one
compromised session can retire another session's true values as an
"evolution".

So the default follows the assumption: ON where a single agent owns the store
(embedded, the product's core promise), OFF where the server is shared. An
explicit ENGRAM_SUPERSEDE_SAME_SOURCE still wins either way — an operator who
knows their writers are trustworthy can opt back in.
"""
from __future__ import annotations

import os

import pytest

from verimem import anti_confab_gate as G


def test_supersede_on_by_default_for_a_single_agent_store(monkeypatch):
    monkeypatch.delenv("ENGRAM_SUPERSEDE_SAME_SOURCE", raising=False)
    monkeypatch.delenv("VERIMEM_MULTI_WRITER", raising=False)
    assert G._supersede_same_source_on() is True


def test_supersede_off_by_default_when_the_server_is_shared(monkeypatch):
    """The single-agent assumption is false by construction here."""
    monkeypatch.delenv("ENGRAM_SUPERSEDE_SAME_SOURCE", raising=False)
    monkeypatch.setenv("VERIMEM_MULTI_WRITER", "1")
    assert G._supersede_same_source_on() is False


@pytest.mark.parametrize("explicit,expected", [("1", True), ("0", False)])
def test_explicit_setting_always_wins(monkeypatch, explicit, expected):
    """An operator who knows their writers stays in control, both ways."""
    monkeypatch.setenv("VERIMEM_MULTI_WRITER", "1")
    monkeypatch.setenv("ENGRAM_SUPERSEDE_SAME_SOURCE", explicit)
    assert G._supersede_same_source_on() is expected


def test_gateway_declares_itself_multi_writer(tmp_path, monkeypatch):
    """The shared server is the multi-writer context: it must SAY so, so the
    write-gate running inside it picks the matching default."""
    fastapi = pytest.importorskip("fastapi")  # noqa: F841
    monkeypatch.delenv("VERIMEM_MULTI_WRITER", raising=False)
    from verimem.gateway import GatewayKeys, create_app
    keys = GatewayKeys(tmp_path / "keys.db")
    create_app(data_dir=tmp_path / "gwdata", keys=keys)
    assert os.environ.get("VERIMEM_MULTI_WRITER") == "1"
