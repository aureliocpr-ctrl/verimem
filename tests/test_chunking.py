"""Text chunking for the document RAG tier (roadmap #1: whole-file ingest).

The critical invariant is PROVENANCE: text[chunk.start:chunk.end] must equal
chunk.text exactly, so a retrieved chunk can cite precisely where it came from —
the provenance moat applied to documents (legal cases, books, code).
"""
from __future__ import annotations

import pytest

from verimem.chunking import Chunk, chunk_text


def test_short_text_is_a_single_chunk() -> None:
    t = "Short document, under the size limit."
    cs = chunk_text(t, chunk_size=1000, overlap=100)
    assert len(cs) == 1
    assert cs[0].text == t
    assert cs[0].start == 0 and cs[0].end == len(t)
    assert cs[0].index == 0


def test_empty_or_whitespace_yields_no_chunks() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n\n  \t ") == []


def test_offsets_reconstruct_original_exactly() -> None:
    # PROVENANCE INVARIANT: the offsets must slice back to the exact chunk text.
    t = ("Alpha sentence one. Sentence two is here.\n\n"
         "Beta paragraph carries more words for the splitter to chew on. ") * 30
    cs = chunk_text(t, chunk_size=220, overlap=40)
    assert len(cs) > 1
    for c in cs:
        assert t[c.start:c.end] == c.text, "start/end must reconstruct chunk exactly"


def test_chunks_cover_and_overlap() -> None:
    t = "word " * 500  # 2500 chars, natural word boundaries
    cs = chunk_text(t, chunk_size=300, overlap=50)
    assert len(cs) > 1
    assert cs[0].start == 0
    assert cs[-1].end == len(t)
    for a, b in zip(cs, cs[1:], strict=False):
        assert b.start < a.end, "consecutive chunks must overlap"
        assert b.index == a.index + 1


def test_chunk_size_respected_even_without_boundaries() -> None:
    t = "x" * 5000  # no spaces/sentences -> hard cut at chunk_size
    cs = chunk_text(t, chunk_size=500, overlap=50)
    assert len(cs) > 1
    for c in cs:
        assert len(c.text) <= 500


def test_overlap_must_be_smaller_than_size() -> None:
    with pytest.raises(ValueError):
        chunk_text("abcdef", chunk_size=100, overlap=100)


def test_prefers_natural_boundary_over_midword_cut() -> None:
    # Two paragraphs; a small chunk_size must break at the paragraph gap,
    # not in the middle of a word.
    t = "First short para." + "\n\n" + "Second paragraph with several more words here."
    cs = chunk_text(t, chunk_size=25, overlap=5)
    # a mid-word cut = chunk's last char is a letter AND the next char is a
    # letter. Ending on whitespace/punctuation is a clean boundary.
    for c in cs:
        if c.end < len(t) and c.text[-1].isalpha() and t[c.end].isalpha():
            pytest.fail(f"cut mid-word near {c.end}: ...{c.text[-8:]}|{t[c.end]}")
