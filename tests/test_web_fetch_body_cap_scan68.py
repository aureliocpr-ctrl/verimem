"""TDD — EHS-05 (codex scan 2026-06-02): web_fetch scaricava l'intero body in
RAM (r.text/r.content) e troncava SOLO il testo a max_chars -> un server puo
rispondere con GB => DoS memoria. Il cap deve agire sul DOWNLOAD, non solo
sull'output.

Fix aggiusta-non-rovina: funzione pura _read_body_capped(resp, max_bytes) che
legge lo stream httpx fermandosi a max_bytes. HERMETIC (fake response, niente
rete). Test RED finche la funzione non esiste.
"""
from __future__ import annotations

import pytest


class _FakeStreamResp:
    """Imita la parte di httpx.Response usata: iter_bytes()."""
    def __init__(self, chunks):
        self._chunks = chunks

    def iter_bytes(self, chunk_size=None):
        yield from self._chunks


def test_read_body_capped_stops_at_limit():
    from verimem.tools_extra import _read_body_capped
    # 10 chunk da 1000 byte = 10_000 disponibili, ma cap a 2500
    resp = _FakeStreamResp([b"x" * 1000] * 10)
    out = _read_body_capped(resp, max_bytes=2500)
    assert isinstance(out, (bytes, bytearray))
    assert len(out) == 2500, f"deve fermarsi al cap, letto {len(out)}"


def test_read_body_capped_under_limit_returns_all():
    from verimem.tools_extra import _read_body_capped
    resp = _FakeStreamResp([b"abc", b"de"])
    out = _read_body_capped(resp, max_bytes=1_000_000)
    assert bytes(out) == b"abcde"


def test_read_body_capped_does_not_overread():
    """Non deve materializzare piu di ~max_bytes anche con chunk enormi."""
    from verimem.tools_extra import _read_body_capped
    # un solo chunk da 10MB; cap 1MB -> non deve ritornare 10MB
    resp = _FakeStreamResp([b"y" * (10 * 1024 * 1024)])
    out = _read_body_capped(resp, max_bytes=1024 * 1024)
    assert len(out) <= 1024 * 1024 + 1, "non deve superare il cap (oltre l'ultimo chunk parziale)"
