"""Text chunking for the document RAG tier (roadmap #1: whole-file ingest).

Splits long documents — legal cases, books, code, imported conversations — into
overlapping chunks that are small enough to embed and retrieve, while keeping
each chunk a COHERENT unit (it prefers to break at a paragraph gap, then a
sentence end, then a word boundary, never mid-word when avoidable).

Provenance is the point. Every ``Chunk`` carries the ``(start, end)`` character
offsets into the ORIGINAL text, and the invariant ``text[start:end] == chunk.text``
holds exactly — so a retrieved chunk can cite precisely where it came from. This
is the provenance moat (source-anchored recall) applied to documents: not just
"here is a passage" but "here is the passage, at these offsets".

No embedding here — this is pure text segmentation. The document tier
(``documents.py``) stores raw snapshots; the semantic layer embeds these chunks.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Natural break points, strongest first: a blank line (paragraph), then a
# sentence terminator followed by whitespace.
_PARA_BREAK = re.compile(r"\n\s*\n")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Chunk:
    """A provenance-anchored slice of a document.

    Invariant: ``original_text[start:end] == text``.
    """

    text: str
    index: int
    start: int
    end: int


def _find_boundary(text: str, start: int, end: int) -> int:
    """Return the best absolute offset to end a chunk within ``[start, end)``.

    Prefers a paragraph break, then a sentence break, then the last word
    boundary. Returns ``end`` unchanged when no earlier boundary is found (a
    hard cut — e.g. a long token with no whitespace).
    """
    window = text[start:end]
    para = list(_PARA_BREAK.finditer(window))
    if para:
        return start + para[-1].end()
    sent = list(_SENTENCE_BREAK.finditer(window))
    if sent:
        return start + sent[-1].end()
    space = window.rfind(" ")
    if space > 0:
        return start + space + 1
    return end


def chunk_text(
    text: str,
    *,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[Chunk]:
    """Split ``text`` into overlapping, boundary-aware, provenance-anchored chunks.

    Args:
        text: the source document text.
        chunk_size: maximum characters per chunk (hard upper bound).
        overlap: characters of overlap between consecutive chunks, so a fact that
            straddles a boundary is not lost. Must be < ``chunk_size``.

    Returns:
        A list of ``Chunk`` in document order. Empty/whitespace-only input yields
        ``[]``. The concatenation of the chunks (minus overlap) reconstructs the
        text, and ``text[c.start:c.end] == c.text`` for every chunk.
    """
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")
    if not text or not text.strip():
        return []

    n = len(text)
    chunks: list[Chunk] = []
    pos = 0
    idx = 0
    while pos < n:
        end = min(pos + chunk_size, n)
        if end < n:
            boundary = _find_boundary(text, pos, end)
            if boundary > pos:
                end = boundary
        piece = text[pos:end]
        if piece.strip():
            chunks.append(Chunk(text=piece, index=idx, start=pos, end=end))
            idx += 1
        if end >= n:
            break
        # Advance with overlap, but always make forward progress (a degenerate
        # boundary must never stall the loop).
        nxt = end - overlap
        pos = nxt if nxt > pos else end
    return chunks


__all__ = ["Chunk", "chunk_text"]
