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

# Natural break points, strongest first: a heading, then a blank line
# (paragraph), then a sentence terminator followed by whitespace.
#
# L'INTESTAZIONE E' STATA AGGIUNTA IL 2026-08-04 e chiude un difetto che si
# vedeva solo da fuori. Usando il prodotto come un ricercatore che
# indicizza il proprio paper, ha chiesto «qual e' la conducibilita' idraulica
# del sottobacino 27?» e ha ricevuto, con score 0.889 e citazione a offset
# esatti, IL VALORE DEL SOTTOBACINO 26. Sul suo documento: 30 chunk, e ZERO
# che cominciassero all'inizio di una sezione.
#
# La gerarchia dei confini c'era gia' — paragrafo, frase, parola — e mancava
# il livello piu' alto. Un titolo non e' un paragrafo un po' piu' forte: e' il
# punto in cui cambia il SOGGETTO, e un chunk che se lo lascia dentro mescola
# la coda di una sezione con la testa della successiva. Su un documento a
# struttura ripetitiva (paper con tabelle, pazienti, campioni, siti, lotti,
# articoli di legge) l'errore e' silenzioso e di UNA UNITA': non «non
# trovato», che si vede, ma «trovato il vicino», che non si vede.
_HEADING = re.compile(r"^[ \t]{0,3}(?:#{1,6}[ \t]|\d+[.)][ \t]+[A-Z])", re.M)
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


def _find_boundary(text: str, start: int, end: int) -> tuple[int, bool]:
    """Return ``(offset, is_heading)``: where to end a chunk in ``[start, end)``.

    Prefers a HEADING, then a paragraph break, then a sentence break, then the
    last word boundary. Returns ``end`` unchanged when no earlier boundary is
    found (a hard cut — e.g. a long token with no whitespace).

    L'INTESTAZIONE SI TAGLIA PRIMA, GLI ALTRI DOPO, e la differenza è tutto il
    punto. Per un paragrafo si prende l'ULTIMO confine della finestra
    (``para[-1]``), cioè si riempie il chunk il più possibile; se si trattasse
    un titolo allo stesso modo, verrebbe inglobato e il chunk conterrebbe la
    coda di una sezione più la testa della successiva. Un titolo va invece
    preso come punto di ROTTURA: si chiude il chunk *davanti* a lui, così la
    sezione nuova comincia un chunk nuovo.

    E si prende la PRIMA intestazione della finestra, non l'ultima: prendendo
    l'ultima, un chunk che ne contiene tre le terrebbe tutte tranne una — che
    è esattamente il mescolamento da evitare. Con la prima, ogni chunk contiene
    al più una sezione.

    ``h.start() > 0`` esclude l'intestazione che apre la finestra: tagliarci
    davanti darebbe un chunk vuoto e il loop non avanzerebbe.
    """
    window = text[start:end]
    head = [h for h in _HEADING.finditer(window) if h.start() > 0]
    if head:
        return start + head[0].start(), True
    para = list(_PARA_BREAK.finditer(window))
    if para:
        return start + para[-1].end(), False
    sent = list(_SENTENCE_BREAK.finditer(window))
    if sent:
        return start + sent[-1].end(), False
    space = window.rfind(" ")
    if space > 0:
        return start + space + 1, False
    return end, False


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
        su_intestazione = False
        if end < n:
            boundary, su_intestazione = _find_boundary(text, pos, end)
            if boundary > pos:
                end = boundary
            else:
                su_intestazione = False
        piece = text[pos:end]
        if piece.strip():
            chunks.append(Chunk(text=piece, index=idx, start=pos, end=end))
            idx += 1
        if end >= n:
            break
        # Advance with overlap, but always make forward progress (a degenerate
        # boundary must never stall the loop).
        #
        # SU UN TITOLO NON SI TORNA INDIETRO (2026-08-04). L'overlap esiste
        # perche' un fatto a cavallo del taglio non vada perso, e su un taglio
        # arbitrario e' giusto. Ma un titolo non e' un taglio arbitrario: e' il
        # confine di un'unita' di senso, e nessun fatto lo attraversa.
        # Riportando indietro il punto di partenza di `overlap` caratteri, il
        # chunk successivo ricomincerebbe DENTRO la sezione precedente — cioe'
        # si rifarebbe da soli il disallineamento appena evitato. Trovato
        # facendo la cura: i chunk restavano sfasati anche dopo aver aggiunto
        # il confine giusto.
        nxt = end if su_intestazione else end - overlap
        pos = nxt if nxt > pos else end
    return chunks


__all__ = ["Chunk", "chunk_text"]
