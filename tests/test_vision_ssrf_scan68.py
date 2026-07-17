"""TDD — vision_describe SSRF (scan 68-Opus 2026-06-02).

_read_image_to_b64_and_media_type() scaricava URL http(s) arbitrarie senza la difesa
_is_blocked_host (la stessa che web_fetch applica) => un'immagine
http://169.254.169.254/... (cloud metadata) o http://127.0.0.1/... (loopback/interno)
veniva fetchata = SSRF (CVE-006). Il fix deve bloccare l'host PRIMA del fetch (e a ogni
redirect). Test HERMETIC: usa loopback:1 (rifiuto immediato, nessuna rete esterna).
"""
from __future__ import annotations

import pytest

from verimem.tools_extra import _read_image_to_b64_and_media_type


def test_read_image_blocks_ssrf_loopback():
    with pytest.raises(Exception) as ei:
        _read_image_to_b64_and_media_type("http://127.0.0.1:1/x.png")
    msg = str(ei.value).lower()
    assert "ssrf" in msg or "blocked" in msg, f"loopback non bloccato come SSRF: {ei.value!r}"


def test_read_image_blocks_cloud_metadata():
    with pytest.raises(Exception) as ei:
        _read_image_to_b64_and_media_type("http://169.254.169.254/latest/meta-data/")
    msg = str(ei.value).lower()
    assert "ssrf" in msg or "blocked" in msg, f"metadata host non bloccato: {ei.value!r}"
