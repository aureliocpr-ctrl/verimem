"""End-to-end secret redaction on the WRITE path — the "source security"
guarantee, locked. Unit tests cover redact_secrets() and the config endpoints;
this asserts the STORED fact is redacted after Memory.add(), across secret
types, so a credential pasted into a memory is never recalled back verbatim.

Redaction is ALWAYS-ON at store time (semantic.py, escape hatch
ENGRAM_REDACT_SECRETS=0). Secrets are constructed at runtime — never a literal
in the file (repo push-protection blocks literal token shapes even in tests).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from engram.client import Memory


def _mem() -> Memory:
    return Memory(Path(tempfile.mkdtemp(prefix="redact_e2e_")) / "m.db")


# (label, sentence, the raw substring that must NOT survive)
def _cases():
    return [
        ("openai", "My OpenAI key is sk-" + "A" * 48, "sk-" + "A" * 48),
        ("aws", "AWS access key AKIA" + "B" * 16, "AKIA" + "B" * 16),
        ("github", "GitHub token ghp_" + "c" * 36, "ghp_" + "c" * 36),
        ("dburl", "DB url postgres://u:" + "S3cretPw" + "@db.example.com/prod",
         "S3cretPw"),
        ("privkey",
         "SSH -----BEGIN PRIVATE KEY-----" + "X" * 40 + "-----END PRIVATE KEY-----",
         "X" * 40),
    ]


@pytest.mark.parametrize("label,sentence,raw", _cases())
def test_secret_is_redacted_in_stored_fact(label, sentence, raw):
    m = _mem()
    res = m.add(sentence, topic="sec", verified_by=["src:t1"])
    fid = res.get("id")
    stored = next((f.proposition for f in m.semantic.all() if f.id == fid), "")
    assert raw not in stored, f"{label}: raw secret survived into storage: {stored!r}"
    assert "[REDACTED]" in stored, f"{label}: no redaction marker: {stored!r}"


@pytest.mark.parametrize("label,sentence,raw", _cases())
def test_redacted_secret_not_recallable(label, sentence, raw):
    m = _mem()
    m.add(sentence, topic="sec", verified_by=["src:t1"])
    hits = m.search(sentence)
    assert not any(raw in str(h) for h in hits), \
        f"{label}: raw secret recalled back into context"


def test_prose_is_untouched():
    # no false positive: an ordinary sentence is stored verbatim
    m = _mem()
    text = "The Berlin warehouse ships orders every Monday morning."
    res = m.add(text, topic="ops", verified_by=["src:t1"])
    stored = next((f.proposition for f in m.semantic.all()
                   if f.id == res.get("id")), "")
    assert stored == text and "[REDACTED]" not in stored
