"""File -> text extraction for the document RAG tier (roadmap #1: whole-file ingest).

Turns a real file (legal case PDF, a book, a DOCX, an HTML export) into plain
text that ``chunking.chunk_text`` can segment and the semantic layer can embed.
Dispatch is by extension; optional parser deps are imported lazily so a missing
one degrades with a clear message, never an import-time crash for everyone.

    extract_text("case.pdf") -> str   ->   chunk_text(...)   ->   embed

Supported: .txt/.md/.rst (native), .pdf (PyMuPDF), .docx (python-docx),
.html/.htm (BeautifulSoup). Others raise a clear ValueError.
"""
from __future__ import annotations

from pathlib import Path

_NATIVE = {".txt", ".md", ".text", ".rst", ".log", ""}


def extract_text(path: str | Path) -> str:
    """Extract plain text from ``path``, dispatched by file extension.

    Raises ``FileNotFoundError`` if the path does not exist, ``ValueError`` for
    an unsupported extension, and ``RuntimeError`` if a needed parser library is
    not installed.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    ext = p.suffix.lower()
    if ext in _NATIVE:
        return p.read_text(encoding="utf-8", errors="replace")
    if ext == ".pdf":
        return _extract_pdf(p)
    if ext == ".docx":
        return _extract_docx(p)
    if ext in (".html", ".htm"):
        return _extract_html(p)
    raise ValueError(f"unsupported file type {ext!r} for {p.name}")


def _extract_pdf(p: Path) -> str:
    try:
        import fitz  # PyMuPDF
    except ImportError as e:  # pragma: no cover - env-dependent
        raise RuntimeError("PDF extraction needs PyMuPDF (pip install pymupdf)") from e
    doc = fitz.open(str(p))
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def _extract_docx(p: Path) -> str:
    try:
        import docx
    except ImportError as e:  # pragma: no cover - env-dependent
        raise RuntimeError("DOCX extraction needs python-docx (pip install python-docx)") from e
    d = docx.Document(str(p))
    return "\n".join(par.text for par in d.paragraphs)


def _extract_html(p: Path) -> str:
    try:
        from bs4 import BeautifulSoup
    except ImportError as e:  # pragma: no cover - env-dependent
        raise RuntimeError("HTML extraction needs beautifulsoup4") from e
    soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="replace"), "html.parser")
    return soup.get_text(separator="\n")


__all__ = ["extract_text"]
