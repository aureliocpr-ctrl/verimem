"""Auto-confirmation on write, wired into store() (ENGRAM_SOURCE_AUTO_CONFIRM).

Two distinct cited sources restating the SAME proposition on a topic corroborate each
other through the real write path — the source-trust consistency channel rises. Default
OFF. The independence-aware acceptance that defends a write-majority cartel is validated
end-to-end on the real gate in benchmark/independence_validation.py --product.
"""
from __future__ import annotations

from engram.client import Memory
from engram.source_trust import reset_book_cache

_PARIS = "The capital is Paris."


def test_two_cited_sources_corroborate_through_write_path(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_AUTO_CONFIRM", "1")
    monkeypatch.setenv("ENGRAM_SOURCE_INDEPENDENCE", "1")
    reset_book_cache()
    mem = Memory(tmp_path / "m.db")
    mem.add(_PARIS, topic="geo/fr", verified_by=["source-doc:atlas:1"])
    mem.add(_PARIS, topic="geo/fr", verified_by=["source-doc:almanac:1"])
    assert mem.consistency_trust("atlas") > 0.5
    assert mem.consistency_trust("almanac") > 0.5


def test_off_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("ENGRAM_SOURCE_AUTO_CONFIRM", raising=False)
    reset_book_cache()
    mem = Memory(tmp_path / "m.db")
    mem.add(_PARIS, topic="geo/fr", verified_by=["source-doc:atlas:1"])
    mem.add(_PARIS, topic="geo/fr", verified_by=["source-doc:almanac:1"])
    assert mem.consistency_trust("atlas") == 0.5      # gated -> book untouched


def test_single_cited_source_does_not_self_confirm(tmp_path, monkeypatch):
    monkeypatch.setenv("ENGRAM_SOURCE_AUTO_CONFIRM", "1")
    monkeypatch.setenv("ENGRAM_SOURCE_INDEPENDENCE", "1")
    reset_book_cache()
    mem = Memory(tmp_path / "m.db")
    # one source restating itself twice is not corroboration
    mem.add(_PARIS, topic="geo/fr", verified_by=["source-doc:atlas:1"])
    mem.add(_PARIS, topic="geo/fr", verified_by=["source-doc:atlas:2"])
    assert mem.consistency_trust("atlas") == 0.5
