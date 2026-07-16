"""AUDIT-LEDGER mod.4 (2026-07-16): a tenant_id maps to a filesystem directory
``tenants/<tenant_id>/memory.db``. The slug regex allows lowercase device names
(`con`, `aux`, `nul`, `com1`…) that are RESERVED on Windows at any path level —
creating such a directory fails on the Windows host the product ships on. Reject
them at key-creation time. Guard against over-rejection: names that merely
CONTAIN a reserved token ("console", "com1x") stay valid.
"""
from __future__ import annotations

import pytest

from engram.gateway import GatewayKeys


def test_windows_reserved_tenant_ids_rejected(tmp_path):
    keys = GatewayKeys(tmp_path / "k.db")
    for bad in ["con", "aux", "nul", "prn", "com1", "com9", "lpt1", "lpt9",
                "con.db", "aux.anything"]:
        with pytest.raises(ValueError):
            keys.create(tenant_id=bad)


def test_names_containing_reserved_token_still_valid(tmp_path):
    keys = GatewayKeys(tmp_path / "k.db")
    for ok in ["console", "connector", "aux-team", "com1x", "lpt", "nullable"]:
        k = keys.create(tenant_id=ok)
        assert k.startswith("vm_"), f"{ok!r} wrongly rejected"
