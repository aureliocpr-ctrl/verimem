"""Tamper anchor-B — the audit head signed with an EXTERNAL key (task #24).

Anchor-A (shipped) exports the hash-chain head for the operator to archive;
an attacker who owns the DB can recompute the chain but NOT forge a head
signed by a key that never lives in the DB-writing process. ed25519 via the
``cryptography`` package (optional extra); the private key is a PEM file the
OPERATOR manages (``VERIMEM_AUDIT_SIGNING_KEY``) — never stored by verimem.

Honest scope: B detects head forgery GIVEN the key stays external; it does
not add C's public timestamping (air-gap-friendly by design).
"""
from __future__ import annotations

import pytest

from verimem import tamper_evidence as te


@pytest.fixture()
def keypair(tmp_path):
    priv, pub = te.generate_audit_keypair(tmp_path)
    return priv, pub


def test_generate_keypair_writes_pem_files(tmp_path):
    priv, pub = te.generate_audit_keypair(tmp_path)
    assert priv.exists() and pub.exists()
    assert b"PRIVATE KEY" in priv.read_bytes()
    assert b"PUBLIC KEY" in pub.read_bytes()


def test_sign_and_verify_roundtrip(keypair):
    priv, pub = keypair
    head = "a" * 64
    sig = te.sign_head(head, priv)
    assert isinstance(sig, str) and sig
    assert te.verify_head_signature(head, sig, pub) is True


def test_verify_fails_on_different_head(keypair):
    priv, pub = keypair
    sig = te.sign_head("a" * 64, priv)
    assert te.verify_head_signature("b" * 64, sig, pub) is False


def test_verify_fails_on_garbage_signature(keypair):
    _priv, pub = keypair
    assert te.verify_head_signature("a" * 64, "not-a-signature", pub) is False


def test_client_audit_head_signed(tmp_path, monkeypatch):
    """Memory.audit_head_signed(): head + ed25519 signature when the operator
    configured VERIMEM_AUDIT_SIGNING_KEY; None head -> None (empty log)."""
    from verimem.client import Memory
    priv, pub = te.generate_audit_keypair(tmp_path)
    monkeypatch.setenv("VERIMEM_AUDIT_LOG", "1")
    monkeypatch.setenv("VERIMEM_AUDIT_SIGNING_KEY", str(priv))
    mem = Memory(tmp_path / "m.db")
    mem.add("The reserve tank holds 500 liters.", topic="b/x")
    out = mem.audit_head_signed()
    assert out is not None
    assert out["head"] == mem.audit_head()
    assert out["algorithm"] == "ed25519"
    assert te.verify_head_signature(out["head"], out["signature"], pub) is True


def test_client_audit_head_signed_none_without_key(tmp_path, monkeypatch):
    from verimem.client import Memory
    monkeypatch.setenv("VERIMEM_AUDIT_LOG", "1")
    monkeypatch.delenv("VERIMEM_AUDIT_SIGNING_KEY", raising=False)
    mem = Memory(tmp_path / "m.db")
    mem.add("The reserve tank holds 500 liters.", topic="b/x")
    assert mem.audit_head_signed() is None   # no key configured -> honest None
