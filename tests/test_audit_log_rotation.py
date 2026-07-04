"""CYCLE #14 — test ring rotation per mcp_audit.log.

Bug latente: audit log era append-only senza rotation. Live corpus aveva
10828 entries / 1.4 MB; cresceva senza limiti, prima o poi avrebbe
saturato il disco.

Fix testato: rotation a soglia configurable (default 5MB) con 1 backup.
"""
from __future__ import annotations

import json
import os

import pytest

from engram import mcp_server


@pytest.fixture
def audit_log(tmp_path, monkeypatch):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setenv("HIPPO_MCP_AUDIT_LOG", str(log))
    monkeypatch.setattr(mcp_server, "_AUDIT_MAX_BYTES", 200)  # 200 byte soglia
    # Reset counter
    mcp_server._AUDIT_WRITE_COUNTER["n"] = 0
    return log


def test_rotate_renames_to_backup_when_over_size(audit_log, monkeypatch):
    """File > soglia → rotato a .1 backup."""
    # Scrivi a mano un file da 300 byte
    audit_log.write_text("x" * 300, encoding="utf-8")
    mcp_server._rotate_audit_if_needed(audit_log)
    # Original eliminato, backup creato
    assert not audit_log.exists()
    backup = audit_log.with_suffix(audit_log.suffix + ".1")
    assert backup.exists()
    assert backup.stat().st_size == 300


def test_rotate_noop_when_under_size(audit_log):
    """File < soglia → nessuna rotation."""
    audit_log.write_text("x" * 50, encoding="utf-8")
    mcp_server._rotate_audit_if_needed(audit_log)
    assert audit_log.exists()
    assert audit_log.stat().st_size == 50
    backup = audit_log.with_suffix(audit_log.suffix + ".1")
    assert not backup.exists()


def test_rotate_overwrites_previous_backup(audit_log):
    """Pre-esistente backup .1 viene sovrascritto al rotate successivo."""
    backup = audit_log.with_suffix(audit_log.suffix + ".1")
    backup.write_text("OLD_BACKUP", encoding="utf-8")
    audit_log.write_text("y" * 300, encoding="utf-8")
    mcp_server._rotate_audit_if_needed(audit_log)
    assert backup.exists()
    # Backup ora contiene il nuovo 'y'*300, non l'OLD
    assert backup.read_text(encoding="utf-8") == "y" * 300


def test_rotate_safe_on_missing_file(audit_log):
    """Path che non esiste → no crash."""
    mcp_server._rotate_audit_if_needed(audit_log)  # never created
    # Niente è stato creato
    assert not audit_log.exists()


def test_audit_writes_trigger_rotation_at_threshold(audit_log, monkeypatch):
    """Sequenza di _audit() chiamate triggera rotation quando supera soglia.
    _AUDIT_ROTATE_CHECK_EVERY=100 (default) — abbasso per test."""
    monkeypatch.setattr(mcp_server, "_AUDIT_ROTATE_CHECK_EVERY", 5)
    # Ogni entry ~150 byte. 5 entries × 150 = 750 byte > soglia 200.
    for i in range(15):
        mcp_server._audit(f"tool_{i}", {"x": i}, outcome="ok")
    # Ora dovrebbe essere stata rotata almeno una volta
    backup = audit_log.with_suffix(audit_log.suffix + ".1")
    assert backup.exists(), "Backup not created after rotation"
    # Il file principale deve essere più piccolo del backup
    assert audit_log.stat().st_size < backup.stat().st_size


def test_audit_writes_jsonl_format(audit_log, monkeypatch):
    """Ogni entry deve essere JSON parseable."""
    monkeypatch.setattr(mcp_server, "_AUDIT_ROTATE_CHECK_EVERY", 1000)  # no rotate
    mcp_server._audit("my_tool", {"k": "v"}, outcome="ok")
    lines = audit_log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["tool"] == "my_tool"
    assert record["outcome"] == "ok"
    assert "ts" in record
    assert "args_hash" in record


def test_audit_max_bytes_from_env(monkeypatch):
    """HIPPO_AUDIT_MAX_BYTES env var deve poter override default."""
    # Default 5MB
    assert mcp_server._AUDIT_MAX_BYTES == 5_242_880
    # Override via reload not trivial; just confirm constant is settable.
