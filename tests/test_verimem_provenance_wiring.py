"""The write path must HONOUR a provenance signature that is present.

verimem ships `provenance_signing` (HMAC binding a verified_by ref to the
proposition it backs) with the crypto proven sound in isolation — and, until
this module, with ZERO call sites: no write or read path ever called
`sign_ref` / `verify_ref` / `verify_fact_refs`, so `VERIMEM_PROVENANCE_KEY`
(alias `ENGRAM_PROVENANCE_KEY`) was documented as an opt-in that could not be
opted into.

The wiring contract, deliberately narrow so it cannot regress the corpus:

* No key configured  -> nothing changes. The signature layer is inert, exactly
  as today, and every existing store keeps its behaviour.
* Key configured, ref carries a VALID signature  -> admitted as usual.
* Key configured, ref carries a signature that does NOT verify -> the write is
  quarantined. A broken signature is not a missing one: someone asserted an
  origin and the assertion does not hold, which is the forgery the SMSR
  complement exists to catch.
* Key configured, ref carries NO signature -> unchanged. Unsigned provenance is
  the historical norm; refusing it would quarantine the whole existing corpus.
* `actor:` refs are exempt in every case (P85: engine writes are admitted by
  verification, never by claimed reputation).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from verimem.provenance_signing import _SIG_TAG, sign_ref
from verimem.semantic import Fact, SemanticMemory

KEY = "test-provenance-key"
PROP = "Il consiglio si riunisce nella sala grande al secondo piano."


@pytest.fixture()
def store(tmp_path: Path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "s.db")


def _store_and_read(store: SemanticMemory, refs: list[str], *, fid: str) -> str:
    fact = Fact(id=fid, topic="probe/signing", proposition=PROP,
                verified_by=list(refs))
    store.store(fact, hook_token=None)
    with store._connect() as conn:
        row = conn.execute("SELECT status FROM facts WHERE id = ?", (fid,)).fetchone()
    return row["status"] if row else ""


def test_no_key_configured_leaves_every_ref_alone(store, monkeypatch):
    """P1 — without a key the layer is inert, tampered signature included."""
    monkeypatch.delenv("VERIMEM_PROVENANCE_KEY", raising=False)
    monkeypatch.delenv("ENGRAM_PROVENANCE_KEY", raising=False)
    signed = sign_ref("source-doc:alice:t1", PROP, key=KEY)
    body, sig = signed.split(_SIG_TAG)
    tampered = f"{body}{_SIG_TAG}{'0' * len(sig)}"
    assert _store_and_read(store, [tampered], fid="p1") != "quarantined"


def test_valid_signature_is_admitted(store, monkeypatch):
    """P2 — a signature that verifies does not stand in the way."""
    monkeypatch.setenv("VERIMEM_PROVENANCE_KEY", KEY)
    signed = sign_ref("source-doc:alice:t1", PROP, key=KEY)
    assert _store_and_read(store, [signed], fid="p2") != "quarantined"


def test_broken_signature_is_quarantined(store, monkeypatch):
    """P3 — the point of the whole module: an origin asserted and not held."""
    monkeypatch.setenv("VERIMEM_PROVENANCE_KEY", KEY)
    signed = sign_ref("source-doc:alice:t1", PROP, key=KEY)
    body, sig = signed.split(_SIG_TAG)
    forged = f"{body.replace('alice', 'mallory')}{_SIG_TAG}{sig}"
    assert _store_and_read(store, [forged], fid="p3") == "quarantined"


def test_cross_fact_replay_is_quarantined(store, monkeypatch):
    """P3b — a signature valid for ANOTHER proposition must not travel."""
    monkeypatch.setenv("VERIMEM_PROVENANCE_KEY", KEY)
    replayed = sign_ref("source-doc:alice:t1", "una proposizione del tutto diversa",
                        key=KEY)
    assert _store_and_read(store, [replayed], fid="p3b") == "quarantined"


def test_unsigned_ref_is_untouched(store, monkeypatch):
    """P4 — unsigned provenance is the historical norm and must keep working."""
    monkeypatch.setenv("VERIMEM_PROVENANCE_KEY", KEY)
    assert _store_and_read(store, ["source-doc:alice:t1"], fid="p4") != "quarantined"


def test_actor_refs_are_exempt(store, monkeypatch):
    """P5 — P85: engine writes are never judged on claimed reputation."""
    monkeypatch.setenv("VERIMEM_PROVENANCE_KEY", KEY)
    assert _store_and_read(store, ["actor:composer"], fid="p5") != "quarantined"
