"""Signed anchor receipt over BOTH audit chains (task #24, step 2).

Step 1 anchored each chain's head off-box; a bare-head signature, though, binds
nothing but the 64-hex string, so (a) one operator key across two chains lets a
signature for chain A's head be presented as chain B's (domain confusion), and
(b) an in-DB ``verify()`` still cannot see a full-chain rewrite or a
tail-truncate+reinsert (adversary F1/F5).

The receipt closes both: the ed25519 signature covers the CANONICAL
serialization of the whole payload — chain-labelled heads, row counts, ts,
algorithm — not the bare head. A later verify recomputes both chains and checks
the anchored head still appears AT the anchored row count, so a rewrite (same
count, different head) or a truncate+reinsert (count restored, head differs) is
caught. Row counts distinguish "no new rows" from "tail truncated to an older
length".

Honest replay/rollback contract (documented, then tested here): an OLD receipt
legitimately signs an OLDER, shorter state, so it will still verify against a
chain truncated back to that state. The defence is operational — verify against
the NEWEST archived receipt — not cryptographic. What the receipt DOES catch is
any state that is not an append-only extension of the one it signed.
"""
from __future__ import annotations

import json
import sqlite3

import pytest

from verimem import audit_anchor as aa
from verimem import tamper_evidence as te
from verimem.adjudication_log import AdjudicationLog
from verimem.semantic import Fact, SemanticMemory


@pytest.fixture()
def keypair(tmp_path):
    priv, pub = te.generate_audit_keypair(tmp_path / "keys")
    return priv, pub


# ---------------------------------------------------------------------------
# Crypto: the signature binds the WHOLE payload, not a bare head
# ---------------------------------------------------------------------------

def test_sign_receipt_and_verify_roundtrip(keypair):
    priv, pub = keypair
    payload = aa.build_payload(
        ts=1721772000.0, mutations_head="a" * 64, mutations_rows=3,
        adjudications_head="b" * 64, adjudications_rows=2)
    sig = te.sign_receipt(payload, priv)
    assert isinstance(sig, str) and sig
    assert te.verify_receipt_signature(payload, sig, pub) is True


def test_verify_receipt_fails_on_tampered_count(keypair):
    priv, pub = keypair
    payload = aa.build_payload(
        ts=1721772000.0, mutations_head="a" * 64, mutations_rows=3,
        adjudications_head=None, adjudications_rows=0)
    sig = te.sign_receipt(payload, priv)
    forged = dict(payload, mutations_rows=99)   # attacker lowers/raises count
    assert te.verify_receipt_signature(forged, sig, pub) is False


def test_verify_receipt_with_private_key_path(keypair):
    """The private PEM is a valid verify key too (public derived from it), so an
    operator who only wired VERIMEM_AUDIT_SIGNING_KEY can still verify."""
    priv, _pub = keypair
    payload = aa.build_payload(
        ts=1.0, mutations_head="a" * 64, mutations_rows=1,
        adjudications_head=None, adjudications_rows=0)
    sig = te.sign_receipt(payload, priv)
    assert te.verify_receipt_signature(payload, sig, priv) is True


def test_domain_separation_head_bound_to_its_chain(keypair):
    """A signature over {mutations_head=H} must NOT verify a payload that moves
    the same H onto adjudications_head — the whole confusion the bare-head
    signature allowed. Binding chain identity into the signed bytes closes it."""
    priv, pub = keypair
    h = "c" * 64
    signed = aa.build_payload(
        ts=1.0, mutations_head=h, mutations_rows=1,
        adjudications_head=None, adjudications_rows=0)
    sig = te.sign_receipt(signed, priv)
    swapped = aa.build_payload(
        ts=1.0, mutations_head=None, mutations_rows=0,
        adjudications_head=h, adjudications_rows=1)
    assert te.verify_receipt_signature(swapped, sig, pub) is False


def test_receipt_carries_no_fact_content(keypair):
    priv, _pub = keypair
    payload = aa.build_payload(
        ts=1.0, mutations_head="a" * 64, mutations_rows=1,
        adjudications_head="b" * 64, adjudications_rows=1)
    receipt = aa.sign_anchor(payload, priv)
    # only action-metadata fields — heads, counts, ts, algorithm, version, sig
    assert set(receipt) == {
        "version", "ts", "algorithm", "mutations_head", "mutations_rows",
        "adjudications_head", "adjudications_rows", "signature"}


# ---------------------------------------------------------------------------
# SDK: Memory.audit_anchor / audit_verify_anchor over both chains
# ---------------------------------------------------------------------------

def _memory_with_both_chains(tmp_path, priv, monkeypatch):
    from verimem.client import Memory
    monkeypatch.setenv("VERIMEM_AUDIT_LOG", "1")
    monkeypatch.setenv("VERIMEM_AUDIT_SIGNING_KEY", str(priv))
    mem = Memory(path=tmp_path / "store" / "semantic.db")
    mem.add("The reserve tank holds 500 liters.", topic="b/x")   # chain 1 row
    mem.semantic.store(Fact(id="f1", proposition="note", topic="t"), embed="sync")
    mem.delete("f1")                                             # chain 2 row
    return mem


def test_audit_anchor_covers_both_chains(tmp_path, keypair, monkeypatch):
    priv, pub = keypair
    mem = _memory_with_both_chains(tmp_path, priv, monkeypatch)
    receipt = mem.audit_anchor()

    assert receipt["algorithm"] == "ed25519"
    assert receipt["mutations_head"] == mem.semantic.audit_head()
    assert receipt["mutations_rows"] == 1
    assert receipt["adjudications_head"] == mem.audit_head()
    assert receipt["adjudications_rows"] >= 1
    payload = {k: v for k, v in receipt.items() if k != "signature"}
    assert te.verify_receipt_signature(payload, receipt["signature"], pub) is True


def test_audit_anchor_raises_without_key(tmp_path, monkeypatch):
    """Unlike audit_head_signed (honest None), the anchor command EXISTS to
    sign: no key configured is an actionable error, never a silent no-op."""
    from verimem.client import Memory
    monkeypatch.delenv("VERIMEM_AUDIT_SIGNING_KEY", raising=False)
    mem = Memory(path=tmp_path / "store" / "semantic.db")
    with pytest.raises(RuntimeError, match="VERIMEM_AUDIT_SIGNING_KEY"):
        mem.audit_anchor()


def test_verify_anchor_passes_on_clean_extension(tmp_path, keypair, monkeypatch):
    priv, _pub = keypair
    mem = _memory_with_both_chains(tmp_path, priv, monkeypatch)
    receipt = mem.audit_anchor()
    # append MORE legitimate mutations after anchoring
    mem.semantic.store(Fact(id="g1", proposition="later", topic="t"), embed="sync")
    mem.delete("g1")

    res = mem.audit_verify_anchor(receipt)
    assert res.ok is True, res.failures


def test_verify_anchor_detects_tail_truncation(tmp_path, keypair, monkeypatch):
    priv, _pub = keypair
    mem = _memory_with_both_chains(tmp_path, priv, monkeypatch)
    receipt = mem.audit_anchor()
    with sqlite3.connect(mem.semantic.db_path) as conn:
        conn.execute("DELETE FROM audit_mutations WHERE rowid=("
                     "SELECT rowid FROM audit_mutations ORDER BY rowid DESC LIMIT 1)")

    res = mem.audit_verify_anchor(receipt)
    assert res.ok is False
    assert any("mutations" in f and "trunc" in f.lower() for f in res.failures), \
        res.failures


def test_verify_anchor_detects_truncate_and_reinsert(tmp_path, keypair, monkeypatch):
    """F5: truncate the tail, then append a FRESH legit row so the count is
    restored and the chain is internally valid again. verify() alone is blind;
    the anchored head-at-count catches it."""
    priv, _pub = keypair
    mem = _memory_with_both_chains(tmp_path, priv, monkeypatch)
    receipt = mem.audit_anchor()
    n = receipt["mutations_rows"]
    with sqlite3.connect(mem.semantic.db_path) as conn:
        conn.execute("DELETE FROM audit_mutations WHERE rowid=("
                     "SELECT rowid FROM audit_mutations ORDER BY rowid DESC LIMIT 1)")
    mem.semantic.store(Fact(id="fx", proposition="reinsert", topic="t"), embed="sync")
    mem.delete("fx")

    assert mem.semantic.audit_count() == n          # count restored
    assert mem.semantic.audit_verify() is None       # chain internally valid
    res = mem.audit_verify_anchor(receipt)
    assert res.ok is False
    assert any("mutations" in f and "head" in f for f in res.failures), res.failures


def test_verify_anchor_detects_edited_row(tmp_path, keypair, monkeypatch):
    priv, _pub = keypair
    mem = _memory_with_both_chains(tmp_path, priv, monkeypatch)
    receipt = mem.audit_anchor()
    with sqlite3.connect(mem.semantic.db_path) as conn:
        conn.execute("UPDATE audit_mutations SET principal='attacker'")

    res = mem.audit_verify_anchor(receipt)
    assert res.ok is False
    assert any("mutations" in f for f in res.failures), res.failures


def test_verify_anchor_detects_forged_signature(tmp_path, keypair, monkeypatch):
    priv, _pub = keypair
    mem = _memory_with_both_chains(tmp_path, priv, monkeypatch)
    receipt = mem.audit_anchor()
    receipt["mutations_rows"] = 999          # tamper the signed payload

    res = mem.audit_verify_anchor(receipt)
    assert res.ok is False
    assert any("signature" in f for f in res.failures), res.failures


# ---------------------------------------------------------------------------
# CLI: verimem audit anchor / verimem audit verify --anchor FILE
# ---------------------------------------------------------------------------

def _sm(tmp_path) -> SemanticMemory:
    return SemanticMemory(db_path=tmp_path / "sem.db")


def _seed_both_chains(sm: SemanticMemory) -> None:
    from pathlib import Path
    sm.store(Fact(id="f1", proposition="note", topic="t"), embed="sync")
    sm.delete("f1", principal="cli:local")                       # chain 2 row
    adj = AdjudicationLog(Path(sm.db_path).with_name("adjudications.db"))
    adj.record(disposition="admitted", topic="t", proposition="p")  # chain 1 row


def test_cli_anchor_emits_signed_receipt(tmp_path, keypair, monkeypatch):
    from typer.testing import CliRunner

    from verimem.cli import app

    priv, pub = keypair
    sm = _sm(tmp_path)
    _seed_both_chains(sm)
    monkeypatch.setenv("VERIMEM_AUDIT_SIGNING_KEY", str(priv))
    out = tmp_path / "anchor.json"

    runner = CliRunner()
    res = runner.invoke(app, ["audit", "anchor", "--db", str(sm.db_path),
                              "--out", str(out)])
    assert res.exit_code == 0, res.output
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["mutations_rows"] == 1
    assert receipt["adjudications_rows"] == 1
    payload = {k: v for k, v in receipt.items() if k != "signature"}
    assert te.verify_receipt_signature(payload, receipt["signature"], pub) is True


def test_cli_anchor_errors_without_key(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from verimem.cli import app

    monkeypatch.delenv("VERIMEM_AUDIT_SIGNING_KEY", raising=False)
    sm = _sm(tmp_path)
    _seed_both_chains(sm)

    runner = CliRunner()
    res = runner.invoke(app, ["audit", "anchor", "--db", str(sm.db_path)])
    assert res.exit_code != 0
    assert "VERIMEM_AUDIT_SIGNING_KEY" in res.output


def test_cli_verify_anchor_ok_then_tampered(tmp_path, keypair, monkeypatch):
    from typer.testing import CliRunner

    from verimem.cli import app

    priv, _pub = keypair
    sm = _sm(tmp_path)
    _seed_both_chains(sm)
    monkeypatch.setenv("VERIMEM_AUDIT_SIGNING_KEY", str(priv))
    out = tmp_path / "anchor.json"

    runner = CliRunner()
    assert runner.invoke(app, ["audit", "anchor", "--db", str(sm.db_path),
                               "--out", str(out)]).exit_code == 0

    ok = runner.invoke(app, ["audit", "verify", "--db", str(sm.db_path),
                             "--anchor", str(out)])
    assert ok.exit_code == 0, ok.output

    # tail-truncate the mutation chain, then re-verify against the same anchor
    with sqlite3.connect(sm.db_path) as conn:
        conn.execute("DELETE FROM audit_mutations")
    bad = runner.invoke(app, ["audit", "verify", "--db", str(sm.db_path),
                              "--anchor", str(out)])
    assert bad.exit_code == 1
    assert "mutations" in bad.output
